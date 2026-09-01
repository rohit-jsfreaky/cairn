"""The hands. Playwright, wrapped so the rest of Cairn never touches it directly.

Three things here matter more than the rest:

1. **A snapshot is a short list of controls, not the page HTML.** Handing a host AI 200 kB
   of markup is exactly the cost Cairn exists to remove. `snapshot()` returns the handful
   of things you can actually act on, with four different ways to find each one.

2. **There are two browser modes, and the difference is deliberate.**

   *Profile mode* (the default in real use) keeps one Chrome profile at
   `~/.cairn/browser-profile`, so you stay signed in between runs exactly as you do in
   your own browser. Some logins — Google, Microsoft, anything with a one-time code —
   cannot be automated at all, and should not be: you sign in once by hand and the session
   is kept.

   *Clean mode* (`profile=None`) throws the browser away every time. Tests use it, and so
   does any demo where the login itself must be shown happening rather than assumed.

3. **Being signed in is not the same as remembering.** The profile holds who you are. Sibyl
   memory holds what Cairn knows about a site. Delete the memory and Cairn is still logged
   in, but has no idea what to click and has to explore again — the deletion test is
   untouched by any of this.
"""

from __future__ import annotations

import json
from contextlib import suppress
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Locator as PWLocator
from playwright.sync_api import Page, sync_playwright
from playwright.sync_api import TimeoutError as PWTimeout

from . import snapshot as aria
from .models import Locator
from .snapshot import Element, Snapshot
from .waits import DEFAULT_WAIT_MS, LOCATOR_WAIT_MS

# Nothing is granted unless a caller asks for it. A site that wants notifications or
# your location puts a prompt over the page, and a prompt over the page blocks the run.
# Denying is silent, and silence is what an unattended agent needs.
NO_PERMISSIONS: list[str] = []

# Granting geolocation without also setting a position makes the site wait forever for a
# fix that never arrives, so the two always travel together.
GEOLOCATION = "geolocation"

# What to do with a confirm box. Accepting is the default because Playwright's own
# default — dismissing — silently cancels saves and submits.
ACCEPT = "accept"
DISMISS = "dismiss"

# Which tab to continue in.
LATEST_TAB = "latest"
MAIN_TAB = "main"

# How much visible page text one look() may return. Enough to read a heading, an amount
# and an error message; not so much that a caller pays for the whole page every time.
MAX_TEXT_CHARS = 1200

# A fixed window for every run. Site layout depends on width - below a breakpoint the
# nav collapses into a hamburger button, so a trail recorded at one size cannot be
# replayed at another. Whatever this is, it must not change between runs.
VIEWPORT = {"width": 1280, "height": 800}

# Where downloaded files land unless a caller says otherwise. A default matters: a task
# like "download this month's invoice" is not done if the file only existed inside a
# temporary browser profile that gets deleted when the context closes.
DEFAULT_DOWNLOADS = Path.home() / ".cairn" / "downloads"

# One shared Chrome profile for every site, so signing in to one does not sign you out of
# another. Shared rather than per-site on purpose: Google and friends check that the
# browser looks like the same browser each visit, and a throwaway profile gets challenged
# every single time.
DEFAULT_PROFILE = Path.home() / ".cairn" / "browser-profile"

# A page that wants a password, or an address that reads like a sign-in, means the session
# has run out. Used only after a step has already failed, so a login page we navigated to
# on purpose is never mistaken for one.
_SIGNED_OUT_HINTS = ("/login", "/signin", "/sign-in", "/sign_in", "/auth", "/sso", "/oauth")

