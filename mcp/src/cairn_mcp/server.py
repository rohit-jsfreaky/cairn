"""Cairn as MCP tools. This is the product.

Your own AI — Claude Code, Cursor, Codex — becomes the brain. Cairn gives it a browser and
a memory. There is no model call anywhere in this file or anything it imports.

Two paths, and the tool descriptions exist to make the host AI pick the right one:

    cold   cairn_open / cairn_look / cairn_act / cairn_save
           Slow. Many calls. Done ONCE per site, ever.

    warm   cairn_run
           One call. Deterministic replay of what was learned. No thinking required.

Every tool is a few lines that call into the `cairn` package. If something here starts
needing real logic, that logic belongs in the engine instead.

Never print to stdout — stdio is the MCP transport and a stray print corrupts it.
"""

from __future__ import annotations

import sys
from typing import Any

from cairn.browser import domain_of
from cairn.executor import Executor, NoTrailError
from cairn.models import Locator
from cairn.operations import ActionFailed, Session
from cairn.store import CairnStore
from cairn.worker import BrowserWorker
from mcp.server.fastmcp import FastMCP

# How many controls to hand back from one look(). Enough to act on, small enough that
# reading it is cheap — the whole point of the project is not paying for page dumps.
MAX_ELEMENTS = 60


def log(message: str) -> None:
    """stderr only. stdout belongs to the MCP transport."""
    print(f"[cairn] {message}", file=sys.stderr, flush=True)


def err(problem: BaseException | str) -> dict[str, Any]:
    """A readable message, never a stack trace."""
    return {"ok": False, "error": str(problem)}


class CairnTools:
    """Holds the one browser and the one memory store for this MCP connection."""

    def __init__(self, *, db_path: str | None = None, headless: bool = True):
        self.store = CairnStore(db_path=db_path)
        self.worker = BrowserWorker(headless=headless)
        self._session: Session | None = None

    def session(self) -> Session:
        """The cold-path session, started the first time it is needed."""
        if self._session is None:
            self.worker.start()
            self._session = Session(self.worker.browser, self.store)  # type: ignore[arg-type]
        return self._session

    def reset_session(self) -> None:
        self._session = None

    def close(self) -> None:
        self.worker.stop()
        self._session = None


