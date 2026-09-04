"""Cairn — a browser memory for AI agents.

Learn a site once, then replay the trail with no model calls.
All Sibyl Memory access lives in `cairn.store`.
"""

from .browser import Browser, Element, Snapshot, domain_of
from .distill import distill
from .events import Emitter, Event
from .executor import Executor, NoTrailError, RepairRequest, ReplayResult
from .models import (
    Control,
    Locator,
    PageMemory,
    Playbook,
    Postcondition,
    RunMetrics,
    SiteKnowledge,
    SiteMap,
    Step,
)
from .operations import Session
from .store import CairnStore

__version__ = "0.2.0"

__all__ = [
    "Browser",
    "CairnStore",
    "Control",
    "Element",
    "Emitter",
    "Event",
    "Executor",
    "Locator",
    "NoTrailError",
    "PageMemory",
    "Playbook",
    "Postcondition",
    "RepairRequest",
    "ReplayResult",
    "RunMetrics",
    "Session",
    "SiteKnowledge",
    "SiteMap",
    "Snapshot",
    "Step",
    "distill",
    "domain_of",
    "__version__",
]
