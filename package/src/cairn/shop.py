"""The shop: trails for sale over HTTP.

Cairn's local commons already lets two agents on one machine hand a trail to each other for
free. This is the other case, and the one that actually happens: two agents on different
machines, with different memory, sharing no file. The only way across is the network — and
the only reason anyone would publish is if they can charge for it.

Browsing is free. The trail is not:

    GET /trails/{domain}            free  — what is for sale, and how well it has held up
    GET /trails/{domain}/{task}     PAID  — the trail itself, behind HTTP 402

That split is the whole design. You must be able to see what you are about to buy, and you
must not be able to get it without paying.

What is sold is exactly what the local commons publishes — `store.my_offers_for`, whose
playbook already went through `Playbook.for_sharing()` and whose notes went through
`SiteKnowledge.for_sharing()`. Nothing is redacted again here, because a second
implementation of a redaction is a second chance to leak one. The catalogue is built from
`store.describe_offer`, a shape with no steps and no locators in it at all, so a browsing
stranger cannot be handed the goods by accident. The HTTP body is still a brand new exit
from this process, so it gets its own test.

**The stock is memory.** The shelf is `store.my_offers_for(...)` and nothing else. Delete
Sibyl, or run `cairn forget`, and there is nothing to sell — the deletion gate reaches this
feature too, which is the point.

No x402 is imported here. All of that lives in `payments.py`, one file, on purpose.
"""

from __future__ import annotations

import socket
from typing import Any

from fastapi import FastAPI, HTTPException

from . import payments
from .store import CairnStore, slug

# The x402 middleware matches raw paths with its own pattern syntax, where `[name]` stands
# for one path segment. Two segments after /trails is the trail; one segment is the free
# catalogue above it, which this pattern deliberately does not cover.
PAID_PATTERN = "GET /trails/[domain]/[task]"

DEFAULT_PORT = 8402  # 402 is the payment status code. Easy to remember, easy to spot.
DEFAULT_HOST = "127.0.0.1"  # Local by default: no firewall prompt, nothing exposed unasked.

NOT_FOUND = 404


def build_app(
    store: CairnStore,
    *,
    pay_to_address: str,
    asking_price: str,
    chain: str,
    facilitator: str,
) -> FastAPI:
    """A shop serving one agent's shared trails.

    Handlers are plain `def`, not `async def`. FastAPI runs sync handlers in a threadpool,
    so `CairnStore`'s blocking reads are safe here without any plumbing — and the store is
    built once and shared, exactly as the MCP server does it, because its two memory clients
    are never mutated precisely so that several threads may use them.
    """
    app = FastAPI(title="Cairn shop", docs_url=None, redoc_url=None)

    @app.get("/health")
    def health() -> dict[str, Any]:
        """Who this shop is and what it charges. Free, so a buyer can look before trusting."""
        return {
            "ok": True,
            "shop": store.who,
            "network": chain,
            "price": asking_price,
            "pay_to": pay_to_address,
        }

    @app.get("/trails/{domain}")
    def catalogue(domain: str) -> dict[str, Any]:
        """FREE. What is for sale for this site, with the evidence behind each trail."""
        return {
            "shop": store.who,
            "domain": domain,
            "price": asking_price,
            "trails": [store.describe_offer(offer) for offer in store.my_offers_for(domain)],
        }

    @app.get("/trails/{domain}/{task}")
    def trail(domain: str, task: str) -> dict[str, Any]:
        """PAID. The trail itself — the same offer the local commons hands to a borrower.

        Reaching this handler at all means the payment already verified: the x402 middleware
        sits in front and answers 402 until it has.

        A request for a trail this shop does not have also gets a 402 first, because the
        paywall runs before the handler and cannot see the inventory. Nobody is charged for
        it: the middleware settles only after the handler and skips settlement entirely on
        any 4xx — verified in the installed SDK, `x402/http/middleware/fastapi.py`, at the
        line commented "Don't settle on error responses". So the worst case is a 404 and an
        untouched wallet, which is the right worst case.
        """
        wanted = slug(task)
        for offer in store.my_offers_for(domain):
            if slug(offer["task"]) == wanted:
                return offer
        raise HTTPException(
            status_code=NOT_FOUND,
            detail=f"this shop has no trail called {task!r} for {domain}.",
        )

    payments.gate(
        app,
        paths=[PAID_PATTERN],
        pay_to_address=pay_to_address,
        asking_price=asking_price,
        chain=chain,
        facilitator=facilitator,
    )
    return app


def serve(
    store: CairnStore,
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
) -> None:
    """Run the shop until interrupted.

    Refuses a busy port with a sentence rather than a stack trace, the same way the demo
    site does — a shop that half-starts during a demo is worse than one that says why not.
    """
    import uvicorn

    if not _port_is_free(host, port):
        raise OSError(
            f"port {port} on {host} is already in use. Another Cairn shop is probably "
            f"already running — stop it, or pass --port with a different number."
        )

    app = build_app(
        store,
        pay_to_address=payments.pay_to(),
        asking_price=payments.price(),
        chain=payments.network(),
        facilitator=payments.facilitator_url(),
    )
    uvicorn.run(app, host=host, port=port, log_level="warning")


def _port_is_free(host: str, port: int) -> bool:
    with socket.socket() as probe:
        return probe.connect_ex((host, port)) != 0
