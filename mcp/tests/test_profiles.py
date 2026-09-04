"""More than one signed-in identity at a time.

Cairn used to keep a single browser profile. A suite testing a marketplace with a customer,
a vendor and an admin therefore had to sign out and back in between roles — slow, and worse,
it made the ORDER of the tests matter: anything that forgot to sign out broke whatever ran
next.

A profile is a whole browser: its own cookies, its own session, its own process. Cairn keeps
them side by side now, so all three stay signed in and switching between them is free.

Memory is deliberately NOT split by profile. The site is one site however many logins reach
it, which is the same reason the map is one merged map per site.
"""

from __future__ import annotations

import pytest
from cairn.browser import DEFAULT_PROFILE_NAME

from cairn_mcp.server import build_server
from helpers import call


@pytest.fixture
def server(tmp_path):
    """A server whose profiles live under the test's own folder, never the real one."""
    built = build_server(
        db_path=str(tmp_path / "memory.db"),
        headless=True,
        downloads=str(tmp_path / "downloads"),
        profile=str(tmp_path / "default-profile"),
        profiles_dir=str(tmp_path / "profiles"),
    )
    yield built
    built.cairn_tools.close()


class TestNamingProfiles:
    def test_it_starts_on_the_default_one(self, server):
        answer = call(server, "cairn_profile")

        assert answer["active"] == DEFAULT_PROFILE_NAME

    def test_a_new_name_is_made_on_the_spot(self, server):
        answer = call(server, "cairn_profile", name="vendor")

        assert answer["active"] == "vendor"
        assert answer["was"] == DEFAULT_PROFILE_NAME

    def test_the_default_keeps_the_folder_it_always_had(self, server, tmp_path):
        """Naming profiles must not quietly move somebody's sign-ins somewhere new."""
        tools = server.cairn_tools

        assert tools.path_for(DEFAULT_PROFILE_NAME) == str(tmp_path / "default-profile")

    def test_every_other_profile_gets_its_own_folder(self, server, tmp_path):
        tools = server.cairn_tools

        vendor = tools.path_for("vendor")
        admin = tools.path_for("admin")

        assert vendor != admin
        assert str(tmp_path / "profiles") in vendor

    def test_a_name_with_spaces_still_makes_one_folder(self, server):
        tools = server.cairn_tools

        assert tools.path_for("Vendor A").endswith("vendor-a")

    def test_listing_says_which_one_is_in_use(self, server):
        call(server, "cairn_profile", name="admin")

        listed = call(server, "cairn_profile")["profiles"]

        assert [row["name"] for row in listed if row["active"]] == ["admin"]


class TestTheyAreReallySeparateBrowsers:
    def test_two_profiles_are_two_browsers_at_the_same_time(self, server, demo_server):
        """The claim, tested rather than asserted: both open, neither closing the other."""
        tools = server.cairn_tools

        call(server, "cairn_profile", name="vendor")
        call(server, "cairn_act", intent="open", action="goto", value=f"{demo_server}/")
        call(server, "cairn_profile", name="customer")
        call(server, "cairn_act", intent="open", action="goto", value=f"{demo_server}/invoices")

        assert tools._workers["vendor"].running
        assert tools._workers["customer"].running

    def test_each_keeps_its_own_page(self, server, demo_server):
        """Switching back must land where that profile left off, not where the other is."""
        call(server, "cairn_profile", name="vendor")
        call(server, "cairn_act", intent="open", action="goto", value=f"{demo_server}/")
        call(server, "cairn_profile", name="customer")
        call(server, "cairn_act", intent="open", action="goto", value=f"{demo_server}/settings")

        call(server, "cairn_profile", name="vendor")
        where = call(server, "cairn_read", kind="url")["value"]

        assert not where.endswith("/settings"), "it landed on the other profile's page"

    def test_each_has_its_own_trace(self, server, demo_server):
        """A trace belongs to the browser that made it. Sharing one would mix an admin's
        steps into a customer's trail."""
        tools = server.cairn_tools
        call(server, "cairn_profile", name="vendor")
        call(server, "cairn_act", intent="open", action="goto", value=f"{demo_server}/")
        call(server, "cairn_read", kind="page")

        call(server, "cairn_profile", name="customer")

        assert tools._sessions["vendor"] is not tools._sessions.get("customer")


class TestMemoryIsNotSplit:
    def test_what_one_profile_learned_the_next_one_knows(self, server, demo_server):
        """One site is one site, however many logins reach it."""
        call(server, "cairn_profile", name="vendor")
        call(server, "cairn_act", intent="open", action="goto", value=f"{demo_server}/")
        call(server, "cairn_read", kind="page")

        call(server, "cairn_profile", name="customer")
        mapped = call(server, "cairn_map", site=demo_server)

        assert mapped["ok"] is True
        assert any(row["path"] == "/" for row in mapped["pages"])
