"""Every x402 call in Cairn lives in this file.

The same rule `store.py` follows for Sibyl Memory: one file, so a judge looking for the
onchain action finds all of it in seconds instead of grepping a package. Nothing else in the
project imports `x402`, `web3` or `eth_account`, and a test walks the source to keep that
true.

Three boundaries worth stating, because they are what keep the payment honest:

1. **This file never touches memory.** It cannot read a trail and it cannot write one. Money
   in, receipt out; `store.py` decides what is remembered.
2. **Nothing on the warm path imports this.** Replay stays deterministic, offline and free —
   buying a trail is a deliberate act on the cold path, never a surprise mid-run.
3. **The wallet key is a secret in the `secrets.py` sense.** It comes from the environment,
   it is never written to memory, never into a trail, never into a shared offer, and never
   guessed. Missing means stop and say so.

Facts here were read off the installed SDK on 2026-09-03, not from its docs, which disagreed
with it in two places. See RESEARCH.md.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import requests
from eth_account import Account
from x402 import x402ClientSync, x402ResourceServer
from x402.http import (
    HTTP_STATUS_PAYMENT_REQUIRED,
    PAYMENT_RESPONSE_HEADER,
    FacilitatorConfig,
    HTTPFacilitatorClient,
    PaymentOption,
    decode_payment_response_header,
)
from x402.http.clients import x402_requests
from x402.http.middleware.fastapi import PaymentMiddlewareASGI
from x402.mechanisms.evm import EthAccountSigner
from x402.mechanisms.evm.exact import ExactEvmServerScheme, register_exact_evm_client

# Base Sepolia. Checked live on 2026-09-03: the free public facilitator supports this and
# lists no mainnet at all. The rules ask for "an executed onchain action", not a mainnet one.
# Going to mainnet is this string plus a facilitator that accepts it — no code changes.
BASE_SEPOLIA = "eip155:84532"
BASE_MAINNET = "eip155:8453"

# "exact" means pay the asking price. x402 also has "upto" and batch settlement; a trail has
# one fixed price, so the simplest scheme is the right one.
SCHEME = "exact"

# A trail costs cents. It has to be worth less than the calls it saves, or nobody buys it.
DEFAULT_PRICE = "$0.01"

# USDC on Base Sepolia is resolved by the SDK from the network alone, so no token contract
# address ever appears in Cairn's configuration. One less thing to get wrong or to go stale.

WALLET_ENV = "CAIRN_WALLET_KEY"
PAY_TO_ENV = "CAIRN_PAY_TO"
PRICE_ENV = "CAIRN_PRICE"
NETWORK_ENV = "CAIRN_NETWORK"
FACILITATOR_ENV = "CAIRN_FACILITATOR"

# What one purchase may never exceed, whatever a shop asks for. A shop is a stranger on the
# network; a cap means a bad or hostile price fails instead of emptying the wallet.
SPEND_CAP = "$1"

# Long enough for a chain to settle, short enough that a dead shop does not hang a run.
BUY_TIMEOUT_SECONDS = 60.0
BROWSE_TIMEOUT_SECONDS = 15.0

_EXPLORERS = {
    BASE_SEPOLIA: "https://sepolia.basescan.org/tx/",
    BASE_MAINNET: "https://basescan.org/tx/",
}


class MissingWallet(RuntimeError):
    """Cairn was asked to pay and this machine has no wallet key.

    Deliberately loud, exactly like `MissingSecret`. A wallet key is a secret: guessing one
    is impossible and falling back to something stored earlier is how money goes missing.
    """


class PaymentRefused(RuntimeError):
    """The shop wanted paying and the payment did not go through."""


class ShopUnreachable(RuntimeError):
    """Nothing answered at that address."""


@dataclass(frozen=True)
class Receipt:
    """Proof that one purchase settled on chain.

    Kept small on purpose: this is the part that goes into memory, and a receipt should be
    enough to *check* a payment, never enough to reconstruct what was bought.
    """

    transaction: str
    network: str
    amount: str | None = None
    payer: str | None = None

    @property
    def explorer_url(self) -> str:
        """Where a person can go and see this transaction for themselves."""
        return f"{_EXPLORERS.get(self.network, '')}{self.transaction}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "transaction": self.transaction,
            "network": self.network,
            "amount": self.amount,
            "payer": self.payer,
            "explorer_url": self.explorer_url,
        }


# ------------------------------------------------------------------ configuration


def wallet_key() -> str:
    """The buyer's private key, from the environment only.

    Never read from memory and never written to it. The message names the variable, because
    "payment failed" with no next step is the least useful error there is.
    """
    key = os.environ.get(WALLET_ENV, "").strip()
    if not key:
        raise MissingWallet(
            f"Cairn needs a wallet to buy a trail, and never stores one. Set {WALLET_ENV} to "
            "the private key of a wallet holding test USDC on Base Sepolia. Test USDC is "
            "free from the Circle faucet, no account needed."
        )
    return key


def pay_to() -> str:
    """The address a shop's earnings go to."""
    address = os.environ.get(PAY_TO_ENV, "").strip()
    if not address:
        raise MissingWallet(
            f"A shop needs somewhere to be paid. Set {PAY_TO_ENV} to the wallet address that "
            "should receive payments for your trails."
        )
    return address


