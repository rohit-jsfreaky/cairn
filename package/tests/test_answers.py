"""A trail has to produce the answer, not just arrive at the page.

Found on GitHub, 2026-09-02, the first real site Cairn ever touched. Asked "how many open
issues does microsoft/playwright have", it explored, got 151, and saved a trail of exactly
one step: the `goto`. The number came from a read, and reads were not recorded.

So the saved trail navigated somewhere and stopped. Every later run still had to read the
page and work the number out again — which is the entire cost the project exists to remove.
"""

from __future__ import annotations

import pytest

from cairn.browser import Browser, domain_of
from cairn.executor import Executor
from cairn.operations import READ_ACTION, Session
from cairn.store import CairnStore

COUNTING = """
<!doctype html>
<title>invoices</title>
<a href="/invoices" id="open">Invoices</a>
<p id="total">1,240.00</p>
<ul>
  <li class="row">August</li>
  <li class="row">September</li>
  <li class="row">October</li>
</ul>
"""


@pytest.fixture
def counted(browser: Browser, store: CairnStore, demo_server: str) -> Session:
    session = Session(browser=browser, store=store)
    session.act("open the billing page", "goto", value=f"{demo_server}/")
    browser.page.set_content(COUNTING)
    return session


def ref_for(session: Session, name: str) -> str:
    for element in session.look()["elements"]:
        if element["name"] == name:
            return element["ref"]
    raise AssertionError(f"no control named {name!r}")


# --------------------------------------------------- what gets written down


def test_an_exploring_read_is_not_a_step(counted: Session) -> None:
    """Most reads are just looking around. Replaying those would achieve nothing."""
    before = len(counted.trace)
    counted.read("text", ref=ref_for(counted, "Invoices"))
    assert len(counted.trace) == before


def test_a_remembered_read_is_a_step(counted: Session) -> None:
    counted.read(
        "text",
        ref=ref_for(counted, "Invoices"),
        remember=True,
        intent="read the invoices link",
    )
    entry = counted.trace[-1]
    assert entry.action == READ_ACTION
    assert entry.intent == "read the invoices link"


def test_a_remembered_read_carries_durable_locators(counted: Session) -> None:
    """A read step is replayed by finding its element again, exactly like a click. Without
    locators it could never be replayed at all."""
    counted.read("text", ref=ref_for(counted, "Invoices"), remember=True)
    element = counted.trace[-1].element
    assert element is not None
    assert element.locators()


def test_a_remembered_read_gets_a_postcondition(counted: Session, demo_server: str) -> None:
    """A read changes nothing, so what must still be true is that the thing being read is
    there at all. If it vanished, the answer would be silently wrong."""
    counted.read("text", ref=ref_for(counted, "Invoices"), remember=True)
    playbook = counted.save("read the invoice total")

    read_step = next(step for step in playbook.steps if step.action == READ_ACTION)
    assert read_step.postcondition.kind == "element_present"


def test_the_read_still_answers_while_being_recorded(counted: Session) -> None:
    answer = counted.read("text", ref=ref_for(counted, "Invoices"), remember=True)
    assert answer == "Invoices"


# ------------------------------------------------- and what replay gives back


def test_a_warm_run_hands_back_the_answer(
    browser: Browser, store: CairnStore, demo_server: str
) -> None:
    """The whole point. Before this, a warm run arrived at the page and said nothing."""
    session = Session(browser=browser, store=store)
    session.act("open the billing page", "goto", value=f"{demo_server}/")
    session.read(
        "text",
        ref=ref_for(session, "Sign in"),
        remember=True,
        intent="read the sign in button",
    )
    session.save("read the sign in button")

    result = Executor(store, browser).run(domain_of(demo_server), task="read the sign in button")

    assert result.ok
    assert result.answers["read the sign in button"] == "Sign in"


def test_a_counting_read_replays_as_a_number(
    browser: Browser, store: CairnStore, demo_server: str
) -> None:
    """ "How many unpaid invoices" is the shape of the real use case."""
    session = Session(browser=browser, store=store)
    session.act("open the billing page", "goto", value=f"{demo_server}/")
    session.read(
        "count",
        ref=ref_for(session, "Sign in"),
        remember=True,
        intent="count the sign in buttons",
    )
    session.save("count the sign in buttons")

    result = Executor(store, browser).run(domain_of(demo_server), task="count the sign in buttons")
    assert result.answers["count the sign in buttons"] == 1


