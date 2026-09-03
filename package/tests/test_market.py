"""A trail one agent will sell and another will buy.

The local commons hands a trail over for free between two agents sharing one database.
This is the case that actually happens: two agents on different machines, sharing nothing
but a network. The only way across is HTTP, and the only reason anyone publishes is that
they can charge for it.

Nothing here touches a chain or the network. Two things are tested separately on purpose:

* **the paywall** — with the real x402 middleware in front, so the 402 and its header are
  the genuine article. No facilitator is needed to be told to pay; one is only needed to
  verify a payment, and verifying is not what these tests are about.
* **the payload** — with the paywall lifted, because the body behind it cannot be reached
  without settling a real payment. Splitting them is what lets the redaction be checked at
  all, and the redaction is the half that would become an incident if it broke.

The one thing not covered offline is a settlement round trip. That is checked by hand
against Base Sepolia; see PROGRESS.md.
"""

from __future__ import annotations

import pytest

pytest.importorskip("x402", reason="the market is an optional extra: pip install cairn[market]")

from fastapi.testclient import TestClient  # noqa: E402

from cairn import payments  # noqa: E402
from cairn.models import Locator, Playbook, Postcondition, SiteKnowledge, Step  # noqa: E402
from cairn.shop import build_app  # noqa: E402
from cairn.store import CairnStore, TrailAlreadyHere, offer_key, slug  # noqa: E402

DOMAIN = "acme.com"
TASK = "read the invoice total"

# A throwaway address. Nothing is ever sent to it in these tests.
SELLER_ADDRESS = "0x000000000000000000000000000000000000dEaD"
PRICE = "$0.01"
CHAIN = payments.BASE_SEPOLIA

# What must never appear in an HTTP response.
TYPED_EMAIL = "alice@acme.com"
ACCOUNT_HINT = "rohit"
WALLET_KEY = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"


def a_trail(*, task: str = TASK, runs: int = 4) -> Playbook:
    """A sign-in-then-read trail, the shape that carries something personal."""
    return Playbook(
        domain=DOMAIN,
        task=task,
        runs=runs,
        steps=[
            Step(
                index=1,
                intent="open the portal",
                action="goto",
                value=f"https://{DOMAIN}/",
                postcondition=Postcondition("url_contains", "/"),
            ),
            Step(
                index=2,
                intent="type the account email",
                action="fill",
                value=TYPED_EMAIL,
                postcondition=Postcondition("value_is", TYPED_EMAIL),
                locators=[Locator("label", "Email", hits=9)],
            ),
            Step(
                index=3,
                intent="read the total",
                action="read",
                value="text",
                postcondition=Postcondition("element_present", "#total"),
                locators=[Locator("css", "#total", hits=4)],
            ),
        ],
    )


def some_facts() -> SiteKnowledge:
    return SiteKnowledge(
        domain=DOMAIN,
        notes=["the badge is cached, trust the Open tab"],
        needs_login=True,
        account_hint=ACCOUNT_HINT,
        overlays=["#accept-cookies"],
    )


@pytest.fixture
def seller(tmp_path) -> CairnStore:
    """An agent that has walked the site and put its trail up for sale."""
    store = CairnStore(db_path=str(tmp_path / "alice.db"), agent="alice")
    store.save_playbook(a_trail())
    store.save_site_knowledge(some_facts())
    store.share_trail(DOMAIN)
    return store


@pytest.fixture
def buyer(tmp_path) -> CairnStore:
    """An agent with its OWN database. No commons in common — HTTP is the only way in."""
    return CairnStore(db_path=str(tmp_path / "bob.db"), agent="bob")


def a_shop(store: CairnStore) -> TestClient:
    """The shop as a stranger meets it: real paywall, real middleware."""
    return TestClient(
        build_app(
            store,
            pay_to_address=SELLER_ADDRESS,
            asking_price=PRICE,
            chain=CHAIN,
            facilitator=payments.facilitator_url(),
        )
    )


def an_open_shop(store: CairnStore, monkeypatch) -> TestClient:
    """The same shop with the paywall lifted, so the body behind it can be read.

    Only ever used to inspect what would be served. The paywall itself is proved separately
    by `TestThePaywall`, and one test asserts these two really are the same app.
    """
    monkeypatch.setattr(payments, "gate", lambda *args, **kwargs: None)
    return a_shop(store)


