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
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from . import actions
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
from .models import Locator, Playbook, RunMetrics, Step
from .operations import check_postcondition
from .secrets import MissingSecret
from .secrets import resolve as resolve_secret
from .store import CairnStore

# A step is considered past saving when this share of the trail is already broken.
STALE_SHARE = 0.5


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

    stale: bool = False
    """The trail is past repairing — the site was rebuilt, not tweaked."""

    needs_login: bool = False
    """We were bounced to a sign-in page. Nothing is wrong with the trail; the session
    simply ran out and a person has to sign in again."""

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


class Executor:
    """Replays a remembered trail. Reads memory, writes back what it learned."""

    def __init__(
        self,
        store: CairnStore,
        browser: Browser,
        *,
        emitter: Emitter | None = None,
    ):
        self.store = store
        self.browser = browser
        self.events = emitter or Emitter()

    _domain: str = ""

    def run(self, domain: str, *, start_url: str | None = None) -> ReplayResult:
        """Walk the remembered trail for one site.

        `start_url` overrides the first step's destination. That is how the demo points a
        trail learned on the normal site at the redesigned one, without editing memory.
        """
        self._domain = domain
        playbook = self._load(domain)
        started = time.perf_counter()
        self.browser.saved_files.clear()
        self.browser.last_download = None
        self.browser.last_download_path = None

        # A trail that is mostly broken is not worth repairing one step at a time.
        if playbook.is_stale:
            return self._retire(playbook, started)

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

        self._finish(playbook, metrics, started, succeeded=True)
        return ReplayResult(ok=True, metrics=metrics, saved_files=list(self.browser.saved_files))

    # ------------------------------------------------------------ one step

    @dataclass
    class _StepOutcome:
        matched_by: str | None = None
        tried: list[str] = field(default_factory=list)
        reason: str = ""
        duration_ms: int = 0

    def _value_for(self, step: Step, domain: str) -> str:
        """What to type. A secret is fetched from this machine, never from memory."""
        if step.secret:
            return resolve_secret(domain, step.secret)
        return step.value or ""

    def _replay_step(self, step: Step, *, start_url: str | None) -> _StepOutcome:
        began = time.perf_counter()

        # Forget any earlier download before acting. Without this a "did it download?"
        # check could be satisfied by a file fetched minutes ago in the same browser, and
        # the step would report success having downloaded nothing.
        self.browser.last_download = None
        self.browser.last_download_path = None

        if step.action == "goto":
            destination = start_url if (start_url and step.index == 1) else step.value
            self.browser.goto(destination or "")
            passed = check_postcondition(self.browser, step.postcondition)
            elapsed = int((time.perf_counter() - began) * 1000)
            if passed:
                return self._StepOutcome(matched_by="url", duration_ms=elapsed)
            return self._StepOutcome(reason="the page did not arrive where it should have")

        outcome = self._StepOutcome()
        # A step that answered a confirm box last time expects the same wording this time.
        self.browser.dialog_policy = step.dialog_choice or ACCEPT
        self.browser.last_dialog = None

        for locator in step.ranked_locators():
            label = f"{locator.kind}:{locator.value}"
            outcome.tried.append(label)

            target = self.browser.resolve(locator)
            if target is None:
                locator.record_miss()
                self.events.emit(DriftDetected(index=step.index, locator=label))
                continue

            try:
                self._do(step, target, domain=self._domain)
            except MissingSecret:
                raise
            except Exception:
                locator.record_miss()
                self.events.emit(DriftDetected(index=step.index, locator=label))
                continue

            changed = self._dialog_changed(step)
            if changed:
                # Never answer a box whose words have changed. A step that recorded
                # "click OK" on "Save changes?" must not blindly accept one that now
                # reads "delete 400 rows?". Stop and let a human or the caller look.
                outcome.reason = changed
                outcome.duration_ms = int((time.perf_counter() - began) * 1000)
                return outcome

            if check_postcondition(self.browser, step.postcondition):
                locator.record_hit()
                outcome.matched_by = label
                outcome.duration_ms = int((time.perf_counter() - began) * 1000)
                return outcome

            # It clicked something, but the page did not move the way it should have.
            # That is drift, not success — this is the check a macro recorder skips.
            locator.record_miss()
            self.events.emit(DriftDetected(index=step.index, locator=label))

        outcome.reason = "every remembered way of finding this went stale"
        return outcome

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

    def _do(self, step: Step, target, *, domain: str) -> None:
        """Replay one recorded action.

        The value comes from `_value_for`, so a password field is filled from this machine
        rather than from memory — memory never held it.
        """
        spec = actions.spec_for(step.action)
        value = self._value_for(step, domain) if spec.name in _TEXT_ENTRY else step.value
        actions.perform(
            step.action,
            page=self.browser.page,
            target=target,
            value=value,
        )
        self.browser.settle()

    def _retire(self, playbook: Playbook, started: float) -> ReplayResult:
        """Throw the trail away, keep what is known about the site, and say so.

        This is the plan's rule: over half the steps broken means the site was rebuilt,
        not adjusted. Repairing step by step from there is slower than walking it again,
        and each repair would be built on a trail that is mostly wrong anyway.
        """
        broken = sum(1 for step in playbook.steps if step.health < 0.5)
        self.store.retire_playbook(playbook.domain)
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
                steps_repaired=0,
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
        """Describe the one broken step, with the current page's controls as candidates."""
        snapshot = self.browser.snapshot()
        return RepairRequest(
            domain=playbook.domain,
            step_index=step.index,
            intent=step.intent,
            action=step.action,
            tried=tried,
            url=snapshot.url,
            candidates=[element.to_dict() for element in snapshot.elements],
        )

    def apply_repair(self, domain: str, step_index: int, locator: Locator) -> Playbook:
        """Save the fix the host AI worked out, for that one step only.

        The new locator goes to the front with a hit already recorded, and the dead ones
        are kept rather than dropped — a locator that fails today may be the one that
        works again after the site is reverted, and its miss count is evidence.
        """
        playbook = self._load(domain)
        step = next(s for s in playbook.steps if s.index == step_index)
        before = step.ranked_locators()[0].value if step.locators else "(nothing)"

        # Drop the routes that just failed and had nothing to show for themselves.
        # A locator with a real track record survives one miss and stays as a fallback.
        step.locators = [existing for existing in step.locators if not existing.is_dead]

        locator.record_hit()
        step.locators.insert(0, locator)
        step.repairs += 1
        playbook.repairs += 1
        playbook.touch()

        self.store.save_playbook(playbook)
        self.store.journal_repair(domain, step_index, before, locator.value)
        self.events.emit(RepairSaved(index=step_index, before=before, after=locator.value))
        self.events.emit(
            MemoryWrite(category="playbook", name=domain, detail=f"repaired step {step_index}")
        )
        return playbook

    # -------------------------------------------------------------- shared

    def _load(self, domain: str) -> Playbook:
        playbook = self.store.load_playbook(domain)
        self.events.emit(MemoryRead(category="playbook", name=domain, found=playbook is not None))
        if playbook is None:
            raise NoTrailError(
                f"nothing remembered for {domain} — there is no trail to follow. "
                f"Explore it once and save, or restore the memory."
            )
        return playbook

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
                steps_repaired=metrics.steps_repaired,
                model_calls=0,
            )
        )
