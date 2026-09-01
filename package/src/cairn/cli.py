"""The terminal face of Cairn.

Five commands, and one of them is the point of the whole project:

    cairn run    --site <url>        replay a remembered trail, no model involved
    cairn sites                      what Cairn knows
    cairn show   <domain>            the trail, step by step
    cairn forget --site <domain>     THE DELETION GATE
    cairn export <domain>            the raw playbook as JSON

`forget` is the one a judge should try. Run `run` twice to see it be fast, then `forget`,
then `run` again and watch it report that there is nothing left to follow.

Uses argparse rather than a CLI framework on purpose: `mcp/` and `backend/` both import
this package, and the fewer dependencies it drags along the easier it is to install with
uvx. Reason logged in PROGRESS.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from urllib.parse import urlparse

from .browser import Browser, domain_of
from .events import Emitter, Event
from .executor import Executor, NoTrailError
from .store import CairnStore

TICK = "+"
CROSS = "!"
DOT = "-"


def render(event: Event) -> None:
    """Turn one event into one line a human can read."""
    kind = event.kind
    data = event.to_dict()

    if kind == "run_started":
        print(f"\n  cairn  {data['domain']}  ({data['mode']} run)")
        print(f"  task   {data['task']}\n")
    elif kind == "memory_read":
        state = "found" if data["found"] else "NOTHING FOUND"
        print(f"  {DOT} memory read   {data['category']}/{data['name']}  {state}")
    elif kind == "memory_write":
        print(f"  {DOT} memory write  {data['category']}/{data['name']}  {data['detail']}")
    elif kind == "step_passed":
        print(
            f"  {TICK} step {data['index']}  {data['intent']}"
            f"   [{data['matched_by']}]  {data['duration_ms']}ms"
        )
    elif kind == "drift_detected":
        print(f"  {DOT}   drift: {data['locator']} no longer matches")
    elif kind == "step_failed":
        print(f"  {CROSS} step {data['index']}  {data['intent']}  — {data['reason']}")
    elif kind == "repair_needed":
        print("\n  this one step needs your AI. Everything else stayed put.")
        print(f"  step {data['index']}: {data['intent']}")
        print(f"  at   {data['url']}")
    elif kind == "repair_saved":
        print(f"  {TICK} repaired step {data['index']}: {data['before']} -> {data['after']}")
    elif kind == "run_finished":
        state = "done" if data["succeeded"] else "stopped"
        print(
            f"\n  {state} in {data['duration_ms']}ms  ·  "
            f"{data['steps_replayed']} steps from memory  ·  "
            f"{data['steps_repaired']} repaired  ·  "
            f"1 tool call  ·  "
            f"{data['model_calls']} model calls\n"
        )
    elif kind == "forgotten":
        print(f"  {TICK} forgot {data['domain']}")


def _site_key(value: str) -> str:
    """Accept either a domain or a full URL, so nobody has to think about which."""
    return domain_of(value) if urlparse(value).scheme else value


# ------------------------------------------------------------------ commands


def cmd_run(args: argparse.Namespace) -> int:
    domain = _site_key(args.site)
    start_url = args.url or (args.site if urlparse(args.site).scheme else None)

    emitter = Emitter()
    emitter.subscribe(render)
    store = CairnStore(db_path=args.db)

    # One trail per site, so a task given here is a check rather than a chooser.
    if args.task:
        remembered = store.load_playbook(domain)
        if remembered is not None and remembered.task.lower() != args.task.lower():
            print()
            print(f'  note: this site is remembered for "{remembered.task}"')
            print(f'        you asked for "{args.task}" — running the remembered one')
            print()

    browser = Browser(headless=not args.headed)
    try:
        browser.start()
        result = Executor(store, browser, emitter=emitter).run(domain, start_url=start_url)
    except NoTrailError as gone:
        print(f"\n  {CROSS} {gone}\n")
        return 2
    finally:
        browser.stop()

    for saved in result.saved_files:
        print(f"  {TICK} saved  {saved}")

    if result.stale:
        print()
        print(f"  {CROSS} {result.reason}")
        for fact in result.site_facts:
            print(f"    still known: {fact}")
        print("    walk it once more and it will be fast again.")
        print()
        return 2

    if result.needs_repair and result.repair is not None:
        print("  hand this to your AI:\n")
        print(json.dumps(result.repair.to_dict(), indent=2)[:1200])
        print()
        return 1
    return 0 if result.ok else 1


def cmd_sites(args: argparse.Namespace) -> int:
    store = CairnStore(db_path=args.db)
    sites = store.list_sites()
    if not sites:
        print("\n  Cairn remembers nothing yet.\n")
        return 0

    print()
    for site in sites:
        playbook = store.load_playbook(site)
        if playbook is None:
            continue
        print(
            f"  {site:<32} {len(playbook.steps)} steps  "
            f"{playbook.runs} runs  health {playbook.health:.0%}"
        )
    print()
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    store = CairnStore(db_path=args.db)
    playbook = store.load_playbook(_site_key(args.domain))
    if playbook is None:
        print(f"\n  nothing remembered for {args.domain}\n")
        return 2

    print(f"\n  {playbook.domain}")
    print(f"  {playbook.task}")
    print(f"  version {playbook.version}  ·  {playbook.runs} runs  ·  {playbook.repairs} repairs\n")
    for step in playbook.steps:
        best = step.ranked_locators()
        via = f"{best[0].kind}:{best[0].value}" if best else step.value or ""
        print(f"  {step.index}. {step.intent}")
        print(f"     {step.action:<7} {via}")
        print(
            f"     expects {step.postcondition.kind} = {step.postcondition.value}"
            f"   health {step.health:.0%}"
        )
    print()
    return 0


def cmd_forget(args: argparse.Namespace) -> int:
    """The deletion gate, as one command."""
    domain = _site_key(args.site)
    store = CairnStore(db_path=args.db)

    if not store.forget_site(domain):
        print(f"\n  nothing to forget for {domain}\n")
        return 2

    print(f"\n  {TICK} forgot {domain}")
    print("    the trail is archived. replay has nothing left to follow.\n")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    store = CairnStore(db_path=args.db)
    playbook = store.load_playbook(_site_key(args.domain))
    if playbook is None:
        print(f"nothing remembered for {args.domain}", file=sys.stderr)
        return 2
    print(json.dumps(playbook.to_dict(), indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cairn",
        description="A browser memory for AI agents. Learn a site once, replay it for free.",
    )
    parser.add_argument("--db", default=None, help="memory database (default: Sibyl's own)")
    subs = parser.add_subparsers(dest="command", required=True)

    run = subs.add_parser("run", help="replay a remembered trail (no model calls)")
    run.add_argument(
        "task",
        nargs="?",
        default=None,
        help='what you want done, e.g. "download this month\'s invoice"',
    )
    run.add_argument("--site", required=True, help="domain or full url")
    run.add_argument("--url", default=None, help="override where the first step goes")
    run.add_argument("--headed", action="store_true", help="watch it happen")
    run.set_defaults(func=cmd_run)

    sites = subs.add_parser("sites", help="list every site Cairn remembers")
    sites.set_defaults(func=cmd_sites)

    show = subs.add_parser("show", help="print one trail, step by step")
    show.add_argument("domain")
    show.set_defaults(func=cmd_show)

    forget = subs.add_parser("forget", help="wipe one site from memory (the deletion gate)")
    forget.add_argument("--site", required=True)
    forget.set_defaults(func=cmd_forget)

    export = subs.add_parser("export", help="print the raw playbook as JSON")
    export.add_argument("domain")
    export.set_defaults(func=cmd_export)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
