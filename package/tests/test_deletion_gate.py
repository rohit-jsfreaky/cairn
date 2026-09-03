"""THE GATE.

The hackathon rules say the memory must be load-bearing: take it away, and the project
must stop doing what it claims. This file is that test, automated.

It runs with NO API key, because Cairn needs none. Anyone can clone this repo and run:

    pytest package/tests/test_deletion_gate.py -v

The shape of the proof is deliberately blunt:

    learn a site      ->  replay is fast and needs no model
    cairn forget      ->  replay has nothing to follow and says so
    learn it again    ->  the fast path comes back

If someone deleted `store.py` and stubbed the memory out, the middle step would pass
silently and the last step would fail. That is the point.
"""

from __future__ import annotations

import pytest
from tests.conftest import TASK, cold_run

from cairn.browser import Browser, domain_of
from cairn.events import Emitter
from cairn.executor import Executor, NoTrailError
from cairn.operations import Session
from cairn.store import CairnStore

# Used only by the paid-trail tests at the bottom, which need no browser and no server:
# a trail that changes hands for money is still just a trail in somebody's memory.
PAID_SITE = "billing.acme.com"
PAID_TASK = "read the invoice total"


@pytest.fixture
def learned_site(browser: Browser, store: CairnStore, demo_server: str) -> str:
    """Walk the site once, so there is something to take away."""
    session = Session(browser, store)
    cold_run(session, demo_server)
    session.save(TASK, domain=domain_of(demo_server))
    return domain_of(demo_server)


class TestTheDeletionGate:
    def test_before_forgetting_the_fast_path_works(
        self, learned_site: str, store: CairnStore, browser: Browser, demo_server: str
    ):
        result = Executor(store, browser).run(learned_site, start_url=f"{demo_server}/")

        assert result.ok is True
        assert result.metrics.steps_replayed == 6
        assert result.metrics.model_calls == 0

    def test_after_forgetting_there_is_nothing_left_to_follow(
        self, learned_site: str, store: CairnStore, browser: Browser, demo_server: str
    ):
        """The whole gate, in five lines."""
        assert store.load_playbook(learned_site) is not None

        store.forget_site(learned_site)

        with pytest.raises(NoTrailError):
            Executor(store, browser).run(learned_site, start_url=f"{demo_server}/")

    def test_it_says_so_out_loud_rather_than_improvising(
        self, learned_site: str, store: CairnStore, browser: Browser, demo_server: str
    ):
        """Failing loudly matters. Quietly falling back to guessing would hide the gate."""
        store.forget_site(learned_site)

        with pytest.raises(NoTrailError) as raised:
            Executor(store, browser).run(learned_site, start_url=f"{demo_server}/")

        message = str(raised.value).lower()
        assert "nothing remembered" in message
        assert learned_site in str(raised.value)

    def test_the_memory_read_is_what_fails(
        self, learned_site: str, store: CairnStore, browser: Browser, demo_server: str
    ):
        """Proves the failure comes from memory being gone, not from the browser."""
        store.forget_site(learned_site)
        emitter = Emitter()

        with pytest.raises(NoTrailError):
            Executor(store, browser, emitter=emitter).run(learned_site)

        reads = emitter.of_kind("memory_read")
        assert reads, "it should still have tried to read memory"
        assert reads[0].to_dict()["found"] is False

    def test_the_site_itself_is_untouched(
        self, learned_site: str, store: CairnStore, browser: Browser, demo_server: str
    ):
        """Forgetting removes what Cairn learned, not the ability to browse.

        Cairn degrades to an ordinary browser tool — slow again, exactly as it was on
        day one. That is the honest claim, and this pins it.
        """
        store.forget_site(learned_site)

        browser.goto(f"{demo_server}/")
        snapshot = browser.snapshot()

        assert snapshot.elements, "the browser still works perfectly well"
        assert any(element.name == "Sign in" for element in snapshot.elements)

    def test_the_fast_path_can_be_earned_back(
        self, learned_site: str, store: CairnStore, browser: Browser, demo_server: str
    ):
        """Walk it again and the trail returns. Forgetting is not damage."""
        store.forget_site(learned_site)

        session = Session(browser, store)
        cold_run(session, demo_server)
        session.save(TASK, domain=learned_site)

        result = Executor(store, browser).run(learned_site, start_url=f"{demo_server}/")
        assert result.ok is True
        assert result.metrics.steps_replayed == 6

    def test_forgetting_one_site_leaves_the_others_alone(
        self, learned_site: str, store: CairnStore, demo_server: str
    ):
        from cairn.models import Playbook

        store.save_playbook(Playbook(domain="other.example.com", task="something else"))

        store.forget_site(learned_site)

        assert store.load_playbook("other.example.com") is not None
        assert store.load_playbook(learned_site) is None