def test_a_run_with_no_remembered_reads_answers_nothing(
    browser: Browser, store: CairnStore, demo_server: str
) -> None:
    """Not an error — plenty of tasks are about doing, not reading."""
    session = Session(browser=browser, store=store)
    session.act("open the billing page", "goto", value=f"{demo_server}/")
    session.save("just open the page")

    result = Executor(store, browser).run(domain_of(demo_server), task="just open the page")
    assert result.ok
    assert result.answers == {}


def test_two_tasks_on_one_site_do_not_collide(
    browser: Browser, store: CairnStore, demo_server: str
) -> None:
    """The other half of what GitHub found: a second task used to overwrite the first."""
    domain = domain_of(demo_server)

    first = Session(browser=browser, store=store)
    first.act("open the billing page", "goto", value=f"{demo_server}/")
    first.read("text", ref=ref_for(first, "Sign in"), remember=True, intent="read the button")
    first.save("read the sign in button")

    second = Session(browser=browser, store=store)
    second.act("open the billing page", "goto", value=f"{demo_server}/")
    second.read("title", remember=True, intent="read the title")
    second.save("read the page title")

    assert sorted(store.trails_for(domain)) == [
        "read the page title",
        "read the sign in button",
    ]

    replay = Executor(store, browser)
    assert replay.run(domain, task="read the sign in button").answers == {
        "read the button": "Sign in"
    }
    assert "read the title" in replay.run(domain, task="read the page title").answers


# ------------------------------- health, after the second GitHub run (P0)


def test_a_step_with_no_locators_is_not_broken() -> None:
    """A `goto` carries its destination in the step, not in a locator. Scoring it zero —
    which is what "no locators" used to mean — made every trail containing one permanently
    part-broken, and dragged it towards being retired."""
    from cairn.models import Postcondition, Step

    step = Step(
        index=1,
        intent="open the page",
        action="goto",
        value="https://example.com/x",
        postcondition=Postcondition("url_contains", "/x"),
    )
    assert step.health == 0.5


def test_a_step_with_no_locators_earns_its_own_record() -> None:
    from cairn.models import Postcondition, Step

    step = Step(
        index=1,
        intent="open the page",
        action="goto",
        postcondition=Postcondition("url_contains", "/x"),
    )
    step.record_hit()
    step.record_hit()
    assert step.health == 1.0

    step.record_miss()
    assert step.health < 1.0


def test_a_fresh_trail_is_not_reported_half_broken(
    browser: Browser, store: CairnStore, demo_server: str
) -> None:
    """The symptom: a brand new working trail reported health 0.25, because its `goto`
    scored zero."""
    session = Session(browser=browser, store=store)
    session.act("open the billing page", "goto", value=f"{demo_server}/")
    session.read("text", ref=ref_for(session, "Sign in"), remember=True, intent="read it")
    playbook = session.save("read the sign in button")

    assert playbook.health >= 0.5


def test_a_healthy_trail_gets_healthier_as_it_runs(
    browser: Browser, store: CairnStore, demo_server: str
) -> None:
    session = Session(browser=browser, store=store)
    session.act("open the billing page", "goto", value=f"{demo_server}/")
    session.read("text", ref=ref_for(session, "Sign in"), remember=True, intent="read it")
    session.save("read the sign in button")

    domain = domain_of(demo_server)
    before = store.load_playbook(domain, "read the sign in button").health
    Executor(store, browser).run(domain, task="read the sign in button")
    after = store.load_playbook(domain, "read the sign in button").health

    assert after > before


def test_starting_somewhere_else_checks_where_it_actually_went(
    browser: Browser, store: CairnStore, demo_server: str
) -> None:
    """`url` used to change where the first step went but not what it checked, so a page
    that loaded perfectly was reported as a broken step — and the step it named could not
    be repaired, because a `goto` has no control to point at."""
    session = Session(browser=browser, store=store)
    session.act("open the billing page", "goto", value=f"{demo_server}/")
    session.read("title", remember=True, intent="read the title")
    session.save("read the title")

    result = Executor(store, browser).run(
        domain_of(demo_server),
        task="read the title",
        start_url=f"{demo_server}/?variant=b",
    )
    assert result.ok, result.reason


