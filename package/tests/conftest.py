"""Shared fixtures: a real demo server, a real browser, and a scripted cold run.

The cold run helper stands in for the host AI. In production that is the user's Claude
Code calling look/act/verify through the MCP server; in tests it is a fixed script. Either
way Cairn's own code is identical, which is the point of keeping the brain outside the
engine.
"""

from __future__ import annotations

import socket
import threading
import time
from collections.abc import Iterator
from typing import Any

import pytest
import uvicorn
from tests.demo_site.app import app

from cairn.browser import Browser
from cairn.operations import Session
from cairn.store import CairnStore

TASK = "download this month's invoice"


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@pytest.fixture(scope="session")
def demo_server() -> Iterator[str]:
    """The demo billing site, running for real over HTTP for the whole test session."""
    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.time() + 15
    while not server.started:
        if time.time() > deadline:
            raise RuntimeError("demo site did not start")
        time.sleep(0.05)

    yield f"http://127.0.0.1:{port}"

    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture
def browser() -> Iterator[Browser]:
    with Browser(headless=True) as running:
        yield running


@pytest.fixture
def store(tmp_path) -> CairnStore:
    """Its own database every time, so tests never touch real memory."""
    return CairnStore(db_path=str(tmp_path / "memory.db"))


def ref_named(snapshot: dict[str, Any], name: str) -> str:
    """Find a control by its visible name, the way a person would."""
    for element in snapshot["elements"]:
        if element["name"] == name:
            return element["ref"]
    names = [element["name"] for element in snapshot["elements"]]
    raise AssertionError(f"no control named {name!r} on this page. saw: {names}")


def cold_run(session: Session, base_url: str, *, variant: str = "a") -> None:
    """What the host AI does on the first visit: look, act, look, act.

    Seven calls. Every later run replays this in one.
    """
    suffix = "" if variant == "a" else f"?variant={variant}"
    session.act("open the billing portal", "goto", value=f"{base_url}/{suffix}")

    page = session.look()
    session.act(
        "type the account email", "fill", ref=ref_named(page, "Email"), value="finance@acme.com"
    )
    session.act("type the password", "fill", ref=ref_named(page, "Password"), value="hunter2")
    session.act("sign in", "click", ref=ref_named(page, "Sign in"))

    page = session.look()
    session.act("open this month's invoice", "click", ref=ref_named(page, "September 2026"))

    page = session.look()
    label = "Download" if variant == "a" else "Get PDF"
    session.act("download the PDF", "click", ref=ref_named(page, label))
