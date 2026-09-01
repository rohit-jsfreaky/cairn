"""Raw trace in, playbook out.

Distilling is where an exploratory run stops being a recording and becomes something that
can check itself. Two jobs:

1. **Give every step a postcondition**, derived from what actually changed when the step
   ran. No postcondition, no step — a step that cannot prove it landed is exactly the
   stale-cache behaviour this project exists to avoid.

2. **Keep several ways to find each element**, ranked. One selector is a single point of
   failure; four independent descriptors mean the usual cosmetic redesign costs nothing.
"""

from __future__ import annotations

from urllib.parse import urlparse

from .models import Locator, Playbook, Postcondition, Step
from .operations import TraceEntry


def distill(trace: list[TraceEntry], *, domain: str, task: str) -> Playbook:
    """Build a playbook from what a cold run actually did."""
    steps = [
        Step(
            index=position,
            intent=entry.intent,
            action=entry.action,
            value=entry.value,
            secret=entry.secret,
            postcondition=postcondition_for(entry),
            locators=locators_for(entry),
            dialog_message=(entry.dialog or {}).get("message"),
            dialog_choice=(entry.dialog or {}).get("choice"),
        )
        for position, entry in enumerate(trace, start=1)
    ]
    return Playbook(domain=domain, task=task, steps=steps)


def postcondition_for(entry: TraceEntry) -> Postcondition:
    """Pick the strongest honest signal that this step landed.

    Order matters. A download is unambiguous, a URL change is nearly so, and new text on
    the page is the weakest of the three — so we only fall back to text when nothing
    better is available.
    """
    if entry.download:
        return Postcondition("download", entry.download)

    if entry.navigated or entry.action == "goto":
        return Postcondition("url_contains", _path_of(entry.url_after))

    if entry.action == "fill" and entry.element is not None:
        # Nothing visibly changes when you type, so assert the field is still there.
        return Postcondition("element_present", entry.element.css)

    if entry.text_gained:
        return Postcondition("text_present", entry.text_gained)

    if entry.element is not None:
        return Postcondition("element_present", entry.element.css)

    return Postcondition("url_contains", _path_of(entry.url_after))


def locators_for(entry: TraceEntry) -> list[Locator]:
    """Every way we know to find this element again, most durable first.

    `goto` has no element, so it carries none — its URL is in the step itself.
    """
    if entry.element is None:
        return []
    return entry.element.locators()


def _path_of(url: str) -> str:
    """Match on the path, not the whole URL.

    The demo site carries `?variant=b` in the query string, and a real site will append
    session ids and tracking parameters. Pinning a step to a full URL would make it break
    for reasons that have nothing to do with the site changing.
    """
    parsed = urlparse(url)
    return parsed.path or url
