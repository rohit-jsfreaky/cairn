"""The demo site is a test fixture, so it needs testing too.

These tests pin down the contract the repair tests will rely on later: variant B must
break exactly one locator and leave everything else alone. If someone edits the demo site
and accidentally changes two things, the repair demo stops being a repair demo, and these
tests are what catches that.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.demo_site.app import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.mark.parametrize("variant", ["a", "b"])
class TestTheFlowWorksInBothVariants:
    def test_login_leads_to_the_invoice_list(self, client: TestClient, variant: str):
        response = client.post(
            "/login",
            data={"email": "finance@acme.com", "password": "hunter2"},
            params={"variant": variant},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert "September 2026" in response.text

    def test_an_invoice_can_be_opened(self, client: TestClient, variant: str):
        response = client.get("/invoices/2026-09", params={"variant": variant})

        assert response.status_code == 200
        assert "September 2026" in response.text

    def test_the_file_downloads(self, client: TestClient, variant: str):
        response = client.get("/invoices/2026-09/file", params={"variant": variant})

        assert response.status_code == 200
        assert "attachment" in response.headers["content-disposition"]
        assert b"Invoice 2026-09" in response.content


class TestVariantBIsARedesign:
    """Exactly one control moves. That is what makes the repair beat honest."""

    def test_variant_a_has_the_original_button(self, client: TestClient):
        html = client.get("/invoices/2026-09").text

        assert 'id="download-btn"' in html
        assert ">Download<" in html
        assert "get-pdf" not in html

    def test_variant_b_renames_and_moves_it(self, client: TestClient):
        html = client.get("/invoices/2026-09", params={"variant": "b"}).text

        assert 'id="get-pdf"' in html
        assert ">Get PDF<" in html
        assert "download-btn" not in html, "the old css locator must genuinely miss"
        assert 'class="toolbar right"' in html, "and it should move, not just get renamed"

    def test_the_href_survives_the_redesign(self, client: TestClient):
        """A locator that used the link target keeps working. A css locator does not.

        This is the whole argument for ranking several locators per step instead of
        recording one selector.
        """
        target = "/invoices/2026-09/file"

        assert target in client.get("/invoices/2026-09").text
        assert target in client.get("/invoices/2026-09", params={"variant": "b"}).text

    def test_the_url_structure_never_changes(self, client: TestClient):
        for variant in ("a", "b"):
            assert client.get("/invoices", params={"variant": variant}).status_code == 200
            assert (
                client.get("/invoices/2026-08", params={"variant": variant}).status_code == 200
            )

    def test_variant_sticks_across_links(self, client: TestClient):
        """Otherwise a run would drift back to variant A halfway through."""
        html = client.get("/invoices", params={"variant": "b"}).text

        assert "?variant=b" in html