# Reads the durable descriptors for ONE element, the ones a locator is built from.
#
# Only ever run for an element actually being acted on. Reading these for every element on
# every look would cost a round trip per element, and most elements are never touched.
_DESCRIBE_JS = """
(el) => {
  const testIdOf = (node) => {
    const names = ['data-testid', 'data-test-id', 'data-test', 'data-qa', 'data-cy'];
    for (const name of names) {
      const found = node.getAttribute(name);
      if (found) return name + '=' + found;
    }
    return null;
  };

  const labelOf = (node) => {
    const doc = node.ownerDocument;
    const forId = node.id && doc.querySelector(`label[for="${CSS.escape(node.id)}"]`);
    if (forId) return (forId.innerText || '').trim();
    const wrapping = node.closest('label');
    if (wrapping) return (wrapping.innerText || '').trim();
    const aria = node.getAttribute('aria-label');
    return aria ? aria.trim() : null;
  };

  const cssOf = (node) => {
    const doc = node.ownerDocument;
    if (node.id && doc.querySelectorAll(`#${CSS.escape(node.id)}`).length === 1) {
      return `#${CSS.escape(node.id)}`;
    }
    if (node.name && node.tagName === 'INPUT') {
      const sel = `${node.tagName.toLowerCase()}[name="${node.name}"]`;
      if (doc.querySelectorAll(sel).length === 1) return sel;
    }
    const parts = [];
    let walker = node;
    while (walker && walker.nodeType === 1 && parts.length < 5) {
      const tag = walker.tagName.toLowerCase();
      if (tag === 'html' || tag === 'body') break;
      const parent = walker.parentElement;
      if (!parent) break;
      const siblings = Array.from(parent.children).filter(c => c.tagName === walker.tagName);
      const index = siblings.indexOf(walker) + 1;
      parts.unshift(siblings.length > 1 ? `${tag}:nth-of-type(${index})` : tag);
      walker = parent;
    }
    return parts.join(' > ');
  };

  const type = (el.getAttribute('type') || '').toLowerCase();
  let value = null;
  if ('value' in el && typeof el.value === 'string') {
    // Never report what is typed in a password box, not even back to the caller.
    value = type === 'password' ? (el.value ? '(filled)' : '') : el.value.slice(0, 120);
  }

  return {
    tag: el.tagName.toLowerCase(),
    css: cssOf(el),
    type: el.getAttribute('type'),
    href: el.getAttribute('href'),
    test_id: testIdOf(el),
    label: labelOf(el),
    placeholder: el.getAttribute('placeholder'),
    title: el.getAttribute('title'),
    alt: el.getAttribute('alt'),
    value: value,
  };
}
"""


def domain_of(url: str) -> str:
    """The memory key for a site. Port included, so a local demo does not collide."""
    parsed = urlparse(url)
    return parsed.netloc or url


class NoSuchTab(RuntimeError):
    """Asked to continue in a tab that is not open."""


class ProfileInUse(RuntimeError):
    """Something else already has Cairn's browser profile open."""


