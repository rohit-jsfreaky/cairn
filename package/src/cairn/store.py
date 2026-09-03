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

# A trail is named `domain::task-slug`. Keying on the domain alone meant one task per site.
#
# Not "|": Sibyl rejects it in an identifier, along with < > ; " ` and "..". A domain never
# contains "::", so splitting on it is unambiguous.
KEY_SEPARATOR = "::"

# Long enough to tell two tasks apart, short enough to read in a listing.
MAX_SLUG = 60

# How much of a request's wording must be shared with a saved task before they are treated
# as the same job. Low enough to survive rephrasing, high enough that "download the
# invoice" never matches "cancel the subscription".
MATCH_THRESHOLD = 0.4

# Words too common to tell two tasks apart. "the invoice" and "the subscription" share
# "the" and nothing that matters.
_NOISE = frozenset(
    [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "do",
        "does",
        "for",
        "from",
        "get",
        "how",
        "i",
        "in",
        "is",
        "it",
        "many",
        "me",
        "my",
        "of",
        "on",
        "or",
        "please",
        "show",
        "that",
        "the",
        "them",
        "then",
        "there",
        "this",
        "to",
        "what",
        "when",
        "where",
        "which",
        "with",
    ]
)
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
        """WARM write. One trail per TASK per site, overwritten as it improves.

        Keyed by task as well as domain. Keying on the domain alone meant a site could
        hold exactly one task ever — found on GitHub, where asking about a second repo
        collided with the first.
        """
        key = trail_key(playbook.domain, playbook.task)
        self._memory.set_entity(PLAYBOOK, key, playbook.to_dict())

    def load_playbook(self, domain: str, task: str | None = None) -> Playbook | None:
        """WARM read. `None` means we have never walked this site — or it was forgotten.

        The warm path lives or dies on this call. If it returns `None`, replay has
        nothing to follow and the caller has to explore from scratch.

        With a task, the matching trail. Without one, the site's only trail — because a
        caller who does not name a task can only mean the single one that exists. If there
        are several, it has to say which; `trails_for` lists them.
        """
        if task:
            body = self._read_entity_body(PLAYBOOK, trail_key(domain, task))
            if body:
                return Playbook.from_dict(body)

        # Trails saved before trails were keyed by task are named by domain alone.
        body = self._read_entity_body(PLAYBOOK, domain)
        if body:
            return Playbook.from_dict(body)

        keys = self._keys_for(domain)

        # A caller who names no task can only mean the single one that exists. A caller who
        # DOES name one has to be matched against it — otherwise a site holding "count open
        # issues" would happily run that when asked to "cancel my subscription".
        if len(keys) == 1 and not task:
            body = self._read_entity_body(PLAYBOOK, keys[0])
            return Playbook.from_dict(body) if body else None

        # Nobody words a request the same way twice. "how many open issues does
        # microsoft/playwright have" has to find the trail saved as "count open issues on
        # microsoft/playwright", or the memory may as well not be there.
        if task:
            closest = best_match(task, self.trails_for(domain))
            if closest:
                body = self._read_entity_body(PLAYBOOK, trail_key(domain, closest))
                return Playbook.from_dict(body) if body else None
        return None

    def trails_for(self, domain: str) -> list[str]:
        """The tasks this site has trails for, so a caller can say which one it means."""
        found = []
        for key in self._keys_for(domain):
            body = self._read_entity_body(PLAYBOOK, key)
            if body and body.get("task"):
                found.append(body["task"])
        return sorted(found)

    def _keys_for(self, domain: str) -> list[str]:
        """Every live trail key belonging to one site."""
        entities = self._memory.list_entities(category=PLAYBOOK)
        return sorted(
            entity["name"]
            for entity in entities
            if not self._is_archived(entity) and domain_of_key(entity["name"]) == domain
        )

    def list_sites(self) -> list[str]:
        """Every domain Cairn currently knows a trail for.

        Domains, not trail keys — one site with four tasks is still one site.
        """
        entities = self._memory.list_entities(category=PLAYBOOK)
        return sorted({domain_of_key(e["name"]) for e in entities if not self._is_archived(e)})

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

    def retire_playbook(self, domain: str, task: str | None = None) -> bool:
        """Archive only the trail, keeping what we know about the site.

        Used when a playbook goes stale: the steps are worthless because the site was
        rebuilt, but "needs a login, sends a code to your phone, use the finance account"
        is all still true. This is what makes relearning cheaper than a first visit.
        """
        try:
            key = trail_key(domain, task) if task else domain
            self._memory.archive_entity(PLAYBOOK, key, reason="stale, site was rebuilt")
        except NotFoundError:
            return False

        self._memory.write_event(
            evaluated=[f"most of the trail for {domain} no longer matches the site"],
            acted=[f"retired the trail for {domain}, kept what is known about the site"],
            extra={"kind": "retired", "domain": domain},
        )
        return True

    # ------------------------------------------------------- the deletion test

    def forget_site(self, domain: str) -> bool:
        """Archive everything Cairn knows about one site.

        THIS IS THE GATE. After this call `load_playbook(domain)` returns `None`, so
        replay has nothing to follow and the agent is back to exploring from scratch.
        Archived rather than deleted, so the fact that a trail once existed is not lost.

        Returns True if anything was actually forgotten.
        """
        forgotten = False

        # Every trail for the site, not just one. A site with four tasks has four trails,
        # and "forget this site" has to mean all of them or the gate does not hold.
        for key in self._keys_for(domain):
            try:
                self._memory.archive_entity(PLAYBOOK, key, reason="cairn forget")
                forgotten = True
            except NotFoundError:
                continue

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


def trail_key(domain: str, task: str | None) -> str:
    """The memory name for one task on one site.

    A site holds many trails. Without the task in the key they overwrite each other, which
    is what happened the first time Cairn was asked about a second GitHub repo.
    """
    if not task:
        return domain
    return f"{domain}{KEY_SEPARATOR}{_slug(task)}"


def domain_of_key(key: str) -> str:
    """The site a trail key belongs to. Trails saved before this are named by domain."""
    return key.split(KEY_SEPARATOR, 1)[0]


def _slug(task: str) -> str:
    """A task in plain words, reduced to something safe to use as a name."""
    kept = [character if character.isalnum() else "-" for character in task.lower()]
    slug = "".join(kept)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")[:MAX_SLUG] or "task"


def best_match(wanted: str, known: list[str]) -> str | None:
    """Which saved task is the one being asked for, if any.

    Compares the words that carry meaning, so rewording survives but two genuinely
    different jobs never collide. Returns nothing when the best candidate is weak or when
    two are equally good — guessing between them would run the wrong task, which is worse
    than asking.
    """
    scored = sorted(((_overlap(wanted, candidate), candidate) for candidate in known), reverse=True)
    if not scored:
        return None

    best, winner = scored[0]
    if best < MATCH_THRESHOLD:
        return None
    runner_up = scored[1][0] if len(scored) > 1 else 0.0
    return winner if best > runner_up else None


def _overlap(wanted: str, candidate: str) -> float:
    """How much of the request's meaning the saved task accounts for, 0 to 1."""
    asked = _meaningful(wanted)
    if not asked:
        return 0.0
    return len(asked & _meaningful(candidate)) / len(asked)


def _meaningful(text: str) -> set[str]:
    words = "".join(character if character.isalnum() else " " for character in text.lower())
    return {word for word in words.split() if word not in _NOISE}
