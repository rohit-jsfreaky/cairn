"""The terminal face of Cairn.

    cairn run    --site <url>        replay a remembered trail, no model involved
    cairn login  --site <url>        open a window and sign in yourself
    cairn sites                      what Cairn knows
    cairn show   <domain>            the trail, step by step
    cairn forget --site <domain>     THE DELETION GATE
    cairn export <domain>            the raw playbook as JSON

    cairn share  <site>              leave a trail for another agent, free
    cairn borrow <site>              take a trail another agent left, free
    cairn commons                    every trail any agent has shared

    cairn sell                       serve your trails for a fee, over HTTP
    cairn buy    <shop> --site ...   pay another agent's shop and import the trail

The first block is one machine. The second is two agents sharing one database. The third is
two agents on different machines, who share nothing but a network — which is why that pair
involves money.

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

from .browser import DEFAULT_PROFILE, Browser, domain_of
from .events import Emitter, Event
from .executor import Executor, NoTrailError
from .store import CairnStore, TrailAlreadyHere, best_match, slug

TICK = "+"
CROSS = "!"
DOT = "-"

# Selling and buying pull in a web server and a blockchain library. Anyone who only
# wants a browser with a memory should never be made to install either, so the market
# is an optional extra and a missing one is a sentence instead of a traceback.
MARKET_MISSING = (
    "buying and selling trails needs a few extra packages. Install them with:\n"
    '       pip install "cairn[market]"'
)


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


def _store(args: argparse.Namespace) -> CairnStore:
    """This agent's memory. Announced when it is not the usual one.

    An exported CAIRN_AGENT that nobody remembers setting looks exactly like data loss —
    `cairn sites` goes quiet and the trails appear to be gone. So say who is asking.
    """
    store = CairnStore(db_path=args.db, agent=getattr(args, "agent", None))
    if store.agent:
        print(f"  (as agent {store.agent})")
    return store


def _site_key(value: str) -> str:
    """Accept either a domain or a full URL, so nobody has to think about which."""
    return domain_of(value) if urlparse(value).scheme else value


# ------------------------------------------------------------------ commands


def cmd_run(args: argparse.Namespace) -> int:
    domain = _site_key(args.site)
    start_url = args.url or (args.site if urlparse(args.site).scheme else None)

    emitter = Emitter()
    emitter.subscribe(render)
    store = _store(args)

    browser = Browser(headless=not args.headed, profile=DEFAULT_PROFILE)
    try:
        browser.start()
        result = Executor(store, browser, emitter=emitter).run(
            domain, task=args.task, start_url=start_url
        )
    except NoTrailError as gone:
        print(f"\n  {CROSS} {gone}\n")
        return 2
    finally:
        browser.stop()

    for saved in result.saved_files:
        print(f"  {TICK} saved  {saved}")

    if result.needs_login:
        print()
        print(f"  {CROSS} {result.reason}")
        print(f"    sign in again with:  cairn login --site {args.site}")
        print()
        return 3

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


def cmd_login(args: argparse.Namespace) -> int:
    """Open a real window so a person can sign in themselves.

    Some logins cannot be automated and should not be: a Google button, a company SSO
    page, a code sent to a phone. Cairn opens the browser, waits, and keeps the session.
    It never sees the password.
    """
    target = args.site if "://" in args.site else f"https://{args.site}"

    print()
    print(f"  opening {target}")
    print("  sign in however the site asks — password, Google, a code on your phone.")

    browser = Browser(headless=False, profile=DEFAULT_PROFILE)
    try:
        browser.start()
        browser.goto(target)
        print()
        input("  press Enter here once you are signed in... ")
        where = browser.page.url
    finally:
        browser.stop()

    print()
    print(f"  {TICK} signed in. session kept for {domain_of(where)}")
    print("    Cairn saved no password and no code, only the session.")
    print(f"    now run:  cairn run --site {args.site}")
    print()
    return 0


def cmd_sites(args: argparse.Namespace) -> int:
    store = _store(args)
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
    store = _store(args)
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
    store = _store(args)

    if not store.forget_site(domain):
        print(f"\n  nothing to forget for {domain}\n")
        return 2

    print(f"\n  {TICK} forgot {domain}")
    print("    the trail is archived. replay has nothing left to follow.\n")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    store = _store(args)
    playbook = store.load_playbook(_site_key(args.domain))
    if playbook is None:
        print(f"nothing remembered for {args.domain}", file=sys.stderr)
        return 2
    print(json.dumps(playbook.to_dict(), indent=2))
    return 0


def cmd_share(args: argparse.Namespace) -> int:
    """Leave a trail where another agent can pick it up."""
    store = _store(args)
    published = store.share_trail(_site_key(args.site), args.task)
    if published is None:
        print(f"\n  {CROSS} no trail here to share. Run the task once first.\n")
        return 2

    print(f'\n  {TICK} shared "{published["task"]}" on {published["domain"]}')
    print(f"     {published['steps']} steps, as agent {published['shared_by']}")
    if published["notes_published"]:
        print("\n     these notes are now readable by every agent:")
        for note in published["notes_published"]:
            print(f"       - {note}")
    if published["values_withheld"]:
        print("\n     what was typed here did NOT leave your machine:")
        for step in published["values_withheld"]:
            print(f"       - {step}")
    print()
    return 0


def cmd_borrow(args: argparse.Namespace) -> int:
    """Take a trail somebody else left for a site this agent has never walked."""
    store = _store(args)
    domain = _site_key(args.site)
    try:
        borrowed = store.borrow_trail(domain, args.task, force=args.force)
    except TrailAlreadyHere as clash:
        print(f"\n  {CROSS} {clash}\n     use --force if that is what you mean.\n")
        return 2

    if borrowed is None:
        print(f"\n  {CROSS} nobody has shared a trail for {domain}.\n")
        return 2

    print(f'\n  {TICK} borrowed "{borrowed.task}" from {borrowed.borrowed_from}')
    print(f"     {len(borrowed.steps)} steps, {borrowed.inherited_runs} clean runs behind it")
    needed = [step.secret for step in borrowed.steps if step.secret]
    if needed:
        print(f"     it will ask you for: {', '.join(needed)} — those were never shared")
    print(f'\n     now run:  cairn run --site {domain} --task "{borrowed.task}"\n')
    return 0


def cmd_commons(args: argparse.Namespace) -> int:
    """Everything any agent has shared, and who left it."""
    store = _store(args)
    offers = store.every_offer()
    if not offers:
        print("\n  nothing has been shared yet.\n")
        return 0

    print(f"\n  {len(offers)} shared trail(s):\n")
    for offer in offers:
        worked = f"worked for {offer['worked_for']}" if offer["worked_for"] else "untried"
        print(f"  {offer['domain']}")
        print(f'    "{offer["task"]}"')
        print(
            f"    left by {offer['shared_by']} · {offer['steps']} steps · "
            f"borrowed {offer['borrows']}x · {worked}"
        )
        if offer["contributors"]:
            print(f"    improved by {', '.join(offer['contributors'])}")
        print()
    return 0


def cmd_sell(args: argparse.Namespace) -> int:
    """Serve this agent's shared trails, paid for with x402 on Base.

    The stock is memory: whatever `cairn share` has published, and nothing else. Forget the
    site and the shelf empties, which is the deletion gate reaching this feature too.
    """
    try:
        from . import payments, shop
    except ImportError:
        print(f"\n  {CROSS} {MARKET_MISSING}\n")
        return 2

    store = _store(args)
    try:
        receives = payments.pay_to()
    except payments.MissingWallet as unset:
        print(f"\n  {CROSS} {unset}\n")
        return 2

    mine = [offer for offer in store.every_offer() if offer["shared_by"] == store.who]
    print(f"\n  {TICK} shop open as agent {store.who}")
    print(f"     http://{args.host}:{args.port}")
    print(f"     {len(mine)} trail(s) for sale at {payments.price()} on {payments.network()}")
    print(f"     paid to {receives}")
    if not mine:
        print(f"\n     {DOT} nothing shared yet. Run: cairn share <site>")
    print("\n     stop with Ctrl+C\n")

    try:
        shop.serve(store, host=args.host, port=args.port)
    except OSError as busy:
        print(f"\n  {CROSS} {busy}\n")
        return 2
    except KeyboardInterrupt:
        print("\n  shop closed.\n")
    return 0


def cmd_buy(args: argparse.Namespace) -> int:
    """Buy a trail from another agent's shop and make it this agent's own."""
    try:
        from . import payments
    except ImportError:
        print(f"\n  {CROSS} {MARKET_MISSING}\n")
        return 2

    store = _store(args)
    domain = _site_key(args.site)

    try:
        listed = payments.browse(args.url, domain)
    except payments.ShopUnreachable as gone:
        print(f"\n  {CROSS} {gone}\n")
        return 2

    wanted = _pick_listing(listed, args.task)
    if wanted is None:
        print(f"\n  {CROSS} that shop has no trail for {domain}.\n")
        return 2

    where = f"{args.url.rstrip('/')}/trails/{domain}/{slug(wanted['task'])}"
    print(f"\n  paying for {wanted['task']!r} on {domain} ...")
    try:
        offer, receipt = payments.buy(where)
    except (payments.MissingWallet, payments.PaymentRefused, payments.ShopUnreachable) as no:
        print(f"\n  {CROSS} {no}\n")
        return 2

    try:
        bought = store.take_bought_trail(offer, receipt=receipt.to_dict(), force=args.force)
    except TrailAlreadyHere as clash:
        print(f"\n  {CROSS} {clash}\n     use --force if that is what you mean.\n")
        return 2

    print(f"  {TICK} bought {bought.task!r} from {bought.borrowed_from}")
    print(f"     {len(bought.steps)} steps, {bought.inherited_runs} clean runs behind it")
    paid = receipt.amount or wanted.get("price") or "a fee"
    print(f"     paid {paid} on {receipt.network}")
    print(f"     {receipt.explorer_url}")
    needed = [step.secret for step in bought.steps if step.secret]
    if needed:
        print(f"     it will ask you for: {', '.join(needed)} - those were never sold")
    print(f'\n     now run:  cairn run --site {domain} --task "{bought.task}"\n')
    return 0


def _pick_listing(listed: list[dict], task: str | None) -> dict | None:
    """Which of a shop's trails the caller meant. The only one, when they did not say."""
    if not listed:
        return None
    if not task:
        return listed[0]
    exact = [offer for offer in listed if offer["task"] == task]
    if exact:
        return exact[0]
    closest = best_match(task, [offer["task"] for offer in listed])
    return next((offer for offer in listed if offer["task"] == closest), None)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cairn",
        description="A browser memory for AI agents. Learn a site once, replay it for free.",
    )
    parser.add_argument("--db", default=None, help="memory database (default: Sibyl's own)")
    parser.add_argument(
        "--agent",
        default=None,
        help="who is asking. Agents share one database and see only their own trails",
    )
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

    login = subs.add_parser(
        "login", help="open a window and sign in yourself (Google, SSO, one-time codes)"
    )
    login.add_argument("--site", required=True, help="domain or full url")
    login.set_defaults(func=cmd_login)

    sites = subs.add_parser("sites", help="list every site Cairn remembers")
    sites.set_defaults(func=cmd_sites)

    show = subs.add_parser("show", help="print one trail, step by step")
    show.add_argument("domain")
    show.set_defaults(func=cmd_show)

    forget = subs.add_parser("forget", help="wipe one site from memory (the deletion gate)")
    forget.add_argument("--site", required=True)
    forget.set_defaults(func=cmd_forget)

    share = subs.add_parser("share", help="leave a trail for other agents to follow")
    share.add_argument("site", help="domain or full url")
    share.add_argument("--task", default=None, help="which trail, if the site has several")
    share.set_defaults(func=cmd_share)

    borrow = subs.add_parser("borrow", help="follow a trail another agent left")
    borrow.add_argument("site", help="domain or full url")
    borrow.add_argument("--task", default=None, help="which trail, if several were shared")
    borrow.add_argument(
        "--force", action="store_true", help="take it even over a trail you repaired"
    )
    borrow.set_defaults(func=cmd_borrow)

    commons = subs.add_parser("commons", help="every trail any agent has shared")
    commons.set_defaults(func=cmd_commons)

    sell = subs.add_parser("sell", help="serve your shared trails for a small fee (x402/Base)")
    sell.add_argument("--port", type=int, default=8402, help="default 8402")
    sell.add_argument("--host", default="127.0.0.1", help="default 127.0.0.1, local only")
    sell.set_defaults(func=cmd_sell)

    buy = subs.add_parser("buy", help="buy a trail from another agent's shop")
    buy.add_argument("url", help="the shop, e.g. http://127.0.0.1:8402")
    buy.add_argument("--site", required=True, help="domain or full url")
    buy.add_argument("--task", default=None, help="which trail, if the shop has several")
    buy.add_argument("--force", action="store_true", help="take it even over a trail you repaired")
    buy.set_defaults(func=cmd_buy)

    export = subs.add_parser("export", help="print the raw playbook as JSON")
    export.add_argument("domain")
    export.set_defaults(func=cmd_export)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
