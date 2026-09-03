"""Buying a trail, through the tool a host AI actually sees.

The engine tests prove the money and the memory work. These prove the AI is told the right
thing at the right moment, which is what decides whether the handoff happens at all — on
the first live test of this project a host AI ignored Cairn entirely and reached for `curl`,
so what the descriptions say is not decoration.

Nothing here touches a chain or the network. `payments.browse` and `payments.buy` are the
seam, and they are faked at it: what is under test is the tool's wiring and its wording.
"""

from __future__ import annotations

import pytest

pytest.importorskip("x402", reason="the market is an optional extra: pip install cairn[market]")

import asyncio  # noqa: E402

from cairn import payments  # noqa: E402
from cairn.models import Playbook, Postcondition, Step  # noqa: E402
from cairn.store import CairnStore  # noqa: E402

from helpers import call  # noqa: E402

SITE = "acme.com"
TASK = "read the invoice total"
SHOP = "http://127.0.0.1:8402"


def a_trail() -> Playbook:
    return Playbook(
        domain=SITE,
        task=TASK,
        runs=3,
        steps=[
            Step(
                index=1,
                intent="open the portal",
                action="goto",
                value=f"https://{SITE}/",
                postcondition=Postcondition("url_contains", "/"),
            ),
            Step(
                index=2,
                intent="type the password",
                action="fill",
                secret="password",
                postcondition=Postcondition("url_contains", "/home"),
            ),
        ],
    )


def an_offer(tmp_path) -> dict:
    """Exactly what a shop would put on the wire: a shared, already-redacted offer."""
    seller = CairnStore(db_path=str(tmp_path / "alice.db"), agent="alice")
    seller.save_playbook(a_trail())
    seller.share_trail(SITE)
    return seller.my_offers_for(SITE)[0]


def a_receipt() -> payments.Receipt:
    return payments.Receipt(transaction="0xfeedface", network=payments.BASE_SEPOLIA, amount="$0.01")


@pytest.fixture
def shop_sells(monkeypatch, tmp_path):
    """A shop that lists one trail and hands it over when paid."""
    offer = an_offer(tmp_path)
    monkeypatch.setattr(
        payments, "browse", lambda url, domain: [{"task": TASK, "steps": 2, "runs": 3}]
    )
    monkeypatch.setattr(payments, "buy", lambda url, **kwargs: (offer, a_receipt()))
    return offer


@pytest.fixture
def shop_is_empty(monkeypatch):
    monkeypatch.setattr(payments, "browse", lambda url, domain: [])


@pytest.fixture
def shop_is_down(monkeypatch):
    def refuse(url, domain):
        raise payments.ShopUnreachable(f"nothing answered at {url}")

    monkeypatch.setattr(payments, "browse", refuse)


# --------------------------------------------------------------------- buying


class TestBuyingThroughTheTool:
    def test_a_bought_trail_becomes_this_agents_own(self, mcp_server, shop_sells):
        bought = call(mcp_server, "cairn_buy", shop=SHOP, site=SITE)

        assert bought["ok"] is True
        assert bought["task"] == TASK
        assert SITE in [row["site"] for row in call(mcp_server, "cairn_sites")["sites"]]

    def test_it_hands_back_the_exact_wording_to_run_with(self, mcp_server, shop_sells):
        """A paraphrase may not match, and the money shot is not a round trip about wording."""
        bought = call(mcp_server, "cairn_buy", shop=SHOP, site=SITE)

        assert TASK in bought["next"]

    def test_it_says_who_it_was_bought_from(self, mcp_server, shop_sells):
        bought = call(mcp_server, "cairn_buy", shop=SHOP, site=SITE)

        assert bought["bought_from"] == "alice"
        assert bought["first_walked_by"] == "alice"
        assert bought["clean_runs_behind_it"] == 3

    def test_and_shows_the_transaction_a_person_can_go_and_check(self, mcp_server, shop_sells):
        """A payment nobody can verify is worth nothing to a judge."""
        paid = call(mcp_server, "cairn_buy", shop=SHOP, site=SITE)["paid"]

        assert paid["transaction"] == "0xfeedface"
        assert paid["explorer_url"].startswith("https://sepolia.basescan.org/tx/")

    def test_it_warns_that_the_login_is_not_included(self, mcp_server, shop_sells):
        """What is sold is the route, never an account. The AI has to know that up front,
        or it will run the trail and be confused when a password is asked for."""
        bought = call(mcp_server, "cairn_buy", shop=SHOP, site=SITE)

        assert bought["you_must_supply"] == ["password"]
        assert "password" in bought["next"]


