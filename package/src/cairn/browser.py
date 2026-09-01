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

from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Locator as PWLocator
from playwright.sync_api import Page, sync_playwright
from playwright.sync_api import TimeoutError as PWTimeout

from .models import Locator

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

# Collects the controls worth remembering, with everything needed to build locators.
# Runs in the page, so one round trip returns the whole snapshot.
_COLLECT_JS = """
() => {
  const roleOf = (el) => {
    const explicit = el.getAttribute('role');
    if (explicit) return explicit;
    const tag = el.tagName.toLowerCase();
    if (tag === 'a') return el.hasAttribute('href') ? 'link' : 'generic';
    if (tag === 'button') return 'button';
    if (tag === 'select') return 'combobox';
    if (tag === 'textarea') return 'textbox';
    if (tag === 'input') {
      const type = (el.getAttribute('type') || 'text').toLowerCase();
      if (type === 'submit' || type === 'button') return 'button';
      if (type === 'checkbox') return 'checkbox';
      if (type === 'radio') return 'radio';
      return 'textbox';
    }
    return tag;
  };

  const nameOf = (el) => {
    const aria = el.getAttribute('aria-label');
    if (aria) return aria.trim();
    if (el.tagName === 'INPUT' && (el.type === 'submit' || el.type === 'button')) {
      return (el.value || '').trim();
    }
    const text = (el.innerText || '').trim();
    if (text) return text.replace(/\\s+/g, ' ').slice(0, 80);
    const labelled = el.id && document.querySelector(`label[for="${el.id}"]`);
    if (labelled) return (labelled.innerText || '').trim();
    return (el.getAttribute('placeholder') || el.getAttribute('title') || '').trim();
  };

  const cssOf = (el) => {
    if (el.id && document.querySelectorAll(`#${CSS.escape(el.id)}`).length === 1) {
      return `#${CSS.escape(el.id)}`;
    }
    if (el.name && el.tagName === 'INPUT') {
      const sel = `${el.tagName.toLowerCase()}[name="${el.name}"]`;
      if (document.querySelectorAll(sel).length === 1) return sel;
    }
    const parts = [];
    let node = el;
    while (node && node.nodeType === 1 && parts.length < 5) {
      const tag = node.tagName.toLowerCase();
      if (tag === 'html' || tag === 'body') break;
      const parent = node.parentElement;
      if (!parent) break;
      const siblings = Array.from(parent.children).filter(c => c.tagName === node.tagName);
      const index = siblings.indexOf(node) + 1;
      parts.unshift(siblings.length > 1 ? `${tag}:nth-of-type(${index})` : tag);
      node = parent;
    }
    return parts.join(' > ');
  };

  const visible = (el) => {
    const rect = el.getBoundingClientRect();
    if (rect.width === 0 && rect.height === 0) return false;
    const style = window.getComputedStyle(el);
    return style.visibility !== 'hidden' && style.display !== 'none';
  };

  const selector = 'a[href], button, input, select, textarea, [role="button"], [role="link"]';
  const out = [];
  document.querySelectorAll(selector).forEach((el, i) => {
    if (!visible(el)) return;
    const type = (el.getAttribute('type') || '').toLowerCase();
    const isSecret = type === 'password';
    let value = null;
    if ('value' in el && typeof el.value === 'string') {
      // Never report what is typed in a password box, not even back to the caller.
      value = isSecret ? (el.value ? '(filled)' : '') : el.value.slice(0, 120);
    }
    out.push({
      ref: 'e' + (out.length + 1),
      role: roleOf(el),
      name: nameOf(el),
      tag: el.tagName.toLowerCase(),
      css: cssOf(el),
      href: el.getAttribute('href'),
      type: el.getAttribute('type'),
      value: value,
    });
  });
  return out;
}
"""


