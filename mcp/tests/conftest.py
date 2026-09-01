"""Fixtures for driving the MCP server the way a host AI would.

The demo billing site lives in the engine's test folder. It is loaded here by file path
rather than by putting that folder on `sys.path`, because both folders have a `tests`
package and the import would collide. One demo site is better than two that can drift.
"""

from __future__ import annotations

import importlib.util
import socket
import sys
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
import uvicorn

DEMO_SITE = Path(__file__).resolve().parents[2] / "package" / "tests" / "demo_site" / "app.py"


def _load_demo_app():
    spec = importlib.util.spec_from_file_location("cairn_demo_site", DEMO_SITE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load the demo site from {DEMO_SITE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.app


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@pytest.fixture(scope="session")
def demo_server() -> Iterator[str]:
    port = _free_port()
    config = uvicorn.Config(_load_demo_app(), host="127.0.0.1", port=port, log_level="error")
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
def mcp_server(tmp_path):
    """A server with its own memory database, torn down properly after each test."""
    from cairn_mcp.server import build_server

    server = build_server(
        db_path=str(tmp_path / "memory.db"),
        headless=True,
        downloads=str(tmp_path / "downloads"),
    )
    yield server
    server.cairn_tools.close()