class TestTheGateSurvivesASharedMemory:
    """A commons is memory too, so it could quietly become a back door around the gate.

    These are the tests that keep "delete the memory and the project stops working" true
    rather than nearly true.
    """

    def test_replay_never_reads_the_commons(self):
        """The rule the whole gate rests on, checked mechanically.

        If `Executor` could fall back to a shared trail, this entire file would be proving
        nothing: a judge would forget a site and replay would carry on regardless. Another
        agent's trail has to be deliberately borrowed first, which copies it into this
        agent's own memory, which is exactly what makes it forgettable.
        """
        import pathlib

        source = (pathlib.Path(__file__).resolve().parents[1] / "src/cairn/executor.py").read_text(
            encoding="utf-8"
        )
        body = source.split('"""', 2)[-1]

        for reaching_out in (
            "offers_for",
            "borrow_trail",
            "every_offer",
            "take_bought_trail",
            "_shared",
        ):
            assert reaching_out not in body, (
                f"executor.py touches the commons via {reaching_out} — the warm path must "
                f"only ever follow a trail this agent holds itself"
            )

        # And it must never reach for the network or a wallet either. A replay that could
        # buy a trail mid-run would be neither deterministic, nor free, nor forgettable.
        for off_machine in ("payments", "shop", "requests"):
            assert off_machine not in body, (
                f"executor.py reaches off this machine via {off_machine} — replay must stay "
                f"offline, deterministic and free"
            )

    def test_forgetting_a_site_leaves_replay_with_nothing_even_when_others_shared_it(
        self, tmp_path, browser, demo_server
    ):
        from cairn.browser import domain_of
        from cairn.executor import Executor, NoTrailError
        from cairn.models import Playbook, Postcondition, Step
        from cairn.store import CairnStore

        shared_db = str(tmp_path / "memory.db")
        site = domain_of(demo_server)
        trail = Playbook(
            domain=site,
            task="open the portal",
            steps=[
                Step(
                    index=1,
                    intent="open the portal",
                    action="goto",
                    value=f"{demo_server}/",
                    postcondition=Postcondition("url_contains", "/"),
                )
            ],
        )

        alice = CairnStore(db_path=shared_db, agent="alice")
        alice.save_playbook(trail)
        alice.share_trail(site)

        bob = CairnStore(db_path=shared_db, agent="bob")
        bob.borrow_trail(site)
        assert Executor(bob, browser).run(site, task="open the portal").ok

        bob.forget_site(site)

        # Alice still offers it. That changes nothing for replay.
        assert bob.offers_for(site)
        with pytest.raises(NoTrailError):
            Executor(bob, browser).run(site, task="open the portal")


class TestTheGateSurvivesATrailThatWasPaidFor:
    """Money buys a copy of a trail. It must not buy an exemption from the gate.

    This is the sharpest question a judge can ask about Phase 5b: once a payment is on a
    public chain forever, is the memory still the thing doing the work? These tests are the
    answer. Nothing here touches a chain — the receipt is a plain dict, which is all a
    receipt ever is once it has been written down.
    """

    @staticmethod
    def _offer(seller):
        from cairn.store import offer_key

        return seller._offer(offer_key(PAID_SITE, PAID_TASK, "alice"))

    @staticmethod
    def _receipt() -> dict:
        return {
            "transaction": "0xnotarealtransaction",
            "network": "eip155:84532",
            "amount": "$0.01",
            "explorer_url": "https://sepolia.basescan.org/tx/0xnotarealtransaction",
        }

    def _sold_and_bought(self, tmp_path):
        """Alice sells, Bob buys. Two databases, so nothing is shared but the offer dict."""
        from cairn.models import Playbook, Postcondition, Step

        alice = CairnStore(db_path=str(tmp_path / "alice.db"), agent="alice")
        alice.save_playbook(
            Playbook(
                domain=PAID_SITE,
                task=PAID_TASK,
                runs=3,
                steps=[
                    Step(
                        index=1,
                        intent="open the portal",
                        action="goto",
                        value=f"https://{PAID_SITE}/",
                        postcondition=Postcondition("url_contains", "/"),
                    )
                ],
            )
        )
        alice.share_trail(PAID_SITE)

        bob = CairnStore(db_path=str(tmp_path / "bob.db"), agent="bob")
        bob.take_bought_trail(self._offer(alice), receipt=self._receipt())
        return alice, bob

    def test_a_bought_trail_can_still_be_forgotten(self, tmp_path):
        _alice, bob = self._sold_and_bought(tmp_path)
        assert bob.load_playbook(PAID_SITE, PAID_TASK) is not None

        bob.forget_site(PAID_SITE)

        assert bob.load_playbook(PAID_SITE, PAID_TASK) is None

    def test_and_the_transaction_cannot_bring_it_back(self, tmp_path):
        """THE POINT. The payment is permanent and public; the trail is neither. A receipt
        is proof that something was bought, never a copy of it — so memory, not the chain,
        is what the replay depends on."""
        _alice, bob = self._sold_and_bought(tmp_path)
        bob.forget_site(PAID_SITE)

        # The receipt is still in the cold journal, transaction hash and all.
        assert "0xnotarealtransaction" in str(bob.read_journal(limit=50))

        # And it is worth nothing: there is no route, and nothing can derive one from it.
        assert bob.load_playbook(PAID_SITE, PAID_TASK) is None
        assert bob.was_forgotten(PAID_SITE) is True

    def test_when_the_seller_forgets_there_is_nothing_left_to_sell(self, tmp_path):
        """The shop's only stock is memory, so `forget` empties the shelf. A shop that kept
        selling a trail its owner had forgotten would be a second source of truth."""
        alice, _bob = self._sold_and_bought(tmp_path)
        assert alice.my_offers_for(PAID_SITE)

        alice.forget_site(PAID_SITE)

        assert alice.my_offers_for(PAID_SITE) == []

    def test_the_buyer_keeps_what_it_paid_for_when_the_seller_forgets(self, tmp_path):
        """The other half of the same rule. A bought trail is the buyer's own copy — the
        seller cannot reach into another agent's memory, and should not be able to."""
        alice, bob = self._sold_and_bought(tmp_path)

        alice.forget_site(PAID_SITE)

        assert bob.load_playbook(PAID_SITE, PAID_TASK) is not None