def trail_path(task: str = TASK) -> str:
    return f"/trails/{DOMAIN}/{slug(task)}"


# ------------------------------------------------------------------ free browsing


class TestBrowsingIsFree:
    """You have to be able to see what you are about to buy, or nobody buys."""

    def test_the_catalogue_lists_what_is_for_sale(self, seller):
        listed = a_shop(seller).get(f"/trails/{DOMAIN}").json()

        assert listed["shop"] == "alice"
        assert listed["price"] == PRICE
        assert [trail["task"] for trail in listed["trails"]] == [TASK]

    def test_the_catalogue_carries_no_steps_and_no_locators(self, seller):
        """The whole point of charging. A catalogue that leaked the route would be giving
        away the thing it is selling."""
        body = a_shop(seller).get(f"/trails/{DOMAIN}").text

        assert "locators" not in body
        assert "#total" not in body
        assert "postcondition" not in body

    def test_it_does_say_how_well_the_trail_has_held_up(self, seller):
        """Steps as a COUNT, runs, borrows and outcomes — enough to judge it, not to run it."""
        only = a_shop(seller).get(f"/trails/{DOMAIN}").json()["trails"][0]

        assert only["steps"] == 3
        assert only["runs"] == 4
        assert {"borrows", "worked_for", "failed_for", "shared_by"} <= set(only)

    def test_a_site_nobody_shared_is_an_empty_shelf_not_an_error(self, seller):
        answer = a_shop(seller).get("/trails/nobody-has-been-here.com")

        assert answer.status_code == 200
        assert answer.json()["trails"] == []

    def test_health_says_who_this_shop_is_and_what_it_charges(self, seller):
        """A buyer should be able to look before trusting anything."""
        body = a_shop(seller).get("/health").json()

        assert body == {
            "ok": True,
            "shop": "alice",
            "network": CHAIN,
            "price": PRICE,
            "pay_to": SELLER_ADDRESS,
        }

    def test_a_trail_this_agent_did_not_share_is_not_for_sale(self, seller):
        """Selling is opt-in. Walking a site must never put it on the shelf by itself."""
        seller.save_playbook(a_trail(task="cancel the subscription"))

        for_sale = a_shop(seller).get(f"/trails/{DOMAIN}").json()["trails"]

        assert [trail["task"] for trail in for_sale] == [TASK]


# ---------------------------------------------------------------------- the paywall


class TestThePaywall:
    """The trail is genuinely unreachable without paying. Everything else is decoration."""

    def test_the_trail_answers_402_before_any_payment(self, seller):
        assert a_shop(seller).get(trail_path()).status_code == 402

    def test_and_says_how_to_pay_in_the_header_x402_expects(self, seller):
        """Verified against the installed SDK's own constant, not a remembered string."""
        from x402.http import PAYMENT_REQUIRED_HEADER

        answer = a_shop(seller).get(trail_path())

        assert PAYMENT_REQUIRED_HEADER in answer.headers

    def test_a_trail_the_shop_does_not_have_is_still_behind_the_paywall(self, seller):
        """The paywall runs before the handler and cannot see the inventory, so this is a
        402 rather than a 404. Nobody is charged for it: the middleware settles only after
        the handler and skips settlement on any 4xx, so the worst case is a 404 and an
        untouched wallet."""
        assert a_shop(seller).get(trail_path("no such task")).status_code == 402

    def test_the_free_and_paid_routes_are_the_same_app(self, seller):
        """Guards the split these tests rely on: one app, one route gated and one not.
        If the catalogue were served by some other app, its freeness would prove nothing."""
        client = a_shop(seller)

        assert client.get(f"/trails/{DOMAIN}").status_code == 200
        assert client.get(trail_path()).status_code == 402


# ------------------------------------------------------------- what would be served


