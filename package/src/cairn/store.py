"""THE MEMORY FILE.

Every read and write to Sibyl Memory in this entire project happens here. Nothing else
imports `sibyl_memory_client`. If you are judging this project and want to see whether the
memory is load-bearing, this one file is the whole answer — and `forget_site` below is the
deletion test.

How the tiers are used:

    WARM  set_entity("playbook", <domain>)         the trail: steps, locators, health
    WARM  set_entity("site_knowledge", <domain>)   facts that outlive a redesign
    COLD  write_event(...)                         every run, drift and repair, in order

Two deliberate choices worth knowing about:

1. Entities are keyed by domain, and Sibyl enforces uniqueness on
   (tenant_id, category, name) at the schema level. A site therefore cannot end up
   holding two conflicting trails.

2. Forgetting ARCHIVES, it does not delete. That matches Sibyl's own
   forgetting-versus-deleting doctrine: the agent stops being able to follow the trail,
   but the record of it having existed is recoverable.
"""

from __future__ import annotations

from typing import Any

from sibyl_memory_client import MemoryClient, NotFoundError

from .models import Playbook, RunMetrics, SiteKnowledge

PLAYBOOK = "playbook"
SITE_KNOWLEDGE = "site_knowledge"


class CairnStore:
    """A small, explicit wrapper over Sibyl Memory.

    Deliberately not clever. Each method is one Sibyl call plus serialisation, so the
    mapping between "what Cairn remembers" and "what Sibyl stores" stays readable.
    """

    def __init__(self, client: MemoryClient | None = None, *, db_path: str | None = None):
        """Uses Sibyl's default local database unless a path is given.

        Tests pass a temporary path so they never touch the developer's real memory.
        """
        if client is not None:
            self._memory = client
        elif db_path is not None:
            self._memory = MemoryClient.local(db_path)
        else:
            self._memory = MemoryClient.local()

    # ---------------------------------------------------------------- playbooks

    def save_playbook(self, playbook: Playbook) -> None:
        """WARM write. One trail per domain, overwritten in place as it improves."""
        self._memory.set_entity(PLAYBOOK, playbook.domain, playbook.to_dict())

    def load_playbook(self, domain: str) -> Playbook | None:
        """WARM read. `None` means we have never walked this site — or it was forgotten.

        The warm path lives or dies on this call. If it returns `None`, replay has
        nothing to follow and the caller has to explore from scratch.
        """
        body = self._read_entity_body(PLAYBOOK, domain)
        return Playbook.from_dict(body) if body else None

    def list_sites(self) -> list[str]:
        """Every domain Cairn currently knows a trail for."""
        entities = self._memory.list_entities(category=PLAYBOOK)
        return sorted(e["name"] for e in entities if not self._is_archived(e))

    def search_similar(self, query: str, *, limit: int = 5) -> list[str]:
        """Full-text search across stored trails, using Sibyl's FTS5 index.

        This is what lets an agent landing on an unfamiliar site ask whether anything
        like it has been walked before.
        """
        results = self._memory.search_entities(query, limit=limit, category=PLAYBOOK)
        hits = getattr(results, "entities", None) or getattr(results, "results", None) or []
        return [hit["name"] for hit in hits if "name" in hit]

    # ----------------------------------------------------------- site knowledge

    def save_site_knowledge(self, knowledge: SiteKnowledge) -> None:
        """WARM write. Survives a playbook being rebuilt from nothing."""
        self._memory.set_entity(SITE_KNOWLEDGE, knowledge.domain, knowledge.to_dict())

    def load_site_knowledge(self, domain: str) -> SiteKnowledge | None:
        body = self._read_entity_body(SITE_KNOWLEDGE, domain)
        return SiteKnowledge.from_dict(body) if body else None

    # ------------------------------------------------------------ cold journal

    def journal_run(self, metrics: RunMetrics) -> None:
        """COLD write. The time-ordered record of what every run actually cost."""
        self._memory.write_event(
            acted=[f"{metrics.mode} run on {metrics.domain}: {metrics.task}"],
            extra={"kind": "run", **metrics.to_dict()},
        )

    def journal_repair(self, domain: str, step_index: int, before: str, after: str) -> None:
        """COLD write. Every repair is recorded, so drift over time is inspectable."""
        self._memory.write_event(
            evaluated=[f"step {step_index} on {domain} no longer matched"],
            acted=[f"repaired step {step_index}: {before} -> {after}"],
            extra={
                "kind": "repair",
                "domain": domain,
                "step_index": step_index,
                "before": before,
                "after": after,
            },
        )

    def read_journal(self, *, limit: int = 50) -> list[dict[str, Any]]:
        """COLD read. Used by the CLI and the dashboard to show memory working."""
        return self._memory.read_events(limit=limit)

    # ------------------------------------------------------- the deletion test

    def forget_site(self, domain: str) -> bool:
        """Archive everything Cairn knows about one site.

        THIS IS THE GATE. After this call `load_playbook(domain)` returns `None`, so
        replay has nothing to follow and the agent is back to exploring from scratch.
        Archived rather than deleted, so the fact that a trail once existed is not lost.

        Returns True if anything was actually forgotten.
        """
        forgotten = False

        for category in (PLAYBOOK, SITE_KNOWLEDGE):
            try:
                self._memory.archive_entity(category, domain, reason="cairn forget")
                forgotten = True
            except NotFoundError:
                continue

        if forgotten:
            self._memory.write_event(
                acted=[f"forgot everything about {domain}"],
                extra={"kind": "forget", "domain": domain},
            )

        return forgotten

    # ------------------------------------------------------------------ helpers

    def _read_entity_body(self, category: str, name: str) -> dict[str, Any] | None:
        """Reads one entity, treating missing and archived alike as 'we do not know'."""
        try:
            entity = self._memory.get_entity(category, name)
        except NotFoundError:
            return None

        if entity is None or self._is_archived(entity):
            return None

        body = entity.get("body") if isinstance(entity, dict) else None
        return body if isinstance(body, dict) else None

    @staticmethod
    def _is_archived(entity: dict[str, Any]) -> bool:
        return str(entity.get("status", "")).lower() == "archived"