@dataclass
class Element:
    """One control on the page, with every way we know to find it again."""

    ref: str
    role: str
    name: str
    tag: str
    css: str
    href: str | None = None
    type: str | None = None
    value: str | None = None
    """What the field currently holds. A page can arrive with fields already filled, and
    an AI that cannot see that will ask the user for something already on screen. Password
    boxes report "(filled)" rather than their contents."""

    def locators(self) -> list[Locator]:
        """Four ways to find this element, most durable first.

        The order is a claim about what survives a redesign: a link target usually
        outlives its label, and a label usually outlives its CSS id. Replay reorders
        these by measured confidence once they have a track record.
        """
        found: list[Locator] = []
        if self.href:
            found.append(Locator("structural", f"href={href_path(self.href)}"))
        if self.name:
            found.append(Locator("role", f"{self.role}|{self.name}"))
            found.append(Locator("text", self.name))
        if self.css:
            found.append(Locator("css", self.css))
        return found

    def to_dict(self) -> dict[str, str | None]:
        described: dict[str, str | None] = {
            "ref": self.ref,
            "role": self.role,
            "name": self.name,
            "css": self.css,
            "href": self.href,
        }
        if self.value:
            described["value"] = self.value
        return described


# How much visible page text one look() may return. Enough to read a heading, an amount
# or an error message; far too little to be a page dump. The whole point of the project is
# not paying to push pages through a model.
MAX_TEXT_CHARS = 1200


@dataclass
class Snapshot:
    """What the page looks like right now, small enough to hand to a model."""

    url: str
    title: str
    elements: list[Element] = field(default_factory=list)
    text: str = ""
    """A trimmed view of what the page says. Without this Cairn can click but never read,
    so "check the balance" or "what does the error say" would be impossible."""

    @property
    def domain(self) -> str:
        return domain_of(self.url)

    def by_ref(self, ref: str) -> Element | None:
        return next((e for e in self.elements if e.ref == ref), None)

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "text": self.text,
            "elements": [e.to_dict() for e in self.elements],
        }


def href_path(href: str) -> str:
    """The stable part of a link target: no query string, no fragment.

    Real sites hang session ids and tracking parameters off their links, and the demo site
    carries `?variant=`. Pinning a locator to the full href would make it miss for reasons
    that have nothing to do with the site changing. Same reasoning as postconditions
    matching on path rather than whole URL.
    """
    parsed = urlparse(href)
    return parsed.path or href


def domain_of(url: str) -> str:
    """The memory key for a site. Port included, so a local demo does not collide."""
    parsed = urlparse(url)
    return parsed.netloc or url


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
    ):
        """`profile=None` means a clean browser every time. Pass a path to stay signed in.

        `touch=True` makes this a touch device, which is what the `tap` action needs. It is
        off by default on purpose: some sites serve a different, mobile layout the moment
        they detect touch, and that would change what every other trail sees.
        """
        self._headless = headless
        self._touch = touch
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
                accept_downloads=True, viewport=VIEWPORT, has_touch=self._touch
            )
            self._page = self._context.new_page()

        self._page.on("download", self._remember_download)
        return self

    def stop(self) -> None:
        for closer in (self._context, self._browser):
            if closer is not None:
                closer.close()
        if self._playwright is not None:
            self._playwright.stop()
        self._playwright = self._browser = self._context = self._page = None

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
        """The page as a short list of things you can act on."""
        raw = self.page.evaluate(_COLLECT_JS)
        return Snapshot(
            url=self.page.url,
            title=self.page.title(),
            elements=[Element(**item) for item in raw],
            text=self.readable_text(),
        )

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

    def resolve(self, locator: Locator, *, timeout_ms: int = 1500) -> PWLocator | None:
        """Turn a stored locator back into something on the page, or None if it misses.

        Returning None rather than raising is deliberate: a miss is normal and expected
        information here, not an error. It is how drift gets noticed.
        """
        try:
            found = self._to_playwright(locator)
            if found is None:
                return None
            found.first.wait_for(state="attached", timeout=timeout_ms)
            return found.first
        except (PWTimeout, Exception):
            return None

    def _to_playwright(self, locator: Locator) -> PWLocator | None:
        page = self.page
        if locator.kind == "css":
            return page.locator(locator.value)
        if locator.kind == "text":
            return page.get_by_text(locator.value, exact=True)
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

        One seam, so that when stored locators learn to name their iframe (2.5e) only this
        method changes.
        """
        return self.page.locator(element.css).first

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
