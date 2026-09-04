"""The cold path: the three verbs a host AI drives.

    look()    what is on this page?
    act()     do one thing, and tell me what changed
    verify()  did the thing I expected actually happen?

There is no model in this file and there never will be. The AI calling these verbs is
somebody else's — normally the user's Claude Code, through `mcp/`. Cairn's job is to make
each call cheap to reason about and to write down what happened, so that the same task
never needs a model again.

`act()` records four independent descriptors of whatever it touched. That redundancy is
the entire reason a redesign is usually survivable: lose the CSS id, keep the link target.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic
from typing import Any, get_args

from playwright.sync_api import Error as PlaywrightError

from . import actions, reads
from . import snapshot as aria
from .browser import LATEST_TAB, Browser, Element, Snapshot, domain_of
from .events import Emitter, MemoryWrite
from .models import (
    Control,
    Locator,
    LocatorKind,
    PageMemory,
    Playbook,
    Postcondition,
    SiteKnowledge,
    SiteMap,
    link_target,
    page_path,
    utc_now,
)
from .store import CairnStore

# Anything in the registry. Kept as a plain str so adding an action never means editing
# a type in a second file — `actions.spec_for` is what actually rejects a bad name.
Action = str

# A download event arrives slightly after the click returns. Poll for it rather than
# guessing one fixed delay: too short is flaky, too long makes every other step slow.
DOWNLOAD_GRACE_MS = 2000
DOWNLOAD_POLL_MS = 50

# A remembered read is a step whose job is to produce a value.
READ_ACTION = "read"

# How long a page whose controls have not changed may go without being written again.
#
# The map is stored as one body per site, so every write re-serialises the whole thing and
# Sibyl re-indexes it for search. Doing that on every single look, during an exploration
# that looks at one page twenty times, would be real time spent to record nothing new. A
# page whose controls CHANGED is always written immediately — this only delays repeat
# sightings of a page that looks exactly as it did before.
MAP_TOUCH_SECONDS = 300

# Actions that put text into a field, and so might be putting a password into one.
_TEXT_ENTRY = {"fill", "type"}


@dataclass
class TraceEntry:
    """One recorded move, with enough context for `distill` to write a step from it."""

    intent: str
    action: Action
    value: str | None = None
    element: Element | None = None
    secret: str | None = None
    dialog: dict[str, str] | None = None
    """The confirm box this step answered, if one appeared: its words and the answer."""
    url_before: str = ""
    url_after: str = ""
    text_gained: str = ""
    download: str | None = None
    at: str = field(default_factory=utc_now)

    @property
    def navigated(self) -> bool:
        return self.url_before != self.url_after


class ActionFailed(RuntimeError):
    """The requested move could not be performed at all."""


class Session:
    """One cold run: a browser, a trace, and somewhere to save the result."""

    def __init__(
        self,
        browser: Browser,
        store: CairnStore | None = None,
        *,
        emitter: Emitter | None = None,
    ):
        self.browser = browser
        self.store = store
        self.events = emitter or Emitter()
        self.trace: list[TraceEntry] = []
        self._snapshot: Snapshot | None = None
        self.last_result: Any = None
        self.tool_calls = 0
        # The site map is read once per site and kept here, because it is one body for the
        # whole site and reloading it on every look would cost more than it saves.
        self._map: SiteMap | None = None
        self._map_written: float | None = None

    # ------------------------------------------------------------------ look

    def look(self) -> dict[str, Any]:
        """Return the page as a short list of controls.

        Deliberately small. The whole cost Cairn removes is a host AI reading pages, so
        handing back raw HTML here would defeat the point of the project.
        """
        self.tool_calls += 1
        self._snapshot = self.browser.snapshot()
        self.remember_page(self._snapshot)
        return self._snapshot.to_dict()

    # ------------------------------------------------------------------- act

    def act(
        self,
        intent: str,
        action: Action,
        *,
        ref: str | None = None,
        value: str | None = None,
        to: str | None = None,
    ) -> dict[str, Any]:
        """Do one thing and report what changed.

        `intent` is the caller's own words for why. It is stored verbatim, because when a
        step breaks a year later, "pick this month" is far more useful to whoever repairs
        it than a CSS selector is.
        """
        self.tool_calls += 1
        url_before = self.browser.page.url if action != "goto" else ""
        text_before = self.browser.text() if action != "goto" else ""
        self.browser.flush_downloads()
        self.browser.last_download = None
        self.browser.last_download_path = None
        self.browser.last_dialog = None
        self.last_result = None

        element = self._perform(action, ref=ref, value=value, to=to)

        # A password is remembered as "there is a password here", never as the password.
        secret = secret_name(element) if action in _TEXT_ENTRY else None

        text_after = self.browser.text()

        # Catch stragglers LAST, immediately before the entry is written. The download
        # event can arrive after the click returns, and reading the page takes long enough
        # for it to land there — so flushing any earlier queued the file without ever
        # saving it, and the step reported a download that was not on disk.
        self.browser.flush_downloads()

        entry = TraceEntry(
            intent=intent,
            action=action,
            value=None if secret else value,
            secret=secret,
            element=element,
            url_before=url_before,
            url_after=self.browser.page.url,
            text_gained=_first_new_line(text_before, text_after),
            download=self.browser.last_download,
            dialog=self.browser.last_dialog,
        )
        # An action that changes nothing is not a step. Replaying `highlight` would draw a
        # box for nobody and then have its postcondition checked anyway.
        if actions.spec_for(action).recordable:
            self.trace.append(entry)
        self._snapshot = None

        return {
            "ok": True,
            "intent": intent,
            "url": entry.url_after,
            "navigated": entry.navigated,
            "download": entry.download,
            "dialog": entry.dialog,
            # `evaluate` and `screenshot` answer something; every other action answers None.
            "result": self.last_result,
            "saved_to": self.browser.last_download_path,
            "secret": secret,
            "note": (
                f"This was a {secret} field, so Cairn did not remember what was typed. "
                f"On a later run it will look the value up on this machine."
                if secret
                else None
            ),
        }

    def _perform(
        self,
        action: Action,
        *,
        ref: str | None,
        value: str | None,
        to: str | None = None,
    ) -> Element | None:
        """Resolve the element, then hand the doing to the registry.

        Finding things is Cairn's job because a durable descriptor has to be recorded at the
        same moment. Performing is Playwright's job. This method is the seam between them.
        """
        try:
            spec = actions.spec_for(action)
        except actions.UnknownAction as unknown:
            raise ActionFailed(str(unknown)) from unknown

        if spec.session_handled:
            self._do_here(action, value)
            return None

        # Describe before acting. The durable descriptors have to be read while the
        # element is still on the page as it was — a click can navigate away, and then
        # there is nothing left to describe.
        element = self.browser.describe(self._element_for(ref)) if spec.needs_target else None
        # `evaluate` and `screenshot` may name an element without requiring one.
        if element is None and ref is not None:
            element = self.browser.describe(self._element_for(ref))
        target = self.browser.locate(element) if element else None
        second = self.browser.locate(self._element_for(to)) if spec.needs_second_target else None

        try:
            self.last_result = actions.perform(
                action, page=self.browser.page, target=target, value=value, second=second
            )
        except actions.ActionNeedsMore as incomplete:
            raise ActionFailed(str(incomplete)) from incomplete

        # Every action, not a chosen few. A download event can arrive after the click has
        # already returned, and a select can navigate just as a click can.
        self.browser.settle()
        return element

    def _do_here(self, action: str, value: str | None) -> None:
        """The few actions that need Cairn's own state rather than just the page."""
        if action == "switch_tab":
            self.browser.switch_tab(value or LATEST_TAB)
            self._snapshot = None
            return
        if action == "new_tab":
            self.browser.new_tab(value or None)
            self._snapshot = None
            return
        if action == "dismiss_when_seen":
            if not value:
                raise ActionFailed("dismiss_when_seen needs a CSS selector")
            self.remember_overlay(value)
            return
        if action == "restart_trail":
            self.trace.clear()
            return
        if action == "set_time":
            if not value:
                raise ActionFailed('set_time needs a date, such as "2026-09-15"')
            self.browser.set_time(value)
            return
        raise ActionFailed(f"{action} is marked session-handled but nothing handles it")

    def remember_overlay(self, selector: str) -> None:
        """Clear an overlay from now on, and write it down so later runs do the same.

        Site knowledge rather than a step, because an overlay appears whenever the site
        decides to — not at a fixed point in a flow. Pinning it to a step would be
        recording an accident.
        """
        self.browser.dismiss_when_seen(selector)
        domain = domain_of(self.browser.page.url)
        knowledge = self.store.load_site_knowledge(domain) or SiteKnowledge(domain=domain)
        self.store.save_site_knowledge(knowledge.merge(overlay=selector))
        self.events.emit(
            MemoryWrite(
                category="site_knowledge",
                name=domain,
                detail=f"dismiss {selector} whenever it appears",
            )
        )

    def remember_page(self, snapshot: Snapshot) -> None:
        """Write down the page that was just looked at, and what was on it.

        This is the cheapest memory in Cairn: the snapshot has already been built, already
        been paid for, and was about to be thrown away. Keeping it costs no extra page
        read, no extra second and no extra token.

        It exists because Cairn used to remember only the route it was asked for. Walking
        to the requests page to submit a request meant SEEING the list, the view button and
        the other six sidebar items — and binning all of it, so that "view a request"
        started blind the next day on a page Cairn had already stood on.

        Never allowed to break a run. Somebody's task failing because a note about it could
        not be filed would be a bad trade in every possible case.
        """
        if self.store is None:
            return
        try:
            self._record(snapshot)
        except Exception as ignored:  # noqa: BLE001 - a note must never fail the task
            self.events.emit(
                MemoryWrite(
                    category="site_map",
                    name=snapshot.url,
                    detail=f"not recorded: {ignored}",
                )
            )

    def _record(self, snapshot: Snapshot) -> None:
        """Merge one sighting into the site's map, and write it if it said anything new."""
        domain = domain_of(snapshot.url)
        if not domain:
            return
        if self._map is None or self._map.domain != domain:
            self._map = self.store.load_site_map(domain) or SiteMap(domain=domain)
            self._map_written = None

        controls = controls_in(snapshot)
        if not controls:
            # Nothing worth remembering, and recording it would be worse than saying
            # nothing: PyPI answered a bot challenge page under the real URL, and a map
            # that kept it would tell a later run this page has nothing on it.
            return

        path = page_path(snapshot.url)
        before = _fingerprint(self._map.page(path))
        self._map.merge(url=snapshot.url, title=snapshot.title, controls=controls)
        after = _fingerprint(self._map.page(path))

        if before == after and not self._due_a_write():
            return

        self.store.save_site_map(self._map)
        self._map_written = monotonic()
        self.events.emit(
            MemoryWrite(
                category="site_map",
                name=domain,
                detail=f"{path} — {len(self._map.page(path).controls)} controls",
            )
        )

    def _due_a_write(self) -> bool:
        """Has enough time passed to bother re-writing an unchanged page?"""
        if self._map_written is None:
            return True
        return (monotonic() - self._map_written) >= MAP_TOUCH_SECONDS

    def _element_for(self, ref: str | None) -> Element:
        """Find what the caller means, by ref or by CSS selector.

        A dashboard keeps its numbers in plain `div`s with no role, and those are correctly
        not offered as controls — so they have no ref, and a selector is the only handle
        there is. Refusing one meant the numbers could not be read at all.
        """
        if ref is None:
            raise ActionFailed("this action needs a ref from cairn_read, or a CSS selector")

        if aria.is_ref(ref):
            if self._snapshot is None:
                self._snapshot = self.browser.snapshot()
            element = self._snapshot.by_ref(ref)
            if element is None:
                raise ActionFailed(f"no element {ref} on this page — look at it again")
            return element

        remembered = _as_stored_locator(ref)
        if remembered is not None:
            return self._element_by_memory(ref, remembered)

        return self._element_by_selector(ref)

    def _element_by_memory(self, wording: str, locator: Locator) -> Element:
        """Find a control by what the MAP calls it, rather than by a ref from this page.

        The map stores what a trail stores — a role and a name, a link target — because
        those are what survive. Without this, the map could only ever be a hint: an AI
        would know a "Sign in" button was on this page and still have to read the whole
        page to get a ref before it could press it, which is the cost the map exists to
        remove.

        The resolver is the same one replay uses, so a control reached this way is reached
        exactly as a remembered step reaches it.
        """
        found = self.browser.resolve(locator)
        if found is None:
            raise ActionFailed(
                f"nothing on this page matches {wording!r}. The map says what was here "
                f"last time, so look at the page with cairn_read(kind='page') — it may "
                f"have moved."
            )
        # `describe` reads the real page a moment later and overwrites these with what is
        # actually there, so the saved step gets all nine durable locators exactly as a
        # snapshot element would. These are only what the element looks like in between.
        role, _, name = locator.value.partition("|") if locator.kind == "role" else ("", "", "")
        return Element(ref=wording, role=role, name=name or wording, found_by=locator)

    def _element_by_selector(self, selector: str) -> Element:
        """Build an element from a CSS selector the caller wrote themselves."""
        try:
            found = self.browser.page.locator(selector)
            if found.count() == 0:
                raise ActionFailed(f"nothing on this page matches {selector!r}")
        except PlaywrightError as bad:
            raise ActionFailed(f"{selector!r} is not a selector this page understands") from bad

        return Element(ref=selector, role="", name="", selector=selector, css=selector)

    # ------------------------------------------------------------------ read

    def read(
        self,
        kind: str,
        *,
        ref: str | None = None,
        attribute: str | None = None,
        remember: bool = False,
        intent: str = "",
    ) -> Any:
        """Look at the page without changing it.

        This is the half of the job that is not clicking. "How many unpaid invoices are
        there", "did the total change", "is the submit button live yet" — all of it is a
        read, and none of it was possible before.

        Exploring reads are not written down — most of them are just looking around, and
        replaying those would achieve nothing.

        `remember=True` makes this read a step. Use it for the read that IS the answer:
        the number the task was about. Without it a saved trail walks to a page and then
        stops, and the caller has to work the answer out again every single time.
        """
        self.tool_calls += 1
        try:
            spec = reads.spec_for(kind)
        except reads.UnknownRead as unknown:
            raise ActionFailed(str(unknown)) from unknown

        element = self.browser.describe(self._element_for(ref)) if spec.needs_target else None
        target = self.browser.locate(element) if element else None
        try:
            answer = reads.read(kind, page=self.browser.page, target=target, attribute=attribute)
        except reads.ReadNeedsMore as incomplete:
            raise ActionFailed(str(incomplete)) from incomplete

        if remember:
            self._remember_read(kind, intent, element, attribute)
        return answer

    def _remember_read(
        self, kind: str, intent: str, element: Element | None, attribute: str | None
    ) -> None:
        """Write a read into the trail, so replay hands back the answer."""
        self.trace.append(
            TraceEntry(
                intent=intent or f"read the {kind}",
                action=READ_ACTION,
                value=f"{kind}:{attribute}" if attribute else kind,
                element=element,
                url_before=self.browser.page.url,
                url_after=self.browser.page.url,
            )
        )

    # ---------------------------------------------------------------- verify

    def verify(self, kind: str, value: str, *, target: str | None = None) -> bool:
        """Check a postcondition. Same code the warm path uses, so what we record is
        exactly what will later be enforced."""
        self.tool_calls += 1
        return check_postcondition(
            self.browser,
            Postcondition(kind=kind, value=value, target=target),  # type: ignore[arg-type]
        )

    # ------------------------------------------------------------------ save

    def save(self, task: str, *, domain: str | None = None) -> Playbook:
        """Turn the trace into a playbook and write it to memory.

        This is the moment a slow, exploratory run becomes a fast one forever after.
        """
        from .distill import distill  # local import keeps the module graph acyclic

        if not self.trace:
            raise ActionFailed("nothing to save — the trace is empty")

        site = domain or domain_of(self.trace[0].url_after or self.browser.page.url)
        playbook = distill(self.trace, domain=site, task=task)

        if self.store is not None:
            self.store.save_playbook(playbook)
            self.events.emit(
                MemoryWrite(
                    category="playbook",
                    name=site,
                    detail=f"{len(playbook.steps)} steps from a cold run",
                )
            )
        return playbook


