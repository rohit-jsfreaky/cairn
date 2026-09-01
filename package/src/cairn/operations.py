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

import time
from dataclasses import dataclass, field
from typing import Any, Literal

from .browser import Browser, Element, Snapshot, domain_of
from .events import Emitter, MemoryWrite
from .models import Playbook, Postcondition, utc_now
from .store import CairnStore

Action = Literal["goto", "click", "fill", "select", "press", "wait"]

# A download event arrives slightly after the click returns. Poll for it rather than
# guessing one fixed delay: too short is flaky, too long makes every other step slow.
DOWNLOAD_GRACE_MS = 2000
DOWNLOAD_POLL_MS = 50


@dataclass
class TraceEntry:
    """One recorded move, with enough context for `distill` to write a step from it."""

    intent: str
    action: Action
    value: str | None = None
    element: Element | None = None
    secret: str | None = None
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
        self.tool_calls = 0

    # ------------------------------------------------------------------ look

    def look(self) -> dict[str, Any]:
        """Return the page as a short list of controls.

        Deliberately small. The whole cost Cairn removes is a host AI reading pages, so
        handing back raw HTML here would defeat the point of the project.
        """
        self.tool_calls += 1
        self._snapshot = self.browser.snapshot()
        return self._snapshot.to_dict()

    # ------------------------------------------------------------------- act

    def act(
        self,
        intent: str,
        action: Action,
        *,
        ref: str | None = None,
        value: str | None = None,
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

        element = self._perform(action, ref=ref, value=value)

        # A password is remembered as "there is a password here", never as the password.
        secret = secret_name(element) if action == "fill" else None

        # The download event can arrive after the click has already returned, so catch
        # any straggler before recording what happened.
        self.browser.flush_downloads()

        text_after = self.browser.text()
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
        )
        self.trace.append(entry)
        self._snapshot = None

        return {
            "ok": True,
            "intent": intent,
            "url": entry.url_after,
            "navigated": entry.navigated,
            "download": entry.download,
            "saved_to": self.browser.last_download_path,
            "secret": secret,
            "note": (
                f"This was a {secret} field, so Cairn did not remember what was typed. "
                f"On a later run it will look the value up on this machine."
                if secret
                else None
            ),
        }

    def _perform(self, action: Action, *, ref: str | None, value: str | None) -> Element | None:
        if action == "goto":
            if not value:
                raise ActionFailed("goto needs a url")
            self.browser.goto(value)
            return None

        if action == "wait":
            time.sleep(float(value or 0.3))
            return None

        element = self._element_for(ref)
        target = self.browser.page.locator(element.css).first

        if action == "click":
            self.browser.click(target)
        elif action == "fill":
            self.browser.fill(target, value or "")
        elif action == "select":
            self.browser.select(target, value or "")
        elif action == "press":
            self.browser.press(target, value or "Enter")
        else:
            raise ActionFailed(f"unknown action: {action}")
        return element

    def _element_for(self, ref: str | None) -> Element:
        if ref is None:
            raise ActionFailed("this action needs a ref from look()")
        if self._snapshot is None:
            self._snapshot = self.browser.snapshot()
        element = self._snapshot.by_ref(ref)
        if element is None:
            raise ActionFailed(f"no element {ref} on this page — call look() again")
        return element

    # ---------------------------------------------------------------- verify

    def verify(self, kind: str, value: str) -> bool:
        """Check a postcondition. Same code the warm path uses, so what we record is
        exactly what will later be enforced."""
        self.tool_calls += 1
        return check_postcondition(self.browser, Postcondition(kind=kind, value=value))  # type: ignore[arg-type]

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


def secret_name(element: Element | None) -> str | None:
    """Is this a field whose value must never be written down?"""
    if element is None:
        return None
    if (element.type or "").lower() == "password":
        return (element.name or "password").strip().lower().replace(" ", "_") or "password"
    return None


def check_postcondition(browser: Browser, expected: Postcondition) -> bool:
    """Did the page actually end up where it should have?

    This is the line between Cairn and a macro recorder, so it lives in one place and
    both the cold and warm paths call it.
    """
    if expected.kind == "url_contains":
        return expected.value in browser.page.url
    if expected.kind == "text_present":
        return expected.value.lower() in browser.text().lower()
    if expected.kind == "text_gone":
        return expected.value.lower() not in browser.text().lower()
    if expected.kind == "element_present":
        return browser.page.locator(expected.value).count() > 0
    if expected.kind == "download":
        # Wait only as long as it actually takes. Returns the moment the file arrives.
        waited = 0
        while browser.last_download is None and waited < DOWNLOAD_GRACE_MS:
            browser.page.wait_for_timeout(DOWNLOAD_POLL_MS)
            waited += DOWNLOAD_POLL_MS
        browser.flush_downloads()
        return browser.last_download is not None
    return False


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
