"""Cairn — a browser memory for AI agents.

Learn a site once, then replay the trail with no model calls.
All Sibyl Memory access lives in `cairn.store`.
"""

from .browser import Browser, Element, Snapshot, domain_of
from .distill import distill
from .events import Emitter, Event
from .executor import Executor, NoTrailError, RepairRequest, ReplayResult
from .models import (
    Locator,
    Playbook,
    Postcondition,
    RunMetrics,
    SiteKnowledge,
    Step,
)
from .operations import Session
from .store import CairnStore

__version__ = "0.1.0"

__all__ = [
    "Browser",
    "CairnStore",
    "Element",
    "Emitter",
    "Event",
    "Executor",
    "Locator",
    "NoTrailError",
    "Playbook",
    "Postcondition",
    "RepairRequest",
    "ReplayResult",
    "RunMetrics",
    "Session",
    "SiteKnowledge",
    "Snapshot",
    "Step",
    "distill",
    "domain_of",
    "__version__",
]
