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

        for reaching_out in ("offers_for", "borrow_trail", "every_offer", "_shared"):
            assert reaching_out not in body, (
                f"executor.py touches the commons via {reaching_out} — the warm path must "
                f"only ever follow a trail this agent holds itself"
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
