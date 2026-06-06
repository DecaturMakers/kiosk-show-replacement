"""
Integration tests for slideshow management in the admin interface.

Tests the slideshow CRUD operations through a real browser:
- Viewing slideshow list (empty and with data)
- Creating new slideshows
- Editing existing slideshows
- Deleting slideshows
- Setting default slideshow
- Action link titles and destinations

Run with: nox -s test-integration
"""

import os
import re
import time

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("SKIP_BROWSER_TESTS", "false").lower() == "true",
    reason="Browser tests skipped",
)
class TestSlideshowManagement:
    """Test slideshow CRUD operations through the admin interface."""

    def test_view_slideshow_list_empty(
        self, enhanced_page: Page, servers: dict, test_database: dict
    ):
        """Test viewing the slideshow list when no slideshows exist."""
        page = enhanced_page
        vite_url = servers["vite_url"]

        # Login first
        self._login(page, vite_url, test_database)

        # Navigate to slideshows page
        page.goto(f"{vite_url}/admin/slideshows")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Verify page header
        expect(page.locator("h1")).to_contain_text("Slideshows")

        # Verify "Create New Slideshow" button exists
        create_button = page.locator("a:has-text('Create New Slideshow')")
        expect(create_button).to_be_visible()

        # Check for empty state OR slideshow table
        # (depends on whether sample data was loaded)
        empty_state = page.locator("text=No Slideshows Found")
        table = page.locator("table")

        # Either empty state or table should be visible
        assert (
            empty_state.is_visible() or table.is_visible()
        ), "Should show either empty state or slideshow table"

    def test_view_slideshow_list_with_data(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        test_slideshow: dict,
    ):
        """Test viewing the slideshow list when slideshows exist."""
        page = enhanced_page
        vite_url = servers["vite_url"]

        # Login first
        self._login(page, vite_url, test_database)

        # Navigate to slideshows page
        page.goto(f"{vite_url}/admin/slideshows")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Verify page header
        expect(page.locator("h1")).to_contain_text("Slideshows")

        # Should show the table with our test slideshow
        table = page.locator("table")
        expect(table).to_be_visible(timeout=10000)

        # Verify our test slideshow appears in the table
        slideshow_name = test_slideshow["name"]
        expect(page.locator(f"text={slideshow_name}")).to_be_visible()

        # Verify table has expected columns
        headers = page.locator("th")
        header_texts = [headers.nth(i).inner_text() for i in range(headers.count())]
        assert "Name" in header_texts
        assert "Status" in header_texts
        assert "Actions" in header_texts

    def test_create_slideshow_success(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        http_client,
        auth_headers,
    ):
        """Test creating a new slideshow with all form fields."""
        page = enhanced_page
        vite_url = servers["vite_url"]

        # Login first
        self._login(page, vite_url, test_database)

        # Navigate to create slideshow page
        page.goto(f"{vite_url}/admin/slideshows/new")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Verify form page loaded
        expect(page.locator("h1")).to_contain_text("Create New Slideshow")

        # Generate unique name
        slideshow_name = f"Test Slideshow {int(time.time() * 1000)}"

        # Fill in the form
        page.locator("#slideshow-name").fill(slideshow_name)
        page.locator("#description").fill("Test description for integration test")
        page.locator("#default-item-duration").fill("15")
        page.locator("#transition-type").select_option("slide")

        # Check the "Active" checkbox (should be checked by default, but ensure it)
        active_checkbox = page.locator("#is_active")
        if not active_checkbox.is_checked():
            active_checkbox.check()

        # Submit the form
        page.locator("button[type='submit']").click()

        # Wait for navigation to slideshow detail page (not /new or /edit)
        # The detail page URL is /admin/slideshows/{id} where id is a number
        # Use expect().to_have_url() with regex for more reliable matching
        expect(page).to_have_url(re.compile(r".*/admin/slideshows/\d+$"), timeout=10000)
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Wait for the page to load and verify we're on the detail page
        # The detail page shows the slideshow name in an h1
        expect(page.locator("h1").first).to_contain_text(slideshow_name, timeout=10000)

        # Cleanup: delete the created slideshow via API
        # Extract slideshow ID from URL
        url = page.url
        slideshow_id = url.split("/")[-1]
        if slideshow_id.isdigit():
            http_client.delete(
                f"/api/v1/slideshows/{slideshow_id}",
                headers=auth_headers,
            )

    def test_create_slideshow_validation_errors(
        self, enhanced_page: Page, servers: dict, test_database: dict
    ):
        """Test that validation errors are shown for invalid input."""
        page = enhanced_page
        vite_url = servers["vite_url"]

        # Login first
        self._login(page, vite_url, test_database)

        # Navigate to create slideshow page
        page.goto(f"{vite_url}/admin/slideshows/new")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Try to submit with empty name
        page.locator("#slideshow-name").fill("")
        page.locator("button[type='submit']").click()

        # Should show validation error
        expect(page.locator("text=Slideshow name is required")).to_be_visible(
            timeout=5000
        )

        # URL should not have changed (still on /new page)
        assert "/new" in page.url, "Should stay on form page when validation fails"

    def test_edit_slideshow(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        test_slideshow: dict,
    ):
        """Test editing an existing slideshow."""
        page = enhanced_page
        vite_url = servers["vite_url"]
        slideshow_id = test_slideshow["id"]

        # Login first
        self._login(page, vite_url, test_database)

        # Navigate to edit page
        page.goto(f"{vite_url}/admin/slideshows/{slideshow_id}/edit")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Verify form loaded with existing data
        expect(page.locator("h1")).to_contain_text("Edit Slideshow")

        # Verify name field has the slideshow name
        name_field = page.locator("#slideshow-name")
        expect(name_field).to_have_value(test_slideshow["name"])

        # Update the description
        new_description = f"Updated description {int(time.time())}"
        page.locator("#description").fill(new_description)

        # Submit the form
        page.locator("button[type='submit']").click()

        # Wait for navigation to detail page
        page.wait_for_url(f"**/admin/slideshows/{slideshow_id}", timeout=10000)

        # Navigate back to edit page to verify change persisted
        page.goto(f"{vite_url}/admin/slideshows/{slideshow_id}/edit")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Verify the description was updated
        expect(page.locator("#description")).to_have_value(new_description)

    def test_delete_slideshow_with_confirmation(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        http_client,
        auth_headers,
    ):
        """Test deleting a slideshow with confirmation dialog."""
        page = enhanced_page
        vite_url = servers["vite_url"]

        # Create a slideshow specifically for this test
        slideshow_name = f"Delete Test {int(time.time() * 1000)}"
        response = http_client.post(
            "/api/v1/slideshows",
            json={
                "name": slideshow_name,
                "description": "Slideshow to be deleted",
                "is_active": True,
            },
            headers=auth_headers,
        )
        assert response.status_code in [200, 201]
        response_data = response.json().get("data", response.json())
        slideshow_id = response_data["id"]

        # Login first
        self._login(page, vite_url, test_database)

        # Navigate to slideshows page
        page.goto(f"{vite_url}/admin/slideshows")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Find the delete button for our slideshow
        # The row contains the slideshow name and has a delete button
        row = page.locator(f"tr:has-text('{slideshow_name}')")
        expect(row).to_be_visible(timeout=10000)

        delete_button = row.locator("button[title='Delete']")

        # Set up dialog handler to accept the confirmation
        page.on("dialog", lambda dialog: dialog.accept())

        # Click delete
        delete_button.click()

        # Wait for the slideshow to be removed from the list
        expect(page.locator(f"text={slideshow_name}")).to_be_hidden(timeout=10000)

        # Verify via API that it's actually deleted
        check_response = http_client.get(
            f"/api/v1/slideshows/{slideshow_id}",
            headers=auth_headers,
        )
        assert check_response.status_code == 404

    def test_duplicate_slideshow_success(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        http_client,
        auth_headers,
    ):
        """Test duplicating a slideshow copies its items, including inactive."""
        page = enhanced_page
        vite_url = servers["vite_url"]

        # Create a slideshow with two items via API
        slideshow_name = f"Duplicate Source {int(time.time() * 1000)}"
        response = http_client.post(
            "/api/v1/slideshows",
            json={
                "name": slideshow_name,
                "description": "Slideshow to be duplicated",
                "is_active": True,
            },
            headers=auth_headers,
        )
        assert response.status_code in [200, 201]
        slideshow_id = response.json()["data"]["id"]

        for title in ["Dup Item One", "Dup Item Two"]:
            response = http_client.post(
                f"/api/v1/slideshows/{slideshow_id}/items",
                json={
                    "title": title,
                    "content_type": "text",
                    "content_text": f"Content of {title}",
                    "is_active": True,
                },
                headers=auth_headers,
            )
            assert response.status_code in [200, 201]
            item_id = response.json()["data"]["id"]

        # Soft-delete the second item so the source has one inactive item
        response = http_client.delete(
            f"/api/v1/slideshow-items/{item_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200

        # Login and navigate to slideshows page
        self._login(page, vite_url, test_database)
        page.goto(f"{vite_url}/admin/slideshows")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        row = page.locator(f"tr:has-text('{slideshow_name}')")
        expect(row).to_be_visible(timeout=10000)

        # Accept the name prompt with a new name
        duplicate_name = f"Duplicated Copy {int(time.time() * 1000)}"
        page.on("dialog", lambda dialog: dialog.accept(duplicate_name))

        # Click the Duplicate button
        row.locator("button[title='Duplicate']").click()

        # The duplicated slideshow should appear in the list
        expect(page.locator(f"tr:has-text('{duplicate_name}')")).to_be_visible(
            timeout=10000
        )

        # Verify via API that the duplicate has both items, one inactive
        response = http_client.get("/api/v1/slideshows", headers=auth_headers)
        assert response.status_code == 200
        duplicate = next(
            s for s in response.json()["data"] if s["name"] == duplicate_name
        )
        response = http_client.get(
            f"/api/v1/slideshows/{duplicate['id']}/items?include_inactive=true",
            headers=auth_headers,
        )
        assert response.status_code == 200
        items = response.json()["data"]
        assert len(items) == 2
        items_by_title = {item["title"]: item for item in items}
        assert items_by_title["Dup Item One"]["is_active"] is True
        assert items_by_title["Dup Item Two"]["is_active"] is False

        # Cleanup: delete both slideshows
        for cleanup_id in [slideshow_id, duplicate["id"]]:
            http_client.delete(
                f"/api/v1/slideshows/{cleanup_id}",
                headers=auth_headers,
            )

    def test_duplicate_slideshow_cancel(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        test_slideshow: dict,
        http_client,
        auth_headers,
    ):
        """Test cancelling the duplicate prompt does nothing."""
        page = enhanced_page
        vite_url = servers["vite_url"]
        slideshow_name = test_slideshow["name"]

        # Login and navigate to slideshows page
        self._login(page, vite_url, test_database)
        page.goto(f"{vite_url}/admin/slideshows")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        row = page.locator(f"tr:has-text('{slideshow_name}')")
        expect(row).to_be_visible(timeout=10000)

        # Count slideshows before, then dismiss the prompt
        response = http_client.get("/api/v1/slideshows", headers=auth_headers)
        count_before = len(response.json()["data"])

        page.on("dialog", lambda dialog: dialog.dismiss())
        row.locator("button[title='Duplicate']").click()

        # Give the UI a moment, then verify nothing was created
        page.wait_for_timeout(1000)
        response = http_client.get("/api/v1/slideshows", headers=auth_headers)
        assert len(response.json()["data"]) == count_before

    def test_duplicate_slideshow_duplicate_name_error(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        test_slideshow: dict,
    ):
        """Test duplicating with an existing name shows an error."""
        page = enhanced_page
        vite_url = servers["vite_url"]
        slideshow_name = test_slideshow["name"]

        # Login and navigate to slideshows page
        self._login(page, vite_url, test_database)
        page.goto(f"{vite_url}/admin/slideshows")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        row = page.locator(f"tr:has-text('{slideshow_name}')")
        expect(row).to_be_visible(timeout=10000)

        # Accept the prompt with the source slideshow's own name
        page.on("dialog", lambda dialog: dialog.accept(slideshow_name))
        row.locator("button[title='Duplicate']").click()

        # An error alert should appear
        alert = page.locator(".alert-danger")
        expect(alert).to_be_visible(timeout=10000)
        expect(alert).to_contain_text("already exists")

    def test_create_slideshow_with_default_checked(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        http_client,
        auth_headers,
    ):
        """Test creating a new slideshow with 'Set as Default' checkbox checked.

        This tests that when creating a new slideshow with the is_default
        checkbox checked, the slideshow is actually saved as the default.
        """
        page = enhanced_page
        vite_url = servers["vite_url"]

        # Login first
        self._login(page, vite_url, test_database)

        # Navigate to create slideshow page
        page.goto(f"{vite_url}/admin/slideshows/new")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Verify form page loaded
        expect(page.locator("h1")).to_contain_text("Create New Slideshow")

        # Generate unique name
        slideshow_name = f"Default Test Create {int(time.time() * 1000)}"

        # Fill in the form
        page.locator("#slideshow-name").fill(slideshow_name)
        page.locator("#description").fill("Test slideshow created as default")
        page.locator("#default-item-duration").fill("15")

        # Check the "Set as Default Slideshow" checkbox
        default_checkbox = page.locator("#is_default")
        expect(default_checkbox).to_be_visible()
        default_checkbox.check()

        # Verify it's checked
        expect(default_checkbox).to_be_checked()

        # Submit the form
        page.locator("button[type='submit']").click()

        # Wait for navigation to slideshow detail page
        expect(page).to_have_url(re.compile(r".*/admin/slideshows/\d+$"), timeout=10000)
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Extract slideshow ID from URL for cleanup and verification
        url = page.url
        slideshow_id = url.split("/")[-1]

        try:
            # Verify the slideshow was created as default via API
            response = http_client.get(
                f"/api/v1/slideshows/{slideshow_id}",
                headers=auth_headers,
            )
            assert response.status_code == 200
            response_data = response.json().get("data", response.json())
            assert (
                response_data["is_default"] is True
            ), f"Slideshow should be default but is_default={response_data['is_default']}"

            # Also verify via the slideshows list page that it shows the Default badge
            page.goto(f"{vite_url}/admin/slideshows")
            page.wait_for_load_state("domcontentloaded", timeout=10000)

            # Find the row for our slideshow and verify it has the Default badge
            row = page.locator(f"tr:has-text('{slideshow_name}')")
            expect(row).to_be_visible(timeout=10000)
            expect(row.locator(".badge:has-text('Default')")).to_be_visible(
                timeout=5000
            )

        finally:
            # Cleanup: delete the created slideshow
            if slideshow_id.isdigit():
                http_client.delete(
                    f"/api/v1/slideshows/{slideshow_id}",
                    headers=auth_headers,
                )

    def test_set_slideshow_as_default(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        http_client,
        auth_headers,
    ):
        """Test setting a slideshow as the default."""
        page = enhanced_page
        vite_url = servers["vite_url"]

        # Create a non-default slideshow for this test
        slideshow_name = f"Default Test {int(time.time() * 1000)}"
        response = http_client.post(
            "/api/v1/slideshows",
            json={
                "name": slideshow_name,
                "description": "Slideshow to be set as default",
                "is_active": True,
                "is_default": False,
            },
            headers=auth_headers,
        )
        assert response.status_code in [200, 201]
        response_data = response.json().get("data", response.json())
        slideshow_id = response_data["id"]

        try:
            # Login first
            self._login(page, vite_url, test_database)

            # Navigate to slideshows page
            page.goto(f"{vite_url}/admin/slideshows")
            page.wait_for_load_state("domcontentloaded", timeout=10000)

            # Find the row for our slideshow
            row = page.locator(f"tr:has-text('{slideshow_name}')")
            expect(row).to_be_visible(timeout=10000)

            # Verify it doesn't have the "Default" badge yet
            # Use a specific selector for the badge to avoid matching text in the name
            default_badge = row.locator(".badge:has-text('Default')")
            # It might not be visible if not default
            initial_has_default = default_badge.is_visible()
            assert not initial_has_default, "Slideshow should not be default initially"

            # Click the "Set as Default" button (star icon)
            set_default_button = row.locator("button[title='Set as Default']")
            expect(set_default_button).to_be_visible()
            set_default_button.click()

            # Wait for the page to refresh and show the Default badge
            page.wait_for_timeout(1000)  # Allow time for API call

            # Reload the page to see updated state
            page.reload()
            page.wait_for_load_state("domcontentloaded", timeout=10000)

            # Find the row again and verify it has the Default badge
            row = page.locator(f"tr:has-text('{slideshow_name}')")
            expect(row).to_be_visible(timeout=10000)
            expect(row.locator(".badge:has-text('Default')")).to_be_visible(
                timeout=5000
            )

        finally:
            # Cleanup
            http_client.delete(
                f"/api/v1/slideshows/{slideshow_id}",
                headers=auth_headers,
            )

    def _login(self, page: Page, vite_url: str, test_database: dict):
        """Helper method to log in to the admin interface."""
        # Navigate to login page
        page.goto(f"{vite_url}/admin/login")

        # Wait for login form
        page.wait_for_selector("input[name='username']", timeout=10000)

        # Get credentials
        user = test_database["users"][0]
        username = user["username"]
        password = user["password"]

        # Fill and submit
        page.locator("input[name='username']").fill(username)
        page.locator("input[name='password']").fill(password)
        page.locator("button[type='submit']").click()

        # Wait for login to complete (dashboard loads)
        page.wait_for_selector("h1:has-text('Dashboard')", timeout=10000)

    def test_slideshow_action_link_titles_and_destinations(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        test_slideshow: dict,
    ):
        """Test that slideshow action links have correct titles and destinations.

        This test verifies that:
        - "Edit Slides" link (eye icon) navigates to /admin/slideshows/{id}
        - "Edit Slideshow" link (pencil icon) navigates to /admin/slideshows/{id}/edit

        The links were previously named "View Details" and "Edit" which was confusing
        because "View Details" actually goes to the slide management page, not a
        read-only view.
        """
        page = enhanced_page
        vite_url = servers["vite_url"]
        slideshow_id = test_slideshow["id"]

        # Login first
        self._login(page, vite_url, test_database)

        # Navigate to slideshows page
        page.goto(f"{vite_url}/admin/slideshows")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Find the row for our test slideshow
        row = page.locator(f"tr:has-text('{test_slideshow['name']}')")
        expect(row).to_be_visible(timeout=10000)

        # Verify "Edit Slides" link exists with correct title and destination
        edit_slides_link = row.locator("a[title='Edit Slides']")
        expect(edit_slides_link).to_be_visible(timeout=5000)

        # Verify it has the eye icon
        expect(edit_slides_link.locator("i.bi-eye")).to_be_visible()

        # Verify the href points to the detail page (not /edit)
        href = edit_slides_link.get_attribute("href")
        assert href == f"/admin/slideshows/{slideshow_id}", (
            f"Edit Slides link should go to /admin/slideshows/{slideshow_id}, "
            f"got {href}"
        )

        # Verify "Edit Slideshow" link exists with correct title and destination
        edit_slideshow_link = row.locator("a[title='Edit Slideshow']")
        expect(edit_slideshow_link).to_be_visible(timeout=5000)

        # Verify it has the pencil icon
        expect(edit_slideshow_link.locator("i.bi-pencil")).to_be_visible()

        # Verify the href points to the edit page
        href = edit_slideshow_link.get_attribute("href")
        assert href == f"/admin/slideshows/{slideshow_id}/edit", (
            f"Edit Slideshow link should go to /admin/slideshows/{slideshow_id}/edit, "
            f"got {href}"
        )

        # Click "Edit Slides" and verify we go to the correct page
        edit_slides_link.click()
        page.wait_for_url(f"**/admin/slideshows/{slideshow_id}", timeout=10000)
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # The detail page shows "Slideshow Items" header
        expect(page.locator("text=Slideshow Items")).to_be_visible(timeout=5000)

        # Go back to slideshows list
        page.goto(f"{vite_url}/admin/slideshows")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Find the row again and click "Edit Slideshow"
        row = page.locator(f"tr:has-text('{test_slideshow['name']}')")
        edit_slideshow_link = row.locator("a[title='Edit Slideshow']")
        edit_slideshow_link.click()
        page.wait_for_url(f"**/admin/slideshows/{slideshow_id}/edit", timeout=10000)
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # The edit page shows "Edit Slideshow" header
        expect(page.locator("h1")).to_contain_text("Edit Slideshow")