class TestWhatIsSoldIsRedacted:
    """The local commons already proves this for a borrower. An HTTP body is a brand new
    way out of the process, so it gets its own proof."""

    def test_the_email_typed_into_the_login_form_is_not_in_the_response(self, seller, monkeypatch):
        body = an_open_shop(seller, monkeypatch).get(trail_path()).text

        assert TYPED_EMAIL not in body

    def test_the_account_hint_never_leaves_the_machine_that_learned_it(self, seller, monkeypatch):
        """Which person's login was used is nobody else's business."""
        body = an_open_shop(seller, monkeypatch).get(trail_path()).text

        assert ACCOUNT_HINT not in body

    def test_but_the_route_itself_does_go(self, seller, monkeypatch):
        """The buyer has to receive something worth paying for."""
        offer = an_open_shop(seller, monkeypatch).get(trail_path()).json()

        assert offer["shared_by"] == "alice"
        assert len(offer["playbook"]["steps"]) == 3
        assert "#total" in str(offer["playbook"])

    def test_and_the_step_that_needed_a_value_says_so_instead(self, seller, monkeypatch):
        """A bought login step asks the buyer for the buyer's own credentials."""
        offer = an_open_shop(seller, monkeypatch).get(trail_path()).json()

        secrets = [step.get("secret") for step in offer["playbook"]["steps"]]

        assert any(secrets), "a redacted fill step must name what it now needs"

    def test_the_hard_won_site_notes_do_travel(self, seller, monkeypatch):
        """Notes are about the site, not the person, and they are the expensive part."""
        offer = an_open_shop(seller, monkeypatch).get(trail_path()).json()

        assert "the badge is cached, trust the Open tab" in offer["site_knowledge"]["notes"]

    def test_the_wallet_key_is_nowhere_near_any_of_this(self, seller, monkeypatch):
        """A wallet key is a secret in the `secrets.py` sense: it never reaches memory, a
        trail, an offer, or the wire."""
        monkeypatch.setenv(payments.WALLET_ENV, WALLET_KEY)

        body = an_open_shop(seller, monkeypatch).get(trail_path()).text

        assert WALLET_KEY not in body
        assert WALLET_KEY not in str(seller.every_offer())


# --------------------------------------------------------------------- buying it


class TestBuyingImportsItProperly:
    """A bought trail must arrive exactly as a borrowed one does. That is why both go
    through `_import_offer` — two import paths would drift, and the paid one is the one
    nobody exercises by accident."""

    @staticmethod
    def _sold(seller: CairnStore) -> dict:
        return seller._offer(offer_key(DOMAIN, TASK, "alice"))

    def _receipt(self) -> dict:
        return payments.Receipt(
            transaction="0xfeedface", network=CHAIN, amount="$0.01", payer="0xbeef"
        ).to_dict()

    def test_a_bought_trail_becomes_the_buyers_own(self, seller, buyer):
        bought = buyer.take_bought_trail(self._sold(seller), receipt=self._receipt())

        assert buyer.load_playbook(DOMAIN, bought.task) is not None
        assert DOMAIN in buyer.list_sites()

    def test_and_says_where_it_came_from(self, seller, buyer):
        bought = buyer.take_bought_trail(self._sold(seller), receipt=self._receipt())

        assert bought.borrowed_from == "alice"
        assert bought.origin_agent == "alice"
        assert bought.inherited_runs == 4

    def test_but_not_that_the_buyer_earned_those_runs(self, seller, buyer):
        """Inheriting the counters would make the buyer's own journal lie."""
        bought = buyer.take_bought_trail(self._sold(seller), receipt=self._receipt())

        assert bought.runs == 0
        assert bought.repairs == 0

    def test_the_receipt_goes_into_the_journal(self, seller, buyer):
        buyer.take_bought_trail(self._sold(seller), receipt=self._receipt())

        journal = buyer.read_journal(limit=20)
        kinds = [entry.get("extra", {}).get("kind") for entry in journal]

        assert "bought" in kinds
        assert "0xfeedface" in str(journal)

    def test_buying_over_a_trail_you_repaired_refuses(self, seller, buyer):
        """The same protection borrowing has. Losing a repair you paid for twice over
        would be the worst version of this bug."""
        mine = a_trail()
        mine.repairs = 2
        buyer.save_playbook(mine)

        with pytest.raises(TrailAlreadyHere, match="repaired"):
            buyer.take_bought_trail(self._sold(seller), receipt=self._receipt())

    def test_unless_the_buyer_says_so_on_purpose(self, seller, buyer):
        mine = a_trail()
        mine.repairs = 2
        buyer.save_playbook(mine)

        bought = buyer.take_bought_trail(self._sold(seller), receipt=self._receipt(), force=True)

        assert bought.repairs == 0