def _as_stored_locator(ref: str) -> Locator | None:
    """Is this a control named the way MEMORY names one, rather than a ref or a selector?

    `role=button|Sign in`, `test_id=data-qa=submit`, `href=/payments` — the same vocabulary
    a trail stores, so what the map hands back can be acted on directly.

    Anything else is left alone and treated as a CSS selector, as before. A real selector
    never begins with one of these words followed by `=`: `[data-x=1]` starts with `[`, and
    `a[href="/x"]` splits at `a[href`.
    """
    kind, separator, value = ref.partition("=")
    if not separator or not value:
        return None
    if kind == "href":
        # Stored as a `structural` locator, whose value keeps the `href=` in front of it.
        return Locator(kind="structural", value=ref)
    if kind in get_args(LocatorKind):
        return Locator(kind=kind, value=value)  # type: ignore[arg-type]
    return None


def controls_in(snapshot: Snapshot) -> list[Control]:
    """The controls on a page, in the form the map keeps them.

    Named controls only. Something with no name cannot be found by name later, so it would
    be bytes in the map that no future run could ever act on.

    No `ref` travels: a ref only means anything inside the snapshot that produced it.
    """
    seen = utc_now()
    return [
        Control(
            role=element.role,
            name=element.name,
            href=_where_it_goes(element.href),
            last_seen=seen,
        )
        for element in snapshot.elements
        if element.name
    ]


