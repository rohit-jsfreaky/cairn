"""The same task, on the same site, five mornings running.

Run it yourself:

    .venv/Scripts/python package/benchmark.py

It uses the demo site in `package/tests/demo_site/`, because that is the only site whose
redesign can be switched on and off on purpose — `?variant=b` renames and moves the
controls, which is what Thursday is. Everything else here is a real browser doing real
work against a real HTTP server.

Two things this deliberately does NOT flatter:

- **Monday's tool calls are counted from a script**, not from a language model exploring.
  A real host AI takes noticeably more than this, because it has to look at the page to
  decide what to do next. The number below is therefore the FLOOR of what memory saves.
- **The clock is honest and unimpressive.** This benchmark contains no model thinking time,
  and thinking time is the cost memory actually removes. Compare the calls and the page
  reads; the seconds are the least interesting column here.
"""

from __future__ import annotations

import os
import socket
import threading
import time
from dataclasses import dataclass

import uvicorn
from tests.demo_site.app import app

from cairn.browser import Browser, domain_of
from cairn.executor import Executor
from cairn.operations import Session
from cairn.secrets import env_var_name
from cairn.store import CairnStore

TASK = "download this month's invoice"


@dataclass
class Morning:
    label: str
    note: str
    seconds: float
    calls: int
    reads: int


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _serve() -> tuple[str, uvicorn.Server]:
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    return f"http://127.0.0.1:{port}", server


def _named(page: dict, name: str) -> str:
    for element in page["elements"]:
        if element["name"] == name:
            return element["ref"]
    raise AssertionError(f"no control called {name!r}")


def monday(browser: Browser, store: CairnStore, url: str) -> Morning:
    """Learning the site. Every call a host AI would make, and every page it would read."""
    began = time.perf_counter()
    session = Session(browser, store)
    reads = 0

    session.act("open the billing portal", "goto", value=f"{url}/")
    page, reads = session.look(), reads + 1
    session.act("type the account email", "fill", ref=_named(page, "Email"), value="a@b.com")
    session.act("type the password", "fill", ref=_named(page, "Password"), value="hunter2")
    session.act("sign in", "click", ref=_named(page, "Sign in"))

    page, reads = session.look(), reads + 1
    session.act("open this month's invoice", "click", ref=_named(page, "September 2026"))

    page, reads = session.look(), reads + 1
    session.act("download the PDF", "click", ref=_named(page, "Download"))
    session.save(TASK)

    return Morning(
        label="Monday",
        note="learning the site",
        seconds=time.perf_counter() - began,
        calls=session.tool_calls,
        # A page read is a look(): the whole control list, handed to a model to think about.
        # It is the expensive half of exploring, and warm replay does none of it.
        reads=reads,
    )


def from_memory(browser: Browser, store: CairnStore, label: str, *, url: str | None = None):
    """One `cairn_run`. No looking, no thinking, no model."""
    began = time.perf_counter()
    result = Executor(store, browser).run(domain_of(url or ""), task=TASK, start_url=url)
    seconds = time.perf_counter() - began

    broke = result.needs_repair
    return result, Morning(
        label=label,
        note="the site changed, one step repaired" if broke else "from memory",
        seconds=seconds,
        calls=1,
        reads=0,
    )


def main() -> int:
    url, server = _serve()
    site = domain_of(url)

    # Cairn never stores a password, so it has to be given one the way a real user would.
    # That is the whole point of the secrets path, and it applies to a benchmark too.
    os.environ[env_var_name(site, "password")] = "hunter2"

    store = CairnStore(db_path="benchmark-memory.db")
    store.forget_site(site)

    week: list[Morning] = []
    with Browser(headless=True) as browser:
        week.append(monday(browser, store, url))

        for label in ("Tuesday", "Wednesday"):
            _, morning = from_memory(browser, store, label, url=f"{url}/")
            week.append(morning)

        # Thursday: the same site, rebuilt. The download control is renamed and moved.
        result, thursday = from_memory(browser, store, "Thursday", url=f"{url}/?variant=b")
        if result.needs_repair and result.repair:
            fixed = next(
                candidate
                for candidate in result.repair.candidates
                if candidate.get("name") == "Get PDF"
            )
            Executor(store, browser).repair_from_ref(
                site, result.repair.step_index, fixed["ref"], task=TASK
            )
            again, _ = from_memory(browser, store, "Thursday", url=f"{url}/?variant=b")
            thursday.calls += 2  # the repair, and the run that followed it
        week.append(thursday)

        _, friday = from_memory(browser, store, "Friday", url=f"{url}/?variant=b")
        friday.label = "Friday"
        week.append(friday)

    server.should_exit = True

    print(f"\n  {TASK}, five mornings, on the demo site in this repo\n")
    print(f"  {'':10}  {'time':>8}  {'tool calls':>10}  {'page reads':>10}  {'model calls':>11}")
    print(f"  {'-' * 56}")
    for morning in week:
        print(
            f"  {morning.label:10}  {morning.seconds:7.1f}s  {morning.calls:>10}  "
            f"{morning.reads:>10}  {0:>11}   {morning.note}"
        )

    first, best = week[0], week[1]
    print(
        f"\n  {first.calls} tool calls became {best.calls}. "
        f"{first.reads} page reads became {best.reads}. "
        f"Model calls were zero throughout, because replay is plain Python.\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
