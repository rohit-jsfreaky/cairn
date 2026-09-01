"""Every way Cairn can act on an element.

This is a registry, not a chain of `if` statements. Each action carries what it needs, what
its value means, and how to prove it landed — so the MCP tool description, the replay
dispatcher and the postcondition defaults all read from one place. Adding an action means
adding one entry.

Full audit of what is here and what was deliberately left out: `package/BROWSING.md`.

Two rules hold throughout:

- **Nothing here resolves an element.** An action is handed an already-resolved Playwright
  locator. That keeps this file independent of how targets are found, which matters because
  the snapshot layer is being replaced underneath it.
- **An action that changes nothing is not recorded.** `highlight` draws a box for a human
  watching; replaying it later would be meaningless. Those are marked `recordable=False`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Locator as PWLocator
from playwright.sync_api import Page

# What a step should check afterwards when the caller does not say. "observed" means work it
# out from what actually changed on the page, which is what `distill` already does.
OBSERVED = "observed"

DEFAULT_WAIT_SECONDS = 0.3
MS_PER_SECOND = 1000
SCREENS_PER_SCROLL = 0.9  # just under a full screen, so nothing scrolls past unseen
SCREENS_TO_REACH_END = 40  # far enough to hit either end of any ordinary page
FALLBACK_VIEWPORT_HEIGHT = 720

# Resolves once the browser has drawn twice, which is when a scroll has been committed.
_TWO_FRAMES = "new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))"


@dataclass(frozen=True)
class ActionSpec:
    """One thing Cairn can do, and everything the rest of the code needs to know about it."""

    name: str
    summary: str
    needs_target: bool = True
    value_means: str | None = None
    needs_second_target: bool = False
    recordable: bool = True
    verifies_with: str = OBSERVED

    def describe(self) -> str:
        """One line for the tool description an AI reads."""
        parts = [f"{self.name} — {self.summary}"]
        if self.value_means:
            parts.append(f"value = {self.value_means}")
        if self.needs_second_target:
            parts.append("needs `to` as well as `ref`")
        if not self.needs_target:
            parts.append("no ref needed")
        return "; ".join(parts)


# ---------------------------------------------------------------- the registry

ACTIONS: dict[str, ActionSpec] = {
    "click": ActionSpec(
        "click",
        "click a link, button or anything clickable",
    ),
    "double_click": ActionSpec(
        "double_click",
        "double click, for grids and file lists that open on two clicks",
    ),
    "hover": ActionSpec(
        "hover",
        "move the pointer over something, for menus that only open on hover",
    ),
    "fill": ActionSpec(
        "fill",
        "put text into a field, replacing whatever is there",
        value_means="the text to put in",
        verifies_with="value_is",
    ),
    "type": ActionSpec(
        "type",
        "type one key at a time. Use instead of fill for search and autocomplete boxes, "
        "which ignore a value that appears all at once because they listen for keystrokes",
        value_means="the text to type",
        verifies_with="value_is",
    ),
    "clear": ActionSpec(
        "clear",
        "empty a field. Do this before typing into a field that already has something in "
        "it, or the two values run together",
        verifies_with="value_is",
    ),
    "press": ActionSpec(
        "press",
        "press a key while the element is focused",
        value_means='a key such as "Enter", "Escape", "Tab", or a combination like "Control+A"',
    ),
    "check": ActionSpec(
        "check",
        "tick a checkbox or radio button. Does nothing if it is already ticked",
        verifies_with="checked_is",
    ),
    "uncheck": ActionSpec(
        "uncheck",
        "untick a checkbox. Does nothing if it is already unticked",
        verifies_with="checked_is",
    ),
    "set_checked": ActionSpec(
        "set_checked",
        "tick or untick to match a value, whatever state it started in",
        value_means='"true" or "false"',
        verifies_with="checked_is",
    ),
    "select": ActionSpec(
        "select",
        "choose from a dropdown",
        value_means=(
            'the option: plain text matches by value, "label:September" matches by what is '
            'shown, "index:2" matches by position, and commas pick several at once'
        ),
        verifies_with="value_is",
    ),
    "upload": ActionSpec(
        "upload",
        "attach a file to a file input",
        value_means="the full path to the file, or several paths separated by commas",
    ),
    "scroll_to": ActionSpec(
        "scroll_to",
        "scroll until something is on screen, for long or lazily loaded lists",
        verifies_with="element_visible",
    ),
    "drag": ActionSpec(
        "drag",
        "drag one element onto another, for reordering and kanban boards",
        needs_second_target=True,
    ),
    "focus": ActionSpec(
        "focus",
        "put the cursor in a field without typing. Some forms only validate on focus",
    ),
    "blur": ActionSpec(
        "blur",
        "take the cursor out of a field, which is what makes many forms validate",
    ),
    "tap": ActionSpec(
        "tap",
        "a touch tap rather than a mouse click. Only works when the browser is emulating "
        "a touch device",
    ),
    "select_text": ActionSpec(
        "select_text",
        "select the text inside an element, usually so the next thing typed replaces it",
    ),
    "dispatch_event": ActionSpec(
        "dispatch_event",
        "fire a raw DOM event. LAST RESORT — it skips the checks that make a normal click "
        "trustworthy, so it can act on something invisible or not ready. Try click, hover "
        "or press first",
        value_means='the event name, such as "click" or "change"',
    ),
    "highlight": ActionSpec(
        "highlight",
        "draw a box around an element so a watching human can see it. Changes nothing",
        recordable=False,
    ),
    "hide_highlight": ActionSpec(
        "hide_highlight",
        "remove the box drawn by highlight. Changes nothing",
        needs_target=False,
        recordable=False,
    ),
    # ---- page level: these act on the whole page, so they take no element -------
    "goto": ActionSpec(
        "goto",
        "open a web address",
        needs_target=False,
        value_means="the full url",
        verifies_with="url_contains",
    ),
    "back": ActionSpec(
        "back",
        "go back one page in history",
        needs_target=False,
        verifies_with="url_contains",
    ),
    "forward": ActionSpec(
        "forward",
        "go forward one page in history",
        needs_target=False,
        verifies_with="url_contains",
    ),
    "reload": ActionSpec(
        "reload",
        "reload the current page",
        needs_target=False,
    ),
    "scroll": ActionSpec(
        "scroll",
        "scroll the page itself, for feeds that load more as you go",
        needs_target=False,
        value_means='"down", "up", "top", "bottom", or a number of pixels',
    ),
    "wait": ActionSpec(
        "wait",
        "wait a fixed number of seconds. Prefer wait_for — a fixed wait is either too "
        "short and flaky or too long and slow",
        needs_target=False,
        value_means="seconds",
    ),
}


class UnknownAction(ValueError):
    """Asked for an action that does not exist."""


class ActionNeedsMore(ValueError):
    """The action was understood but something it requires was not given."""


def spec_for(action: str) -> ActionSpec:
    try:
        return ACTIONS[action]
    except KeyError:
        known = ", ".join(sorted(ACTIONS))
        raise UnknownAction(f"no action called {action!r}. Known actions: {known}") from None


def catalogue() -> str:
    """The whole action list as one block of text, for the MCP tool description.

    Generated rather than written by hand, so a new action can never be missing from the
    description an AI reads.
    """
    return "\n".join(f"  {spec.describe()}" for spec in ACTIONS.values())


# ------------------------------------------------------------------ performing


def perform(
    action: str,
    *,
    page: Page,
    target: PWLocator | None = None,
    value: str | None = None,
    second: PWLocator | None = None,
) -> None:
    """Do one thing.

    The element, when one is needed, is already resolved — this function never searches for
    it. Playwright's own actionability checks (visible, stable, enabled, able to receive
    events) run inside each call below, which is why Cairn does not reimplement waiting.
    """
    spec = spec_for(action)

    if spec.needs_target and target is None:
        raise ActionNeedsMore(f"{action} needs an element to act on")
    if spec.needs_second_target and second is None:
        raise ActionNeedsMore(f"{action} needs a second element, given as `to`")
    if spec.value_means and value is None and action not in _VALUE_OPTIONAL:
        raise ActionNeedsMore(f"{action} needs a value: {spec.value_means}")

    _RUNNERS[action](page, target, value, second)


# Each runner has the same shape so the registry can call them without special cases.
# `_T` is the resolved element, absent for page-level actions.
_T = PWLocator


def _click(page: Page, t: _T, value: str | None, second: _T | None) -> None:
    t.click()


def _double_click(page: Page, t: _T, value: str | None, second: _T | None) -> None:
    t.dblclick()


def _hover(page: Page, t: _T, value: str | None, second: _T | None) -> None:
    t.hover()


def _fill(page: Page, t: _T, value: str | None, second: _T | None) -> None:
    t.fill(value or "")


def _type(page: Page, t: _T, value: str | None, second: _T | None) -> None:
    # One key at a time. Search and autocomplete boxes listen for keystrokes and ignore a
    # value that simply appears, which is exactly what `fill` does.
    t.press_sequentially(value or "")


def _clear(page: Page, t: _T, value: str | None, second: _T | None) -> None:
    t.clear()


def _press(page: Page, t: _T, value: str | None, second: _T | None) -> None:
    t.press(value or "Enter")


def _check(page: Page, t: _T, value: str | None, second: _T | None) -> None:
    t.check()


def _uncheck(page: Page, t: _T, value: str | None, second: _T | None) -> None:
    t.uncheck()


def _set_checked(page: Page, t: _T, value: str | None, second: _T | None) -> None:
    t.set_checked(_as_bool(value))


def _select(page: Page, t: _T, value: str | None, second: _T | None) -> None:
    t.select_option(**_select_options(value or ""))


def _upload(page: Page, t: _T, value: str | None, second: _T | None) -> None:
    paths = [Path(part.strip()) for part in (value or "").split(",") if part.strip()]
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise ActionNeedsMore(f"no file at {', '.join(missing)}")
    t.set_input_files(paths)


def _scroll_to(page: Page, t: _T, value: str | None, second: _T | None) -> None:
    t.scroll_into_view_if_needed()


def _drag(page: Page, t: _T, value: str | None, second: _T | None) -> None:
    assert second is not None  # guaranteed by perform()
    t.drag_to(second)


def _focus(page: Page, t: _T, value: str | None, second: _T | None) -> None:
    t.focus()


def _blur(page: Page, t: _T, value: str | None, second: _T | None) -> None:
    t.blur()


def _tap(page: Page, t: _T, value: str | None, second: _T | None) -> None:
    try:
        t.tap()
    except PlaywrightError as refused:
        if "hasTouch" not in str(refused):
            raise
        raise ActionNeedsMore(
            "tap needs a touch device. Start the browser with touch=True, or use click "
            "instead — on most sites click does the same thing."
        ) from refused


def _select_text(page: Page, t: _T, value: str | None, second: _T | None) -> None:
    t.select_text()


def _dispatch_event(page: Page, t: _T, value: str | None, second: _T | None) -> None:
    t.dispatch_event(value or "click")


def _highlight(page: Page, t: _T, value: str | None, second: _T | None) -> None:
    t.highlight()


def _hide_highlight(page: Page, t: _T | None, value: str | None, second: _T | None) -> None:
    page.hide_highlight()


def _goto(page: Page, t: _T | None, value: str | None, second: _T | None) -> None:
    page.goto(value or "")


def _back(page: Page, t: _T | None, value: str | None, second: _T | None) -> None:
    page.go_back()


def _forward(page: Page, t: _T | None, value: str | None, second: _T | None) -> None:
    page.go_forward()


def _reload(page: Page, t: _T | None, value: str | None, second: _T | None) -> None:
    page.reload()


def _scroll(page: Page, t: _T | None, value: str | None, second: _T | None) -> None:
    size = page.viewport_size or {"width": 1280, "height": FALLBACK_VIEWPORT_HEIGHT}
    # A wheel event only moves whatever is under the pointer, and the pointer starts in the
    # top-left corner. Centring it also means the wheel lands on the main panel rather than
    # on some narrow strip at the edge of the page.
    page.mouse.move(size["width"] / 2, size["height"] / 2)
    page.mouse.wheel(0, _scroll_amount(page, value))
    _wait_for_scroll(page)


def _wait_for_scroll(page: Page) -> None:
    """Let the browser actually apply the scroll before anything reads the page.

    `mouse.wheel` returns before the scroll is committed, so reading the position straight
    afterwards gives the position from *before* the scroll. On an infinite feed that means
    scrolling and then immediately reading the same rows again, forever.

    Two animation frames is enough for the commit, and unlike waiting for the position to
    change it is still correct at the very bottom of a page, where scrolling moves nothing.
    """
    page.evaluate(_TWO_FRAMES)


def _wait(page: Page, t: _T | None, value: str | None, second: _T | None) -> None:
    page.wait_for_timeout(float(value or DEFAULT_WAIT_SECONDS) * MS_PER_SECOND)


_RUNNERS: dict[str, Any] = {
    "click": _click,
    "double_click": _double_click,
    "hover": _hover,
    "fill": _fill,
    "type": _type,
    "clear": _clear,
    "press": _press,
    "check": _check,
    "uncheck": _uncheck,
    "set_checked": _set_checked,
    "select": _select,
    "upload": _upload,
    "scroll_to": _scroll_to,
    "drag": _drag,
    "focus": _focus,
    "blur": _blur,
    "tap": _tap,
    "select_text": _select_text,
    "dispatch_event": _dispatch_event,
    "highlight": _highlight,
    "hide_highlight": _hide_highlight,
    "goto": _goto,
    "back": _back,
    "forward": _forward,
    "reload": _reload,
    "scroll": _scroll,
    "wait": _wait,
}

# These have a sensible default, so a missing value is not an error.
_VALUE_OPTIONAL = {"press", "dispatch_event", "scroll", "wait"}


# -------------------------------------------------------------------- helpers


def _scroll_amount(page: Page, value: str | None) -> float:
    """Turn a written scroll instruction into a number of pixels."""
    height = page.viewport_size["height"] if page.viewport_size else FALLBACK_VIEWPORT_HEIGHT
    word = (value or "down").strip().lower()
    if word in {"down", ""}:
        return height * SCREENS_PER_SCROLL
    if word == "up":
        return -height * SCREENS_PER_SCROLL
    if word == "bottom":
        return height * SCREENS_TO_REACH_END
    if word == "top":
        return -height * SCREENS_TO_REACH_END
    try:
        return float(word)
    except ValueError:
        raise ActionNeedsMore(
            f'cannot scroll by {value!r} — use "down", "up", "top", "bottom" or a number'
        ) from None


def _as_bool(value: str | None) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "on", "checked"}


def _select_options(value: str) -> dict[str, Any]:
    """Turn one written value into keyword arguments for `select_option`.

    A dropdown option can be picked by the value behind it, by the words a person actually
    sees, or by position. Sites change the hidden value far more often than the visible
    label, so `label:September` is the more durable way to record a choice.

    Playwright's Python API takes these as separate keyword arguments. The list-of-dicts
    form works only in JavaScript, and here it fails without saying why.
    """
    values: list[str] = []
    labels: list[str] = []
    indexes: list[int] = []

    for part in (piece.strip() for piece in value.split(",")):
        if not part:
            continue
        if part.startswith("label:"):
            labels.append(part[len("label:") :])
        elif part.startswith("index:"):
            indexes.append(int(part[len("index:") :]))
        elif part.startswith("value:"):
            values.append(part[len("value:") :])
        else:
            values.append(part)

    chosen: dict[str, Any] = {}
    if values:
        chosen["value"] = values
    if labels:
        chosen["label"] = labels
    if indexes:
        chosen["index"] = indexes
    return chosen


def sanity_check() -> None:
    """Every action in the registry has a runner, and every runner is in the registry.

    Called by a test. Without it, adding an action to one and not the other fails only when
    somebody happens to use it.
    """
    missing_runner = sorted(set(ACTIONS) - set(_RUNNERS))
    missing_spec = sorted(set(_RUNNERS) - set(ACTIONS))
    if missing_runner or missing_spec:
        raise AssertionError(
            f"action registry out of step — no runner for {missing_runner}, "
            f"no spec for {missing_spec}"
        )
