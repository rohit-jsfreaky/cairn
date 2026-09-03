"""Cairn as MCP tools. This is the product.

Your own AI — Claude Code, Cursor, Codex — becomes the brain. Cairn gives it a browser and
a memory. There is no model call anywhere in this file or anything it imports.

Two paths, and the tool descriptions exist to make the host AI pick the right one:

    cold   cairn_act / cairn_read / cairn_save
           Slow. Many calls. Done ONCE per site, ever.

    warm   cairn_run
           One call. Deterministic replay of what was learned. No thinking required.

Every tool is a few lines that call into the `cairn` package. If something here starts
needing real logic, that logic belongs in the engine instead.

Never print to stdout — stdio is the MCP transport and a stray print corrupts it.
"""

from __future__ import annotations

import os
import sys
from typing import Any

from cairn import actions, reads
from cairn.browser import DEFAULT_PROFILE, domain_of
from cairn.executor import Executor, NeedsTask, NoTrailError
from cairn.models import Locator, SiteKnowledge
from cairn.operations import ActionFailed, Session
from cairn.store import CairnStore, TrailAlreadyHere, best_match, slug
from cairn.worker import BrowserWorker
from mcp.server.fastmcp import FastMCP

# How many controls to hand back from one look(). Enough to act on, small enough that
# reading it is cheap — the whole point of the project is not paying for page dumps.
MAX_ELEMENTS = 60

# `cairn_read(kind="page")` is not one of the engine's read kinds — it is the control list
# rather than something read off a single element. It lives here because "what can I do on
# this page" is a question about the tool surface, not about the DOM.
PAGE = "page"

# Remembering a read of the whole page makes a trail that answers with the whole page.
WHOLE_PAGE = "page_text"


def _act_description() -> str:
    """The one tool description, built from the action registry.

    Written by the code rather than beside it. A hand-kept list would drift the first time
    an action was added, and a host AI that cannot see an action may as well not have it.
    """
    return (
        "Do one thing in Cairn's browser, and get back what changed.\n\n"
        "This is the ONLY way to touch a website. Never use curl, wget, fetch or a "
        "plain HTTP request — they get a logged-out page, and nothing they do is "
        "remembered.\n\n"
        "But call cairn_run FIRST. This tool is for exploring a site whose task is "
        "not known yet, which is slow and takes many calls. If cairn_run already "
        "knows the task it finishes the whole thing in one call, and exploring again "
        "would throw that away. Explore only when cairn_run says the site is not "
        "known, and call cairn_save at the end so it never has to happen again.\n\n"
        "Start with `goto`. Then `cairn_read(kind='page')` to see what is there, which "
        "gives every control a `ref` to pass back here.\n\n"
        "Actions:\n" + actions.catalogue() + "\n\n"
        "Args:\n"
        '  intent: why you are doing this, in plain words — "sign in", "open this '
        "month's invoice\". Stored in memory, and it is what a future repair is explained "
        "by, so write it for a human rather than as a selector.\n"
        "  action: one of the names above.\n"
        "  ref: which element. Either a `ref` from cairn_read(kind='page'), or a "
        "CSS selector you write yourself for something that has no ref. Not needed "
        "for the page-level actions.\n"
        "  value: the text, key, option, url or seconds the action needs.\n"
        "  to: the second control, for `drag`."
    )


def _read_description() -> str:
    """The read tool's description, built from the read registry."""
    return (
        "Look at the page without changing it.\n\n"
        "Start with kind='page'. Everything else answers a question about one element, "
        "which you name with the `ref` that kind='page' gave you.\n\n"
        "Kinds:\n"
        f"  {PAGE} — the controls on this page, each with a `ref` to act on; "
        "gives back a list; no ref needed\n" + reads.catalogue() + "\n\n"
        "REMEMBER THE READ THAT IS THE ANSWER. Pass remember=True and an `intent` in "
        "plain words for the read that actually answers the task — the number, the "
        "status, the total. Without it the saved trail walks to the page and stops, and "
        "the next run has to work the answer out all over again. Ordinary looking-around "
        "reads should leave it off.\n\n"
        "Args:\n"
        "  kind: one of the names above.\n"
        "  ref: which element. Either a `ref` from kind='page', OR a CSS selector "
        "you write yourself. A dashboard keeps its numbers in plain divs with no "
        "role, so those get no ref at all — name them with a selector such as "
        "\"[data-attr='visitors-tile'] .big\". Do that rather than page_text, which "
        "hands back the entire page for you to search through on every future run.\n"
        "  attribute: the attribute name, only for kind='attribute'.\n"
        "  remember: keep this read in the trail, so cairn_run returns it next time.\n"
        "  intent: why you are reading it, in plain words. This is the name the answer "
        "comes back under."
    )