def build_server(*, db_path: str | None = None, headless: bool = True) -> FastMCP:
    """Wire the tools. Kept in a function so tests can build a server without running it."""
    tools = CairnTools(db_path=db_path, headless=headless)

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
            "explore with cairn_open, cairn_look and cairn_act, then cairn_save. That "
            "teaches Cairn the site so it is never explored again."
        ),
    )

    # ------------------------------------------------------------ warm path

    @server.tool()
    def cairn_run(site: str, url: str | None = None) -> dict[str, Any]:
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
          ok=True                  the task is done. Report the result and stop.
          needs_repair=True        the site changed. ONE step broke and is described in
                                   `repair`. Pick the right control from `repair.candidates`
                                   and call cairn_repair. Do not re-explore the whole site.
          known=False              Cairn has never been here. Explore with cairn_open /
                                   cairn_look / cairn_act, then call cairn_save.

        Args:
            site: The site, as a domain or a full URL (e.g. "billing.acme.com").
            url: Optional. Where the first step should go, if it differs from what was
                learned — useful when the same site is reached by a different entry URL.
        """
        key = domain_of(site) if "://" in site else site
        try:
            result = tools.worker.submit(
                lambda browser: Executor(tools.store, browser).run(key, start_url=url)
            )
        except NoTrailError as unknown:
            return {
                "ok": False,
                "known": False,
                "site": key,
                "message": str(unknown),
                "next": (
                    "Cairn has not walked this site. Explore it once with cairn_open, "
                    "cairn_look and cairn_act, then call cairn_save so this never has to "
                    "happen again."
                ),
            }
        except Exception as failure:  # noqa: BLE001 - reported, not raised at the client
            return err(failure)

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
                    "call cairn_repair with its css. Then call cairn_run again."
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
        }

    @server.tool()
    def cairn_repair(site: str, step_index: int, css: str) -> dict[str, Any]:
        """Teach Cairn the new way to find ONE step that broke, then remember it forever.

        Call this only after cairn_run came back with needs_repair. Pass the `css` of the
        control you picked from repair.candidates. Cairn puts it at the front of that
        step's locators and saves it, so the next run is fast again with no repair.

        Args:
            site: The same site you passed to cairn_run.
            step_index: repair.step_index from the cairn_run result.
            css: The css of your chosen control, taken from repair.candidates.
        """
        key = domain_of(site) if "://" in site else site
        try:
            playbook = tools.worker.submit(
                lambda browser: Executor(tools.store, browser).apply_repair(
                    key, step_index, Locator("css", css)
                )
            )
        except Exception as failure:  # noqa: BLE001
            return err(failure)

        return {
            "ok": True,
            "site": key,
            "step_index": step_index,
            "repairs_total": playbook.repairs,
            "next": "Fixed and saved. Call cairn_run again to finish the task.",
        }

    @server.tool()
    def cairn_sites() -> dict[str, Any]:
        """List every website Cairn remembers, with how well each trail is holding up.

        Useful for answering "what do you already know how to do?".
        """
        try:
            sites = []
            for domain in tools.store.list_sites():
                playbook = tools.store.load_playbook(domain)
                if playbook is not None:
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
        if playbook is None:
            return {"ok": False, "known": False, "site": key, "message": "nothing remembered"}
        return {"ok": True, "site": key, "playbook": playbook.to_dict()}

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
            forgotten = tools.store.forget_site(key)
        except Exception as failure:  # noqa: BLE001
            return err(failure)

        if not forgotten:
            return {"ok": False, "site": key, "message": "nothing was remembered for this site"}
        return {
            "ok": True,
            "site": key,
            "message": (
                "Forgotten. The trail is archived, so cairn_run has nothing to follow and "
                "this site would have to be learned again from scratch."
            ),
        }

    # ------------------------------------------------------------ cold path

    @server.tool()
    def cairn_open(url: str) -> dict[str, Any]:
        """Open a web page in Cairn's browser, to start learning a site.

        Only needed when cairn_run says the site is not known. After this, use cairn_look
        to see what is on the page.

        Args:
            url: Full URL, including https://.
        """
        try:
            session = tools.session()
            tools.worker.submit(lambda _browser: session.act("open the page", "goto", value=url))
            return {"ok": True, "url": url, "next": "Call cairn_look to see the page."}
        except Exception as failure:  # noqa: BLE001
            return err(failure)

    @server.tool()
    def cairn_look() -> dict[str, Any]:
        """See what is on the current page: a short list of things you can act on.

        You get the controls only — links, buttons and fields — each with a `ref` you pass
        to cairn_act. This is deliberately not the page HTML; reading whole pages is the
        cost Cairn exists to remove.
        """
        try:
            session = tools.session()
            page = tools.worker.submit(lambda _browser: session.look())
        except Exception as failure:  # noqa: BLE001
            return err(failure)

        page["elements"] = page["elements"][:MAX_ELEMENTS]
        return {"ok": True, **page}

    @server.tool()
    def cairn_act(
        intent: str,
        action: str,
        ref: str | None = None,
        value: str | None = None,
    ) -> dict[str, Any]:
        """Do one thing on the page, and get back what changed.

        Args:
            intent: Why you are doing this, in plain words, e.g. "sign in" or "open this
                month's invoice". This is stored in memory and is what a future repair is
                explained by, so write it for a human, not as a selector.
            action: One of "click", "fill", "select", "press", "goto".
            ref: The `ref` of the control, from cairn_look. Not needed for "goto".
            value: Text to type, option to select, key to press, or the URL for "goto".
        """
        try:
            session = tools.session()
            outcome = tools.worker.submit(
                lambda _browser: session.act(intent, action, ref=ref, value=value)  # type: ignore[arg-type]
            )
            return {"ok": True, **outcome}
        except ActionFailed as refused:
            return err(refused)
        except Exception as failure:  # noqa: BLE001
            return err(failure)

    @server.tool()
    def cairn_save(task: str) -> dict[str, Any]:
        """Remember everything you just did, so this task never needs exploring again.

        Call this once the task is finished. Cairn turns what you did into a trail with a
        check on every step, and stores it. From now on the same task is one cairn_run
        call with no thinking at all.

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
            "message": (
                f"Learned {playbook.domain} in {len(playbook.steps)} steps. "
                f"Next time, one cairn_run call does all of it."
            ),
        }

    server.cairn_tools = tools  # type: ignore[attr-defined]
    return server


def run_stdio() -> None:
    """Entry point for `cairn-mcp` and `python -m cairn_mcp`."""
    server = build_server()
    log("ready — cairn_run first, explore only if the site is unknown")
    try:
        server.run()
    finally:
        server.cairn_tools.close()  # type: ignore[attr-defined]