class Browser:
    """A single browsing session. Always a fresh context, never a reused profile."""

    def __init__(
        self,
        *,
        headless: bool = True,
        downloads: Path | None = None,
        profile: Path | None = None,
        touch: bool = False,
        permissions: list[str] | None = None,
        geolocation: tuple[float, float] | None = None,
        timeout_ms: int = DEFAULT_WAIT_MS,
    ):
        """`profile=None` means a clean browser every time. Pass a path to stay signed in.

        `touch=True` makes this a touch device, which is what the `tap` action needs. It is
        off by default on purpose: some sites serve a different, mobile layout the moment
        they detect touch, and that would change what every other trail sees.

        `permissions` is empty unless asked for. A site that wants notifications or your
        location puts a prompt over the page, and that prompt blocks everything behind it.

        `geolocation` is a (latitude, longitude) pair, for dashboards that show different
        numbers by region. Passing one grants the geolocation permission automatically —
        granting it without a position makes a site wait forever for a fix that never
        comes.

        `timeout_ms` is the one place patience is set. It applies to every Playwright call
        that does not name its own, so there is a single number to change when a site is
        slow rather than a scattering of them.
        """
        self._headless = headless
        self._touch = touch
        self._timeout_ms = timeout_ms
        self._geolocation = geolocation
        self._permissions = list(permissions) if permissions else list(NO_PERMISSIONS)
        if geolocation is not None and GEOLOCATION not in self._permissions:
            self._permissions.append(GEOLOCATION)
        self._downloads = Path(downloads) if downloads is not None else DEFAULT_DOWNLOADS
        self._profile = Path(profile) if profile is not None else None
        self._playwright = None
        self._browser = None
        self._context = None
        self._page: Page | None = None
        self.last_download: str | None = None
        self.last_download_path: str | None = None
        self.saved_files: list[str] = []
        self._pending_downloads: list[Any] = []
        self.dialog_policy: str = ACCEPT
        """What to do with a confirm box when one appears.

        Accepting by default is the deliberate choice. Playwright's own default is to
        dismiss every dialog, and dismissing silently cancels a save or a submit — the run
        appears to succeed while nothing happened. Whatever is chosen, the message and the
        choice are both recorded, and replay stops if the message has changed."""
        self.last_dialog: dict[str, str] | None = None
        self.tabs: list[Page] = []
        self._watched: list[Page] = []
        self._overlays: list[str] = []

    # ------------------------------------------------------------- lifecycle

    def start(self) -> Browser:
        self._playwright = sync_playwright().start()

        if self._profile is not None:
            self._profile.mkdir(parents=True, exist_ok=True)
            # Chrome allows one process per profile. A clear message beats a raw crash.
            try:
                self._context = self._playwright.chromium.launch_persistent_context(
                    str(self._profile),
                    headless=self._headless,
                    accept_downloads=True,
                    viewport=VIEWPORT,
                    has_touch=self._touch,
                    **self._context_options(),
                )
            except Exception as clash:
                self._playwright.stop()
                self._playwright = None
                raise ProfileInUse(
                    "Cairn's browser profile is already open in another window. Close the "
                    "sign-in window (or the other Cairn run) and try again."
                ) from clash
            self._browser = None
            pages = self._context.pages
            self._page = pages[0] if pages else self._context.new_page()
        else:
            self._browser = self._playwright.chromium.launch(headless=self._headless)
            self._context = self._browser.new_context(
                accept_downloads=True,
                viewport=VIEWPORT,
                has_touch=self._touch,
                **self._context_options(),
            )
            self._page = self._context.new_page()

        # One place to control patience, rather than a timeout argument scattered across
        # every call site.
        self._context.set_default_timeout(self._timeout_ms)
        self._context.set_default_navigation_timeout(self._timeout_ms)

        self.tabs = [self._page]
        self._watch(self._page)
        # A tab opened by the site — "open in new tab", and most sign-in-with-Google
        # flows — arrives here. It is never switched to automatically: which tab a trail
        # continues in is a decision to record, not to guess.
        self._context.on("page", self._remember_tab)
        return self

    def _context_options(self) -> dict[str, Any]:
        """The context settings that are the same however the browser was launched."""
        options: dict[str, Any] = {"permissions": self._permissions}
        if self._geolocation is not None:
            latitude, longitude = self._geolocation
            options["geolocation"] = {"latitude": latitude, "longitude": longitude}
        return options

    @property
    def permissions(self) -> list[str]:
        """What this browser has been allowed to do. Empty unless a caller asked."""
        return list(self._permissions)

    @property
    def timeout_ms(self) -> int:
        """How long any single Playwright call may take before giving up."""
        return self._timeout_ms

    def set_timeout(self, timeout_ms: int) -> None:
        """Change how patient the browser is, for a site that is genuinely slow."""
        self._timeout_ms = timeout_ms
        if self._context is not None:
            self._context.set_default_timeout(timeout_ms)
            self._context.set_default_navigation_timeout(timeout_ms)

    def new_tab(self, url: str | None = None) -> Page:
        """Open a tab of our own and continue in it.

        Unlike a tab the site opens, this one was asked for, so switching to it is not a
        guess.
        """
        if self._context is None:
            raise RuntimeError("the browser is not running")
        page = self._context.new_page()
        self._remember_tab(page)
        self._page = page
        if url:
            self.goto(url)
        return page

    def _watch(self, page: Page) -> None:
        """Attach the listeners every tab needs, including tabs the site opens itself.

        Once per page and never twice. A second download listener queues the same file
        twice, and saving an already-saved download fails — so the file silently never
        reaches disk.
        """
        if page in self._watched:
            return
        self._watched.append(page)
        page.on("download", self._remember_download)
        page.on("dialog", self._answer_dialog)

    def _remember_tab(self, page: Page) -> None:
        if page not in self.tabs:
            self.tabs.append(page)
        self._watch(page)

    def _answer_dialog(self, dialog: Any) -> None:
        """Answer a confirm box, and write down both the words and the answer.

        An unanswered dialog blocks every later step: the browser simply stops. So one of
        these must always run — doing nothing is not a neutral option.
        """
        self.last_dialog = {
            "type": dialog.type,
            "message": dialog.message,
            "choice": self.dialog_policy,
        }
        if self.dialog_policy == ACCEPT:
            dialog.accept()
        else:
            dialog.dismiss()

    # ------------------------------------------------------------------ tabs

    def switch_tab(self, which: str = LATEST_TAB) -> Page:
        """Continue in another tab. `latest`, `main`, or a number from 0."""
        self.tabs = [page for page in self.tabs if not page.is_closed()]
        if not self.tabs:
            raise NoSuchTab("every tab has been closed")

        if which == LATEST_TAB:
            chosen = self.tabs[-1]
        elif which == MAIN_TAB:
            chosen = self.tabs[0]
        else:
            try:
                chosen = self.tabs[int(which)]
            except (ValueError, IndexError):
                raise NoSuchTab(
                    f"no tab {which!r}. There are {len(self.tabs)} open, numbered from 0"
                ) from None

        self._page = chosen
        chosen.bring_to_front()
        return chosen

    # -------------------------------------------------------------- overlays

    def dismiss_when_seen(self, selector: str) -> None:
        """Clear an overlay automatically, whenever it gets in the way.

        Cookie banners and "rate us" pop-ups do not appear at a fixed point in a flow —
        they appear whenever the site feels like it, which is why they break recorded
        trails so reliably. Playwright can watch for one and clear it the moment it blocks
        an action, so it never becomes a step at all.

        Registered against the site, not the step, and remembered in site knowledge.
        """
        if selector in self._overlays:
            return
        self._overlays.append(selector)
        target = self.page.locator(selector)
        self.page.add_locator_handler(target, lambda overlay: overlay.click(), times=None)

    @property
    def overlays(self) -> list[str]:
        """The overlays currently being watched for."""
        return list(self._overlays)

    def stop(self) -> None:
        for closer in (self._context, self._browser):
            if closer is not None:
                closer.close()
        if self._playwright is not None:
            self._playwright.stop()
        self._playwright = self._browser = self._context = self._page = None
        self.tabs = []
        self._watched = []
        self._overlays = []

    def __enter__(self) -> Browser:
        return self.start()

    def __exit__(self, *_exc) -> None:
        self.stop()

    @property
    def page(self) -> Page:
        if self._page is None:
            raise RuntimeError("browser not started — call start() or use it as a context manager")
        return self._page

    def _remember_download(self, download) -> None:
        """Queue the download. Do NOT save it here.

        This runs inside Playwright's event callback, and calling `save_as` from there
        while another sync call is still in flight fails with "Download.save_as:
        canceled". So the file is only queued, and `flush_downloads` writes it once the
        action that triggered it has finished.
        """
        self.last_download = download.suggested_filename
        self._pending_downloads.append(download)

    def flush_downloads(self) -> None:
        """Write any queued downloads to disk.

        Playwright throws its temporary copy away when the context closes, so a download
        that is never saved is a download that never happened as far as the user is
        concerned. Called after every action that can trigger one.
        """
        while self._pending_downloads:
            download = self._pending_downloads.pop(0)
            self._downloads.mkdir(parents=True, exist_ok=True)
            destination = self._downloads / download.suggested_filename
            download.save_as(destination)
            self.last_download_path = str(destination)
            self.saved_files.append(str(destination))

    # ----------------------------------------------------------------- doing

    def goto(self, url: str) -> None:
        self.page.goto(url, wait_until="domcontentloaded")

    def snapshot(self) -> Snapshot:
        """The page as a short list of things you can act on.

        Playwright's own accessibility snapshot, which sees through shadow roots and into
        iframes, and reports a pointer cursor — which is how a `div` acting as a button
        gets found at all.
        """
        raw = self.page.locator("body").aria_snapshot(mode="ai")
        return Snapshot(
            url=self.page.url,
            title=self.page.title(),
            elements=aria.parse(raw, frames=self._frame_selectors(raw)),
            text=self.readable_text(),
        )

    def _frame_selectors(self, raw: str) -> dict[str, str]:
        """Map each frame number to a selector for its iframe.

        An element inside an iframe cannot be found later by a plain selector, because
        `page.locator` does not look inside frames. The locator has to name the frame too,
        so the iframe itself needs a durable selector of its own.
        """
        selectors: dict[str, str] = {}
        for number, ref in enumerate(aria.iframe_refs(raw), start=1):
            described = self._describe_ref(ref)
            if described and described.get("css"):
                selectors[str(number)] = described["css"]
        return selectors

    def _describe_ref(self, ref: str) -> dict[str, Any] | None:
        try:
            return self.page.locator(f"aria-ref={ref}").evaluate(_DESCRIBE_JS)
        except PlaywrightError:
            return None

    def describe(self, element: Element) -> Element:
        """Fill in the durable descriptors for one element, by reading the page.

        Done here rather than during `snapshot` because it costs a round trip each, and
        only the elements actually acted on ever need them. A ref is good for one snapshot;
        these are what get written down.
        """
        described = self._describe_ref(element.ref)
        if not described:
            return element
        for key, value in described.items():
            if value is not None and hasattr(element, key):
                setattr(element, key, value)
        return element

    def readable_text(self, limit: int = MAX_TEXT_CHARS) -> str:
        """What the page says, tidied and cut short.

        Blank lines collapsed, and cut at a line break rather than mid-word so the result
        reads like text instead of a truncated blob.
        """
        newline = "\n"
        lines = [line.strip() for line in self.text().splitlines()]
        tidy = newline.join(line for line in lines if line)
        if len(tidy) <= limit:
            return tidy

        cut = tidy[:limit]
        edge = cut.rfind(newline)
        trimmed = cut[:edge] if edge > limit // 2 else cut
        return trimmed + newline + "…"

    def resolve(self, locator: Locator, *, timeout_ms: int = LOCATOR_WAIT_MS) -> PWLocator | None:
        """Turn a stored locator back into something on the page, or None if it misses.

        Returning None rather than raising is deliberate: a miss is normal and expected
        information here, not an error. It is how drift gets noticed.
        """
        try:
            found = self._to_playwright(locator)
            if found is None:
                return None
            # "visible", not "attached". Attached only means the element exists in the
            # page — which is already true while it is sliding into place and cannot yet
            # receive a click. Visible also waits for it to stop moving.
            found.first.wait_for(state="visible", timeout=timeout_ms)
            return found.first
        except (PWTimeout, Exception):
            return None

    def _to_playwright(self, locator: Locator) -> PWLocator | None:
        """Turn one stored locator back into a Playwright locator, refinements applied."""
        base = self._base_locator(locator)
        if base is None:
            return None
        if locator.has_text:
            base = base.filter(has_text=locator.has_text)
        if locator.nth is not None:
            base = base.nth(locator.nth)
        return base

    def _base_locator(self, locator: Locator) -> PWLocator | None:
        # An element inside an iframe is invisible to `page.locator`, so a locator that
        # named a frame has to be resolved through that frame.
        page: Any = self.page.frame_locator(locator.frame) if locator.frame else self.page
        if locator.kind == "css":
            return page.locator(locator.value)
        if locator.kind == "text":
            return page.get_by_text(locator.value, exact=True)
        if locator.kind == "label":
            return page.get_by_label(locator.value, exact=True)
        if locator.kind == "placeholder":
            return page.get_by_placeholder(locator.value, exact=True)
        if locator.kind == "title":
            return page.get_by_title(locator.value, exact=True)
        if locator.kind == "alt":
            return page.get_by_alt_text(locator.value, exact=True)
        if locator.kind == "test_id":
            # Not `get_by_test_id`: that reads one globally configured attribute name, and
            # real sites use data-testid, data-test-id, data-test, data-qa and data-cy. The
            # name is stored with the value, so this matches whichever the site actually
            # uses without any global setting.
            name, _, wanted = locator.value.partition("=")
            if not wanted:
                return None
            return page.locator(f"[{name}={json.dumps(wanted)}]")
        if locator.kind == "role":
            role, _, name = locator.value.partition("|")
            if not name:
                return page.get_by_role(role)  # type: ignore[arg-type]
            return page.get_by_role(role, name=name, exact=True)  # type: ignore[arg-type]
        if locator.kind == "structural" and locator.value.startswith("href="):
            path = locator.value[len("href=") :].replace('"', "")
            # Exact path, optionally followed by a query string or fragment.
            return page.locator(f'[href="{path}"], [href^="{path}?"], [href^="{path}#"]')
        return None

    def locate(self, element: Element) -> PWLocator:
        """Turn a snapshot element into something Playwright can act on.

        `aria-ref` resolves through shadow roots and across frame boundaries on its own, so
        nothing here needs to know where the element lives. That is only true within the
        snapshot the ref came from — which is why acting always re-reads it, and why refs
        never reach memory.
        """
        return self.page.locator(f"aria-ref={element.ref}").first

    def settle(self) -> None:
        """Let the page catch up after an action.

        Runs after every action rather than after a chosen few. The old code waited only
        after `click` and `press`, so a `select` that navigated was never waited for and
        the next snapshot could be read from the page being replaced.
        """
        # Navigating away mid-wait is normal, not a failure. The next call re-reads
        # whatever page we landed on.
        with suppress(PlaywrightError):
            self.page.wait_for_load_state("domcontentloaded")
        self.flush_downloads()

    def looks_signed_out(self) -> bool:
        """Does this look like we were bounced back to a sign-in page?

        Only ever asked after a step has already failed. A site we deliberately opened at
        its login page must not be mistaken for an expired session.
        """
        address = self.page.url.lower()
        if any(hint in address for hint in _SIGNED_OUT_HINTS):
            return True
        try:
            return self.page.locator('input[type="password"]').count() > 0
        except Exception:
            return False

    def text(self) -> str:
        """Visible page text, used only for postcondition checks — never sent to a model."""
        try:
            return self.page.inner_text("body")
        except Exception:
            return ""