# ------------------------------------------------------------ when it goes wrong


class TestItFailsInSentences:
    """Every one of these is a message a host AI has to act on. A stack trace is useless
    to it, and so is "error"."""

    def test_a_shop_that_is_not_answering(self, mcp_server, shop_is_down):
        refused = call(mcp_server, "cairn_buy", shop=SHOP, site=SITE)

        assert refused["ok"] is False
        assert "nothing answered" in refused["error"]
        assert "Traceback" not in str(refused)

    def test_a_shop_with_nothing_for_this_site(self, mcp_server, shop_is_empty):
        refused = call(mcp_server, "cairn_buy", shop=SHOP, site="nobody-sells-this.com")

        assert refused["ok"] is False
        assert "no trail for nobody-sells-this.com" in refused["error"]

    def test_a_shop_that_sells_something_else_says_what(self, mcp_server, monkeypatch):
        """Being told what IS on sale is the difference between one more call and giving up."""
        monkeypatch.setattr(
            payments, "browse", lambda url, domain: [{"task": "cancel the subscription"}]
        )

        refused = call(mcp_server, "cairn_buy", shop=SHOP, site=SITE, task="something else")

        assert "cancel the subscription" in refused["error"]

    def test_no_wallet_names_the_variable_to_set(self, mcp_server, monkeypatch, tmp_path):
        """A payment that failed with no next step is the least useful error there is."""
        monkeypatch.delenv(payments.WALLET_ENV, raising=False)
        monkeypatch.setattr(payments, "browse", lambda url, domain: [{"task": TASK}])

        refused = call(mcp_server, "cairn_buy", shop=SHOP, site=SITE)

        assert refused["ok"] is False
        assert payments.WALLET_ENV in refused["error"]

    def test_buying_over_a_repaired_trail_needs_saying_so(self, mcp_server, shop_sells):
        mine = a_trail()
        mine.repairs = 2
        mcp_server.cairn_tools.store.save_playbook(mine)

        refused = call(mcp_server, "cairn_buy", shop=SHOP, site=SITE)

        assert refused["ok"] is False
        assert "force=true" in refused["error"]

    def test_but_force_gets_through(self, mcp_server, shop_sells):
        mine = a_trail()
        mine.repairs = 2
        mcp_server.cairn_tools.store.save_playbook(mine)

        assert call(mcp_server, "cairn_buy", shop=SHOP, site=SITE, force=True)["ok"] is True


# ------------------------------------------------------------------- being told


class TestTheAiIsToldBuyingIsAnOption:
    def test_an_unknown_site_mentions_buying_when_a_shop_is_configured(
        self, mcp_server, monkeypatch
    ):
        """Otherwise the AI explores a site somebody has already walked and paid for."""
        monkeypatch.setenv("CAIRN_SHOPS", SHOP)

        nudge = call(mcp_server, "cairn_run", site="never-seen.com")["next"]

        assert "cairn_buy" in nudge
        assert SHOP in nudge

    def test_but_stays_quiet_when_no_shop_is_configured(self, mcp_server, monkeypatch):
        """Suggesting a purchase from nowhere would be noise, and worse, a dead end."""
        monkeypatch.delenv("CAIRN_SHOPS", raising=False)

        nudge = call(mcp_server, "cairn_run", site="never-seen.com")["next"]

        assert "cairn_buy" not in nudge
        assert "Explore it once" in nudge

    def test_the_description_says_what_is_and_is_not_sold(self, mcp_server):
        """Nobody should learn that a login is not included by running the trail."""
        described = {t.name: t.description or "" for t in asyncio.run(mcp_server.list_tools())}

        text = described["cairn_buy"]
        assert "NOT AN ACCOUNT" in text
        assert payments.WALLET_ENV in text

    def test_cairn_run_is_still_the_first_thing_the_instructions_name(self, mcp_server):
        """A fifteenth tool must not dislodge the one that has to be called first."""
        instructions = mcp_server.instructions or ""

        assert "cairn_run FIRST" in instructions
        assert instructions.index("cairn_run") < instructions.index("cairn_act")