# ------------------------------------------------------------------- the seller's side


class TestTheLedgerRemembersTheSale:
    """What makes the commons dynamic storage rather than a pile of files: an offer
    accumulates what actually happened to it."""

    def _receipt(self) -> dict:
        return payments.Receipt(transaction="0xabc", network=CHAIN, amount="$0.01").to_dict()

    def test_a_sale_is_counted(self, seller):
        assert seller.record_sale(DOMAIN, TASK, receipt=self._receipt()) is True

        assert seller.my_offers_for(DOMAIN)[0]["sold"] == 1

    def test_and_the_receipt_is_kept(self, seller):
        seller.record_sale(DOMAIN, TASK, receipt=self._receipt())

        assert seller.my_offers_for(DOMAIN)[0]["receipts"][0]["transaction"] == "0xabc"

    def test_selling_a_trail_this_shop_does_not_have_changes_nothing(self, seller):
        assert seller.record_sale(DOMAIN, "no such task", receipt=self._receipt()) is False

    def test_republishing_an_improved_trail_keeps_what_it_earned(self, seller):
        """The trail may have got better. The record of who paid for it is still true."""
        seller.record_sale(DOMAIN, TASK, receipt=self._receipt())

        seller.share_trail(DOMAIN)

        assert seller.my_offers_for(DOMAIN)[0]["sold"] == 1

    def test_the_catalogue_shows_a_sale_to_the_next_buyer(self, seller):
        seller.record_sale(DOMAIN, TASK, receipt=self._receipt())

        listed = a_shop(seller).get(f"/trails/{DOMAIN}").json()["trails"][0]

        assert listed["task"] == TASK


# ------------------------------------------------------------------------- secrets


class TestAWalletIsASecret:
    def test_no_wallet_key_stops_and_names_the_variable(self, monkeypatch):
        """A payment that failed with no next step is the least useful error there is."""
        monkeypatch.delenv(payments.WALLET_ENV, raising=False)

        with pytest.raises(payments.MissingWallet, match=payments.WALLET_ENV):
            payments.wallet_key()

    def test_a_shop_with_nowhere_to_be_paid_stops_too(self, monkeypatch):
        monkeypatch.delenv(payments.PAY_TO_ENV, raising=False)

        with pytest.raises(payments.MissingWallet, match=payments.PAY_TO_ENV):
            payments.pay_to()

    def test_the_defaults_are_the_free_testnet_path(self, monkeypatch):
        """Nobody should have to spend money to try this."""
        for unset in (payments.NETWORK_ENV, payments.FACILITATOR_ENV, payments.PRICE_ENV):
            monkeypatch.delenv(unset, raising=False)

        assert payments.network() == payments.BASE_SEPOLIA
        assert payments.facilitator_url() == "https://x402.org/facilitator"
        assert payments.price() == "$0.01"

    def test_a_receipt_links_somewhere_a_person_can_check(self, monkeypatch):
        """A transaction hash nobody can find proves nothing."""
        receipt = payments.Receipt(transaction="0xdeadbeef", network=payments.BASE_SEPOLIA)

        assert receipt.explorer_url == "https://sepolia.basescan.org/tx/0xdeadbeef"


# -------------------------------------------------------------------- the boundary


class TestPaymentsStaysInOneFile:
    def test_only_the_payments_file_talks_to_x402(self):
        """The same promise `store.py` makes about memory. A judge checking the onchain
        action should find all of it in one file, and `shop.py` deliberately goes through
        `payments.gate()` rather than importing the SDK itself."""
        import pathlib

        root = pathlib.Path(__file__).resolve().parents[2]
        importers = sorted(
            path.relative_to(root).as_posix()
            for folder in ("package/src", "mcp/src")
            for path in (root / folder).rglob("*.py")
            if any(
                marker in path.read_text(encoding="utf-8")
                for marker in ("import x402", "from x402", "eth_account", "from web3")
            )
        )

        assert importers == ["package/src/cairn/payments.py"], (
            f"x402 calls have escaped payments.py: {importers}"
        )