def log(message: str) -> None:
    """stderr only. stdout belongs to the MCP transport."""
    print(f"[cairn] {message}", file=sys.stderr, flush=True)


def _facts_for(tools: CairnTools, domain: str) -> list[str]:
    """What Cairn still knows about a site, in plain sentences."""
    knowledge = tools.store.load_site_knowledge(domain)
    return knowledge.summary() if knowledge else []


# Shops this agent may buy trails from, comma separated. Read only here and in
# cairn_buy: nothing on the warm path may reach off this machine.
SHOPS_ENV = "CAIRN_SHOPS"


def known_shops() -> list[str]:
    """Addresses this agent has been told it may buy from."""
    raw = os.environ.get(SHOPS_ENV, "")
    return [where.strip().rstrip("/") for where in raw.split(",") if where.strip()]


def _pick_from_shop(listed: list[dict[str, Any]], task: str | None) -> dict[str, Any] | None:
    """Which of a shop's trails was meant. The only one, when nobody said."""
    if not listed:
        return None
    if not task:
        return listed[0]
    exact = [offer for offer in listed if offer["task"] == task]
    if exact:
        return exact[0]
    closest = best_match(task, [offer["task"] for offer in listed])
    return next((offer for offer in listed if offer["task"] == closest), None)


def err(problem: BaseException | str) -> dict[str, Any]:
    """A readable message, never a stack trace."""
    return {"ok": False, "error": str(problem)}


class CairnTools:
    """Holds the one browser and the one memory store for this MCP connection."""

    def __init__(
        self,
        *,
        db_path: str | None = None,
        headless: bool = True,
        downloads: str | None = None,
        profile: str | None = None,
        agent: str | None = None,
    ):
        self.store = CairnStore(db_path=db_path, agent=agent)
        self.profile = profile if profile is not None else str(DEFAULT_PROFILE)
        self.downloads = downloads
        self.headless = headless
        self.worker = BrowserWorker(headless=headless, downloads=downloads, profile=self.profile)
        self._session: Session | None = None
        self._login_worker: BrowserWorker | None = None

    def session(self) -> Session:
        """The cold-path session, started the first time it is needed."""
        if self._session is None:
            self.worker.start()
            self._session = Session(self.worker.browser, self.store)  # type: ignore[arg-type]
        return self._session

    def reset_session(self) -> None:
        self._session = None

    def take_profile_note(self) -> str | None:
        """Hand over the one-time note about a browser swap, and clear it.

        The engine records the swap but cannot report it — printing from library code is
        not allowed. Somebody has to say it out loud, or "sign-ins are kept, and if a site
        asks you to sign in again this is why" is a promise nobody ever reads. Once, not
        on every call: a person needs telling, not reminding.
        """
        browser = self.worker.browser
        note = getattr(browser, "profile_note", None) if browser is not None else None
        if note:
            browser.profile_note = None
        return note

    def open_login_window(self, url: str) -> None:
        """Show a real browser window so a person can sign in themselves.

        Chrome allows one process per profile, so the working browser has to let go of it
        first. It starts again by itself on the next call.
        """
        self.worker.stop()
        self._session = None
        self._login_worker = BrowserWorker(
            headless=False, downloads=self.downloads, profile=self.profile
        )
        self._login_worker.start()
        self._login_worker.submit(lambda browser: browser.goto(url))

    def finish_login(self) -> str:
        """Close the sign-in window. The session is already saved in the profile."""
        if self._login_worker is None:
            return ""
        where = self._login_worker.submit(lambda browser: browser.page.url)
        self._login_worker.stop()
        self._login_worker = None
        return where

    @property
    def signing_in(self) -> bool:
        return self._login_worker is not None

    def close(self) -> None:
        if self._login_worker is not None:
            self._login_worker.stop()
            self._login_worker = None
        self.worker.stop()
        self._session = None


