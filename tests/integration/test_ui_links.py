"""
Integration tests for UI links feature: footer and Help navbar link.

Tests verify:
- Footer visible on admin dashboard with correct text and links
- Footer visible on login page
- Help link visible in navbar
- Footer NOT visible on display slideshow view

Run with: nox -s test-integration
"""

import os

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("SKIP_BROWSER_TESTS", "false").lower() == "true",
    reason="Browser tests skipped",
)
class TestUILinks:
    """Test footer and Help link across UI pages."""

    def _login(self, page: Page, vite_url: str, test_database: dict):
        """Helper method to log in to the admin interface."""
        page.goto(f"{vite_url}/admin/login")
        page.wait_for_selector("input[name='username']", timeout=10000)

        user = test_database["users"][0]
        page.locator("input[name='username']").fill(user["username"])
        page.locator("input[name='password']").fill(user["password"])
        page.locator("button[type='submit']").click()

        page.wait_for_selector("h1:has-text('Dashboard')", timeout=10000)

    def test_footer_visible_on_dashboard(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
    ):
        """Test that footer is visible on admin dashboard with correct content."""
        page = enhanced_page
        vite_url = servers["vite_url"]

        self._login(page, vite_url, test_database)

        # Wait for footer to appear
        footer = page.locator("footer")
        expect(footer).to_be_visible(timeout=10000)

        # Check footer text content
        footer_text = footer.inner_text()
        assert "kiosk-show-replacement" in footer_text
        assert "Free and Open Source Software" in footer_text
        assert "Copyright 2026 Jason Antman / Decatur Makers" in footer_text

        # Check GitHub link
        github_link = footer.locator(
            "a[href='https://github.com/Decaturmakers/kiosk-show-replacement']"
        )
        expect(github_link).to_be_visible()

        # Check MIT license link
        mit_link = footer.locator("a[href='https://opensource.org/license/mit']")
        expect(mit_link).to_be_visible()

    def test_footer_visible_on_login_page(
        self,
        enhanced_page: Page,
        servers: dict,
    ):
        """Test that footer is visible on the login page."""
        page = enhanced_page
        vite_url = servers["vite_url"]

        page.goto(f"{vite_url}/admin/login")
        page.wait_for_selector("input[name='username']", timeout=10000)

        # Wait for footer to appear
        footer = page.locator("footer")
        expect(footer).to_be_visible(timeout=10000)

        # Check footer text content
        footer_text = footer.inner_text()
        assert "kiosk-show-replacement" in footer_text
        assert "Free and Open Source Software" in footer_text
        assert "Copyright 2026 Jason Antman / Decatur Makers" in footer_text

    def test_help_link_visible_in_navbar(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
    ):
        """Test that Help link is visible in the admin navbar."""
        page = enhanced_page
        vite_url = servers["vite_url"]

        self._login(page, vite_url, test_database)

        # Check for Help link in navbar
        help_link = page.locator(
            "a[href='https://decaturmakers.github.io/kiosk-show-replacement/usage.html']"
        )
        expect(help_link).to_be_visible(timeout=10000)
        expect(help_link).to_have_text("Help")

    def test_footer_not_visible_on_slideshow_display(
        self,
        enhanced_page: Page,
        servers: dict,
        http_client,
        auth_headers,
    ):
        """Test that footer is NOT visible on the display slideshow view."""
        page = enhanced_page
        flask_url = servers["flask_url"]

        # Create a slideshow and display via API
        slideshow_response = http_client.post(
            "/api/v1/slideshows",
            json={
                "name": "Footer Test Slideshow",
                "description": "Slideshow for footer absence test",
                "default_item_duration": 10,
                "is_active": True,
            },
            headers=auth_headers,
        )
        assert slideshow_response.status_code in [200, 201]
        slideshow_data = slideshow_response.json().get(
            "data", slideshow_response.json()
        )
        slideshow_id = slideshow_data["id"]

        # Add a text item
        item_response = http_client.post(
            f"/api/v1/slideshows/{slideshow_id}/items",
            json={
                "title": "Test Slide",
                "content_type": "text",
                "content_text": "Test content",
                "display_duration": 30,
                "order_index": 0,
            },
            headers=auth_headers,
        )
        assert item_response.status_code in [200, 201]

        # Create a display
        display_response = http_client.post(
            "/api/v1/displays",
            json={
                "name": "footer-test-display",
                "description": "Display for footer test",
            },
            headers=auth_headers,
        )
        assert display_response.status_code in [200, 201]
        display_data = display_response.json().get("data", display_response.json())

        # Assign slideshow to display
        assign_response = http_client.put(
            f"/api/v1/displays/{display_data['id']}",
            json={"current_slideshow_id": slideshow_id},
            headers=auth_headers,
        )
        assert assign_response.status_code == 200

        # Navigate to the display slideshow view
        page.goto(f"{flask_url}/display/footer-test-display")

        # Wait for slideshow content to load
        page.wait_for_selector(".slideshow-container", timeout=10000)

        # Verify footer is NOT present
        footer_count = page.locator("footer").count()
        assert footer_count == 0, "Footer should not be visible on slideshow display"
