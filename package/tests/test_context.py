"""The browser context: permissions, position, tabs, and one place for patience.

Most of Playwright's `BrowserContext` is deliberately absent — cookies and storage are
already handled by keeping a whole browser profile, which is stronger than replaying a
saved blob. What is here is the short list that changes whether a real site works at all.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from cairn import actions
from cairn.browser import GEOLOCATION, Browser
from cairn.waits import DEFAULT_WAIT_MS

# Asks for a permission the moment it loads, then reports what it was told.
ASKS = """
<!doctype html>
<title>permission</title>
<p id="log">asking…</p>
<script>
  Notification.requestPermission().then(state => {
    document.getElementById('log').textContent = 'notifications:' + state;
  });
</script>
"""

WHERE = """
<!doctype html>
<title>where am I</title>
<p id="log">locating…</p>
<script>
  navigator.geolocation.getCurrentPosition(
    pos => {
      document.getElementById('log').textContent =
        pos.coords.latitude.toFixed(2) + ',' + pos.coords.longitude.toFixed(2);
    },
    err => { document.getElementById('log').textContent = 'denied'; }
  );
</script>
"""


@pytest.fixture
def located(tmp_path) -> Iterator[Browser]:
    """A browser that has been told where it is. Kolkata."""
    with Browser(
        headless=True,
        downloads=tmp_path / "downloads",
        geolocation=(22.57, 88.36),
    ) as running:
        yield running


# ------------------------------------------------------------- permissions


def test_nothing_is_granted_by_default(browser: Browser) -> None:
    """A site asking for notifications puts a prompt over the page, and a prompt over the
    page blocks everything behind it. Denying is silent, and an unattended agent needs
    silence rather than a dialog nobody is there to answer."""
    assert browser.permissions == []


def test_a_permission_request_is_refused_without_blocking(browser: Browser) -> None:
    browser.page.set_content(ASKS)
    browser.page.wait_for_function(
        "document.getElementById('log').textContent !== 'asking…'", timeout=5000
    )
    assert browser.page.locator("#log").inner_text() == "notifications:denied"


def test_a_permission_can_be_granted_when_a_site_genuinely_needs_one(tmp_path) -> None:
    with Browser(
        headless=True, downloads=tmp_path / "downloads", permissions=["notifications"]
    ) as allowed:
        assert allowed.permissions == ["notifications"]


# ------------------------------------------------------------- geolocation


def test_geolocation_grants_its_own_permission(located: Browser) -> None:
    """Granting geolocation without also setting a position makes a site wait forever for
    a fix that never arrives, so the two always travel together."""
    assert GEOLOCATION in located.permissions


def test_a_site_is_told_where_it_is(located: Browser, demo_server: str) -> None:
    # Chrome only hands out a position on a secure origin, and `about:blank` is not one.
    # 127.0.0.1 counts as secure, so the demo server is a real origin to ask from.
    located.page.goto(f"{demo_server}/")
    located.page.set_content(WHERE)
    located.page.wait_for_function(
        "document.getElementById('log').textContent !== 'locating…'", timeout=5000
    )
    assert located.page.locator("#log").inner_text() == "22.57,88.36"


def test_location_is_refused_when_none_was_set(browser: Browser, demo_server: str) -> None:
    browser.page.goto(f"{demo_server}/")
    browser.page.set_content(WHERE)
    browser.page.wait_for_function(
        "document.getElementById('log').textContent !== 'locating…'", timeout=5000
    )
    assert browser.page.locator("#log").inner_text() == "denied"


# ----------------------------------------------------------------- patience


def test_there_is_one_timeout(browser: Browser) -> None:
    assert browser.timeout_ms == DEFAULT_WAIT_MS


def test_patience_can_be_changed_for_a_slow_site(browser: Browser) -> None:
    browser.set_timeout(2000)
    assert browser.timeout_ms == 2000


def test_the_timeout_actually_applies(browser: Browser) -> None:
    """If the default were ignored, a missing element would hang for Playwright's own 30
    seconds instead of giving up when we said to."""
    from playwright.sync_api import TimeoutError as PWTimeout

    browser.set_timeout(400)
    browser.page.set_content("<p>nothing here</p>")
    with pytest.raises(PWTimeout):
        browser.page.locator("#never").click()


def test_a_slow_timeout_can_be_set_at_launch(tmp_path) -> None:
    with Browser(headless=True, downloads=tmp_path / "downloads", timeout_ms=45000) as patient:
        assert patient.timeout_ms == 45000


# --------------------------------------------------------------------- tabs


def test_new_tab(browser: Browser, demo_server: str) -> None:
    """A tab we asked for, unlike one the site opened. Switching to it is not a guess."""
    first = browser.page
    opened = browser.new_tab(f"{demo_server}/")

    assert opened is not first
    assert browser.page is opened
    assert len(browser.tabs) == 2
    assert demo_server in browser.page.url


def test_new_tab_can_be_blank(browser: Browser) -> None:
    browser.new_tab()
    assert len(browser.tabs) == 2


def test_a_tab_we_opened_is_watched_like_any_other(browser: Browser) -> None:
    """Its dialogs and downloads have to reach the same handlers, or a flow that continues
    in a new tab quietly loses both."""
    browser.new_tab()
    browser.page.set_content("<button id='go' onclick=\"confirm('Sure?')\">Go</button>")
    browser.page.locator("#go").click()
    assert browser.last_dialog is not None
    assert browser.last_dialog["message"] == "Sure?"


def test_going_back_to_the_first_tab(browser: Browser, demo_server: str) -> None:
    first = browser.page
    browser.new_tab(f"{demo_server}/")
    browser.switch_tab("main")
    assert browser.page is first


def test_new_tab_is_session_handled() -> None:
    assert actions.ACTIONS["new_tab"].session_handled


def test_new_tab_needs_no_value() -> None:
    """A blank tab is a perfectly ordinary thing to want."""
    actions.spec_for("new_tab")
    assert "new_tab" in actions._VALUE_OPTIONAL


# ------------------------------------------------ signing in, for real (P0)


class TestTheBrowserDoesNotAnnounceItself:
    """Google refused a sign-in with "This browser or app may not be secure".

    Playwright's bundled Chromium sets `navigator.webdriver = true` and launches with
    `--enable-automation`, and Google blocks OAuth in anything that says so. The person
    signs in themselves, with their own hands, in a window they can see, to their own
    account — so what those flags claimed was simply not true, and it cost the user the one
    thing Cairn cannot do for them.
    """

    def test_it_is_not_flagged_as_driven_by_a_program(self, browser: Browser) -> None:
        assert browser.page.evaluate("() => navigator.webdriver") is False

    def test_the_login_window_is_not_flagged_either(self, tmp_path) -> None:
        """The headed window is the one that matters — it is where a person signs in."""
        with Browser(headless=False, downloads=tmp_path / "d") as visible:
            assert visible.page.evaluate("() => navigator.webdriver") is False

    def test_it_does_not_say_it_is_headless(self, browser: Browser) -> None:
        """Some sites refuse "HeadlessChrome" on sight. Whether a screen is being watched
        is a fact about the screen, not about who is typing."""
        assert "Headless" not in browser.page.evaluate("() => navigator.userAgent")

    def test_it_prefers_the_real_chrome_on_this_machine(self, browser: Browser) -> None:
        """Sites that gate sign-in treat Chromium as suspicious however it behaves."""
        from cairn.browser import REAL_CHROME

        assert browser._channel in (REAL_CHROME, None)

    def test_a_missing_chrome_is_a_downgrade_not_a_failure(self, tmp_path, monkeypatch) -> None:
        """A browser that starts is worth more than one that is perfectly disguised."""
        from playwright.sync_api import Error as PlaywrightError

        running = Browser(headless=True, downloads=tmp_path / "d")
        real_launch = None

        def only_bundled_works(**options):
            if options.get("channel"):
                raise PlaywrightError("Chromium distribution 'chrome' is not found")
            return real_launch(**options)

        with running:
            real_launch = running._playwright.chromium.launch
            monkeypatch.setattr(running._playwright.chromium, "launch", only_bundled_works)
            running._channel = "chrome"
            fallback = running._launch()

            assert running._channel is None
            fallback.close()


class TestAProfileBelongsToOneBrowser:
    """A silent fallback threw away a sign-in that had been done by hand an hour earlier.

    Measured on the real profile:

        channel='chrome'  FAILED: Target page, context or browser has been closed
        channel=None      opened OK -> us.posthog.com/login?next=...

    The fallback was written for "Chrome is not installed" but caught every failure,
    including "another window has this profile". Chromium cannot read a session Chrome
    wrote, so it produced a browser that looked fine and was signed out — after the one
    thing Cairn asks a person to do themselves.
    """

    def test_the_owner_is_written_into_the_profile(self, tmp_path) -> None:
        from cairn.browser import PROFILE_OWNER

        profile = tmp_path / "profile"
        with Browser(headless=True, profile=profile, downloads=tmp_path / "d"):
            pass

        marker = profile / PROFILE_OWNER
        assert marker.is_file()
        assert marker.read_text(encoding="utf-8").strip() in ("chrome", "chromium")

    def test_a_chromium_profile_is_never_opened_with_chrome(self, tmp_path) -> None:
        """The direction that loses a login."""
        from cairn.browser import BUNDLED, PROFILE_OWNER

        profile = tmp_path / "profile"
        profile.mkdir()
        (profile / PROFILE_OWNER).write_text(BUNDLED, encoding="utf-8")

        with Browser(headless=True, profile=profile, downloads=tmp_path / "d") as running:
            assert running._channel is None

    def test_a_chrome_profile_stays_on_chrome(self, tmp_path) -> None:
        from cairn.browser import PROFILE_OWNER, REAL_CHROME

        profile = tmp_path / "profile"
        profile.mkdir()
        (profile / PROFILE_OWNER).write_text(REAL_CHROME, encoding="utf-8")

        with Browser(headless=True, profile=profile, downloads=tmp_path / "d") as running:
            assert running._channel == REAL_CHROME

    def test_only_a_missing_browser_counts_as_missing(self) -> None:
        """The failure that started this said "Target page, context or browser has been
        closed". Reading that as "Chrome is not installed" is what did the damage."""
        from playwright.sync_api import Error as PlaywrightError

        from cairn.browser import _is_missing_browser

        missing = PlaywrightError("Chromium distribution 'chrome' is not found")
        busy = PlaywrightError("Target page, context or browser has been closed")

        assert _is_missing_browser(missing)
        assert not _is_missing_browser(busy)

    def test_a_busy_profile_says_so_instead_of_downgrading(self, tmp_path) -> None:
        """Refusing clearly beats opening a browser that is quietly signed out."""
        from playwright.sync_api import Error as PlaywrightError

        from cairn.browser import ProfileInUse

        profile = tmp_path / "profile"
        running = Browser(headless=True, profile=profile, downloads=tmp_path / "d")
        running._playwright = None

        class Busy:
            def launch_persistent_context(self, *args, **kwargs):
                raise PlaywrightError("Target page, context or browser has been closed")

        running._playwright = type("PW", (), {"chromium": Busy()})()
        running._profile = profile
        running._headless = True
        running._touch = False
        running._timeout_ms = 1000
        running._geolocation = None
        running._permissions = []

        with pytest.raises(ProfileInUse) as raised:
            running._open_profile()
        assert "already open" in str(raised.value)
