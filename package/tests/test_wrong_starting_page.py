"""A trail can be perfectly healthy and still not run, because you are somewhere else.

Reported twice from a real marketplace. Replaying "sign in as admin" WHILE ALREADY SIGNED
IN sends `/admin/sign-in` to `/admin/dashboard`, so there is no email field to fill. Cairn
called it drift, offered twenty-three dashboard controls as repair candidates — nav links,
stat tiles, a date picker — and told the caller to pick the one matching "enter the admin
email". None of them was an email field. An agent following that instruction literally
binds a working step to a nav link and destroys the trail.

The first attempt only noticed when step 1 was a `goto` whose URL check failed, which
misses almost every real trail: `url_contains` is a substring test, so a trail starting at
a bare host matches every page on that site, and a trail that navigates by CLICKING never
went through that branch at all.

So a step now records the page it was performed on, and replay asks the question directly —
before it tries a single locator. That order is the important part, and the second class
below is why.
"""

from __future__ import annotations

import pytest

from cairn.browser import Browser
from cairn.executor import Executor
from cairn.models import Locator, Playbook, Postcondition, Step
from cairn.store import CairnStore

SITE = "billing.example"
TASK = "sign in"


def a_trail(*, belongs_on: str) -> Playbook:
    """Open a page, then type into a field that only exists on `belongs_on`.

    The shape every sign-in trail has: step one says WHERE, step two needs something that
    is only there.
    """
    return Playbook(
        domain=SITE,
        task=TASK,
        steps=[
            Step(
                index=1,
                intent="open the sign-in page",
                action="goto",
                value="/admin",
                postcondition=Postcondition("url_contains", "/admin"),
            ),
            Step(
                index=2,
                intent="type the billing email",
                action="fill",
                value="finance@acme.com",
                postcondition=Postcondition("element_present", "#billing-email"),
                locators=[Locator("css", "#billing-email")],
                page=belongs_on,
            ),
        ],
    )


@pytest.fixture
def astray(store: CairnStore) -> CairnStore:
    """A trail whose second step belongs on /settings, replayed somewhere else.

    The demo site's `/admin` redirects to `/invoices`, the way a sign-in page redirects
    once you are already signed in.
    """
    store.save_playbook(a_trail(belongs_on="/settings"))
    return store


class TestBeingOnTheWrongPage:
    def test_it_is_not_reported_as_something_to_repair(
        self, astray: CairnStore, browser: Browser, demo_server: str
    ) -> None:
        result = Executor(astray, browser).run(SITE, task=TASK, start_url=f"{demo_server}/admin")

        assert result.ok is False
        assert result.wrong_place is True
        assert result.needs_repair is False

    def test_and_no_candidates_are_offered_to_bind_it_to(
        self, astray: CairnStore, browser: Browser, demo_server: str
    ) -> None:
        """Offering candidates IS the damage. Nothing on this page should ever be bound to
        this step."""
        result = Executor(astray, browser).run(SITE, task=TASK, start_url=f"{demo_server}/admin")

        assert result.repair is None

    def test_it_says_where_the_step_belongs_and_where_we_are(
        self, astray: CairnStore, browser: Browser, demo_server: str
    ) -> None:
        result = Executor(astray, browser).run(SITE, task=TASK, start_url=f"{demo_server}/admin")

        assert "/settings" in result.reason
        assert "/invoices" in result.reason
        assert "not met" in result.reason

    def test_and_says_plainly_not_to_repair_it(
        self, astray: CairnStore, browser: Browser, demo_server: str
    ) -> None:
        result = Executor(astray, browser).run(SITE, task=TASK, start_url=f"{demo_server}/admin")

        assert "NOT repair" in result.reason

    def test_the_already_done_case_is_named_because_it_is_the_common_one(
        self, astray: CairnStore, browser: Browser, demo_server: str
    ) -> None:
        result = Executor(astray, browser).run(SITE, task=TASK, start_url=f"{demo_server}/admin")

        assert "already" in result.reason.lower()


class TestItDoesNotDamageTheTrailItRefusedToRun:
    """The fault that was worse than the one reported.

    Deciding late — after the locators had been tried — meant every wrong-place replay
    recorded a miss against a perfectly good locator. A few of those drag the trail's
    health under half, `is_stale` turns true, and the trail is RETIRED. Stopping the bad
    repair does nothing about that; only asking the question first does.
    """

    def test_the_healthy_locator_is_not_marked_as_drift(
        self, astray: CairnStore, browser: Browser, demo_server: str
    ) -> None:
        before = astray.load_playbook(SITE, TASK).steps[1].locators[0].misses

        Executor(astray, browser).run(SITE, task=TASK, start_url=f"{demo_server}/admin")

        after = astray.load_playbook(SITE, TASK).steps[1].locators[0].misses
        assert after == before

    def test_and_the_trail_is_never_condemned_however_often_you_do_it(
        self, astray: CairnStore, browser: Browser, demo_server: str
    ) -> None:
        """A handful of wrong-place replays used to be enough to retire a trail.

        Health may RISE — step one really does succeed every time, and earns its hit. What
        must never happen is a fall, or `is_stale` turning true on a trail that was never
        broken.
        """
        was = astray.load_playbook(SITE, TASK).health

        for _ in range(5):
            Executor(astray, browser).run(SITE, task=TASK, start_url=f"{demo_server}/admin")

        after = astray.load_playbook(SITE, TASK)
        assert after.health >= was
        assert after.is_stale is False


class TestARedirectIsStillFine:
    def test_a_step_replayed_where_it_belongs_still_runs(
        self, store: CairnStore, browser: Browser, demo_server: str
    ) -> None:
        """The tolerance that caused this must not be thrown out with it: a site that
        canonicalises its own URL has to keep working."""
        store.save_playbook(a_trail(belongs_on="/settings"))

        result = Executor(store, browser).run(SITE, task=TASK, start_url=f"{demo_server}/settings")

        assert result.ok is True
        assert result.wrong_place is False

    def test_a_trail_from_before_this_existed_still_replays(
        self, store: CairnStore, browser: Browser, demo_server: str
    ) -> None:
        """Steps saved before they recorded a page have nothing to compare, and must opt
        out rather than refuse everything."""
        store.save_playbook(a_trail(belongs_on=""))

        result = Executor(store, browser).run(SITE, task=TASK, start_url=f"{demo_server}/settings")

        assert result.ok is True


class TestATrailThatNavigatesByClicking:
    """The shape the first attempt could not see at all.

    That version only noticed when step 1 was a `goto` whose URL check failed. A trail that
    reaches its page by CLICKING a link never went through that branch, so it was offered
    for repair every time — and most real trails are this shape.
    """

    def clicking_trail(self) -> Playbook:
        return Playbook(
            domain=SITE,
            task=TASK,
            steps=[
                Step(
                    index=1,
                    intent="open the account menu",
                    action="click",
                    postcondition=Postcondition("element_present", "#account-menu"),
                    locators=[Locator("css", "#account-menu")],
                    page="/settings",
                )
            ],
        )

    def test_it_is_still_caught(
        self, store: CairnStore, browser: Browser, demo_server: str
    ) -> None:
        store.save_playbook(self.clicking_trail())

        result = Executor(store, browser).run(SITE, task=TASK, start_url=f"{demo_server}/invoices")

        assert result.wrong_place is True
        assert result.needs_repair is False
        assert result.repair is None
