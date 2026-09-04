"""Check this machine, and say plainly what to fix.

Everything Cairn needs that is NOT Python code: a browser that is downloaded separately, a
folder it can write to, a memory database, and — only if you sell or buy trails — a wallet.
Each of those has produced a confusing failure at some point in this project's life, and a
stranger meeting one of them mid-run has to read a traceback to find out what went wrong.

This is the command that answers it before they hit it. `cairn doctor` names the problem and
the fix, and exits non-zero only when something ESSENTIAL is broken, so it is usable in a
setup script.
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

# Anything below this and pip would have refused the install, but a wheel copied by hand
# would not have been checked at all.
MINIMUM_PYTHON = (3, 11)

# How long to let a browser prove it can start. Generous: a first launch on a cold machine
# unpacks and verifies, and calling that a failure would be worse than waiting.
BROWSER_CHECK_MS = 60_000


@dataclass
class Check:
    """One thing that either works or needs a named fix."""

    name: str
    ok: bool
    detail: str
    fix: str = ""
    essential: bool = True


def _python() -> Check:
    running = sys.version_info[:2]
    if running >= MINIMUM_PYTHON:
        return Check("python", True, f"{running[0]}.{running[1]}")
    return Check(
        "python",
        False,
        f"{running[0]}.{running[1]}",
        f"Cairn needs {MINIMUM_PYTHON[0]}.{MINIMUM_PYTHON[1]} or newer.",
    )


def _cairn() -> Check:
    from cairn import __version__

    return Check("cairn", True, __version__)


def _browser() -> Check:
    """The one people actually hit. `pip install` does not bring a browser with it."""
    from .browser import Browser, NoDisplay, ProfileUnavailable

    try:
        with Browser(headless=True, timeout_ms=BROWSER_CHECK_MS) as running:
            return Check("browser", True, running._channel or "bundled Chromium")
    except (NoDisplay, ProfileUnavailable) as known:
        return Check("browser", False, "will not start", str(known))
    except Exception as unknown:  # noqa: BLE001 - reported to a person, not re-raised
        said = str(unknown).split("Browser logs:")[0].strip().replace("\n", " ")[:160]
        return Check(
            "browser",
            False,
            "will not start",
            f"{said}\n       Usually: python -m playwright install chromium",
        )


def _profile() -> Check:
    """Only a problem once it exists — a missing one is made on first use."""
    from .browser import DEFAULT_PROFILE, Browser, NoDisplay, ProfileUnavailable

    if not DEFAULT_PROFILE.exists():
        return Check("profile", True, "none yet, made on first use", essential=False)
    try:
        with Browser(headless=True, profile=DEFAULT_PROFILE, timeout_ms=BROWSER_CHECK_MS) as up:
            opened = up._channel or "bundled Chromium"
            note = f" — {up.profile_note}" if up.profile_note else ""
            return Check("profile", True, f"opens with {opened}{note}")
    except (NoDisplay, ProfileUnavailable) as known:
        return Check("profile", False, "will not open", str(known))


def _memory() -> Check:
    """Sibyl writes a SQLite file. A read-only home is a silent, confusing failure."""
    from .store import CairnStore

    try:
        store = CairnStore()
        sites = store.list_sites()
        return Check("memory", True, f"{len(sites)} site(s) remembered")
    except Exception as broken:  # noqa: BLE001 - reported to a person, not re-raised
        return Check(
            "memory",
            False,
            "cannot be opened",
            f"{str(broken)[:160]}\n       Check that your home folder is writable.",
        )


def _downloads() -> Check:
    """A download task is not done if the file cannot be written anywhere."""
    from .browser import DEFAULT_DOWNLOADS

    try:
        DEFAULT_DOWNLOADS.mkdir(parents=True, exist_ok=True)
        # The handle has to be closed before the file can be removed: Windows refuses to
        # delete a file that is still open, and `mkstemp` hands back an OPEN one.
        handle, where = tempfile.mkstemp(dir=DEFAULT_DOWNLOADS)
        os.close(handle)
        Path(where).unlink()
        return Check("downloads", True, str(DEFAULT_DOWNLOADS))
    except OSError as denied:
        return Check("downloads", False, str(DEFAULT_DOWNLOADS), f"Cannot write there: {denied}")


def _market() -> Check:
    """Optional by design: nobody who only wants a browser should install a wallet."""
    try:
        from . import payments
    except ImportError:
        return Check(
            "market",
            False,
            "not installed",
            'Only needed to sell or buy trails: pip install "cairn-browser-mcp[market]"',
            essential=False,
        )

    wallet = "wallet set" if os.environ.get(payments.WALLET_ENV) else "no wallet key"
    receives = "pay-to set" if os.environ.get(payments.PAY_TO_ENV) else "no pay-to address"
    return Check("market", True, f"{payments.network()} · {wallet} · {receives}", essential=False)


def run_checks() -> list[Check]:
    """Every check, in the order a person meets them."""
    return [
        _python(),
        _cairn(),
        _browser(),
        _profile(),
        _memory(),
        _downloads(),
        _market(),
    ]


def cmd_doctor(args: argparse.Namespace) -> int:
    """Print what works, what does not, and exactly what to do about it."""
    del args

    print()
    broken = []
    for check in run_checks():
        mark = "ok  " if check.ok else ("FAIL" if check.essential else "--  ")
        print(f"  {mark}  {check.name:<10} {check.detail}")
        if not check.ok:
            for line in check.fix.splitlines():
                print(f"        {line}")
            if check.essential:
                broken.append(check.name)

    print()
    if broken:
        print(f"  {len(broken)} thing(s) need fixing: {', '.join(broken)}\n")
        return 1
    print("  Everything Cairn needs is here.\n")
    return 0