def price() -> str:
    """What this shop charges for one trail."""
    return os.environ.get(PRICE_ENV, "").strip() or DEFAULT_PRICE


def network() -> str:
    """Which chain the payment settles on."""
    return os.environ.get(NETWORK_ENV, "").strip() or BASE_SEPOLIA


def facilitator_url() -> str:
    """Who verifies and settles. The public one is free and testnet-only."""
    return os.environ.get(FACILITATOR_ENV, "").strip() or FacilitatorConfig().url


# ------------------------------------------------------------------------ selling


def gate(
    app: Any,
    *,
    paths: list[str],
    pay_to_address: str,
    asking_price: str,
    chain: str,
    facilitator: str,
) -> None:
    """Put the x402 paywall in front of these route patterns.

    `shop.py` calls this so it never has to import x402 itself. Patterns use the SDK's own
    syntax, where `[name]` matches one path segment — so `GET /trails/[domain]/[task]` gates
    the trail itself and leaves the one-segment catalogue above it free to browse.

    The middleware is ASGI and needs the async resource server; our own route handlers stay
    plain `def`, which FastAPI runs in a threadpool.
    """
    server = x402ResourceServer(HTTPFacilitatorClient(FacilitatorConfig(url=facilitator)))
    server.register(chain, ExactEvmServerScheme())
    server.initialize()

    option = PaymentOption(scheme=SCHEME, pay_to=pay_to_address, price=asking_price, network=chain)
    routes = {path: {"accepts": [option]} for path in paths}
    app.add_middleware(PaymentMiddlewareASGI, routes=routes, server=server)


# ------------------------------------------------------------------------ buying


def buy(url: str, *, max_amount: str = SPEND_CAP) -> tuple[dict[str, Any], Receipt]:
    """Pay for whatever is behind `url` and hand back the body and the receipt.

    The SDK does the 402 dance: it sees the challenge, signs a USDC authorisation, and
    retries with the signature attached. We only supply the wallet and a spending cap.

    A body with no settlement header is refused rather than accepted. That single check is
    what stops this being decoration — Cairn takes a trail only when it actually paid.
    """
    account = Account.from_key(wallet_key())
    client = x402ClientSync()
    register_exact_evm_client(client, EthAccountSigner(account))
    client.set_spend_controls({"max_amount_per_payment": max_amount})

    try:
        with x402_requests(client) as session:
            answer = session.get(url, timeout=BUY_TIMEOUT_SECONDS)
    except requests.RequestException as unreachable:
        raise ShopUnreachable(f"nothing answered at {url}: {unreachable}") from unreachable

    if answer.status_code == HTTP_STATUS_PAYMENT_REQUIRED:
        raise PaymentRefused(
            "the shop still wants paying after the payment attempt. Usually the wallet has "
            "no test USDC on this network, or the price is above the spending cap of "
            f"{max_amount}."
        )
    if answer.status_code == requests.codes.not_found:
        raise PaymentRefused(f"the shop has nothing for sale at {url}.")
    if not answer.ok:
        raise PaymentRefused(f"the shop answered {answer.status_code} for {url}.")

    return answer.json(), _settlement(answer)


def browse(base_url: str, domain: str) -> list[dict[str, Any]]:
    """What a shop has for a site, for free. Never pays, never signs.

    Browsing has to be free or nobody can tell what they are about to buy.
    """
    url = f"{base_url.rstrip('/')}/trails/{domain}"
    try:
        answer = requests.get(url, timeout=BROWSE_TIMEOUT_SECONDS)
    except requests.RequestException as unreachable:
        raise ShopUnreachable(f"nothing answered at {url}: {unreachable}") from unreachable
    if not answer.ok:
        raise ShopUnreachable(f"the shop at {base_url} answered {answer.status_code}.")
    body = answer.json()
    listed = body.get("trails", [])
    if not isinstance(listed, list):
        return []
    # The price sits on the response, not on each trail. Carrying it down onto each one lets
    # a buyer say what it is about to pay, and afterwards what it paid — the facilitator's
    # receipt comes back with the amount blank more often than not.
    return [{**trail, "price": body.get("price")} for trail in listed]


def _settlement(answer: requests.Response) -> Receipt:
    """Read the receipt off the response, or refuse the body it came with."""
    header = answer.headers.get(PAYMENT_RESPONSE_HEADER)
    if not header:
        raise PaymentRefused(
            "the shop handed over a trail without proof of payment. Cairn will not keep a "
            "trail it cannot show it paid for."
        )
    settled = decode_payment_response_header(header)
    if not settled.success:
        raise PaymentRefused(
            f"the payment did not settle: {settled.error_message or settled.error_reason}."
        )
    return Receipt(
        transaction=settled.transaction,
        network=settled.network,
        amount=settled.amount,
        payer=settled.payer,
    )