def _where_it_goes(href: str | None) -> str | None:
    """A link's destination, or nothing when it does not have one.

    A fragment-only target — `#main-content` on PostHog, `#start-of-content` on GitHub —
    is a jump inside the page a screen reader uses, not a place. The map is about places,
    so recording it would offer an AI somewhere to go that is where it already is.

    The CONTROL is still kept. A site can perfectly well hang `href="#"` on a real button,
    and dropping those would lose things worth clicking.
    """
    if not href or href.startswith("#"):
        return None
    return link_target(href)


def _fingerprint(page: PageMemory | None) -> tuple[str, tuple[tuple[str, str], ...]] | None:
    """What makes one sighting of a page different from another.

    The title and which controls are on it. Not their order, and not when they were seen —
    those move for reasons that do not mean the page has changed.
    """
    if page is None:
        return None
    return (page.title, tuple(sorted(control.identity for control in page.controls)))


def secret_name(element: Element | None) -> str | None:
    """Is this a field whose value must never be written down?"""
    if element is None:
        return None
    if (element.type or "").lower() == "password":
        return (element.name or "password").strip().lower().replace(" ", "_") or "password"
    return None


def check_postcondition(browser: Browser, expected: Postcondition) -> bool:
    """Did the page actually end up where it should have?

    This is the line between Cairn and a macro recorder — a recorder clicks and hopes.
    It lives in one place and both the cold and the warm path call it.

    Everything that looks at an element goes through `reads.read`, so a check can never
    disagree with the read an AI would have done by hand.
    """
    if expected.kind == "url_contains":
        return expected.value in browser.page.url
    if expected.kind == "text_present":
        return expected.value.lower() in browser.text().lower()
    if expected.kind == "text_gone":
        return expected.value.lower() not in browser.text().lower()
    if expected.kind == "element_present":
        return _count_matching(browser, expected) > 0
    if expected.kind == "element_gone":
        return _count_matching(browser, expected) == 0
    if expected.kind == "count_is":
        return _count_matching(browser, expected) == _as_number(expected.value)
    if expected.kind == "value_is":
        return _read_for(browser, expected, "value") == expected.value
    if expected.kind == "checked_is":
        return _read_for(browser, expected, "checked") is _as_bool(expected.value)
    if expected.kind == "attribute_is":
        name, _, wanted = expected.value.partition("=")
        found = _read_for(browser, expected, "attribute", attribute=name.strip())
        return (found or "") == wanted
    if expected.kind == "download":
        # Wait only as long as it actually takes. Returns the moment the file arrives.
        waited = 0
        while browser.last_download is None and waited < DOWNLOAD_GRACE_MS:
            browser.page.wait_for_timeout(DOWNLOAD_POLL_MS)
            waited += DOWNLOAD_POLL_MS
        browser.flush_downloads()
        return browser.last_download is not None
    return False


