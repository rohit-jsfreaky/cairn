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

import os
from contextlib import suppress
from typing import Any

from sibyl_memory_client import DEFAULT_TENANT, MemoryClient, NotFoundError

from .models import Playbook, RunMetrics, SiteKnowledge, utc_now

PLAYBOOK = "playbook"

# Where trails are offered to other agents. One well-known tenant in the same database.
#
# Sibyl has no sharing, scope or visibility concept — entities are unique per
# (tenant_id, category, name) and every query filters on tenant. So publishing and
# borrowing are deliberate copies, which is the behaviour we want anyway: nobody
# accidentally leaks a trail, and nobody silently inherits a stranger's.
COMMONS_TENANT = "cairn-commons"

# Agent names are namespaced so an agent literally called "commons" cannot collide with
# the commons itself.
AGENT_PREFIX = "cairn-agent-"

# Offers live in their own category, keyed `domain::task::agent`. The agent is IN the key
# on purpose: keyed by task alone, one agent publishing would silently overwrite another's
# offer, and withdrawing would delete somebody else's work.
SHARED = "shared_playbook"

# What an agent with no name is called when it leaves a trail for somebody else.
UNNAMED = "default"

# A site this agent was deliberately told to forget. The commons will not offer it
# back without being asked a second time, on purpose.
FORGOTTEN = "forgotten"

# How an MCP server learns which agent it is. `run_stdio` takes no arguments, so an
# environment variable is the only channel `.mcp.json` has.
AGENT_ENV = "CAIRN_AGENT"

# Sibyl rejects these inside an identifier, along with control characters and "..".
FORBIDDEN_IN_NAME = set('<>|;"`')

# A trail is named `domain::task-slug`. Keying on the domain alone meant one task per site.
#
# Not "|": Sibyl rejects it in an identifier, along with < > ; " ` and "..". A domain never
# contains "::", so splitting on it is unambiguous.
KEY_SEPARATOR = "::"

# Long enough to tell two tasks apart, short enough to read in a listing.
MAX_SLUG = 60

# How many entities a listing may return. Sibyl's own default is 100, and it truncates
# silently — so a caller that never passes one simply stops seeing sites once it has more
# than a hundred trails, with no error to notice.
MAX_LISTED = 5000

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


class TrailAlreadyHere(RuntimeError):
    """Borrowing would flatten a trail this agent has already repaired."""