# ----------------- finding the right trail, after the third GitHub run (P1)


def test_a_task_worded_differently_still_finds_its_trail(store: CairnStore) -> None:
    """Seen live: the trail was saved as "count open issues on microsoft/playwright" and a
    user asking "how many open issues does microsoft/playwright have" found nothing, so the
    host AI explored the site again and saved over what was there.

    Nobody words a request the same way twice."""
    from cairn.models import Playbook

    for task in (
        "count open issues on microsoft/playwright",
        "count open issues on elysiajs/elysia-openapi",
    ):
        store.save_playbook(Playbook(domain="github.com", task=task))

    found = store.load_playbook("github.com", "how many open issues does microsoft/playwright have")
    assert found is not None
    assert found.task == "count open issues on microsoft/playwright"


def test_the_right_one_of_two_similar_trails(store: CairnStore) -> None:
    from cairn.models import Playbook

    for task in (
        "count open issues on microsoft/playwright",
        "count open issues on elysiajs/elysia-openapi",
    ):
        store.save_playbook(Playbook(domain="github.com", task=task))

    found = store.load_playbook("github.com", "open issues for elysia-openapi")
    assert found.task == "count open issues on elysiajs/elysia-openapi"


def test_an_unrelated_task_matches_nothing(store: CairnStore) -> None:
    """Running the wrong trail is worse than admitting there is none."""
    from cairn.models import Playbook

    store.save_playbook(Playbook(domain="github.com", task="count open issues on playwright"))
    assert store.load_playbook("github.com", "cancel my subscription") is None


def test_matching_ignores_words_that_carry_no_meaning() -> None:
    from cairn.store import best_match

    known = ["download the invoice", "cancel the subscription"]
    assert best_match("please can you download my invoice", known) == "download the invoice"


def test_two_equally_good_matches_pick_neither() -> None:
    """Guessing between them would run the wrong task."""
    from cairn.store import best_match

    assert best_match("open issues", ["open issues here", "open issues there"]) is None


def test_a_site_with_trails_never_reports_itself_unknown(
    browser: Browser, store: CairnStore, demo_server: str
) -> None:
    """ "Which task?" and "never been here" demand opposite responses. Reporting the second
    when the first was true is what caused the re-exploration."""
    from cairn.executor import NeedsTask

    domain = domain_of(demo_server)
    for task in ("first task", "second task"):
        session = Session(browser=browser, store=store)
        session.act("open the billing page", "goto", value=f"{demo_server}/")
        session.save(task)

    with pytest.raises(NeedsTask) as raised:
        Executor(store, browser).run(domain)

    assert sorted(raised.value.tasks) == ["first task", "second task"]
    assert "remembered" in str(raised.value)


# ------------------------------ reaching a dashboard number, from PostHog (P0)

DASHBOARD = """
<!doctype html>
<title>web analytics</title>
<nav><a href="/home">Home</a><a href="/web">Web analytics</a></nav>
<div class="tile" data-attr="visitors-tile">
  <div class="label">Visitors</div>
  <div class="big">22</div>
  <div class="change">-37.0%</div>
</div>
<div class="tile" data-attr="views-tile">
  <div class="label">Page views</div>
  <div class="big">28</div>
</div>
<p>lots and lots of other page text nobody wants in an answer</p>
"""


@pytest.fixture
def dashboard(browser: Browser, store: CairnStore, demo_server: str) -> Session:
    session = Session(browser=browser, store=store)
    session.act("open the dashboard", "goto", value=f"{demo_server}/")
    browser.page.set_content(DASHBOARD)
    return session


def test_a_number_with_no_role_has_no_ref(dashboard: Session) -> None:
    """Not a bug — a plain div is not a control and should not be offered as one. But it
    means a selector is the only handle those numbers have."""
    names = [element["name"] for element in dashboard.look()["elements"]]
    assert "22" not in names


def test_a_css_selector_works_wherever_a_ref_does(dashboard: Session) -> None:
    """What the host AI reached for unprompted on PostHog, and did not get."""
    assert dashboard.read("text", ref='[data-attr="visitors-tile"] .big') == "22"