def _selector_of(expected: Postcondition) -> str:
    """Which element the check is about.

    The older kinds put their selector in `value` because they had nothing to compare it
    against. The newer ones need `value` for the expected answer, so they use `target`.
    Reading either way keeps every playbook already in memory loadable.
    """
    return expected.target or expected.value


def _count_matching(browser: Browser, expected: Postcondition) -> int:
    return reads.read(
        "count", page=browser.page, target=browser.page.locator(_selector_of(expected))
    )


def _read_for(
    browser: Browser, expected: Postcondition, kind: str, *, attribute: str | None = None
) -> Any:
    """Read one thing, treating a missing element as a failed check rather than a crash.

    A postcondition asks a yes/no question. If the element it names is gone, the honest
    answer is no — and that is drift, which the caller handles. It is not an error.
    """
    target = browser.page.locator(_selector_of(expected)).first
    try:
        return reads.read(kind, page=browser.page, target=target, attribute=attribute)
    except PlaywrightError:
        return None


def _as_number(value: str) -> int:
    try:
        return int(value.strip())
    except ValueError:
        return -1


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"true", "1", "yes", "on", "checked"}


def _first_new_line(before: str, after: str) -> str:
    """The first line of text that appeared, used to derive a postcondition.

    Cheap on purpose. A step only needs one honest signal that the page moved, not a diff.
    """
    seen = set(before.splitlines())
    for line in after.splitlines():
        stripped = line.strip()
        if stripped and stripped not in seen and len(stripped) > 3:
            return stripped[:80]
    return ""