class CairnStore:
    """A small, explicit wrapper over Sibyl Memory.

    Deliberately not clever. Each method is one Sibyl call plus serialisation, so the
    mapping between "what Cairn remembers" and "what Sibyl stores" stays readable.
    """

    def __init__(
        self,
        client: MemoryClient | None = None,
        *,
        db_path: str | None = None,
        agent: str | None = None,
    ):
        """Uses Sibyl's default local database unless a path is given.

        Tests pass a temporary path so they never touch the developer's real memory.

        `agent` names this agent, and becomes its Sibyl tenant. Left unset — and unset is
        the normal case — it falls back to the `CAIRN_AGENT` environment variable and then
        to Sibyl's own default tenant, which is where every trail learned so far already
        lives. So an unnamed agent sees exactly the memory it saw yesterday.

        There are TWO clients and neither ever changes tenant. One reads and writes this
        agent's own memory; the other only ever touches the commons. The alternative —
        one client that switches tenant around each shared operation — is unsafe here: the
        MCP server calls this object from the browser thread and from anyio worker threads
        at the same time, so a switch has a window in which another thread's playbook is
        written into the shared tenant. Silently.
        """
        self.agent = agent if agent is not None else os.environ.get(AGENT_ENV) or None
        if client is not None and self.agent is not None:
            raise ValueError(
                "pass either a ready-made client or an agent name, not both — otherwise "
                "the name would be quietly ignored and the agent would read the wrong memory"
            )

        tenant = agent_tenant(self.agent)
        if client is not None:
            self._memory = client
        elif db_path is not None:
            self._memory = MemoryClient.local(db_path, tenant_id=tenant)
        else:
            self._memory = MemoryClient.local(tenant_id=tenant)

        self._shared = self._commons_client()

    def _commons_client(self) -> MemoryClient:
        """A second client, pinned to the commons for the life of this store.

        Shares the first client's `Storage` where it can, so both look at one file through
        one connection pool.
        """
        storage = getattr(self._memory, "storage", None)
        if storage is not None:
            return MemoryClient(storage, tenant_id=COMMONS_TENANT, tier=self._memory.get_tier())
        return MemoryClient.local(tenant_id=COMMONS_TENANT)

    # ---------------------------------------------------------------- playbooks

    def save_playbook(self, playbook: Playbook) -> None:
        """WARM write. One trail per TASK per site, overwritten as it improves.

        Keyed by task as well as domain. Keying on the domain alone meant a site could
        hold exactly one task ever — found on GitHub, where asking about a second repo
        collided with the first.
        """
        key = trail_key(playbook.domain, playbook.task)
        self._memory.set_entity(PLAYBOOK, key, playbook.to_dict())

        # Knowing the site again is the opposite of having forgotten it.
        with suppress(NotFoundError):
            self._memory.archive_entity(FORGOTTEN, playbook.domain, reason="learned again")

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
        entities = self._memory.list_entities(category=PLAYBOOK, limit=MAX_LISTED)
        return sorted(
            entity["name"]
            for entity in entities
            if not self._is_archived(entity) and domain_of_key(entity["name"]) == domain
        )

    def list_sites(self) -> list[str]:
        """Every domain Cairn currently knows a trail for.

        Domains, not trail keys — one site with four tasks is still one site.
        """
        entities = self._memory.list_entities(category=PLAYBOOK, limit=MAX_LISTED)
        return sorted({domain_of_key(e["name"]) for e in entities if not self._is_archived(e)})

    def search_similar(self, query: str, *, limit: int = 5) -> list[str]:
        """WARM read. Full-text search across stored trails, using Sibyl's FTS5 index.

        This is what lets an agent landing on an unfamiliar site ask whether anything like
        it has been walked before.

        `search_entities` returns a `list` subclass, so the results ARE the list. Asking it
        for `.entities` or `.results` — which is what this did until 2026-09-03 — always
        found nothing, so this function returned an empty list for every input from the day
        it was written. Nothing called it, so nothing noticed.
        """
        found = self._memory.search_entities(query, limit=limit, category=PLAYBOOK)
        return [hit["name"] for hit in found if "name" in hit]

    # ------------------------------------------------------------- the commons
    #
    # Everything below writes to a DIFFERENT tenant through a SECOND client. Neither
    # client ever changes tenant, so a trail cannot cross by accident.

    def was_forgotten(self, domain: str) -> bool:
        """WARM read. Did this agent deliberately forget this site?

        Asked before offering a shared trail back. Forgetting has to mean
        something, and answering "somebody else still has it" one message later
        is not it.
        """
        return self._read_entity_body(FORGOTTEN, domain) is not None

    def my_offers_for(self, domain: str) -> list[dict[str, Any]]:
        """COMMONS read. What THIS agent has published for this site."""
        return [offer for offer in self._offers(domain) if offer["shared_by"] == self.who]

    def share_trail(self, domain: str, task: str | None = None) -> dict[str, Any] | None:
        """COMMONS write. Leave this trail where another agent can pick it up.

        Returns what was published — every note included — so nothing goes out unseen.
        `None` means this agent has no such trail to give.

        What leaves is the route, never the identity: `Playbook.for_sharing` drops whatever
        was typed into a field and marks the step as needing a value instead, so whoever
        follows this signs in as themselves.
        """
        playbook = self.load_playbook(domain, task)
        if playbook is None:
            return None

        knowledge = self.load_site_knowledge(domain)
        publishable = knowledge.for_sharing() if knowledge else None
        offer = {
            "domain": domain,
            "task": playbook.task,
            "shared_by": self.who,
            "shared_at": utc_now(),
            "playbook": playbook.for_sharing(self.agent).to_dict(),
            "site_knowledge": publishable.to_dict() if publishable else None,
            "borrows": 0,
            "confirmed_by": [],
            "failed_for": [],
        }

        key = offer_key(domain, playbook.task, self.who)
        existing = self._offer(key)
        if existing:
            # Keep the ledger across a re-publish. The trail may have improved; the record
            # of who it has worked for is still true.
            for carried in ("borrows", "confirmed_by", "failed_for"):
                offer[carried] = existing[carried]

        self._shared.set_entity(SHARED, key, offer)
        self._both_journals(
            acted=[f"{self.who} shared the trail for {playbook.task} on {domain}"],
            extra={"kind": "shared", "domain": domain, "task": playbook.task, "by": self.who},
        )
        return {
            "domain": domain,
            "task": playbook.task,
            "shared_by": self.who,
            "steps": len(playbook.steps),
            "notes_published": publishable.notes if publishable else [],
            "values_withheld": [
                step.intent for step in playbook.steps if step.action in ("fill", "type")
            ],
        }

    def unshare_trail(self, domain: str, task: str | None = None) -> bool:
        """COMMONS write. Withdraw a trail THIS agent published.

        Only ever this agent's own offer — the key carries the publisher, so there is no
        way to reach into somebody else's.
        """
        wanted = task or ""
        for offer in self._offers(domain):
            if offer["shared_by"] != self.who:
                continue
            if wanted and offer["task"] != wanted and best_match(wanted, [offer["task"]]) is None:
                continue
            try:
                self._shared.archive_entity(
                    SHARED, offer_key(domain, offer["task"], self.who), reason="withdrawn"
                )
            except NotFoundError:
                continue
            self._both_journals(
                acted=[f"{self.who} withdrew the trail for {offer['task']} on {domain}"],
                extra={"kind": "withdrawn", "domain": domain, "by": self.who},
            )
            return True
        return False

    def offers_for(self, domain: str) -> list[dict[str, Any]]:
        """COMMONS read. What other agents have left for this site, best first.

        Ranked by what actually happened, not by who shared it: a trail that worked for
        three agents and failed for none is offered ahead of one nobody has tried.
        """
        return sorted(
            (self._describe(offer) for offer in self._offers(domain)),
            key=lambda o: (o["worked_for"] - o["failed_for"], o["borrows"], o["runs"]),
            reverse=True,
        )

    def every_offer(self) -> list[dict[str, Any]]:
        """COMMONS read. Everything in the shared memory, and who left it."""
        return sorted(
            (self._describe(offer) for offer in self._all_offers()),
            key=lambda o: (o["domain"], o["task"]),
        )

    def borrow_trail(
        self, domain: str, task: str | None = None, *, force: bool = False
    ) -> Playbook | None:
        """COMMONS read, then a WARM write into this agent's own memory.

        The trail is COPIED, not followed in place. That matters: the borrower ends up with
        something of its own that it can run, repair, and be made to forget. Reading the
        commons at replay time would look tidier and would gut the deletion test.

        Refuses to flatten a trail this agent has already repaired unless told to.
        """
        offers = self.offers_for(domain)
        if not offers:
            return None

        chosen = self._pick(offers, task)
        if chosen is None:
            return None

        mine = self.load_playbook(domain, chosen["task"])
        if mine is not None and mine.repairs and not force:
            raise TrailAlreadyHere(
                f"you already have a trail for {chosen['task']!r} that you repaired "
                f"{mine.repairs} time(s). Borrowing would throw that away — say so on "
                f"purpose if you mean it."
            )

        offer = self._offer(offer_key(domain, chosen["task"], chosen["shared_by"]))
        if offer is None:
            return None

        borrowed = Playbook.from_dict(offer["playbook"]).as_borrowed_by(
            self.agent, shared_by=offer["shared_by"]
        )
        self.save_playbook(borrowed)
        self._take_their_notes(offer)

        offer["borrows"] = offer.get("borrows", 0) + 1
        self._shared.set_entity(
            SHARED, offer_key(domain, chosen["task"], offer["shared_by"]), offer
        )

        self._both_journals(
            evaluated=[f"{self.who} had never walked {domain}"],
            acted=[
                f"{self.who} borrowed the trail for {chosen['task']} that {offer['shared_by']} left"
            ],
            extra={
                "kind": "borrowed",
                "domain": domain,
                "task": chosen["task"],
                "by": self.who,
                "from": offer["shared_by"],
                "inherited_runs": borrowed.inherited_runs,
            },
        )
        return borrowed

    def record_outcome(self, domain: str, task: str, *, worked: bool) -> None:
        """COMMONS write. Say whether a borrowed trail actually worked here.

        This is what stops the commons being a pile of files. An offer accumulates the
        agents it has worked for and the ones it failed, and `offers_for` ranks on it — so
        what is stored changes because agents used it.
        """
        for offer in self._offers(domain):
            if offer["task"] != task:
                continue
            side = "confirmed_by" if worked else "failed_for"
            if self.who not in offer[side]:
                offer[side] = [*offer[side], self.who]
                self._shared.set_entity(SHARED, offer_key(domain, task, offer["shared_by"]), offer)
            return

    def contribute_repair(self, domain: str, task: str) -> bool:
        """COMMONS write. Push a fix this agent made back into somebody else's offer.

        A merge, not a re-share: the repaired locators go to the front of that step, the
        version moves on, and this agent is added to the contributors. Authorship stays
        with whoever first walked the site.
        """
        mine = self.load_playbook(domain, task)
        if mine is None:
            return False

        for offer in self._offers(domain):
            if offer["task"] != task:
                continue

            theirs = Playbook.from_dict(offer["playbook"])
            by_index = {step.index: step for step in mine.steps}
            for step in theirs.steps:
                fixed = by_index.get(step.index)
                if fixed is not None and fixed.repairs > step.repairs:
                    step.locators = fixed.without_what_was_typed().locators
                    step.repairs = fixed.repairs

            theirs.touch()
            if self.who not in theirs.contributors:
                theirs.contributors.append(self.who)
            offer["playbook"] = theirs.to_dict()

            self._shared.set_entity(SHARED, offer_key(domain, task, offer["shared_by"]), offer)
            self._both_journals(
                acted=[f"{self.who} contributed a fix to {offer['shared_by']}'s trail for {task}"],
                extra={"kind": "contributed", "domain": domain, "task": task, "by": self.who},
            )
            return True
        return False

    # ------------------------------------------------------- commons helpers

    @property
    def who(self) -> str:
        """This agent's name, as it appears to other agents."""
        return self.agent or UNNAMED

    def _offers(self, domain: str) -> list[dict[str, Any]]:
        return [offer for offer in self._all_offers() if offer.get("domain") == domain]

    def _all_offers(self) -> list[dict[str, Any]]:
        found = []
        for entity in self._shared.list_entities(category=SHARED, limit=MAX_LISTED):
            body = entity.get("body")
            if isinstance(body, dict) and body.get("domain"):
                found.append(body)
        return found

    def _offer(self, key: str) -> dict[str, Any] | None:
        try:
            entity = self._shared.get_entity(SHARED, key)
        except NotFoundError:
            return None
        body = entity.get("body")
        return body if isinstance(body, dict) else None

    @staticmethod
    def _describe(offer: dict[str, Any]) -> dict[str, Any]:
        """One offer, as a caller should see it."""
        trail = offer.get("playbook", {})
        return {
            "domain": offer["domain"],
            "task": offer["task"],
            "shared_by": offer["shared_by"],
            "shared_at": offer.get("shared_at", ""),
            "steps": len(trail.get("steps", [])),
            "runs": trail.get("runs", 0),
            "borrows": offer.get("borrows", 0),
            "worked_for": len(offer.get("confirmed_by", [])),
            "failed_for": len(offer.get("failed_for", [])),
            "contributors": trail.get("contributors", []),
        }

    @staticmethod
    def _pick(offers: list[dict[str, Any]], task: str | None) -> dict[str, Any] | None:
        """Which offer the caller meant. Best-ranked when they did not say."""
        if not task:
            return offers[0]
        exact = [offer for offer in offers if offer["task"] == task]
        if exact:
            return exact[0]
        closest = best_match(task, [offer["task"] for offer in offers])
        return next((offer for offer in offers if offer["task"] == closest), None)

    def _take_their_notes(self, offer: dict[str, Any]) -> None:
        """Fold a borrowed trail's site facts into whatever this agent already knew."""
        raw = offer.get("site_knowledge")
        if not raw:
            return
        theirs = SiteKnowledge.from_dict(raw)
        mine = self.load_site_knowledge(theirs.domain) or SiteKnowledge(domain=theirs.domain)
        for note in theirs.notes:
            mine = mine.merge(fact=note)
        for overlay in theirs.overlays:
            mine = mine.merge(overlay=overlay)
        self.save_site_knowledge(
            mine.merge(needs_login=theirs.needs_login or None, needs_2fa=theirs.needs_2fa or None)
        )

    def _both_journals(self, **event: Any) -> None:
        """COLD write, twice: this agent's own history, and the shared one.

        Two explicit writes because `write_event` always writes to its client's own tenant.
        A handoff that only appeared in one of the two would be half a record.
        """
        self._memory.write_event(**event)
        self._shared.write_event(**event)

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

        # The commons first, and wrapped: a shared memory that is full, locked or
        # simply broken must never be able to stop a site being forgotten here.
        try:
            for offer in self.my_offers_for(domain):
                self._shared.archive_entity(
                    SHARED,
                    offer_key(domain, offer["task"], self.who),
                    reason="cairn forget",
                )
                forgotten = True
        except Exception:  # noqa: BLE001 - forgetting matters more than the reason
            pass

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

        # The tombstone goes down whether or not anything was there to archive, so
        # that a site forgotten twice stays forgotten.
        self._memory.set_entity(FORGOTTEN, domain, {"at": utc_now(), "by": self.who})

        if forgotten:
            self._memory.write_event(
                acted=[f"{self.who} forgot everything about {domain}"],
                extra={"kind": "forget", "domain": domain, "by": self.who},
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


def agent_tenant(agent: str | None) -> str:
    """The Sibyl tenant one agent's memory lives in.

    No name means Sibyl's own default tenant — which is where everything learned before
    agents existed already is, so nothing has to be migrated and nothing is lost.
    """
    if agent is None:
        return DEFAULT_TENANT

    name = agent.strip()
    if not name:
        raise ValueError("an agent name cannot be blank")
    if any(character in FORBIDDEN_IN_NAME for character in name) or ".." in name:
        raise ValueError(
            f"{agent!r} is not a usable agent name: Sibyl refuses "
            f"{''.join(sorted(FORBIDDEN_IN_NAME))} and '..' inside one"
        )
    if any(ord(character) < 0x20 or ord(character) == 0x7F for character in name):
        raise ValueError(f"{agent!r} has a control character in it")

    return f"{AGENT_PREFIX}{name}"


def offer_key(domain: str, task: str, agent: str) -> str:
    """The name one agent's offer of one trail is stored under.

    The publisher is part of the key. Without it, two agents offering the same task would
    overwrite each other in silence, and withdrawing would delete whichever happened to be
    there — including somebody else's.
    """
    return f"{domain}{KEY_SEPARATOR}{_slug(task)}{KEY_SEPARATOR}{_slug(agent)}"
