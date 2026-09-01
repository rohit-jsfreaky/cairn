"""The shapes Cairn remembers.

Everything here is a plain dataclass with an explicit `to_dict` / `from_dict`, because
these objects are written into Sibyl Memory as JSON bodies. Keeping the serialisation
explicit means the stored shape is a deliberate decision, not a side effect of whatever
library we happen to use.

Nothing in this module talks to memory. That is `store.py`, and only `store.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

LocatorKind = Literal[
    "test_id",
    "structural",
    "label",
    "role",
    "placeholder",
    "alt",
    "title",
    "text",
    "css",
]

# How much a single confirmed hit or miss moves a locator's health.
_HIT_WEIGHT = 1.0
_MISS_WEIGHT = 2.0  # a miss is worse news than a hit is good news


def utc_now() -> str:
    """One timestamp format everywhere: ISO 8601, UTC, seconds precision."""
    return datetime.now(UTC).replace(microsecond=0).isoformat()


@dataclass
class Locator:
    """One way to find an element on the page.

    A step keeps several of these, ranked. Replay tries them in order, so when a site
    changes its CSS but keeps its accessible name, the role locator still lands and the
    step survives without any repair at all.
    """

    kind: LocatorKind
    value: str
    # Refinements. These are not kinds of their own because they compose with every kind:
    # "the third row" and "the row containing September" are narrowings of any locator, not
    # separate ways of searching.
    nth: int | None = None
    """Which match to take when several look alike. 0 is the first, -1 the last."""
    has_text: str | None = None
    """Narrow to the match containing this text — how you find one row in a list."""
    hits: int = 0
    misses: int = 0
    last_ok: str | None = None

    @property
    def confidence(self) -> float:
        """0.0 to 1.0. Unproven locators start neutral rather than perfect."""
        attempts = self.hits + self.misses
        if attempts == 0:
            return 0.5
        score = (self.hits * _HIT_WEIGHT) - (self.misses * _MISS_WEIGHT)
        return max(0.0, min(1.0, score / (attempts * _HIT_WEIGHT)))

    def record_hit(self) -> None:
        self.hits += 1
        self.last_ok = utc_now()

    def record_miss(self) -> None:
        self.misses += 1

    @property
    def is_dead(self) -> bool:
        """Has failed and has nothing to show for it, so it is not worth keeping.

        A locator that once worked keeps some confidence after a single miss, so a
        one-off failure never kills a proven route. One that has never landed and has now
        failed is just weight in the trail.
        """
        return self.misses > 0 and self.confidence == 0.0

    def describe(self) -> str:
        """How this locator reads in a repair request or an export."""
        written = f"{self.kind}={self.value}"
        if self.has_text:
            written += f" containing {self.has_text!r}"
        if self.nth is not None:
            written += f" [{self.nth}]"
        return written

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "value": self.value,
            **({"nth": self.nth} if self.nth is not None else {}),
            **({"has_text": self.has_text} if self.has_text else {}),
            "hits": self.hits,
            "misses": self.misses,
            "last_ok": self.last_ok,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Locator:
        return cls(
            kind=raw["kind"],
            value=raw["value"],
            nth=raw.get("nth"),
            has_text=raw.get("has_text"),
            hits=raw.get("hits", 0),
            misses=raw.get("misses", 0),
            last_ok=raw.get("last_ok"),
        )


@dataclass
class Postcondition:
    """What must be true after a step, for the step to count as landed.

    This is the line between Cairn and a macro recorder. A recorder clicks and hopes.
    Cairn checks that the page actually moved, which is how it knows a site changed
    instead of silently doing nothing.
    """

    kind: Literal[
        "url_contains",
        "text_present",
        "text_gone",
        "element_present",
        "element_gone",
        "download",
        "value_is",
        "checked_is",
        "count_is",
        "attribute_is",
    ]
    value: str
    # Which element to look at, for the kinds that check one. The older kinds carry their
    # selector in `value`, so this stays optional and old saved playbooks still load.
    target: str | None = None

    def to_dict(self) -> dict[str, Any]:
        written: dict[str, Any] = {"kind": self.kind, "value": self.value}
        if self.target:
            written["target"] = self.target
        return written

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Postcondition:
        return cls(kind=raw["kind"], value=raw["value"], target=raw.get("target"))


@dataclass
class Step:
    """One move along the trail: what we meant, what we did, how to find it again."""

    index: int
    intent: str
    # Any action in the registry. Kept as a plain str so adding one never means editing
    # a type in a second file — `actions.spec_for` is what rejects a bad name.
    action: str
    postcondition: Postcondition
    locators: list[Locator] = field(default_factory=list)
    value: str | None = None
    repairs: int = 0

    dialog_message: str | None = None
    """The exact words of the confirm box this step answered, if there was one."""
    dialog_choice: str | None = None
    """What was answered: "accept" or "dismiss".

    Both are stored because the choice alone is not safe to replay. A step that recorded
    "click OK" must never blindly accept a box that now reads "delete 400 rows?" — so on
    replay a changed message stops the run instead of answering it."""

    secret: str | None = None
    """Names a value this step needs but must never remember, such as "password".

    When this is set, `value` stays empty and the real value is looked up on the machine
    running the replay. A password in a memory file is a password in a backup, a sync
    folder and a support ticket."""

    @property
    def health(self) -> float:
        """The best locator we have is how healthy the step is."""
        if not self.locators:
            return 0.0
        return max(loc.confidence for loc in self.locators)

    def ranked_locators(self) -> list[Locator]:
        """Most trustworthy first. Replay walks this order and stops at the first hit."""
        return sorted(self.locators, key=lambda loc: loc.confidence, reverse=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "intent": self.intent,
            "action": self.action,
            "value": self.value,
            "postcondition": self.postcondition.to_dict(),
            "locators": [loc.to_dict() for loc in self.locators],
            "repairs": self.repairs,
            "secret": self.secret,
            "dialog_message": self.dialog_message,
            "dialog_choice": self.dialog_choice,
            "health": round(self.health, 3),
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Step:
        return cls(
            index=raw["index"],
            intent=raw["intent"],
            action=raw["action"],
            value=raw.get("value"),
            postcondition=Postcondition.from_dict(raw["postcondition"]),
            locators=[Locator.from_dict(loc) for loc in raw.get("locators", [])],
            repairs=raw.get("repairs", 0),
            secret=raw.get("secret"),
            dialog_message=raw.get("dialog_message"),
            dialog_choice=raw.get("dialog_choice"),
        )


@dataclass
class Playbook:
    """The trail for one task on one site. This is the thing memory holds."""

    domain: str
    task: str
    steps: list[Step] = field(default_factory=list)
    version: int = 1
    runs: int = 0
    repairs: int = 0
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    @property
    def health(self) -> float:
        """Average step health. Used to decide when a playbook is past saving."""
        if not self.steps:
            return 0.0
        return sum(step.health for step in self.steps) / len(self.steps)

    @property
    def is_stale(self) -> bool:
        """More than half the trail is broken — the site has moved on, not drifted."""
        if not self.steps:
            return True
        broken = sum(1 for step in self.steps if step.health < 0.5)
        return broken > len(self.steps) / 2

    def touch(self) -> None:
        self.updated_at = utc_now()
        self.version += 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "task": self.task,
            "version": self.version,
            "runs": self.runs,
            "repairs": self.repairs,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "health": round(self.health, 3),
            "steps": [step.to_dict() for step in self.steps],
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Playbook:
        return cls(
            domain=raw["domain"],
            task=raw["task"],
            steps=[Step.from_dict(step) for step in raw.get("steps", [])],
            version=raw.get("version", 1),
            runs=raw.get("runs", 0),
            repairs=raw.get("repairs", 0),
            created_at=raw.get("created_at", utc_now()),
            updated_at=raw.get("updated_at", utc_now()),
        )


@dataclass
class SiteKnowledge:
    """Facts about a site that outlive any particular trail.

    A redesign throws away the playbook's locators but not the fact that the site needs
    two-factor, or which account you log in with, or that it locks you out after five
    wrong passwords. Keeping these separate is why relearning a rebuilt site is cheaper
    than a first visit — and it is the reason throwing a stale trail away is safe.

    `notes` is free text on purpose. The useful facts about a real site do not fit a
    fixed set of fields: "the invoice only appears after the 3rd", "the export takes two
    minutes", "use the finance login, not the admin one". A closed schema would only
    capture the easy ones.
    """

    domain: str
    notes: list[str] = field(default_factory=list)
    needs_login: bool = False
    needs_2fa: bool = False
    account_hint: str | None = None
    overlays: list[str] = field(default_factory=list)
    """Things that pop up over the page at unpredictable moments — cookie banners, "rate
    us", survey invitations. Learned once, then cleared automatically forever after.

    This belongs to the site and not to any one trail: an overlay appears on whichever step
    happens to be running when it decides to show up, so pinning it to a step would be
    recording an accident."""
    updated_at: str = field(default_factory=utc_now)

    def merge(
        self,
        *,
        fact: str | None = None,
        needs_login: bool | None = None,
        needs_2fa: bool | None = None,
        account_hint: str | None = None,
        overlay: str | None = None,
    ) -> SiteKnowledge:
        """Add to what is known. Never replaces the whole record.

        Facts arrive one at a time, from different visits. Overwriting would mean the
        last thing noticed erases everything learned before it.
        """
        if fact:
            cleaned = fact.strip()
            if cleaned and cleaned not in self.notes:
                self.notes.append(cleaned)
        if overlay and overlay not in self.overlays:
            self.overlays.append(overlay)
        if needs_login is not None:
            self.needs_login = needs_login
        if needs_2fa is not None:
            self.needs_2fa = needs_2fa
        if account_hint:
            self.account_hint = account_hint
        self.updated_at = utc_now()
        return self

    @property
    def is_empty(self) -> bool:
        return not (self.notes or self.needs_login or self.needs_2fa or self.account_hint)

    def summary(self) -> list[str]:
        """What to hand an AI that is about to walk this site for the first time."""
        lines = list(self.notes)
        if self.needs_login:
            lines.append("this site needs a login")
        if self.needs_2fa:
            lines.append("this site asks for a second factor, such as a code")
        if self.account_hint:
            lines.append(f"the account used here is {self.account_hint}")
        return lines

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "notes": self.notes,
            "needs_login": self.needs_login,
            "needs_2fa": self.needs_2fa,
            "account_hint": self.account_hint,
            "overlays": self.overlays,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> SiteKnowledge:
        return cls(
            domain=raw["domain"],
            notes=raw.get("notes", []),
            needs_login=raw.get("needs_login", False),
            needs_2fa=raw.get("needs_2fa", False),
            account_hint=raw.get("account_hint"),
            overlays=list(raw.get("overlays", [])),
            updated_at=raw.get("updated_at", utc_now()),
        )


@dataclass
class RunMetrics:
    """What one run cost. The warm-versus-cold contrast is the whole pitch, so this
    is measured rather than asserted."""

    domain: str
    task: str
    mode: Literal["cold", "warm"]
    duration_ms: int = 0
    steps_total: int = 0
    steps_replayed: int = 0
    steps_repaired: int = 0
    tool_calls: int = 0
    model_calls: int = 0
    pages_read: int = 0
    succeeded: bool = False
    started_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "task": self.task,
            "mode": self.mode,
            "duration_ms": self.duration_ms,
            "steps_total": self.steps_total,
            "steps_replayed": self.steps_replayed,
            "steps_repaired": self.steps_repaired,
            "tool_calls": self.tool_calls,
            "model_calls": self.model_calls,
            "pages_read": self.pages_read,
            "succeeded": self.succeeded,
            "started_at": self.started_at,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> RunMetrics:
        return cls(
            domain=raw["domain"],
            task=raw["task"],
            mode=raw["mode"],
            duration_ms=raw.get("duration_ms", 0),
            steps_total=raw.get("steps_total", 0),
            steps_replayed=raw.get("steps_replayed", 0),
            steps_repaired=raw.get("steps_repaired", 0),
            tool_calls=raw.get("tool_calls", 0),
            model_calls=raw.get("model_calls", 0),
            pages_read=raw.get("pages_read", 0),
            succeeded=raw.get("succeeded", False),
            started_at=raw.get("started_at", utc_now()),
        )