def test_a_selector_read_can_be_remembered(dashboard: Session) -> None:
    dashboard.read(
        "text",
        ref='[data-attr="visitors-tile"] .big',
        remember=True,
        intent="unique visitors, last 7 days",
    )
    element = dashboard.trace[-1].element
    assert element is not None
    assert element.locators()


def test_the_answer_is_the_number_not_the_whole_page(
    browser: Browser, store: CairnStore, demo_server: str
) -> None:
    """The PostHog symptom. With no way to name the tile, the saved answer was the entire
    page — five thousand characters with the number somewhere inside — handed back on every
    single run for the model to search."""
    session = Session(browser=browser, store=store)
    session.act("open the dashboard", "goto", value=f"{demo_server}/")
    browser.page.set_content(DASHBOARD)
    session.read(
        "text",
        ref='[data-attr="visitors-tile"] .big',
        remember=True,
        intent="unique visitors, last 7 days",
    )
    playbook = session.save("get unique visitors from the last 7 days")

    # The trail names the tile, not the page.
    read_step = next(step for step in playbook.steps if step.action == READ_ACTION)
    assert read_step.locators
    assert "nobody wants" not in str(read_step.to_dict())


def test_a_selector_can_be_acted_on_too(dashboard: Session) -> None:
    dashboard.browser.page.set_content(
        '<div class="tile" onclick="document.title=\'tile clicked\'">Visitors</div>'
    )
    dashboard.act("press the tile", "click", ref=".tile")
    assert dashboard.browser.page.title() == "tile clicked"


def test_a_selector_that_matches_nothing_says_so(dashboard: Session) -> None:
    from cairn.operations import ActionFailed

    with pytest.raises(ActionFailed) as raised:
        dashboard.read("text", ref=".no-such-tile")
    assert "no-such-tile" in str(raised.value)


def test_nonsense_is_not_mistaken_for_a_selector(dashboard: Session) -> None:
    from cairn.operations import ActionFailed

    with pytest.raises(ActionFailed):
        dashboard.read("text", ref="((((")


def test_refs_and_selectors_are_told_apart() -> None:
    from cairn import snapshot as aria

    assert aria.is_ref("e4")
    assert aria.is_ref("f1e2")
    assert not aria.is_ref(".tile")
    assert not aria.is_ref('[data-attr="visitors-tile"] .big')
    assert not aria.is_ref("div.big")


def test_a_hand_written_selector_survives_being_described(dashboard: Session) -> None:
    """Seen on PostHog. The AI dug through the DOM with `evaluate`, built
    `...:has-text("Visitors") div.text-4xl`, and checked it matched exactly one element.

    Describing it then overwrote that with a positional path worked out from the page —
    `div > div > div:nth-of-type(2)` — which breaks the moment a tile is added above it.
    The careful selector was thrown away, silently, for a worse one.
    """
    picked = '.tile:has-text("Visitors") .big'
    dashboard.read("text", ref=picked, remember=True, intent="unique visitors")

    element = dashboard.trace[-1].element
    assert element is not None
    assert element.locators()[0].value == picked


def test_the_worked_out_path_is_kept_as_a_spare(dashboard: Session) -> None:
    """Two ways to find the same thing beats one. Theirs is anchored to meaning; ours
    still works the day the class names change."""
    dashboard.read("text", ref='.tile:has-text("Visitors") .big', remember=True, intent="v")

    element = dashboard.trace[-1].element
    css = [locator.value for locator in element.locators() if locator.kind == "css"]
    assert len(css) == 2
    assert css[0] != css[1]


def test_a_ref_element_is_unaffected(dashboard: Session) -> None:
    """Nothing changes for elements that came from a snapshot — they never had a selector
    of their own to protect."""
    ref = ref_for(dashboard, "Web analytics")
    dashboard.read("text", ref=ref, remember=True, intent="the link")

    element = dashboard.trace[-1].element
    assert element.fallback_css == ""


# ------------------- repair, after the third PostHog run (P0 and P1)

AMBIGUOUS = """
<!doctype html>
<title>two of the same</title>
<main><div><div><div><div><button id="real" onclick="document.title='right one'">Analytics</button></div></div></div></div></main>
<aside><section><nav><div><div><div><div><div>
  <button id="decoy" onclick="document.title='WRONG ONE'">Analytics</button>
</div></div></div></div></div></nav></section></aside>
"""


