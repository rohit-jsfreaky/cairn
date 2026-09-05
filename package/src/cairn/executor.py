"""The warm path. Deterministic replay, with ZERO model calls.

This file is the product. Everything else supports it.

Replaying a step means: try the stored locators in confidence order, do the action, then
check the postcondition. Three outcomes:

  lands on the first locator   the common case, costs nothing
  lands on a later locator     the site changed cosmetically; we re-rank and move on,
                               still with no model involved
  every locator misses         a real break. Cairn stops, and hands back ONE step for the
                               host AI to work out. Not the whole task, one step.

`model_calls` is hard-coded to 0 in the metrics for a replay, because there is no code
path here that could make one. If that ever stops being true, this docstring is a lie and
the deletion gate is worthless.

THE WARM PATH NEVER READS THE COMMONS. Not once, not as a fallback, not to peek.
Replay may only follow a trail this agent holds in its own memory, because that is
exactly what `cairn forget` takes away — and if replay could reach into the shared
memory instead, `test_deletion_gate.py` would be proving nothing at all. Another
agent's trail has to be deliberately borrowed first, which copies it here, which is
what makes it forgettable.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from playwright.sync_api import Error as PlaywrightError

from . import actions, reads
from .browser import ACCEPT, Browser
from .events import (
    DriftDetected,
    Emitter,
    MemoryRead,
    MemoryWrite,
    RepairNeeded,
    RepairSaved,
    RunFinished,
    RunStarted,
    StepFailed,
    StepPassed,
    StepStarted,
)
from .models import (
    Locator,
    Playbook,
    Postcondition,
    RunMetrics,
    SiteMap,
    Step,
    href_path,
    page_path,
)
from .operations import READ_ACTION, check_postcondition, controls_in
from .secrets import MissingSecret
from .secrets import resolve as resolve_secret
from .store import CairnStore

# A step is considered past saving when this share of the trail is already broken.
STALE_SHARE = 0.5

# How long to let the site finish moving after a trail's LAST action before saying the run
# is done. Spent only by trails that end by pressing something — a trail ending in a read
# has nothing in flight — and only in full by a page that never stops calling home.
SETTLE_AFTER_LAST_STEP_MS = 4000


# Actions that put text into a field, so the value may be a secret held on this machine
# rather than in the trail.
_TEXT_ENTRY = {"fill", "type"}


@dataclass
class RepairRequest:
    """Everything a host AI needs to fix one step, and nothing more.

    This is deliberately small. Handing back the whole page would put us right back to
    paying page-reading costs on every run.
    """

    domain: str
    step_index: int
    intent: str
    action: str
    tried: list[str] = field(default_factory=list)
    url: str = ""
    candidates: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "step_index": self.step_index,
            "intent": self.intent,
            "action": self.action,
            "tried": self.tried,
            "url": self.url,
            "candidates": self.candidates,
        }


@dataclass
class ReplayResult:
    ok: bool
    metrics: RunMetrics
    repair: RepairRequest | None = None
    reason: str = ""
    saved_files: list[str] = field(default_factory=list)
    """Files this run actually wrote to disk. A "download the invoice" task is not done
    until there is a real file, so replay reports paths rather than just filenames."""

    answers: dict[str, Any] = field(default_factory=dict)
    """What the remembered reads said, keyed by the intent they were recorded under.

    This is what makes a warm run *answer* rather than merely arrive. A trail for "how many
    open issues" that navigates to the page and stops is worth almost nothing — the caller
    still has to read the number itself, which was the whole cost we set out to remove."""

    stale: bool = False
    """The trail is past repairing — the site was rebuilt, not tweaked."""

    needs_login: bool = False
    """We were bounced to a sign-in page. Nothing is wrong with the trail; the session
    simply ran out and a person has to sign in again."""

    wrong_place: bool = False
    """The trail is fine; the page it starts from is not the page we are on.

    Deliberately NOT `needs_repair`. Replaying a sign-in while already signed in lands on
    the dashboard, where none of the controls is the one the step wants — and a repair
    offered there would bind a working step to whatever happened to be lying around."""

    blocked: bool = False
    """A human check — a captcha — stood in the way. Deliberately NOT `needs_repair`:
    there is nothing to repair, and nothing an AI can do about it either. Reporting it as
    drift would mark good locators dead for a page the trail never actually reached."""

    site_facts: list[str] = field(default_factory=list)
    """What is still known about the site after a stale trail is thrown away. This is why
    relearning is cheaper than a first visit."""

    @property
    def needs_repair(self) -> bool:
        return self.repair is not None


class NoTrailError(RuntimeError):
    """There is nothing in memory for this site.

    Raised after `cairn forget`. This is the deletion gate doing its job: with the memory
    gone there is no fast path left, and Cairn says so instead of quietly improvising.
    """


class NeedsTask(NoTrailError):
    """The site is remembered, but the caller did not say which of its tasks it wants.

    Deliberately NOT the same as `NoTrailError`. "Which one?" and "never been here" are
    opposite situations that demand opposite responses, and reporting the second when the
    first was true made a host AI re-explore a site it already knew — overwriting what was
    there. Subclassing keeps old handlers working while letting new ones tell them apart.
    """

    def __init__(self, message: str, *, tasks: list[str]):
        super().__init__(message)
        self.tasks = tasks


def _said_nothing(step: Step) -> str:
    """Why an empty answer is reported as a broken step rather than a quiet success."""
    return (
        f"{step.intent!r} used to answer and came back empty. The element is still there, "
        f"so nothing looks broken — but the thing this step exists to read is gone or has "
        f"moved to another element on the page."
    )


def _same_page(here: str, recorded: str) -> bool:
    """Two addresses that mean the same page.

    Ids are generalised away, so `/invoices/2026-09` and `/invoices/2026-10` are one page,
    and a trailing slash is not a different place — a site that answers both
    `/admin/sign-in` and `/admin/sign-in/` has not moved anything.
    """
    return page_path(here).rstrip("/") == page_path(recorded).rstrip("/")


def _redirected_there(landed: str, asked_for: str) -> bool:
    """Did we arrive, allowing for the site rewriting the address on the way?

    Real sites canonicalise constantly: MDN answers /Web/API/fetch with
    /Web/API/Window/fetch, others add a locale, a trailing slash or a www. The path we
    asked for is then nowhere in the URL we landed on, and a strict path check calls a
    perfectly good page a failure — while naming a `goto` step as the thing to repair,
    which cannot be repaired, because a goto has no control to point at.

    Being on the host we asked for is the honest signal that navigation worked. If the
    page is actually wrong, the very next step fails on the thing it cannot find, which is
    a far more useful place to be told.
    """
    if not asked_for:
        return False
    return bool(urlparse(landed).netloc) and urlparse(landed).netloc == urlparse(asked_for).netloc


class Executor:
    """Replays a remembered trail. Reads memory, writes back what it learned."""

    def __init__(
        self,
        store: CairnStore,
        browser: Browser,
        *,
        emitter: Emitter | None = None,
        profile: str | None = None,
    ):
        self.store = store
        self.browser = browser
        self.events = emitter or Emitter()
        # Which signed-in identity this replay is. Only secrets need it: one domain can
        # have a customer, a vendor and an admin sign-in, each with its own password.
        self.profile = profile

    _domain: str = ""

    def run(
        self, domain: str, *, task: str | None = None, start_url: str | None = None
    ) -> ReplayResult:
        """Walk the remembered trail for one task on one site.

        `start_url` overrides the first step's destination. That is how the demo points a
        trail learned on the normal site at the redesigned one, without editing memory.
        """
        self._domain = domain
        self.answers: dict[str, Any] = {}
        playbook = self._load(domain, task)
        started = time.perf_counter()
        self.browser.saved_files.clear()
        self.browser.last_download = None
        self.browser.last_download_path = None

        # A trail that is mostly broken is not worth repairing one step at a time.
        if playbook.is_stale:
            return self._retire(playbook, started)

        self._arm_overlays(domain)
        self.events.emit(RunStarted(domain=domain, task=playbook.task, mode="warm"))

        metrics = RunMetrics(
            domain=domain,
            task=playbook.task,
            mode="warm",
            steps_total=len(playbook.steps),
            tool_calls=1,  # the whole run is one call from the caller's side
            model_calls=0,  # nothing in this file can make one
        )

        for step in playbook.steps:
            self.events.emit(StepStarted(index=step.index, intent=step.intent))
            outcome = self._replay_step(step, start_url=start_url)

            if outcome.matched_by is not None:
                metrics.steps_replayed += 1
                self.events.emit(
                    StepPassed(
                        index=step.index,
                        intent=step.intent,
                        matched_by=outcome.matched_by,
                        duration_ms=outcome.duration_ms,
                    )
                )
                continue

            # Decided BEFORE the repair request is built. Building it takes a snapshot of
            # the wrong page and writes it into the site map, and emits RepairNeeded to
            # every listener — all of it about a page this trail has nothing to do with.
            if outcome.off_trail is not None:
                belongs, here = outcome.off_trail
                self.events.emit(
                    StepFailed(index=step.index, intent=step.intent, reason=outcome.reason)
                )
                self._finish(playbook, metrics, started, succeeded=False)
                return ReplayResult(
                    ok=False,
                    metrics=metrics,
                    wrong_place=True,
                    reason=(
                        f"Step {step.index} ({step.intent!r}) belongs on {belongs}, and we "
                        f"are on {here}. Nothing is broken — the trail's starting state is "
                        f"not met. The commonest reason is that the work is already done: "
                        f"replaying a sign-in while signed in lands on the dashboard. Do "
                        f"NOT repair this step. There is nothing on this page for it to be "
                        f"bound to, and binding it would destroy a working trail."
                    ),
                    saved_files=list(self.browser.saved_files),
                )

            self.events.emit(
                StepFailed(index=step.index, intent=step.intent, reason=outcome.reason)
            )
            request = self._repair_request(playbook, step, outcome.tried)
            self.events.emit(
                RepairNeeded(
                    index=step.index,
                    intent=step.intent,
                    tried=outcome.tried,
                    url=request.url,
                )
            )
            # Being on the wrong page looks exactly like a broken step, and this is the
            # most dangerous of the lookalikes. Replaying "sign in as admin" while ALREADY
            # signed in sends /admin/sign-in to /admin/dashboard, so there is no email
            # field to fill — and the repair offered twenty-three dashboard controls, not
            # one of them an email field. An agent following that instruction literally
            # would bind the step to a nav link and destroy a trail that was never broken.
            # A human check looks exactly like a broken step too, and it is the one thing
            # neither Cairn nor a host AI can repair its way past. Say what happened and
            # stop, rather than handing back a page with no way through it.
            standing_in_the_way = self.browser.captcha_on_page()
            if standing_in_the_way is not None:
                self._finish(playbook, metrics, started, succeeded=False)
                return ReplayResult(
                    ok=False,
                    metrics=metrics,
                    blocked=True,
                    reason=(
                        f"{playbook.domain} put a human check in the way, so the run "
                        f"stopped. The trail is not broken and nothing was repaired — "
                        f"a captcha cannot be automated past. Open the site yourself, "
                        f"clear the check, and run again."
                    ),
                    saved_files=list(self.browser.saved_files),
                )

            # Being signed out looks exactly like a broken step, and asking an AI to
            # repair its way past a login page would waste a run and teach it nonsense.
            if self.browser.looks_signed_out():
                self._finish(playbook, metrics, started, succeeded=False)
                return ReplayResult(
                    ok=False,
                    metrics=metrics,
                    needs_login=True,
                    reason=(
                        f"{playbook.domain} asked to sign in again. The trail is fine — "
                        f"the session ran out."
                    ),
                    saved_files=list(self.browser.saved_files),
                )

            # That step's locators just took a miss. If that tipped the whole trail past
            # half broken, stop asking for repairs and relearn instead.
            if playbook.is_stale:
                self.store.save_playbook(playbook)
                return self._retire(playbook, started)

            self._finish(playbook, metrics, started, succeeded=False)
            return ReplayResult(
                ok=False,
                metrics=metrics,
                repair=request,
                reason=outcome.reason,
                saved_files=list(self.browser.saved_files),
            )

        self._let_the_last_step_land(playbook)
        self._finish(playbook, metrics, started, succeeded=True)
        return ReplayResult(
            ok=True,
            metrics=metrics,
            saved_files=list(self.browser.saved_files),
            answers=dict(self.answers),
        )

    def _let_the_last_step_land(self, playbook: Playbook) -> None:
        """Do not hand back a finished run while the site is still moving.

        A sign-in trail ends by pressing a button, and the app redirects a moment later.
        Cairn used to return the instant the last step's check passed, so a caller reading
        the URL straight afterwards saw the sign-in page and concluded the trail had
        failed — then went and re-explored a site Cairn already knew, which is the exact
        cost this whole project exists to remove.

        Only for a trail that ends in an ACTION. Most trails end with a read — the answer —
        and there is nothing in flight after one of those, so the common case and the
        benchmark pay nothing at all.
        """
        if not playbook.steps or playbook.steps[-1].action == READ_ACTION:
            return
        self.browser.settle()
        # Network quiet, not a timer. A sign-in that POSTs and then navigates takes as
        # long as it takes, and any fixed number is a guess that is too short on a slow
        # day — the first attempt at this waited 400ms and still handed back the sign-in
        # page. `wait_until_quiet` returns the moment the site stops calling home, so
        # the whole budget is only ever spent by a page that never goes quiet.
        self.browser.wait_until_quiet(SETTLE_AFTER_LAST_STEP_MS)

    # ------------------------------------------------------------ one step

    @dataclass
    class _StepOutcome:
        matched_by: str | None = None
        tried: list[str] = field(default_factory=list)
        reason: str = ""
        duration_ms: int = 0
        off_trail: tuple[str, str] | None = None
        """Where this step belongs, and where we actually are — when they differ.

        Set INSTEAD of trying the locators, so a replay in the wrong place marks nothing
        as drift. That mattered more than the wrong repair it also prevents: every wrong-
        place replay used to record a miss against a perfectly good locator, and a few of
        them dragged the trail's health under half, at which point it was retired. The
        trail destroyed itself for being replayed at the wrong moment."""

    def _value_for(self, step: Step, domain: str) -> str:
        """What to type. A secret is fetched from this machine, never from memory."""
        if step.secret:
            return resolve_secret(domain, step.secret, profile=self.profile)
        return step.value or ""

    def _replay_step(self, step: Step, *, start_url: str | None) -> _StepOutcome:
        began = time.perf_counter()

        # Forget any earlier download before acting. Without this a "did it download?"
        # check could be satisfied by a file fetched minutes ago in the same browser, and
        # the step would report success having downloaded nothing.
        self.browser.last_download = None
        self.browser.last_download_path = None

        # Are we even on the page this step belongs to? Asked FIRST, before a single
        # locator is tried, because everything that follows assumes we are.
        astray = self._off_trail(step)
        if astray is not None:
            return self._StepOutcome(off_trail=astray)

        if step.action == "goto":
            sent_elsewhere = bool(start_url) and step.index == 1
            destination = start_url if sent_elsewhere else step.value
            self.browser.goto(destination or "")

            # When the caller redirects the first step, the stored check is about the old
            # address and cannot apply. Checking it anyway reported `needs_repair` on a
            # page that had loaded perfectly — and the step it named could not be repaired,
            # because a `goto` has no control to point at.
            expected = (
                Postcondition("url_contains", href_path(destination or ""))
                if sent_elsewhere
                else step.postcondition
            )
            # A canonicalising redirect still counts as arriving. Walking into the WRONG
            # page is caught by the next step, which knows which page it belongs on.
            passed = check_postcondition(self.browser, expected) or _redirected_there(
                self.browser.page.url, destination or ""
            )

            elapsed = int((time.perf_counter() - began) * 1000)
            if passed:
                step.record_hit()
                return self._StepOutcome(matched_by="url", duration_ms=elapsed)
            step.record_miss()
            return self._StepOutcome(reason="the page did not arrive where it should have")

        # A read of the whole page — its title, its url, the errors it logged — names no
        # element, so there is nothing to find and nothing that can go stale.
        if step.action == READ_ACTION and not step.locators:
            spoke = self._read_answer(step, None)
            elapsed = int((time.perf_counter() - began) * 1000)
            if not spoke:
                step.record_miss()
                return self._StepOutcome(reason=_said_nothing(step))
            step.record_hit()
            return self._StepOutcome(matched_by="page", duration_ms=elapsed)

        outcome = self._StepOutcome()
        # A step that answered a confirm box last time expects the same wording this time.
        self.browser.dialog_policy = step.dialog_choice or ACCEPT
        self.browser.last_dialog = None

        settled, found_anything, missed = self._try_locators(step, outcome, began=began)
        if settled is not None:
            self._blame(missed, step)
            return settled

        # Nothing on the page matched. Before calling that drift, take the other
        # explanation seriously: the page may simply not have finished drawing. A slow
        # site marked as drift is the worst outcome there is — it costs no error, quietly
        # drags good locators toward dead, and invites a "repair" that replaces working
        # locators with identical ones.
        #
        # Only worth a second look when NOTHING resolved. If something did resolve and the
        # action or the check then failed, that is real, and repeating it could click the
        # same button twice.
        #
        # A READ is the exception, and it is safe to be: reading twice changes nothing.
        # A JavaScript-rendered page routinely hands over an element that is present and
        # still empty — the cold run had a settle before it looked and replay did not, so
        # the trail read a heading that was there and blank. Letting a read settle and try
        # again is the difference between working on a modern site and not.
        if not found_anything or step.action == READ_ACTION:
            self.browser.wait_until_quiet()
            outcome.tried.clear()
            settled, _, missed = self._try_locators(step, outcome, began=began)
            if settled is not None:
                self._blame(missed, step)
                return settled

        self._blame(missed, step)
        outcome.reason = "every remembered way of finding this went stale"
        return outcome

    def _try_locators(
        self, step: Step, outcome: _StepOutcome, *, began: float
    ) -> tuple[_StepOutcome | None, bool, list[tuple[Locator, str]]]:
        """One pass over a step's locators, collecting misses instead of recording them.

        Handing the misses back rather than applying them is the whole point. A page that
        has not rendered yet makes every locator look dead, and writing that down would
        damage a trail that is perfectly fine. Only the pass that actually decides the
        step's fate gets to blame anything.

        Returns the finished outcome if the step resolved either way, whether any locator
        found an element at all, and the misses this pass would like recorded.
        """
        missed: list[tuple[Locator, str]] = []
        found_anything = False

        for locator in step.ranked_locators():
            label = f"{locator.kind}:{locator.value}"
            outcome.tried.append(label)

            # A read only needs the element to BE there. Insisting it be visible is what
            # made a hidden heading unreplayable on a page it had been recorded from.
            target = self.browser.resolve(locator, visible=step.action != READ_ACTION)
            if target is None:
                missed.append((locator, label))
                continue

            found_anything = True
            try:
                spoke = self._do(step, target, domain=self._domain)
            except MissingSecret:
                raise
            except PlaywrightError:
                # Only the browser's own failures are drift. A bug of ours — an unknown
                # action, a malformed step — has to surface as itself instead of being
                # filed away as "this locator stopped matching", which is where a real
                # fault would go to die quietly.
                missed.append((locator, label))
                continue

            if not spoke:
                # This locator found an element, and reading it produced nothing where it
                # once produced an answer. Treat it as a MISS rather than a failure, so
                # the next locator gets its turn — on a real product listing, where a
                # stored link matched nine cards, that is exactly what finds the right one.
                missed.append((locator, label))
                continue

            changed = self._dialog_changed(step)
            if changed:
                # Never answer a box whose words have changed. A step that recorded
                # "click OK" on "Save changes?" must not blindly accept one that now
                # reads "delete 400 rows?". Stop and let a human or the caller look.
                outcome.reason = changed
                outcome.duration_ms = int((time.perf_counter() - began) * 1000)
                return outcome, found_anything, missed

            if check_postcondition(self.browser, step.postcondition):
                locator.record_hit()
                outcome.matched_by = label
                outcome.duration_ms = int((time.perf_counter() - began) * 1000)
                return outcome, found_anything, missed

            # It clicked something, but the page did not move the way it should have.
            # That is drift, not success — this is the check a macro recorder skips.
            missed.append((locator, label))

        return None, found_anything, missed

    def _off_trail(self, step: Step) -> tuple[str, str] | None:
        """Is this step being replayed somewhere it was never recorded?

        A `goto` names its own destination, so it can never be in the wrong place. Every
        other step was recorded on a particular page, and if we are not on it the step is
        not broken — the trail's starting state simply is not met. Replaying "sign in as
        admin" while already signed in is the everyday version: the site sends
        /admin/sign-in to /admin/dashboard, and the email field the step wants was never
        going to be there.

        Trails saved before steps recorded their page have nothing to compare, and opt out.
        """
        if step.action == "goto" or not step.page:
            return None
        here = self.browser.page.url
        if _same_page(here, step.page):
            return None
        return (step.page, here)

    def _blame(self, missed: list[tuple[Locator, str]], step: Step) -> None:
        """Write down the misses from the pass that actually decided the step."""
        for locator, label in missed:
            locator.record_miss()
            self.events.emit(DriftDetected(index=step.index, locator=label))

    def _read_answer(self, step: Step, target) -> bool:
        """Replay a remembered read and keep what it said. False if it said nothing.

        This is what makes a warm run *answer* rather than merely arrive. A trail for
        "how many open issues" is worth nothing if it navigates to the page and stops.

        Emptiness is a failure when this read ANSWERED at the time it was learned. The
        element still being there is not enough: on a real product listing a stored link
        matched nine cards, replay read the one with no text, every check passed
        and the run reported success while handing back "". A step that used to answer and
        now does not is the page moving underneath the trail, which is drift, and drift is
        repairable — silence is not.
        """
        kind, _, attribute = (step.value or "text").partition(":")
        answer = reads.read(
            kind, page=self.browser.page, target=target, attribute=attribute or None
        )
        self.answers[step.intent] = answer
        return not (step.answered and not str(answer).strip())

    def _dialog_changed(self, step: Step) -> str | None:
        """Did a confirm box appear whose wording is not what was recorded?

        Answered dialogs are the one thing replay must not treat as routine. The choice
        was made once, for a specific question; the same click can mean something
        completely different behind a different question.
        """
        seen = self.browser.last_dialog
        if seen is None or not step.dialog_message:
            return None
        if seen["message"].strip() == step.dialog_message.strip():
            return None
        return (
            f"this step answered {step.dialog_message.strip()!r} before, but the site now "
            f"asks {seen['message'].strip()!r} — stopping rather than answering it"
        )

    def _arm_overlays(self, domain: str) -> None:
        """Re-arm the overlays this site is known for, before the trail starts.

        This is what makes "learned once" mean anything. Without it the banner is cleared
        on the run that met it and covers the page again on every run after.
        """
        knowledge = self.store.load_site_knowledge(domain)
        if knowledge is None:
            return
        for selector in knowledge.overlays:
            self.browser.dismiss_when_seen(selector)
        if knowledge.overlays:
            self.events.emit(
                MemoryRead(
                    category="site_knowledge",
                    name=domain,
                    found=True,
                )
            )

    def _do(self, step: Step, target, *, domain: str) -> bool:
        """Replay one recorded action. False when a remembered read came back empty.

        The value comes from `_value_for`, so a password field is filled from this machine
        rather than from memory — memory never held it.
        """
        if step.action == READ_ACTION:
            return self._read_answer(step, target)

        spec = actions.spec_for(step.action)
        value = self._value_for(step, domain) if spec.name in _TEXT_ENTRY else step.value
        was = self.browser.page.url
        actions.perform(
            step.action,
            page=self.browser.page,
            target=target,
            value=value,
        )
        self.browser.settle()
        # This step is recorded as one that changes the address. If it has not changed
        # yet, the app may be doing it itself a moment later — which is how every
        # single-page sidebar link works. Cheap when it was going to change anyway.
        if step.postcondition.kind == "url_contains" and self.browser.page.url == was:
            self.browser.await_url_change(was)
        return True

    def _retire(self, playbook: Playbook, started: float) -> ReplayResult:
        """Throw the trail away, keep what is known about the site, and say so.

        This is the plan's rule: over half the steps broken means the site was rebuilt,
        not adjusted. Repairing step by step from there is slower than walking it again,
        and each repair would be built on a trail that is mostly wrong anyway.
        """
        broken = sum(1 for step in playbook.steps if step.health < 0.5)
        self.store.retire_playbook(playbook.domain, playbook.task)
        self.events.emit(
            MemoryWrite(
                category="playbook",
                name=playbook.domain,
                detail=f"retired as stale ({broken} of {len(playbook.steps)} steps broken)",
            )
        )

        knowledge = self.store.load_site_knowledge(playbook.domain)
        self.events.emit(
            MemoryRead(
                category="site_knowledge",
                name=playbook.domain,
                found=knowledge is not None,
            )
        )

        metrics = RunMetrics(
            domain=playbook.domain,
            task=playbook.task,
            mode="warm",
            steps_total=len(playbook.steps),
            trail_repairs=playbook.repairs,
            tool_calls=1,
            model_calls=0,
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
        self.store.journal_run(metrics)
        self.events.emit(
            RunFinished(
                domain=playbook.domain,
                succeeded=False,
                duration_ms=metrics.duration_ms,
                steps_replayed=0,
                trail_repairs=playbook.repairs,
                model_calls=0,
            )
        )

        return ReplayResult(
            ok=False,
            metrics=metrics,
            stale=True,
            reason=(
                f"{broken} of {len(playbook.steps)} steps no longer match this site. "
                f"It was rebuilt, not tweaked, so the trail has been retired."
            ),
            site_facts=knowledge.summary() if knowledge else [],
        )

    # -------------------------------------------------------------- repair

    def _repair_request(self, playbook: Playbook, step: Step, tried: list[str]) -> RepairRequest:
        """Describe the one broken step, with the current page's controls as candidates.

        The candidates are described in full rather than left as bare refs. Whoever repairs
        this step has to write down a locator that will still work next month, and a ref is
        good for one snapshot only — so the durable descriptors have to travel with it.
        """
        snapshot = self.browser.snapshot()
        self._remember_page(playbook.domain, snapshot)
        return RepairRequest(
            domain=playbook.domain,
            step_index=step.index,
            intent=step.intent,
            action=step.action,
            tried=tried,
            url=snapshot.url,
            candidates=[self.browser.describe(element).to_dict() for element in snapshot.elements],
        )

    def _remember_page(self, domain: str, snapshot: Any) -> None:
        """Keep the page this snapshot came from in the site's map.

        The only place the warm path touches the map, and deliberately so. Replay reads no
        pages at all — that is the whole claim — so there is normally no snapshot to keep.
        A broken step is the exception: one has just been built to describe the candidates,
        it is free, and it is taken at exactly the moment the page is KNOWN to have moved,
        which is when a stale map is worth correcting.

        Never allowed to break a run, for the same reason as on the cold path.
        """
        try:
            site_map = self.store.load_site_map(domain) or SiteMap(domain=domain)
            self.store.save_site_map(
                site_map.merge(
                    url=snapshot.url,
                    title=snapshot.title,
                    controls=controls_in(snapshot),
                )
            )
        except Exception:  # noqa: BLE001 - a note must never fail the task
            return
        self.events.emit(
            MemoryWrite(category="site_map", name=domain, detail=f"{snapshot.url} after drift")
        )

    def repair_from_ref(
        self, domain: str, step_index: int, ref: str, *, task: str | None = None
    ) -> Playbook:
        """Fix a step by pointing at the control that should have been used.

        Better than handing over one selector: the element is described in full, so the
        step gets back every durable way of finding it — test id, link target, label, role,
        text — exactly as a fresh recording would. A repair that stored a single positional
        path left the step more fragile than when it was first learned.
        """
        snapshot = self.browser.snapshot()
        element = snapshot.by_ref(ref)
        if element is None:
            raise NoTrailError(f"no control {ref!r} on this page — look at it again")

        found = self.browser.describe(element).locators()
        if not found:
            raise NoTrailError(f"{ref!r} offers no durable way of being found again")
        return self.apply_repair(domain, step_index, found, task=task)

    def apply_repair(
        self,
        domain: str,
        step_index: int,
        locator: Locator | list[Locator],
        *,
        task: str | None = None,
    ) -> Playbook:
        """Save the fix the host AI worked out, for that one step only.

        The new locators go to the front with a hit already recorded, and the dead ones
        are kept rather than dropped — a locator that fails today may be the one that
        works again after the site is reverted, and its miss count is evidence.
        """
        fresh = [locator] if isinstance(locator, Locator) else list(locator)
        if not fresh:
            raise NoTrailError("a repair needs at least one way of finding the element")

        playbook = self._load(domain, task)
        step = next(s for s in playbook.steps if s.index == step_index)
        before = step.ranked_locators()[0].value if step.locators else "(nothing)"

        # Drop the routes that just failed and had nothing to show for themselves.
        # A locator with a real track record survives one miss and stays as a fallback.
        step.locators = [existing for existing in step.locators if not existing.is_dead]

        # Only the first is credited with the hit — it is the one actually confirmed.
        fresh[0].record_hit()
        step.locators = fresh + step.locators
        step.repairs += 1
        playbook.repairs += 1
        playbook.touch()

        after = fresh[0].value
        self.store.save_playbook(playbook)
        self.store.journal_repair(domain, step_index, before, after)
        self.events.emit(RepairSaved(index=step_index, before=before, after=after))
        self.events.emit(
            MemoryWrite(category="playbook", name=domain, detail=f"repaired step {step_index}")
        )
        return playbook

    # -------------------------------------------------------------- shared

    def _load(self, domain: str, task: str | None = None) -> Playbook:
        playbook = self.store.load_playbook(domain, task)
        self.events.emit(MemoryRead(category="playbook", name=domain, found=playbook is not None))
        if playbook is not None:
            return playbook

        # A site can hold several trails. "Which one?" and "never been here" are opposite
        # situations that demand opposite responses, so they must never share an error.
        # Reporting the second when the first was true is what made a host AI re-explore
        # a site it already knew, and save over what was there.
        known = self.store.trails_for(domain)
        if known:
            raise NeedsTask(
                f"{domain} is remembered, but not this task. Say which one you mean.",
                tasks=known,
            )
        raise NoTrailError(
            f"nothing remembered for {domain} — there is no trail to follow. "
            f"Explore it once and save, or restore the memory."
        )

    def _finish(
        self,
        playbook: Playbook,
        metrics: RunMetrics,
        started: float,
        *,
        succeeded: bool,
    ) -> None:
        metrics.duration_ms = int((time.perf_counter() - started) * 1000)
        metrics.succeeded = succeeded
        metrics.trail_repairs = playbook.repairs

        # Locator hit/miss counts were updated in place while replaying, so saving here
        # is what makes the trail get better every time it is walked.
        playbook.runs += 1
        self.store.save_playbook(playbook)
        self.store.journal_run(metrics)

        self.events.emit(
            MemoryWrite(category="playbook", name=playbook.domain, detail="scores updated")
        )
        self.events.emit(
            RunFinished(
                domain=playbook.domain,
                succeeded=succeeded,
                duration_ms=metrics.duration_ms,
                steps_replayed=metrics.steps_replayed,
                trail_repairs=metrics.trail_repairs,
                model_calls=0,
            )
        )