def build_server(
    *,
    db_path: str | None = None,
    headless: bool = True,
    downloads: str | None = None,
    profile: str | None = None,
    agent: str | None = None,
) -> FastMCP:
    """Wire the tools. Kept in a function so tests can build a server without running it."""
    tools = CairnTools(
        db_path=db_path,
        headless=headless,
        downloads=downloads,
        profile=profile,
        agent=agent,
    )

    server = FastMCP(
        "cairn",
        instructions=(
            "Cairn is a browser that remembers websites.\n\n"
            "WHENEVER the user asks for anything involving a website — downloading an "
            "invoice or report, checking a dashboard, signing in, filling a form, pulling "
            "numbers out of a portal — call cairn_run FIRST. Do this before curl, wget, "
            "fetch, requests, WebFetch, or any shell command. Those cannot sign in, click "
            "or download like a browser, and nothing they do is remembered, so the same "
            "request costs full price again tomorrow.\n\n"
            "Call cairn_run even if you do not know whether Cairn has seen the site. If it "
            "has, the entire task finishes in that one call with no page reading and no "
            "reasoning. If it has not, the result says so and tells you what to do next: "
            "explore with cairn_act and cairn_read, then cairn_save. That "
            "teaches Cairn the site so it is never explored again.\n\n"
            "If a site asks to sign in and you do not have the password, never guess and "
            "never automate a Google or SSO button. Call cairn_login, ask the user to sign "
            "in in the window that opens, then call cairn_login_done. Cairn keeps one "
            "browser profile, so they only ever have to do that once per site."
        ),
    )

    # ------------------------------------------------------------ warm path

    @server.tool()
    def cairn_run(site: str, task: str | None = None, url: str | None = None) -> dict[str, Any]:
        """Do something on a website. USE THIS FOR ANY WEBSITE TASK, and use it FIRST.

        Downloading an invoice or report, checking a dashboard, signing in, filling a form,
        pulling numbers out of a portal — start here, every time, before anything else.

        Do NOT use curl, wget, fetch, requests, or any shell command for website work.
        They cannot sign in, click, or download the way a real browser does, and nothing
        they do is remembered, so the next request costs exactly as much all over again.

        Call this even when you do not know whether Cairn has seen the site before. If it
        has, the whole task finishes in this single call, with no page reading and no
        reasoning. If it has not, the result tells you exactly how to proceed.

        Three possible answers:
          ok=True                  the task is done. `answers` holds what the trail
                                   read — report it and stop.
          needs_repair=True        the site changed. ONE step broke and is described in
                                   `repair`. Pick the right control from `repair.candidates`
                                   and call cairn_repair. Do not re-explore the whole site.
          known=False              Cairn has never been here. Explore with
                                   cairn_act and cairn_read, then cairn_save.

        Args:
            site: The site, as a domain or a full URL (e.g. "billing.acme.com").
            task: Which task, in the same plain words it was saved under. Only needed when
                a site has more than one — the result says so and lists them.
            url: Optional. Where the first step should go, if it differs from what was
                learned — useful when the same site is reached by a different entry URL.
        """
        key = domain_of(site) if "://" in site else site
        try:
            result = tools.worker.submit(
                lambda browser: Executor(tools.store, browser).run(key, task=task, start_url=url)
            )
        except NeedsTask as ambiguous:
            # NOT "unknown". Saying that made a host AI explore a site it already knew and
            # save over the trail that was there.
            return {
                "ok": False,
                "known": True,
                "needs_task": True,
                "site": key,
                "tasks": ambiguous.tasks,
                "message": str(ambiguous),
                "next": (
                    "Cairn already knows this site. Call cairn_run again with `task` set "
                    "to whichever of `tasks` matches what was asked. Do NOT explore — the "
                    "trail is already there."
                ),
            }
        except NoTrailError as unknown:
            facts = _facts_for(tools, key)
            offers = [] if tools.store.was_forgotten(key) else tools.store.offers_for(key)

            if offers:
                # Somebody else has already walked this. Exploring now would throw their
                # work away, so the instruction is REPLACED, not added to.
                return {
                    "ok": False,
                    "known": False,
                    "site": key,
                    "message": str(unknown),
                    "site_facts": facts,
                    "shared_trails": offers,
                    "next": (
                        f"Do NOT explore. Another agent has already walked {key} and left "
                        f"a trail: {offers[0]['task']!r}, shared by "
                        f"{offers[0]['shared_by']!r}. Call cairn_borrow to take it, then "
                        f"cairn_run again with `task` set to exactly that wording."
                    ),
                }

            if tools.store.was_forgotten(key):
                return {
                    "ok": False,
                    "known": False,
                    "site": key,
                    "message": str(unknown),
                    "site_facts": facts,
                    "was_forgotten": True,
                    "next": (
                        f"You told Cairn to forget {key}. Another agent may still have a "
                        f"trail for it, and Cairn will not quietly follow one — that would "
                        f"make forgetting meaningless. Either walk the site again, or say "
                        f"plainly that you want somebody else's trail and call "
                        f"cairn_borrow."
                    ),
                }

            return {
                "ok": False,
                "known": False,
                "site": key,
                "message": str(unknown),
                "site_facts": facts,
                "next": (
                    "Cairn has not walked this site. Explore it once with "
                    "cairn_act and cairn_read, then call cairn_save so this "
                    "never has to happen again."
                    + (
                        f" Before exploring, note that this agent may buy trails from "
                        f"{', '.join(known_shops())} — call cairn_buy to check whether one "
                        f"already sells a trail for {key}. Buying costs a few cents and one "
                        f"call; exploring costs many."
                        if known_shops()
                        else ""
                    )
                    + (
                        " site_facts is what Cairn still knows about this site from before "
                        "— use it so you do not rediscover the same things."
                        if facts
                        else " While exploring, call cairn_note for anything worth "
                        "remembering that is not a step, such as needing a login, a code "
                        "sent to a phone, or a limit on how often you may try."
                    )
                ),
            }
        except Exception as failure:  # noqa: BLE001 - reported, not raised at the client
            return err(failure)

        if result.needs_login:
            return {
                "ok": False,
                "known": True,
                "needs_login": True,
                "site": key,
                "message": result.reason,
                "next": (
                    "Do not try to repair this and do not guess a password. Ask the user to "
                    "sign in: call cairn_login, tell them to sign in in the window that "
                    "opens, and when they say they are done call cairn_login_done. Then "
                    "call cairn_run again."
                ),
            }

        if result.stale:
            return {
                "ok": False,
                "known": False,
                "stale": True,
                "site": key,
                "message": result.reason,
                "site_facts": result.site_facts,
                "next": (
                    "The site was rebuilt, so the old trail was thrown away but everything "
                    "Cairn knows about the site was kept. Explore it again "
                    "with cairn_act and cairn_read — use site_facts so you "
                    "do not rediscover what is already known — then call "
                    "cairn_save."
                ),
            }

        if result.needs_repair and result.repair is not None:
            repair = result.repair.to_dict()
            repair["candidates"] = repair["candidates"][:MAX_ELEMENTS]
            return {
                "ok": False,
                "known": True,
                "needs_repair": True,
                "site": key,
                "steps_replayed": result.metrics.steps_replayed,
                "repair": repair,
                "next": (
                    "Only this one step broke; everything before it still worked. Choose "
                    "the control from repair.candidates that matches repair.intent, then "
                    "call cairn_repair with its REF. Then call cairn_run again."
                ),
            }

        return {
            "ok": result.ok,
            "known": True,
            "site": key,
            "task": result.metrics.task,
            "steps_replayed": result.metrics.steps_replayed,
            "duration_ms": result.metrics.duration_ms,
            "model_calls": 0,
            "pages_read": 0,
            "saved_files": result.saved_files,
            # What the remembered reads said. This is the answer — report it and stop.
            "answers": result.answers,
        }

    @server.tool()
    def cairn_repair(
        site: str,
        step_index: int,
        ref: str | None = None,
        css: str | None = None,
        task: str | None = None,
    ) -> dict[str, Any]:
        """Teach Cairn the new way to find ONE step that broke, then remember it forever.

        Call this only after cairn_run came back with needs_repair.

        PASS `ref`, NOT `css`. Give the `ref` of the control you picked from
        repair.candidates. Cairn then looks that element up and stores every durable way of
        finding it — its test id, its link target, its label, its role, its text — exactly
        as it would if the step were being learned for the first time. A repair that stores
        one CSS path leaves the step more fragile than when it started, which is backwards.

        `css` still works for the rare case where the control you want is not in the
        candidate list at all.

        Args:
            site: The same site you passed to cairn_run.
            step_index: repair.step_index from the cairn_run result.
            ref: The `ref` of your chosen control, from repair.candidates. Preferred.
            css: A CSS selector instead, when nothing in the candidates fits.
            task: Which task, if the site has more than one trail.
        """
        key = domain_of(site) if "://" in site else site
        if not ref and not css:
            return err("say which control to use: a `ref` from repair.candidates, or a `css`")

        try:
            if ref:
                playbook = tools.worker.submit(
                    lambda browser: Executor(tools.store, browser).repair_from_ref(
                        key, step_index, ref, task=task
                    )
                )
            else:
                playbook = tools.worker.submit(
                    lambda browser: Executor(tools.store, browser).apply_repair(
                        key, step_index, Locator("css", css or ""), task=task
                    )
                )
        except Exception as failure:  # noqa: BLE001
            return err(failure)

        step = next((s for s in playbook.steps if s.index == step_index), None)
        return {
            "ok": True,
            "site": key,
            "step_index": step_index,
            "ways_to_find_it": [locator.describe() for locator in step.locators] if step else [],
            "repairs_total": playbook.repairs,
            "next": "Fixed and saved. Call cairn_run again to finish the task.",
        }

    @server.tool()
    def cairn_share(site: str, task: str | None = None) -> dict[str, Any]:
        """Leave a trail where other agents can pick it up.

        Call this once a task works, if the trail is worth somebody else having. They get
        the route; they do not get you.

        WHAT LEAVES YOUR MACHINE: the steps, every way of finding each control, the checks,
        and the notes saved with cairn_note — the result below lists those notes in full,
        so read it. WHAT NEVER LEAVES: anything typed into a field, and the account hint.
        A shared login step asks whoever follows it for their own credentials.

        Anyone who can read this memory can read what you share here.

        Args:
            site: The site, as a domain or full URL.
            task: Which task, if this site has more than one trail.
        """
        key = domain_of(site) if "://" in site else site
        try:
            published = tools.store.share_trail(key, task)
        except Exception as failure:  # noqa: BLE001
            return err(failure)

        if published is None:
            return err(
                f"you have no trail for {key} to share. Run the task once and call "
                f"cairn_save first."
            )
        return {"ok": True, **published, "next": "Another agent can now call cairn_borrow."}

    @server.tool()
    def cairn_borrow(site: str, task: str | None = None, force: bool = False) -> dict[str, Any]:
        """Take a trail another agent left for a site you have never walked.

        Use this when cairn_run comes back with `shared_trails`. The trail is copied into
        your own memory, so from then on it is yours: you can run it, repair it, and be
        made to forget it.

        It arrives with the evidence it earned elsewhere — the locators that are already
        known to work are tried first — but not with the other agent's run counts.

        A step that types something arrives asking YOU for the value, because it was never
        given theirs.

        Args:
            site: The site, as a domain or full URL.
            task: Which trail, if several were shared. Left out, you get the one that has
                worked for the most agents.
            force: Take it even though you have a trail here you already repaired.
        """
        key = domain_of(site) if "://" in site else site
        try:
            borrowed = tools.store.borrow_trail(key, task, force=force)
        except TrailAlreadyHere as clash:
            return err(f"{clash} Call again with force=true if that is what you mean.")
        except Exception as failure:  # noqa: BLE001
            return err(failure)

        if borrowed is None:
            return err(f"nobody has shared a trail for {key}.")

        needed = [step.secret for step in borrowed.steps if step.secret]
        return {
            "ok": True,
            "site": key,
            # The EXACT wording to pass to cairn_run. A paraphrase may not match.
            "task": borrowed.task,
            "left_by": borrowed.borrowed_from,
            "first_walked_by": borrowed.origin_agent,
            "steps": len(borrowed.steps),
            "clean_runs_behind_it": borrowed.inherited_runs,
            "you_must_supply": needed,
            "next": (
                f"It is yours now. Call cairn_run with site={key!r} and task="
                f"{borrowed.task!r} — exactly that wording."
                + (
                    f" It will ask you for: {', '.join(needed)}. Those were never shared."
                    if needed
                    else ""
                )
            ),
        }

    @server.tool()
    def cairn_commons() -> dict[str, Any]:
        """Every trail any agent has shared, and who left it.

        Answers "what does this team already know how to do?" — including sites this agent
        has never opened.
        """
        try:
            offers = tools.store.every_offer()
        except Exception as failure:  # noqa: BLE001
            return err(failure)
        return {
            "ok": True,
            "count": len(offers),
            "shared_trails": offers,
            "you_are": tools.store.who,
        }

    @server.tool()
    def cairn_buy(shop: str, site: str, task: str | None = None, force: bool = False):
        """Buy a trail from another agent's shop, over the internet, for a few cents.

        Use this when cairn_run says a site is NOT known and no other agent on this machine
        has shared a trail for it. Someone on another machine may have walked it already,
        and buying their trail costs one call and a few cents of USDC on Base. Exploring the
        same site yourself costs many calls and a lot of page reading.

        What happens: Cairn asks the shop what it has for the site, which is free. Then it
        asks for the trail, gets HTTP 402 Payment Required, pays, and imports what comes
        back. The trail becomes this agent's own — it can be run, repaired, and forgotten
        like any other.

        WHAT YOU BUY IS THE ROUTE, NOT AN ACCOUNT. Anything the seller typed into a field
        was stripped before it left their machine, so a sign-in step arrives asking YOU for
        your own credentials.

        Needs a wallet: set CAIRN_WALLET_KEY to a private key holding test USDC on Base
        Sepolia. Test USDC is free from the Circle faucet and needs no account.

        Args:
            shop: the shop's address, e.g. "http://127.0.0.1:8402".
            site: the site you want a trail for, as a domain.
            task: which trail, if the shop sells more than one for that site.
            force: buy it even over a trail you have already repaired yourself.
        """
        try:
            from cairn import payments
        except ImportError:
            return err(
                'buying needs an extra: pip install "cairn[market]" in the environment '
                "running this MCP server, then restart it."
            )

        key = domain_of(site) if "://" in site else site
        try:
            listed = payments.browse(shop, key)
        except payments.ShopUnreachable as gone:
            return err(gone)

        wanted = _pick_from_shop(listed, task)
        if wanted is None:
            sells = [offer["task"] for offer in listed]
            return err(
                f"the shop at {shop} has no trail for {key}."
                + (f" It does sell: {sells}." if sells else "")
            )

        where = f"{shop.rstrip('/')}/trails/{key}/{slug(wanted['task'])}"
        try:
            offer, receipt = payments.buy(where)
        except (
            payments.MissingWallet,
            payments.PaymentRefused,
            payments.ShopUnreachable,
        ) as refused:
            return err(refused)

        try:
            bought = tools.store.take_bought_trail(offer, receipt=receipt.to_dict(), force=force)
        except TrailAlreadyHere as clash:
            return err(f"{clash} Call again with force=true if that is what you mean.")
        except Exception as failure:  # noqa: BLE001
            return err(failure)

        needs = sorted({step.secret for step in bought.steps if step.secret})
        return {
            "ok": True,
            "site": key,
            "task": bought.task,
            "bought_from": bought.borrowed_from,
            "first_walked_by": bought.origin_agent,
            "steps": len(bought.steps),
            "clean_runs_behind_it": bought.inherited_runs,
            "paid": {**receipt.to_dict(), "price": wanted.get("price")},
            "you_must_supply": needs,
            "next": (
                f"The trail is yours now. Call cairn_run with site={key!r} and "
                f"task={bought.task!r} — exactly that wording."
                + (
                    f" It will ask you for: {needs}. Those were never sold; supply your own."
                    if needs
                    else ""
                )
            ),
        }

    @server.tool()
    def cairn_sites() -> dict[str, Any]:
        """List every website Cairn remembers, with how well each trail is holding up.

        Useful for answering "what do you already know how to do?".
        """
        try:
            # One row per TRAIL, not per site. A site can hold several tasks, and
            # listing by site alone would hide every one after the first.
            sites = []
            for domain in tools.store.list_sites():
                for task in tools.store.trails_for(domain) or [None]:
                    playbook = tools.store.load_playbook(domain, task)
                    if playbook is None:
                        continue
                    sites.append(
                        {
                            "site": domain,
                            "task": playbook.task,
                            "steps": len(playbook.steps),
                            "runs": playbook.runs,
                            "health": round(playbook.health, 2),
                        }
                    )
            return {"ok": True, "count": len(sites), "sites": sites}
        except Exception as failure:  # noqa: BLE001
            return err(failure)

    @server.tool()
    def cairn_show(site: str) -> dict[str, Any]:
        """Show the remembered trail for one site, step by step.

        Use when the user asks what Cairn will actually do, or why a step keeps breaking.

        Args:
            site: Domain or full URL.
        """
        key = domain_of(site) if "://" in site else site
        playbook = tools.store.load_playbook(key)
        facts = _facts_for(tools, key)
        if playbook is None:
            return {
                "ok": False,
                "known": False,
                "site": key,
                "site_facts": facts,
                "message": "no trail remembered for this site",
            }
        return {
            "ok": True,
            "site": key,
            "playbook": playbook.to_dict(),
            "site_facts": facts,
        }

    @server.tool()
    def cairn_forget(site: str) -> dict[str, Any]:
        """Make Cairn forget one website completely.

        After this, cairn_run has nothing left to follow and the site would have to be
        explored from scratch again. Use it when the user asks Cairn to forget a site, or
        to prove that the memory is what makes the fast path work.

        Args:
            site: Domain or full URL.
        """
        key = domain_of(site) if "://" in site else site
        try:
            # Counted before it happens, because forgetting withdraws them.
            withdrawn = len(tools.store.my_offers_for(key))
            still_offered = len(tools.store.offers_for(key)) - withdrawn
            forgotten = tools.store.forget_site(key)
        except Exception as failure:  # noqa: BLE001
            return err(failure)

        if not forgotten:
            return {"ok": False, "site": key, "message": "nothing was remembered for this site"}

        message = (
            "Forgotten. The trail is archived, so cairn_run has nothing to follow and this "
            "site would have to be learned again from scratch."
        )
        if withdrawn:
            message += f" Withdrawn from the shared memory: {withdrawn} offer(s)."
        if still_offered > 0:
            # Said plainly rather than left to be discovered. Sibyl gives no way to
            # enumerate tenants, so this really is a boundary Cairn cannot cross — which
            # is a guarantee, not a shortcoming, but only if somebody says so.
            message += (
                f" {still_offered} other agent(s) still hold their own copy. Cairn cannot "
                f"reach into another agent's memory, and will not offer you theirs back "
                f"unless you ask for it on purpose."
            )
        return {
            "ok": True,
            "site": key,
            "withdrawn_from_commons": withdrawn,
            "other_agents_still_have_it": still_offered,
            "message": message,
        }

    @server.tool()
    def cairn_note(
        site: str,
        fact: str | None = None,
        needs_login: bool | None = None,
        needs_2fa: bool | None = None,
        account: str | None = None,
    ) -> dict[str, Any]:
        """Remember a fact about a website that is not a step.

        Steps break when a site is redesigned. Facts do not. "It locks you out after five
        wrong passwords", "the invoice only appears after the 3rd", "the export takes two
        minutes", "use the finance login, not the admin one" — these stay true through any
        redesign, and Cairn hands them back the next time this site has to be learned.

        Call this whenever you notice something while exploring that a person would want
        told before doing this task themselves. Each call ADDS; nothing is overwritten, so
        call it as many times as you like.

        Args:
            site: Domain or full URL.
            fact: One thing worth remembering, in plain words.
            needs_login: True if this site requires signing in.
            needs_2fa: True if it asks for a code or a second factor.
            account: Which account is used here, e.g. "finance@acme.com".
        """
        key = domain_of(site) if "://" in site else site
        if fact is None and needs_login is None and needs_2fa is None and account is None:
            return err("give at least one of: fact, needs_login, needs_2fa, account")

        try:
            knowledge = tools.store.load_site_knowledge(key) or SiteKnowledge(domain=key)
            knowledge.merge(
                fact=fact,
                needs_login=needs_login,
                needs_2fa=needs_2fa,
                account_hint=account,
            )
            tools.store.save_site_knowledge(knowledge)
        except Exception as failure:  # noqa: BLE001
            return err(failure)

        return {
            "ok": True,
            "site": key,
            "known_facts": knowledge.summary(),
            "message": (
                "Saved. This survives a redesign, and comes back if the site ever has to "
                "be learned again."
            ),
        }

    @server.tool()
    def cairn_login(site: str) -> dict[str, Any]:
        """Open a real browser window so the USER can sign in to a site themselves.

        Use this when a site needs a login that you cannot or should not do: a "Sign in
        with Google" button, a company SSO page, or anything that sends a one-time code.
        Never try to type those yourself and never guess a password.

        A visible Chrome window opens on that site. Tell the user to sign in there, in
        their own time. When they say they are done, call cairn_login_done.

        Cairn keeps one browser profile, so after this the user stays signed in to this
        site — and every other site they have signed in to — until it expires.

        Args:
            site: The site to open, as a full URL where possible.
        """
        target = site if "://" in site else f"https://{site}"
        try:
            tools.open_login_window(target)
        except Exception as failure:  # noqa: BLE001
            return err(failure)

        return {
            "ok": True,
            "site": domain_of(target),
            "opened": target,
            "next": (
                "A browser window is now open. Tell the user: sign in there however the "
                "site asks — password, Google, a code on your phone — and say when you are "
                "done. Then call cairn_login_done. Do not call any other Cairn tool until "
                "then, because the sign-in window is holding the browser."
            ),
        }

    @server.tool()
    def cairn_login_done(site: str) -> dict[str, Any]:
        """Close the sign-in window once the user says they are signed in.

        Cairn saves nothing about how they signed in — no password, no code. It simply
        keeps the browser session, the same way their own browser does, so later runs
        start already signed in.

        Args:
            site: The same site passed to cairn_login.
        """
        key = domain_of(site) if "://" in site else site
        if not tools.signing_in:
            return err("no sign-in window is open — call cairn_login first")

        try:
            ended_at = tools.finish_login()
            knowledge = tools.store.load_site_knowledge(key) or SiteKnowledge(domain=key)
            knowledge.merge(
                fact="signed in by hand; Cairn keeps the session in its browser profile",
                needs_login=True,
            )
            tools.store.save_site_knowledge(knowledge)
        except Exception as failure:  # noqa: BLE001
            return err(failure)

        return {
            "ok": True,
            "site": key,
            "ended_at": ended_at,
            "known_facts": knowledge.summary(),
            "next": (
                "Signed in and the window is closed. Call cairn_run again — and if the "
                "site is still unknown, explore it now and call cairn_save."
            ),
        }

    # ------------------------------------------------------------ cold path

    @server.tool(description=_act_description())
    def cairn_act(
        intent: str,
        action: str,
        ref: str | None = None,
        value: str | None = None,
        to: str | None = None,
    ) -> dict[str, Any]:
        try:
            session = tools.session()
            outcome = tools.worker.submit(
                lambda _browser: session.act(intent, action, ref=ref, value=value, to=to)
            )
            note = tools.take_profile_note()
            return {"ok": True, **outcome, **({"note": note} if note else {})}
        except (ActionFailed, actions.UnknownAction, actions.ActionNeedsMore) as refused:
            return err(refused)
        except Exception as failure:  # noqa: BLE001
            return err(failure)

    @server.tool(description=_read_description())
    def cairn_read(
        kind: str = PAGE,
        ref: str | None = None,
        attribute: str | None = None,
        remember: bool = False,
        intent: str = "",
    ) -> dict[str, Any]:
        try:
            session = tools.session()
            if kind == PAGE:
                page = tools.worker.submit(lambda _browser: session.look())
                page["elements"] = page["elements"][:MAX_ELEMENTS]
                note = tools.take_profile_note()
                return {"ok": True, "kind": PAGE, **page, **({"note": note} if note else {})}

            answer = tools.worker.submit(
                lambda _browser: session.read(
                    kind, ref=ref, attribute=attribute, remember=remember, intent=intent
                )
            )
            reply: dict[str, Any] = {
                "ok": True,
                "kind": kind,
                "ref": ref,
                "value": answer,
                "remembered": remember,
            }
            # Said at the moment it happens, not only in the tool description. A host AI
            # remembered a whole-page read on PostHog despite the description, because the
            # tiles had no ref and page_text looked like the only way through.
            if remember and kind == WHOLE_PAGE:
                reply["warning"] = (
                    "This trail's answer is now the entire page, and every future run will "
                    "hand back thousands of characters for you to search. If you can name "
                    "what you actually want with a CSS selector — pass it as `ref` — read "
                    "that instead and remember that one."
                )
            return reply
        except (ActionFailed, reads.UnknownRead, reads.ReadNeedsMore) as refused:
            return err(refused)
        except Exception as failure:  # noqa: BLE001
            return err(failure)

    @server.tool()
    def cairn_save(task: str) -> dict[str, Any]:
        """Remember everything you just did, so this task never needs exploring again.

        Call this once the task is finished. Cairn turns what you did into a trail with a
        check on every step, and stores it. From now on the same task is one cairn_run
        call with no thinking at all.

        EVERYTHING you did is written down, including the parts that went wrong. If you
        took a wrong turn, undid something, or clicked your way out of a stuck menu, those
        become steps too — and a saved mistake is replayed forever. Before saving, call
        cairn_act(action="restart_trail") and walk the task once, cleanly. The result below
        lists every step it kept, so check it says what you meant to do.

        Args:
            task: What was accomplished, in plain words, e.g. "download this month's
                invoice".
        """

        try:
            session = tools.session()
            playbook = tools.worker.submit(lambda _browser: session.save(task))
        except ActionFailed as refused:
            return err(refused)
        except Exception as failure:  # noqa: BLE001
            return err(failure)

        tools.reset_session()
        return {
            "ok": True,
            "site": playbook.domain,
            "task": playbook.task,
            "steps": len(playbook.steps),
            # Shown so the AI can see whether its own fumbling got written down. On
            # PostHog a saved trail began "close the stuck context menu", which failed on
            # the first replay and took the whole run with it.
            "trail": [f"{s.index}. {s.action} — {s.intent}" for s in playbook.steps],
            "message": (
                f"Learned {playbook.domain} in {len(playbook.steps)} steps. "
                f"Next time, one cairn_run call does all of it."
            ),
        }

    server.cairn_tools = tools  # type: ignore[attr-defined]
    return server


def run_stdio() -> None:
    """Entry point for `cairn-mcp` and `python -m cairn_mcp`.

    Configured entirely by environment, because that is the only channel an `.mcp.json`
    entry has — this function takes no arguments and nothing calls it with any.

        CAIRN_AGENT    who this agent is. Unset means the memory that already exists.
        CAIRN_PROFILE  which browser profile to use. Two agents CANNOT share one: Chrome
                       allows a single process per profile, and a shared profile would also
                       mean the second agent is already signed in to everything the first
                       one is — which is not what "an agent that has never seen this site"
                       should mean.
        CAIRN_DB       which memory database. Agents share this on purpose; it is how a
                       trail gets from one to the other.
    """
    server = build_server(
        agent=os.environ.get("CAIRN_AGENT") or None,
        profile=os.environ.get("CAIRN_PROFILE") or None,
        db_path=os.environ.get("CAIRN_DB") or None,
    )
    who = os.environ.get("CAIRN_AGENT") or "the default agent"
    log(f"ready as {who} — cairn_run first, explore only if the site is unknown")
    try:
        server.run()
    finally:
        server.cairn_tools.close()  # type: ignore[attr-defined]