def test_a_stored_css_path_matches_exactly_one_element(browser: Browser) -> None:
    """Seen live on PostHog. `cssOf` walked five levels and stopped whether or not the
    result was unique — and five levels is nothing in a React app, where the real path was
    fifteen. The suffix matched two places, `locate` takes `.first`, and replay clicked the
    wrong control: a repaired step kept opening a "Remove from sidebar panel" menu that
    then blocked every read after it."""
    browser.page.set_content(AMBIGUOUS)

    for element in browser.snapshot().elements:
        described = browser.describe(element)
        if described.css:
            assert browser.page.locator(described.css).count() == 1, (
                f"{described.css} matches more than one element"
            )


def test_no_css_is_stored_rather_than_an_ambiguous_one(browser: Browser) -> None:
    """A selector that reliably finds the wrong thing is worse than having none."""
    browser.page.set_content("<div><span>a</span></div><div><span>a</span></div>")
    for element in browser.snapshot().elements:
        described = browser.describe(element)
        assert not described.css or browser.page.locator(described.css).count() == 1


def test_a_repair_stores_every_way_of_finding_the_control(
    browser: Browser, store: CairnStore, demo_server: str
) -> None:
    """The host AI's own words, mid-run: "Cairn only takes plain CSS." It had a better
    locator in mind, could not express it, and fell back to a positional path that then
    matched the wrong element. A repair used to leave a step MORE fragile than when it was
    first learned."""
    from cairn.executor import Executor
    from cairn.models import Locator

    domain = domain_of(demo_server)
    session = Session(browser=browser, store=store)
    session.act("open the billing page", "goto", value=f"{demo_server}/")
    session.act("sign in", "click", ref=ref_for(session, "Sign in"))
    session.save("sign in")

    playbook = store.load_playbook(domain, "sign in")
    playbook.steps[1].locators = [Locator("css", "#long-gone", misses=9)]
    store.save_playbook(playbook)

    replay = Executor(store, browser)
    replay.browser.goto(f"{demo_server}/")
    ref = next(
        element["ref"]
        for element in Session(browser, store).look()["elements"]
        if element["name"] == "Sign in"
    )
    fixed = replay.repair_from_ref(domain, 2, ref, task="sign in")

    kinds = {locator.kind for locator in fixed.steps[1].locators}
    assert len(kinds) > 1, f"a repair stored only {kinds}"


def test_a_fumbled_step_can_be_dropped_before_saving(
    browser: Browser, store: CairnStore, demo_server: str
) -> None:
    """Found by replaying Rohit's real PostHog trail. It began:

        1. press  close the stuck context menu
        2. click  open the Analytics section...

    Both were the AI getting out of a mess it had made. Step 1 failed on the first replay
    and took the whole run with it — six steps saved, zero replayed, no answer.
    """
    session = Session(browser=browser, store=store)
    session.act("open the billing page", "goto", value=f"{demo_server}/")
    session.act("get out of a stuck menu", "press", value="Escape")
    assert len(session.trace) == 2

    session.act("start the trail here", "restart_trail")
    assert session.trace == []

    session.act("open the billing page", "goto", value=f"{demo_server}/")
    session.read("title", remember=True, intent="read the title")
    playbook = session.save("read the title")

    assert [step.action for step in playbook.steps] == ["goto", "read"]
    assert all("stuck menu" not in step.intent for step in playbook.steps)


def test_restarting_leaves_the_browser_where_it_is(
    browser: Browser, store: CairnStore, demo_server: str
) -> None:
    """Explore however you like, then walk the task cleanly from wherever you ended up."""
    session = Session(browser=browser, store=store)
    session.act("open the billing page", "goto", value=f"{demo_server}/")
    where = browser.page.url

    session.act("start the trail here", "restart_trail")
    assert browser.page.url == where


def test_restarting_is_never_a_step_itself(
    browser: Browser, store: CairnStore, demo_server: str
) -> None:
    session = Session(browser=browser, store=store)
    session.act("open the billing page", "goto", value=f"{demo_server}/")
    session.act("start the trail here", "restart_trail")
    session.act("open it again", "goto", value=f"{demo_server}/")

    assert [entry.action for entry in session.trace] == ["goto"]
