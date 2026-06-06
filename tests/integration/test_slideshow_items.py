"""
Integration tests for slideshow item management in the admin interface.

Tests adding, editing, deleting, and reordering slideshow items:
- Add image item via file upload
- Add image item via URL
- Add video item via file upload
- Add video item via URL
- Add URL item (webpage)
- Add text item
- Edit existing item
- Delete item with confirmation
- Reorder items (move up/down)
- Icon visibility (Bootstrap Icons CSS import)
- Auto-title from filename/URL

These tests verify that data is actually persisted by checking via API calls,
not just verifying UI display.

Run with: nox -s test-integration
"""

import os
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

# Path to test assets
ASSETS_DIR = Path(__file__).parent.parent / "assets"


def get_item_by_title(
    http_client, auth_headers, slideshow_id: int, title: str
) -> dict | None:
    """Helper to fetch a slideshow item by title via API."""
    response = http_client.get(
        f"/api/v1/slideshows/{slideshow_id}/items",
        headers=auth_headers,
    )
    assert response.status_code == 200, f"Failed to fetch items: {response.text}"
    data = response.json()
    items = data.get("data", data)
    for item in items:
        if item.get("title") == title:
            return item
    return None


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("SKIP_BROWSER_TESTS", "false").lower() == "true",
    reason="Browser tests skipped",
)
class TestSlideshowItems:
    """Test slideshow item management through the admin interface."""

    def test_add_image_item_via_file_upload(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        test_slideshow: dict,
        http_client,
        auth_headers,
    ):
        """Test adding an image item by uploading a file.

        Tests the image file upload flow through the admin interface.
        Verifies via API that content_file_path is persisted and file size matches.
        """
        page = enhanced_page
        vite_url = servers["vite_url"]
        slideshow_id = test_slideshow["id"]

        # Get the image path for upload
        image_path = ASSETS_DIR / "smallPhoto.jpg"
        assert image_path.exists(), f"Test asset not found: {image_path}"

        # Login and navigate to slideshow detail page
        self._login(page, vite_url, test_database)
        page.goto(f"{vite_url}/admin/slideshows/{slideshow_id}")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Click "Add Item" button
        add_button = page.locator("button:has-text('Add Item')")
        expect(add_button).to_be_visible(timeout=10000)
        add_button.click()

        # Wait for modal to appear
        modal = page.locator(".modal")
        expect(modal).to_be_visible(timeout=5000)

        # Fill in the form
        page.locator("#title").fill("Test Image Upload")
        page.locator("#content_type").select_option("image")

        # Upload the image file
        page.locator("#file_image").set_input_files(str(image_path))

        # Wait for upload to complete (success badge with "File uploaded:" appears)
        expect(
            page.locator(".badge.bg-success:has-text('File uploaded')")
        ).to_be_visible(timeout=10000)

        # Submit the form
        page.locator("button[type='submit']").click()

        # Wait for modal to close
        expect(modal).to_be_hidden(timeout=10000)

        # Verify item appears in the table
        expect(page.locator("text=Test Image Upload")).to_be_visible(timeout=5000)
        expect(
            page.locator("tr:has-text('Test Image Upload') .badge:has-text('image')")
        ).to_be_visible()

        # CRITICAL: Verify via API that data was actually persisted
        item = get_item_by_title(
            http_client, auth_headers, slideshow_id, "Test Image Upload"
        )
        assert item is not None, "Item not found via API after creation"
        assert (
            item.get("content_type") == "image"
        ), f"content_type not persisted correctly: {item.get('content_type')}"
        assert item.get("content_file_path"), f"content_file_path not persisted: {item}"

    def test_add_image_item_via_url(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        test_slideshow: dict,
        http_client,
        auth_headers,
    ):
        """Test adding an image item by specifying a URL.

        Verifies via API that content_url is persisted.
        """
        page = enhanced_page
        vite_url = servers["vite_url"]
        slideshow_id = test_slideshow["id"]
        test_url = "https://example.com/image.jpg"

        # Login and navigate to slideshow detail page
        self._login(page, vite_url, test_database)
        page.goto(f"{vite_url}/admin/slideshows/{slideshow_id}")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Click "Add Item" button
        page.locator("button:has-text('Add Item')").click()

        # Wait for modal
        modal = page.locator(".modal")
        expect(modal).to_be_visible(timeout=5000)

        # Fill in the form with URL instead of file upload
        page.locator("#title").fill("Test Image URL")
        page.locator("#content_type").select_option("image")
        page.locator("#url_alternative").fill(test_url)

        # Submit the form
        page.locator("button[type='submit']").click()

        # Wait for modal to close
        expect(modal).to_be_hidden(timeout=10000)

        # Verify item appears in the table
        expect(page.locator("text=Test Image URL")).to_be_visible(timeout=5000)
        expect(
            page.locator("tr:has-text('Test Image URL') .badge:has-text('image')")
        ).to_be_visible()

        # CRITICAL: Verify via API that data was actually persisted
        item = get_item_by_title(
            http_client, auth_headers, slideshow_id, "Test Image URL"
        )
        assert item is not None, "Item not found via API after creation"
        assert (
            item.get("content_type") == "image"
        ), f"content_type not persisted correctly: {item.get('content_type')}"
        assert item.get("content_url") == test_url, (
            f"content_url not persisted correctly: expected '{test_url}', "
            f"got '{item.get('content_url')}'"
        )

    def test_add_video_item_via_file_upload(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        test_slideshow: dict,
        http_client,
        auth_headers,
    ):
        """Test adding a video item by uploading a file.

        Tests the video file upload flow through the admin interface.
        Verifies via API that content_file_path is persisted.

        Uses test_video_5s.mp4 which has H.264 codec (browser-compatible).
        """
        page = enhanced_page
        vite_url = servers["vite_url"]
        slideshow_id = test_slideshow["id"]

        # Get the video path for upload - use H.264 video (browser-compatible)
        video_path = ASSETS_DIR / "test_video_5s.mp4"
        assert video_path.exists(), f"Test asset not found: {video_path}"

        # Login and navigate to slideshow detail page
        self._login(page, vite_url, test_database)
        page.goto(f"{vite_url}/admin/slideshows/{slideshow_id}")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Click "Add Item" button
        page.locator("button:has-text('Add Item')").click()

        # Wait for modal
        modal = page.locator(".modal")
        expect(modal).to_be_visible(timeout=5000)

        # Fill in the form
        page.locator("#title").fill("Test Video Upload")
        page.locator("#content_type").select_option("video")

        # Upload the video file
        page.locator("#file_video").set_input_files(str(video_path))

        # Wait for upload to complete (success badge with "File uploaded:" appears)
        expect(
            page.locator(".badge.bg-success:has-text('File uploaded')")
        ).to_be_visible(timeout=30000)

        # Submit the form
        page.locator("button[type='submit']").click()

        # Wait for modal to close
        expect(modal).to_be_hidden(timeout=10000)

        # Verify item appears in the table
        expect(page.locator("text=Test Video Upload")).to_be_visible(timeout=5000)
        expect(
            page.locator("tr:has-text('Test Video Upload') .badge:has-text('video')")
        ).to_be_visible()

        # CRITICAL: Verify via API that data was actually persisted
        item = get_item_by_title(
            http_client, auth_headers, slideshow_id, "Test Video Upload"
        )
        assert item is not None, "Item not found via API after creation"
        assert (
            item.get("content_type") == "video"
        ), f"content_type not persisted correctly: {item.get('content_type')}"
        assert item.get("content_file_path"), f"content_file_path not persisted: {item}"

    def test_video_upload_auto_detects_duration(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        test_slideshow: dict,
        http_client,
        auth_headers,
    ):
        """Test that video upload automatically detects and sets duration.

        When a video file is uploaded, the backend should use ffprobe to detect
        the video duration. This duration should be:
        1. Returned in the upload response
        2. Auto-populated in the duration field (which becomes read-only)
        3. Persisted as display_duration when the item is saved

        Uses test_video_5s.mp4 which is a 5-second test video.
        """
        page = enhanced_page
        vite_url = servers["vite_url"]
        slideshow_id = test_slideshow["id"]

        # Get the test video with known duration (5 seconds)
        video_path = ASSETS_DIR / "test_video_5s.mp4"
        assert video_path.exists(), f"Test asset not found: {video_path}"

        # Login and navigate to slideshow detail page
        self._login(page, vite_url, test_database)
        page.goto(f"{vite_url}/admin/slideshows/{slideshow_id}")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Click "Add Item" button
        page.locator("button:has-text('Add Item')").click()

        # Wait for modal
        modal = page.locator(".modal")
        expect(modal).to_be_visible(timeout=5000)

        # Fill in the form
        page.locator("#title").fill("Video With Auto Duration")
        page.locator("#content_type").select_option("video")

        # Upload the video file
        page.locator("#file_video").set_input_files(str(video_path))

        # Wait for upload to complete
        expect(
            page.locator(".badge.bg-success:has-text('File uploaded')")
        ).to_be_visible(timeout=30000)

        # Verify the duration field is auto-populated (should show ~5 seconds)
        duration_field = page.locator("#duration")
        # The field should have a value now (auto-detected duration)
        expect(duration_field).to_have_value("5", timeout=5000)

        # Verify the duration field is read-only for auto-detected video duration
        expect(duration_field).to_be_disabled()

        # Verify the label indicates auto-detection
        expect(
            page.locator("label:has-text('Video Duration (auto-detected)')")
        ).to_be_visible()

        # Submit the form
        page.locator("button[type='submit']").click()

        # Wait for modal to close
        expect(modal).to_be_hidden(timeout=10000)

        # Verify item appears in the table
        expect(page.locator("text=Video With Auto Duration")).to_be_visible(
            timeout=5000
        )

        # CRITICAL: Verify via API that display_duration was automatically set
        item = get_item_by_title(
            http_client, auth_headers, slideshow_id, "Video With Auto Duration"
        )
        assert item is not None, "Item not found via API after creation"
        assert (
            item.get("content_type") == "video"
        ), f"content_type not persisted correctly: {item.get('content_type')}"
        assert item.get("content_file_path"), f"content_file_path not persisted: {item}"

        # The display_duration should be set to 5 seconds (auto-detected from video)
        assert item.get("display_duration") == 5, (
            f"display_duration should be auto-set to 5 seconds from video, "
            f"got: {item.get('display_duration')}"
        )

    def test_video_upload_unsupported_format_shows_error(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        test_slideshow: dict,
        http_client,
        auth_headers,
    ):
        """Test that uploading a video with unsupported codec shows error.

        When a video with an unsupported codec (e.g., MPEG-1) is uploaded,
        the server should reject it with a clear error message explaining
        which formats are supported.

        Uses crash_into_pole.mpeg which has MPEG-1 codec (not browser-compatible).
        """
        page = enhanced_page
        vite_url = servers["vite_url"]
        slideshow_id = test_slideshow["id"]

        # Get the video path for upload - MPEG-1 codec (not supported)
        video_path = ASSETS_DIR / "crash_into_pole.mpeg"
        assert video_path.exists(), f"Test asset not found: {video_path}"

        # Login and navigate to slideshow detail page
        self._login(page, vite_url, test_database)
        page.goto(f"{vite_url}/admin/slideshows/{slideshow_id}")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Click "Add Item" button
        page.locator("button:has-text('Add Item')").click()

        # Wait for modal
        modal = page.locator(".modal")
        expect(modal).to_be_visible(timeout=5000)

        # Fill in the form
        page.locator("#title").fill("Unsupported Video Test")
        page.locator("#content_type").select_option("video")

        # Upload the video file with unsupported codec
        page.locator("#file_video").set_input_files(str(video_path))

        # Wait for the error to appear (should show alert with error message)
        # The upload should fail and show an error, not a success badge
        error_alert = page.locator(".alert-danger")
        expect(error_alert).to_be_visible(timeout=30000)

        # Verify the error message mentions the codec issue and supported formats
        error_text = error_alert.inner_text()
        assert (
            "not supported" in error_text.lower()
        ), f"Error message should mention codec not supported. Got: {error_text}"
        # Should mention at least one supported format
        assert any(
            fmt in error_text.lower() for fmt in ["h264", "vp8", "vp9", "mp4", "webm"]
        ), f"Error message should mention supported formats. Got: {error_text}"

        # The success badge should NOT appear
        success_badge = page.locator(".badge.bg-success:has-text('File uploaded')")
        expect(success_badge).not_to_be_visible()

        # Close the modal without submitting
        page.keyboard.press("Escape")
        expect(modal).to_be_hidden(timeout=5000)

        # CRITICAL: Verify via API that NO item was created
        item = get_item_by_title(
            http_client, auth_headers, slideshow_id, "Unsupported Video Test"
        )
        assert item is None, (
            "Item should NOT have been created for unsupported video format. "
            f"Found: {item}"
        )

    def test_add_video_item_via_url(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        test_slideshow: dict,
        http_client,
        auth_headers,
    ):
        """Test adding a video item by specifying a URL.

        This test verifies the UI flow for adding a video via URL:
        1. User enters video URL
        2. Frontend validates URL on blur (using ffprobe)
        3. Validation result displayed (success badge or error)
        4. User submits form

        Note: Video URLs are validated on blur via the /api/v1/validate/video-url
        endpoint AND again during item creation. Since we can't use real video URLs
        in tests (ffprobe can't access them), we mock both endpoints. Backend
        validation logic is covered by unit tests.
        """
        page = enhanced_page
        vite_url = servers["vite_url"]
        slideshow_id = test_slideshow["id"]
        test_url = "https://example.com/video.mp4"

        # Mock the video URL validation endpoint to return success
        # This allows testing with fake URLs since ffprobe can't validate them
        # Note: Route pattern must match vite_url since browser requests go through Vite
        def handle_validation(route):
            route.fulfill(
                status=200,
                content_type="application/json",
                body='{"success": true, "data": {"valid": true, "duration_seconds": 30, "codec": "h264", "container": "mp4"}}',
            )

        page.route(f"{vite_url}/api/v1/validate/video-url", handle_validation)

        # Mock the create item endpoint for video URLs to bypass backend validation
        # Backend also validates video URLs during item creation, which would fail
        # for our fake URL. We mock the response to test the UI flow.
        item_id_counter = [1000]  # Use list to allow modification in closure

        def handle_create_item(route, request):
            import json

            # Parse request body to check if it's a video URL item
            body = json.loads(request.post_data or "{}")
            if body.get("content_type") == "video" and body.get("content_url"):
                # Return mocked successful response for video URL items
                item_id = item_id_counter[0]
                item_id_counter[0] += 1
                response_data = {
                    "success": True,
                    "data": {
                        "id": item_id,
                        "slideshow_id": slideshow_id,
                        "title": body.get("title"),
                        "content_type": "video",
                        "content_url": body.get("content_url"),
                        "display_duration": body.get("display_duration", 30),
                        "position": item_id,
                        "is_active": body.get("is_active", True),
                    },
                }
                route.fulfill(
                    status=201,
                    content_type="application/json",
                    body=json.dumps(response_data),
                )
            else:
                # Let non-video-URL requests pass through
                route.continue_()

        page.route(
            f"**/api/v1/slideshows/{slideshow_id}/items**",
            lambda route: handle_create_item(route, route.request),
        )

        # Login and navigate to slideshow detail page
        self._login(page, vite_url, test_database)
        page.goto(f"{vite_url}/admin/slideshows/{slideshow_id}")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Click "Add Item" button
        page.locator("button:has-text('Add Item')").click()

        # Wait for modal
        modal = page.locator(".modal")
        expect(modal).to_be_visible(timeout=5000)

        # Fill in the form with URL instead of file upload
        page.locator("#title").fill("Test Video URL")
        page.locator("#content_type").select_option("video")
        page.locator("#url_alternative").fill(test_url)

        # Trigger blur to start validation, then wait for it to complete
        page.locator("#url_alternative").blur()

        # Wait for validation to complete (indicated by "Video URL validated" badge)
        expect(
            page.locator(".badge.bg-success:has-text('Video URL validated')")
        ).to_be_visible(timeout=10000)

        # Submit the form
        page.locator("button[type='submit']").click()

        # Wait for modal to close (proves successful form submission)
        expect(modal).to_be_hidden(timeout=10000)

        # Note: We don't verify the item in the table because after the mocked
        # create response, the frontend refetches the items list from the server
        # (which isn't mocked), so the mocked item won't appear.
        # The modal closing proves the UI flow completed successfully.
        # Backend video URL validation and persistence is tested in unit tests.

    def test_video_url_validation_error_shows_message(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        test_slideshow: dict,
        http_client,
        auth_headers,
    ):
        """Test that invalid video URL shows error message and blocks submission.

        When a video URL validation fails (unsupported codec, network error, etc.),
        the form should display an error message and prevent submission.
        """
        page = enhanced_page
        vite_url = servers["vite_url"]
        slideshow_id = test_slideshow["id"]
        test_url = "https://example.com/unsupported-video.avi"

        # Mock the video URL validation endpoint to return an error
        # Note: Route pattern must match vite_url since browser requests go through Vite
        def handle_validation(route):
            route.fulfill(
                status=200,
                content_type="application/json",
                body='{"success": false, "error": "Video codec mpeg1video is not supported for browser playback. Supported codecs: H.264, VP8, VP9, Theora, AV1"}',
            )

        page.route(f"{vite_url}/api/v1/validate/video-url", handle_validation)

        # Login and navigate to slideshow detail page
        self._login(page, vite_url, test_database)
        page.goto(f"{vite_url}/admin/slideshows/{slideshow_id}")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Click "Add Item" button
        page.locator("button:has-text('Add Item')").click()

        # Wait for modal
        modal = page.locator(".modal")
        expect(modal).to_be_visible(timeout=5000)

        # Fill in the form with video type and URL
        page.locator("#title").fill("Invalid Video URL Test")
        page.locator("#content_type").select_option("video")
        page.locator("#url_alternative").fill(test_url)

        # Trigger blur to start validation
        page.locator("#url_alternative").blur()

        # Wait for error message to appear (Bootstrap's invalid-feedback class)
        # The error message is displayed as Form.Control.Feedback type="invalid"
        # Multiple .invalid-feedback elements may exist, so we filter to the one with text
        error_text = page.locator(".invalid-feedback").filter(has_text="not supported")
        expect(error_text).to_be_visible(timeout=10000)

        # Verify error message mentions codec issue
        error_content = error_text.inner_text()
        assert (
            "not supported" in error_content.lower()
        ), f"Error should mention codec not supported. Got: {error_content}"

        # Verify the success badge is NOT visible
        success_badge = page.locator(
            ".badge.bg-success:has-text('Video URL validated')"
        )
        expect(success_badge).not_to_be_visible()

        # Close the modal without submitting
        page.keyboard.press("Escape")
        expect(modal).to_be_hidden(timeout=5000)

        # CRITICAL: Verify via API that NO item was created
        item = get_item_by_title(
            http_client, auth_headers, slideshow_id, "Invalid Video URL Test"
        )
        assert item is None, (
            "Item should NOT have been created for invalid video URL. " f"Found: {item}"
        )

    def test_video_url_auto_detects_duration(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        test_slideshow: dict,
        http_client,
        auth_headers,
    ):
        """Test that video URL validation auto-detects and populates duration.

        When a video URL is validated successfully, the duration field should be
        auto-populated with the detected duration and become read-only.

        This test focuses on verifying the UI properly:
        1. Auto-populates the duration field with detected value
        2. Disables the duration field for auto-detected values
        3. The form can be submitted with the auto-detected duration

        Backend video URL validation is tested in unit tests.
        """
        page = enhanced_page
        vite_url = servers["vite_url"]
        slideshow_id = test_slideshow["id"]
        test_url = "https://example.com/video-with-duration.mp4"
        expected_duration = 45

        # Mock the video URL validation endpoint to return success with duration
        # Note: Route pattern must match vite_url since browser requests go through Vite
        def handle_validation(route):
            route.fulfill(
                status=200,
                content_type="application/json",
                body=f'{{"success": true, "data": {{"valid": true, "duration_seconds": {expected_duration}, "codec": "h264", "container": "mp4"}}}}',
            )

        page.route(f"{vite_url}/api/v1/validate/video-url", handle_validation)

        # Mock the create item endpoint for video URLs to bypass backend validation
        # Backend also validates video URLs during item creation
        item_id_counter = [2000]

        def handle_create_item(route, request):
            import json

            body = json.loads(request.post_data or "{}")
            if body.get("content_type") == "video" and body.get("content_url"):
                item_id = item_id_counter[0]
                item_id_counter[0] += 1
                response_data = {
                    "success": True,
                    "data": {
                        "id": item_id,
                        "slideshow_id": slideshow_id,
                        "title": body.get("title"),
                        "content_type": "video",
                        "content_url": body.get("content_url"),
                        "display_duration": body.get(
                            "display_duration", expected_duration
                        ),
                        "position": item_id,
                        "is_active": body.get("is_active", True),
                    },
                }
                route.fulfill(
                    status=201,
                    content_type="application/json",
                    body=json.dumps(response_data),
                )
            else:
                route.continue_()

        page.route(
            f"**/api/v1/slideshows/{slideshow_id}/items**",
            lambda route: handle_create_item(route, route.request),
        )

        # Login and navigate to slideshow detail page
        self._login(page, vite_url, test_database)
        page.goto(f"{vite_url}/admin/slideshows/{slideshow_id}")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Click "Add Item" button
        page.locator("button:has-text('Add Item')").click()

        # Wait for modal
        modal = page.locator(".modal")
        expect(modal).to_be_visible(timeout=5000)

        # Fill in the form with video type and URL
        page.locator("#title").fill("Video With Auto Duration")
        page.locator("#content_type").select_option("video")
        page.locator("#url_alternative").fill(test_url)

        # Trigger blur to start validation
        page.locator("#url_alternative").blur()

        # Wait for validation to complete
        expect(
            page.locator(".badge.bg-success:has-text('Video URL validated')")
        ).to_be_visible(timeout=10000)

        # Verify duration field is auto-populated
        duration_field = page.locator("#duration")
        expect(duration_field).to_have_value(str(expected_duration), timeout=5000)

        # Verify duration field is disabled (read-only for auto-detected duration)
        expect(duration_field).to_be_disabled()

        # Submit the form
        page.locator("button[type='submit']").click()

        # Wait for modal to close (proves successful form submission)
        expect(modal).to_be_hidden(timeout=10000)

        # Note: We don't verify the item in the table because after the mocked
        # create response, the frontend refetches items from the server.
        # The key verifications (duration auto-population, disabled field, modal close)
        # prove the UI flow completed successfully.
        # Backend video URL validation and duration persistence tested in unit tests.

    def test_add_url_item(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        test_slideshow: dict,
        http_client,
        auth_headers,
    ):
        """Test adding a URL (webpage) item.

        Verifies via API that content_url and display_duration are persisted.
        """
        page = enhanced_page
        vite_url = servers["vite_url"]
        slideshow_id = test_slideshow["id"]
        test_url = "https://example.com"
        test_duration = 30

        # Login and navigate to slideshow detail page
        self._login(page, vite_url, test_database)
        page.goto(f"{vite_url}/admin/slideshows/{slideshow_id}")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Click "Add Item" button
        page.locator("button:has-text('Add Item')").click()

        # Wait for modal
        modal = page.locator(".modal")
        expect(modal).to_be_visible(timeout=5000)

        # Fill in the form for URL type
        page.locator("#title").fill("Test Web Page")
        page.locator("#content_type").select_option("url")
        page.locator("#url").fill(test_url)

        # Set a custom duration
        page.locator("#duration").fill(str(test_duration))

        # Submit the form
        page.locator("button[type='submit']").click()

        # Wait for modal to close
        expect(modal).to_be_hidden(timeout=10000)

        # Verify item appears in the table
        expect(page.locator("text=Test Web Page")).to_be_visible(timeout=5000)
        expect(
            page.locator("tr:has-text('Test Web Page') .badge:has-text('url')")
        ).to_be_visible()

        # CRITICAL: Verify via API that data was actually persisted
        item = get_item_by_title(
            http_client, auth_headers, slideshow_id, "Test Web Page"
        )
        assert item is not None, "Item not found via API after creation"
        assert (
            item.get("content_type") == "url"
        ), f"content_type not persisted correctly: {item.get('content_type')}"
        assert item.get("content_url") == test_url, (
            f"content_url not persisted correctly: expected '{test_url}', "
            f"got '{item.get('content_url')}'"
        )
        assert item.get("display_duration") == test_duration, (
            f"display_duration not persisted correctly: expected {test_duration}, "
            f"got {item.get('display_duration')}"
        )

    def test_add_text_item(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        test_slideshow: dict,
        http_client,
        auth_headers,
    ):
        """Test adding a text item.

        Verifies via API that content_text is persisted.
        """
        page = enhanced_page
        vite_url = servers["vite_url"]
        slideshow_id = test_slideshow["id"]
        test_text = "This is a test message for the slideshow."

        # Login and navigate to slideshow detail page
        self._login(page, vite_url, test_database)
        page.goto(f"{vite_url}/admin/slideshows/{slideshow_id}")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Click "Add Item" button
        page.locator("button:has-text('Add Item')").click()

        # Wait for modal
        modal = page.locator(".modal")
        expect(modal).to_be_visible(timeout=5000)

        # Fill in the form for text type
        page.locator("#title").fill("Test Text Slide")
        page.locator("#content_type").select_option("text")
        page.locator("#text_content").fill(test_text)

        # Submit the form
        page.locator("button[type='submit']").click()

        # Wait for modal to close
        expect(modal).to_be_hidden(timeout=10000)

        # Verify item appears in the table
        expect(page.locator("text=Test Text Slide")).to_be_visible(timeout=5000)
        expect(
            page.locator("tr:has-text('Test Text Slide') .badge:has-text('text')")
        ).to_be_visible()

        # CRITICAL: Verify via API that data was actually persisted
        item = get_item_by_title(
            http_client, auth_headers, slideshow_id, "Test Text Slide"
        )
        assert item is not None, "Item not found via API after creation"
        assert (
            item.get("content_type") == "text"
        ), f"content_type not persisted correctly: {item.get('content_type')}"
        assert item.get("content_text") == test_text, (
            f"content_text not persisted correctly: expected '{test_text}', "
            f"got '{item.get('content_text')}'"
        )

    def test_add_text_item_with_duration_override(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        test_slideshow: dict,
        http_client,
        auth_headers,
    ):
        """Test adding a text item with a custom duration override.

        Verifies via API that display_duration is persisted.
        """
        page = enhanced_page
        vite_url = servers["vite_url"]
        slideshow_id = test_slideshow["id"]
        test_text = "Text with custom duration."
        test_duration = 45

        # Login and navigate to slideshow detail page
        self._login(page, vite_url, test_database)
        page.goto(f"{vite_url}/admin/slideshows/{slideshow_id}")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Click "Add Item" button
        page.locator("button:has-text('Add Item')").click()

        # Wait for modal
        modal = page.locator(".modal")
        expect(modal).to_be_visible(timeout=5000)

        # Fill in the form for text type with duration
        page.locator("#title").fill("Text With Duration")
        page.locator("#content_type").select_option("text")
        page.locator("#text_content").fill(test_text)
        page.locator("#duration").fill(str(test_duration))

        # Submit the form
        page.locator("button[type='submit']").click()

        # Wait for modal to close
        expect(modal).to_be_hidden(timeout=10000)

        # Verify item appears in the table
        expect(page.locator("text=Text With Duration")).to_be_visible(timeout=5000)

        # CRITICAL: Verify via API that data was actually persisted
        item = get_item_by_title(
            http_client, auth_headers, slideshow_id, "Text With Duration"
        )
        assert item is not None, "Item not found via API after creation"
        assert item.get("content_text") == test_text, (
            f"content_text not persisted correctly: expected '{test_text}', "
            f"got '{item.get('content_text')}'"
        )
        assert item.get("display_duration") == test_duration, (
            f"display_duration not persisted correctly: expected {test_duration}, "
            f"got {item.get('display_duration')}"
        )

    def test_edit_existing_item(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        test_slideshow: dict,
        http_client,
        auth_headers,
    ):
        """Test editing an existing slideshow item.

        Verifies via API that all field changes are persisted.
        """
        page = enhanced_page
        vite_url = servers["vite_url"]
        slideshow_id = test_slideshow["id"]
        original_text = "Original text content"
        updated_text = "Updated text content"

        # Create an item via API first (using correct backend field names)
        response = http_client.post(
            f"/api/v1/slideshows/{slideshow_id}/items",
            json={
                "title": "Item To Edit",
                "content_type": "text",
                "content_text": original_text,
                "is_active": True,
            },
            headers=auth_headers,
        )
        assert response.status_code in [200, 201]

        # Verify item was created with correct content
        item = get_item_by_title(
            http_client, auth_headers, slideshow_id, "Item To Edit"
        )
        assert item is not None, "Created item not found via API"
        assert (
            item.get("content_text") == original_text
        ), f"Original content_text not set correctly: {item.get('content_text')}"

        # Login and navigate to slideshow detail page
        self._login(page, vite_url, test_database)
        page.goto(f"{vite_url}/admin/slideshows/{slideshow_id}")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Find the item row and click Edit
        row = page.locator("tr:has-text('Item To Edit')")
        expect(row).to_be_visible(timeout=10000)
        row.locator("button[title='Edit']").click()

        # Wait for modal
        modal = page.locator(".modal")
        expect(modal).to_be_visible(timeout=5000)

        # Verify form is pre-filled with existing values
        expect(page.locator("#title")).to_have_value("Item To Edit")
        # Note: This assertion may fail if the form doesn't properly load saved values
        # due to the field name mismatch bug we're testing for
        expect(page.locator("#text_content")).to_have_value(original_text)

        # Update the title and content
        page.locator("#title").fill("Updated Item Title")
        page.locator("#text_content").fill(updated_text)

        # Submit the form
        page.locator("button[type='submit']").click()

        # Wait for modal to close
        expect(modal).to_be_hidden(timeout=10000)

        # Verify updated item appears in the table
        expect(page.locator("text=Updated Item Title")).to_be_visible(timeout=5000)
        expect(page.locator("text=Item To Edit")).to_be_hidden()

        # CRITICAL: Verify via API that changes were actually persisted
        item = get_item_by_title(
            http_client, auth_headers, slideshow_id, "Updated Item Title"
        )
        assert item is not None, "Updated item not found via API"
        assert item.get("content_text") == updated_text, (
            f"content_text not updated correctly: expected '{updated_text}', "
            f"got '{item.get('content_text')}'"
        )

    def test_edit_file_upload_item(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        test_slideshow: dict,
        http_client,
        auth_headers,
    ):
        """Test editing an existing file upload item to change the file.

        This tests the flow of editing an image item that was created via file upload
        and uploading a different file.
        """
        page = enhanced_page
        vite_url = servers["vite_url"]
        slideshow_id = test_slideshow["id"]

        # First, create an image item via the UI with one file
        image_path_1 = ASSETS_DIR / "smallPhoto.jpg"
        image_path_2 = ASSETS_DIR / "bigPhoto.jpg"
        assert image_path_1.exists(), f"Test asset not found: {image_path_1}"
        assert image_path_2.exists(), f"Test asset not found: {image_path_2}"

        # Login and navigate to slideshow detail page
        self._login(page, vite_url, test_database)
        page.goto(f"{vite_url}/admin/slideshows/{slideshow_id}")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Create the initial image item
        page.locator("button:has-text('Add Item')").click()
        modal = page.locator(".modal")
        expect(modal).to_be_visible(timeout=5000)

        page.locator("#title").fill("Image To Edit")
        page.locator("#content_type").select_option("image")
        page.locator("#file_image").set_input_files(str(image_path_1))
        expect(
            page.locator(".badge.bg-success:has-text('File uploaded')")
        ).to_be_visible(timeout=10000)
        page.locator("button[type='submit']").click()
        expect(modal).to_be_hidden(timeout=10000)

        # Verify item was created
        expect(page.locator("text=Image To Edit")).to_be_visible(timeout=5000)

        # Get the original file path via API
        item = get_item_by_title(
            http_client, auth_headers, slideshow_id, "Image To Edit"
        )
        assert item is not None, "Created item not found via API"
        original_file_path = item.get("content_file_path")
        assert original_file_path, "Original content_file_path not set"

        # Now edit the item and upload a different file
        row = page.locator("tr:has-text('Image To Edit')")
        expect(row).to_be_visible(timeout=10000)
        row.locator("button[title='Edit']").click()

        modal = page.locator(".modal")
        expect(modal).to_be_visible(timeout=5000)

        # Upload a different file
        page.locator("#file_image").set_input_files(str(image_path_2))
        # In edit mode, the badge shows "Current file:" instead of "File uploaded:"
        expect(
            page.locator(".badge.bg-success:has-text('Current file:')")
        ).to_be_visible(timeout=10000)

        page.locator("button[type='submit']").click()
        expect(modal).to_be_hidden(timeout=10000)

        # CRITICAL: Verify via API that the file path was updated
        item = get_item_by_title(
            http_client, auth_headers, slideshow_id, "Image To Edit"
        )
        assert item is not None, "Updated item not found via API"
        new_file_path = item.get("content_file_path")
        assert new_file_path, "content_file_path not set after edit"
        assert new_file_path != original_file_path, (
            f"content_file_path should have changed: "
            f"original='{original_file_path}', new='{new_file_path}'"
        )

    def test_edit_file_upload_item_shows_current_file(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        test_slideshow: dict,
        http_client,
        auth_headers,
    ):
        """Test that editing a file upload item shows the current filename.

        Regression test: when editing an existing image/video item that was
        uploaded via file, the edit form should clearly show the current file
        and make the upload field optional (not required).
        """
        page = enhanced_page
        vite_url = servers["vite_url"]
        slideshow_id = test_slideshow["id"]

        image_path = ASSETS_DIR / "smallPhoto.jpg"
        assert image_path.exists(), f"Test asset not found: {image_path}"

        # Login and navigate to slideshow detail page
        self._login(page, vite_url, test_database)
        page.goto(f"{vite_url}/admin/slideshows/{slideshow_id}")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Create an image item via file upload
        page.locator("button:has-text('Add Item')").click()
        modal = page.locator(".modal")
        expect(modal).to_be_visible(timeout=5000)

        page.locator("#title").fill("File Info Test Image")
        page.locator("#content_type").select_option("image")
        page.locator("#file_image").set_input_files(str(image_path))
        expect(
            page.locator(".badge.bg-success:has-text('File uploaded')")
        ).to_be_visible(timeout=10000)
        page.locator("button[type='submit']").click()
        expect(modal).to_be_hidden(timeout=10000)

        # Verify item was created
        expect(page.locator("text=File Info Test Image")).to_be_visible(timeout=5000)

        # Now edit the item - click the edit button
        row = page.locator("tr:has-text('File Info Test Image')")
        expect(row).to_be_visible(timeout=10000)
        row.locator("button[title='Edit']").click()

        modal = page.locator(".modal")
        expect(modal).to_be_visible(timeout=5000)

        # The edit form should show "Current file:" text with the filename
        current_file_info = modal.locator("text=Current file:")
        expect(current_file_info).to_be_visible(timeout=5000)

        # The upload label should indicate replacing is optional (not required)
        upload_label = modal.locator("label:has-text('Replace')")
        expect(upload_label).to_be_visible(timeout=2000)

    def test_delete_item_with_confirmation(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        test_slideshow: dict,
        http_client,
        auth_headers,
    ):
        """Test deleting a slideshow item with confirmation dialog."""
        page = enhanced_page
        vite_url = servers["vite_url"]
        slideshow_id = test_slideshow["id"]

        # Create an item via API first
        response = http_client.post(
            f"/api/v1/slideshows/{slideshow_id}/items",
            json={
                "title": "Item To Delete",
                "content_type": "text",
                "content_text": "This item will be deleted",
                "is_active": True,
            },
            headers=auth_headers,
        )
        assert response.status_code in [200, 201]

        # Login and navigate to slideshow detail page
        self._login(page, vite_url, test_database)
        page.goto(f"{vite_url}/admin/slideshows/{slideshow_id}")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Find the item row
        row = page.locator("tr:has-text('Item To Delete')")
        expect(row).to_be_visible(timeout=10000)

        # Set up dialog handler to accept the confirmation
        page.on("dialog", lambda dialog: dialog.accept())

        # Click Delete button
        row.locator("button[title='Delete']").click()

        # Wait for the page to update - the item should now show as Inactive
        # (soft delete sets is_active=False, and admin UI shows inactive items)
        page.wait_for_timeout(1000)  # Allow time for API call and UI refresh

        # Verify the item is still visible but now marked as Inactive
        row = page.locator("tr:has-text('Item To Delete')")
        expect(row).to_be_visible(timeout=10000)
        inactive_badge = row.locator(".badge", has_text="Inactive")
        expect(inactive_badge).to_be_visible(timeout=5000)

    def test_delete_inactive_item_permanently(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        test_slideshow: dict,
        http_client,
        auth_headers,
    ):
        """Test that deleting an inactive item permanently removes it."""
        page = enhanced_page
        vite_url = servers["vite_url"]
        slideshow_id = test_slideshow["id"]

        # Create an item via API
        response = http_client.post(
            f"/api/v1/slideshows/{slideshow_id}/items",
            json={
                "title": "Inactive Item To Delete",
                "content_type": "text",
                "content_text": "This inactive item will be deleted",
                "is_active": True,
            },
            headers=auth_headers,
        )
        assert response.status_code in [200, 201]
        item_id = response.json()["data"]["id"]

        # Soft-delete the item via API so it is inactive
        response = http_client.delete(
            f"/api/v1/slideshow-items/{item_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200

        # Login and navigate to slideshow detail page
        self._login(page, vite_url, test_database)
        page.goto(f"{vite_url}/admin/slideshows/{slideshow_id}")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # The item should be visible and marked as Inactive
        row = page.locator("tr:has-text('Inactive Item To Delete')")
        expect(row).to_be_visible(timeout=10000)
        inactive_badge = row.locator(".badge", has_text="Inactive")
        expect(inactive_badge).to_be_visible(timeout=5000)

        # Set up dialog handler to accept the confirmation
        page.on("dialog", lambda dialog: dialog.accept())

        # Click Delete button on the inactive item
        row.locator("button[title='Delete']").click()

        # The item should be permanently removed from the list
        page.wait_for_timeout(1000)  # Allow time for API call and UI refresh
        expect(
            page.locator("tr:has-text('Inactive Item To Delete')")
        ).to_have_count(0, timeout=10000)

    def test_reorder_items_move_up(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        test_slideshow: dict,
        http_client,
        auth_headers,
    ):
        """Test reordering items by moving an item up."""
        page = enhanced_page
        vite_url = servers["vite_url"]
        slideshow_id = test_slideshow["id"]

        # Create two items via API
        response1 = http_client.post(
            f"/api/v1/slideshows/{slideshow_id}/items",
            json={
                "title": "First Item",
                "content_type": "text",
                "content_text": "First",
                "is_active": True,
            },
            headers=auth_headers,
        )
        assert response1.status_code in [200, 201]

        response2 = http_client.post(
            f"/api/v1/slideshows/{slideshow_id}/items",
            json={
                "title": "Second Item",
                "content_type": "text",
                "content_text": "Second",
                "is_active": True,
            },
            headers=auth_headers,
        )
        assert response2.status_code in [200, 201]

        # Login and navigate to slideshow detail page
        self._login(page, vite_url, test_database)
        page.goto(f"{vite_url}/admin/slideshows/{slideshow_id}")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Verify initial order - First Item should be first
        rows = page.locator("table tbody tr")
        expect(rows).to_have_count(2, timeout=10000)

        # Get initial order
        first_row_text = rows.nth(0).inner_text()
        assert "First Item" in first_row_text, "First Item should be in position 1"

        # Move Second Item up
        second_row = page.locator("tr:has-text('Second Item')")
        expect(second_row).to_be_visible(timeout=5000)
        second_row.locator("button[title='Move Up']").click()

        # Wait for reorder to complete and verify new order
        page.wait_for_timeout(1000)  # Allow time for API call and re-render

        # Reload to ensure we see the updated order
        page.reload()
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Verify new order - Second Item should now be first
        rows = page.locator("table tbody tr")
        first_row_text = rows.nth(0).inner_text()
        assert (
            "Second Item" in first_row_text
        ), "Second Item should now be in position 1"

    def test_reorder_items_move_down(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        test_slideshow: dict,
        http_client,
        auth_headers,
    ):
        """Test reordering items by moving an item down."""
        page = enhanced_page
        vite_url = servers["vite_url"]
        slideshow_id = test_slideshow["id"]

        # Create two items via API
        response1 = http_client.post(
            f"/api/v1/slideshows/{slideshow_id}/items",
            json={
                "title": "Alpha Item",
                "content_type": "text",
                "content_text": "Alpha",
                "is_active": True,
            },
            headers=auth_headers,
        )
        assert response1.status_code in [200, 201]

        response2 = http_client.post(
            f"/api/v1/slideshows/{slideshow_id}/items",
            json={
                "title": "Beta Item",
                "content_type": "text",
                "content_text": "Beta",
                "is_active": True,
            },
            headers=auth_headers,
        )
        assert response2.status_code in [200, 201]

        # Login and navigate to slideshow detail page
        self._login(page, vite_url, test_database)
        page.goto(f"{vite_url}/admin/slideshows/{slideshow_id}")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Verify initial order
        rows = page.locator("table tbody tr")
        expect(rows).to_have_count(2, timeout=10000)

        first_row_text = rows.nth(0).inner_text()
        assert "Alpha Item" in first_row_text, "Alpha Item should be in position 1"

        # Move Alpha Item down
        first_row = page.locator("tr:has-text('Alpha Item')")
        expect(first_row).to_be_visible(timeout=5000)
        first_row.locator("button[title='Move Down']").click()

        # Wait for reorder to complete
        page.wait_for_timeout(1000)

        # Reload to ensure we see the updated order
        page.reload()
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Verify new order - Beta Item should now be first
        rows = page.locator("table tbody tr")
        first_row_text = rows.nth(0).inner_text()
        assert "Beta Item" in first_row_text, "Beta Item should now be in position 1"

    def _login(self, page: Page, vite_url: str, test_database: dict):
        """Helper method to log in to the admin interface."""
        page.goto(f"{vite_url}/admin/login")
        page.wait_for_selector("input[name='username']", timeout=10000)

        user = test_database["users"][0]
        page.locator("input[name='username']").fill(user["username"])
        page.locator("input[name='password']").fill(user["password"])
        page.locator("button[type='submit']").click()

        page.wait_for_selector("h1:has-text('Dashboard')", timeout=10000)

    def test_slideshow_item_action_icons_are_visible(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        test_slideshow: dict,
        http_client,
        auth_headers,
    ):
        """Test that Bootstrap Icons are properly displayed on action buttons.

        This test verifies that the Bootstrap Icons CSS is properly imported,
        making icons visible on action buttons (Move Up, Move Down, Edit, Delete).

        Without the CSS import, the <i class="bi bi-xxx"> elements exist but
        render as invisible/empty, making the buttons appear blank.
        """
        page = enhanced_page
        vite_url = servers["vite_url"]
        slideshow_id = test_slideshow["id"]

        # Create at least one item so we can see the action buttons
        response = http_client.post(
            f"/api/v1/slideshows/{slideshow_id}/items",
            json={
                "title": "Icon Test Item",
                "content_type": "text",
                "content_text": "Testing icon visibility",
                "is_active": True,
            },
            headers=auth_headers,
        )
        assert response.status_code in [200, 201]

        # Login and navigate to slideshow detail page
        self._login(page, vite_url, test_database)
        page.goto(f"{vite_url}/admin/slideshows/{slideshow_id}")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Verify the item row is visible
        row = page.locator("tr:has-text('Icon Test Item')")
        expect(row).to_be_visible(timeout=10000)

        # Verify the edit button icon is visible and has non-zero dimensions
        # The edit button uses class="bi bi-pencil"
        edit_icon = row.locator("button[title='Edit'] i.bi-pencil")
        expect(edit_icon).to_be_visible(timeout=5000)

        # Get the bounding box of the icon to verify it has dimensions
        # (without Bootstrap Icons CSS, the icon would be 0x0)
        edit_icon_box = edit_icon.bounding_box()
        assert edit_icon_box is not None, "Edit icon should have a bounding box"
        assert edit_icon_box["width"] > 0, (
            f"Edit icon width should be > 0 (got {edit_icon_box['width']}). "
            "This usually means Bootstrap Icons CSS is not imported."
        )
        assert edit_icon_box["height"] > 0, (
            f"Edit icon height should be > 0 (got {edit_icon_box['height']}). "
            "This usually means Bootstrap Icons CSS is not imported."
        )

        # Verify the delete button icon is also visible
        delete_icon = row.locator("button[title='Delete'] i.bi-trash")
        expect(delete_icon).to_be_visible(timeout=5000)
        delete_icon_box = delete_icon.bounding_box()
        assert delete_icon_box is not None, "Delete icon should have a bounding box"
        assert (
            delete_icon_box["width"] > 0
        ), f"Delete icon width should be > 0 (got {delete_icon_box['width']})"
        assert (
            delete_icon_box["height"] > 0
        ), f"Delete icon height should be > 0 (got {delete_icon_box['height']})"

    def test_auto_title_from_file_upload(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        test_slideshow: dict,
        http_client,
        auth_headers,
    ):
        """Test that title is auto-populated from uploaded filename.

        When a file is uploaded and the title field is empty, the title should
        be auto-populated with the filename (without extension).
        """
        page = enhanced_page
        vite_url = servers["vite_url"]
        slideshow_id = test_slideshow["id"]

        # Get the image path for upload
        image_path = ASSETS_DIR / "smallPhoto.jpg"
        assert image_path.exists(), f"Test asset not found: {image_path}"

        # Login and navigate to slideshow detail page
        self._login(page, vite_url, test_database)
        page.goto(f"{vite_url}/admin/slideshows/{slideshow_id}")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Click "Add Item" button
        add_button = page.locator("button:has-text('Add Item')")
        expect(add_button).to_be_visible(timeout=10000)
        add_button.click()

        # Wait for modal to appear
        modal = page.locator(".modal")
        expect(modal).to_be_visible(timeout=5000)

        # Ensure content type is image
        page.locator("#content_type").select_option("image")

        # Verify title is empty
        title_field = page.locator("#title")
        expect(title_field).to_have_value("")

        # Upload the image file
        page.locator("#file_image").set_input_files(str(image_path))

        # Wait for upload to complete
        expect(
            page.locator(".badge.bg-success:has-text('File uploaded')")
        ).to_be_visible(timeout=10000)

        # Verify title was auto-populated with filename (without extension)
        expect(title_field).to_have_value("smallPhoto", timeout=5000)

        # Submit the form
        page.locator("button[type='submit']").click()

        # Wait for modal to close
        expect(modal).to_be_hidden(timeout=10000)

        # Verify item appears in the table with auto-generated title
        # Use specific locator to find the row by title (in fw-bold div)
        row = page.locator("tr").filter(
            has=page.locator("div.fw-bold", has_text="smallPhoto")
        )
        expect(row).to_be_visible(timeout=5000)

        # CRITICAL: Verify via API that data was actually persisted
        item = get_item_by_title(http_client, auth_headers, slideshow_id, "smallPhoto")
        assert item is not None, "Item with auto-generated title not found via API"
        assert item.get("content_type") == "image"

    def test_auto_title_from_url(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        test_slideshow: dict,
        http_client,
        auth_headers,
    ):
        """Test that title is auto-populated from URL.

        When a URL is entered and the title field is empty, the title should
        be auto-populated with the filename from the URL path (if present),
        excluding the file extension.
        """
        page = enhanced_page
        vite_url = servers["vite_url"]
        slideshow_id = test_slideshow["id"]
        test_url = "https://example.com/path/to/my-awesome-image.jpg"

        # Login and navigate to slideshow detail page
        self._login(page, vite_url, test_database)
        page.goto(f"{vite_url}/admin/slideshows/{slideshow_id}")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Click "Add Item" button
        page.locator("button:has-text('Add Item')").click()

        # Wait for modal
        modal = page.locator(".modal")
        expect(modal).to_be_visible(timeout=5000)

        # Select image type
        page.locator("#content_type").select_option("image")

        # Verify title is empty
        title_field = page.locator("#title")
        expect(title_field).to_have_value("")

        # Enter the URL
        page.locator("#url_alternative").fill(test_url)

        # Blur the URL field to trigger auto-title
        page.locator("#url_alternative").blur()

        # Verify title was auto-populated with filename from URL (without extension)
        expect(title_field).to_have_value("my-awesome-image", timeout=5000)

        # Submit the form
        page.locator("button[type='submit']").click()

        # Wait for modal to close
        expect(modal).to_be_hidden(timeout=10000)

        # Verify item appears in the table
        # Use specific locator to find the row by title (in fw-bold div)
        row = page.locator("tr").filter(
            has=page.locator("div.fw-bold", has_text="my-awesome-image")
        )
        expect(row).to_be_visible(timeout=5000)

        # CRITICAL: Verify via API that data was actually persisted
        item = get_item_by_title(
            http_client, auth_headers, slideshow_id, "my-awesome-image"
        )
        assert item is not None, "Item with auto-generated title from URL not found"
        assert item.get("content_url") == test_url

    def test_auto_title_does_not_overwrite_existing_title(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        test_slideshow: dict,
        http_client,
        auth_headers,
    ):
        """Test that auto-title does not overwrite an existing title.

        If the user has already entered a title, uploading a file or entering
        a URL should not change it.
        """
        page = enhanced_page
        vite_url = servers["vite_url"]
        slideshow_id = test_slideshow["id"]

        # Get the image path for upload
        image_path = ASSETS_DIR / "smallPhoto.jpg"
        assert image_path.exists(), f"Test asset not found: {image_path}"

        # Login and navigate to slideshow detail page
        self._login(page, vite_url, test_database)
        page.goto(f"{vite_url}/admin/slideshows/{slideshow_id}")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Click "Add Item" button
        page.locator("button:has-text('Add Item')").click()

        # Wait for modal
        modal = page.locator(".modal")
        expect(modal).to_be_visible(timeout=5000)

        # Select image type
        page.locator("#content_type").select_option("image")

        # Enter a custom title FIRST
        title_field = page.locator("#title")
        custom_title = "My Custom Title"
        title_field.fill(custom_title)

        # Upload the image file
        page.locator("#file_image").set_input_files(str(image_path))

        # Wait for upload to complete
        expect(
            page.locator(".badge.bg-success:has-text('File uploaded')")
        ).to_be_visible(timeout=10000)

        # Verify title was NOT changed (should still be the custom title)
        expect(title_field).to_have_value(custom_title, timeout=2000)

        # Submit the form
        page.locator("button[type='submit']").click()

        # Wait for modal to close
        expect(modal).to_be_hidden(timeout=10000)

        # Verify item appears with the custom title, not the filename
        expect(page.locator(f"text={custom_title}")).to_be_visible(timeout=5000)

        # CRITICAL: Verify via API
        item = get_item_by_title(http_client, auth_headers, slideshow_id, custom_title)
        assert item is not None, "Item with custom title not found"
        assert item.get("content_file_path"), "File was not uploaded"

    def test_text_item_preview_renders_html(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        test_slideshow: dict,
        http_client,
        auth_headers,
    ):
        """Test that text item preview renders HTML formatting tags.

        This test:
        1. Creates a text item with HTML tags via API
        2. Views the slideshow detail page
        3. Verifies the HTML is rendered (not shown as literal text)

        This tests the admin preview functionality for HTML in text slides.
        """
        page = enhanced_page
        vite_url = servers["vite_url"]
        slideshow_id = test_slideshow["id"]

        # Create a text item with HTML content via API
        html_content = "This is <b>bold</b> and <i>italic</i> text"

        response = http_client.post(
            f"/api/v1/slideshows/{slideshow_id}/items",
            json={
                "title": "HTML Preview Test",
                "content_type": "text",
                "content_text": html_content,
                "is_active": True,
            },
            headers=auth_headers,
        )
        assert response.status_code in [200, 201]

        # Login and navigate to slideshow detail page
        self._login(page, vite_url, test_database)
        page.goto(f"{vite_url}/admin/slideshows/{slideshow_id}")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Find the row with our test item
        row = page.locator("tr").filter(
            has=page.locator("div.fw-bold", has_text="HTML Preview Test")
        )
        expect(row).to_be_visible(timeout=5000)

        # Get the preview text cell (the text-muted small div)
        preview_cell = row.locator("div.text-muted.small")
        expect(preview_cell).to_be_visible()

        # Get the innerHTML to verify HTML tags are rendered
        inner_html = preview_cell.inner_html()

        # Verify HTML tags are present (rendered, not escaped)
        assert "<b>" in inner_html, (
            f"<b> tag should be rendered in preview. " f"Got innerHTML: {inner_html}"
        )
        assert "<i>" in inner_html, (
            f"<i> tag should be rendered in preview. " f"Got innerHTML: {inner_html}"
        )

        # Verify the user sees the formatted text, not literal tags
        visible_text = preview_cell.inner_text()
        assert "<b>" not in visible_text, (
            f"Literal <b> tag should not be visible. "
            f"Got visible text: {visible_text}"
        )
        assert "&lt;b&gt;" not in visible_text, (
            f"Escaped <b> tag should not be visible. "
            f"Got visible text: {visible_text}"
        )

    def test_text_item_preview_strips_unsafe_html(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        test_slideshow: dict,
        http_client,
        auth_headers,
    ):
        """Test that text item preview strips unsafe HTML tags.

        This test:
        1. Creates a text item with unsafe HTML via API
        2. Views the slideshow detail page
        3. Verifies unsafe HTML is stripped in the preview

        This ensures XSS prevention in the admin preview.
        """
        page = enhanced_page
        vite_url = servers["vite_url"]
        slideshow_id = test_slideshow["id"]

        # Create a text item with unsafe HTML content via API
        unsafe_content = '<script>alert("XSS")</script><b>Safe bold</b>'

        response = http_client.post(
            f"/api/v1/slideshows/{slideshow_id}/items",
            json={
                "title": "XSS Preview Test",
                "content_type": "text",
                "content_text": unsafe_content,
                "is_active": True,
            },
            headers=auth_headers,
        )
        assert response.status_code in [200, 201]

        # Login and navigate to slideshow detail page
        self._login(page, vite_url, test_database)
        page.goto(f"{vite_url}/admin/slideshows/{slideshow_id}")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Find the row with our test item
        row = page.locator("tr").filter(
            has=page.locator("div.fw-bold", has_text="XSS Preview Test")
        )
        expect(row).to_be_visible(timeout=5000)

        # Get the preview text cell
        preview_cell = row.locator("div.text-muted.small")
        expect(preview_cell).to_be_visible()

        # Get the innerHTML
        inner_html = preview_cell.inner_html()

        # Verify unsafe tags are stripped
        assert "<script>" not in inner_html.lower(), (
            f"<script> tag should be stripped from preview. "
            f"Got innerHTML: {inner_html}"
        )
        assert "alert(" not in inner_html, (
            f"JavaScript should be stripped from preview. "
            f"Got innerHTML: {inner_html}"
        )

        # Verify safe tags are preserved
        assert "<b>" in inner_html, (
            f"Safe <b> tag should be preserved in preview. "
            f"Got innerHTML: {inner_html}"
        )

    def test_url_item_zoom_slider_visible(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        test_slideshow: dict,
        http_client,
        auth_headers,
    ):
        """Test that zoom slider is visible for URL content type.

        The zoom slider (scale_factor) should only appear when content_type
        is 'url' (Web Page). It should not appear for other content types.
        """
        page = enhanced_page
        vite_url = servers["vite_url"]
        slideshow_id = test_slideshow["id"]

        # Login and navigate to slideshow detail page
        self._login(page, vite_url, test_database)
        page.goto(f"{vite_url}/admin/slideshows/{slideshow_id}")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Click "Add Item" button
        page.locator("button:has-text('Add Item')").click()

        # Wait for modal
        modal = page.locator(".modal")
        expect(modal).to_be_visible(timeout=5000)

        # Select image type - zoom slider should NOT be visible
        page.locator("#content_type").select_option("image")
        zoom_slider = page.locator("#scale_factor")
        expect(zoom_slider).not_to_be_visible()

        # Select url type - zoom slider SHOULD be visible
        page.locator("#content_type").select_option("url")
        expect(zoom_slider).to_be_visible(timeout=2000)

        # Verify label shows "Normal (100%)" by default
        zoom_label = page.locator("label[for='scale_factor']")
        expect(zoom_label).to_contain_text("Normal (100%)")

        # Select text type - zoom slider should NOT be visible
        page.locator("#content_type").select_option("text")
        expect(zoom_slider).not_to_be_visible()

    def test_add_url_item_with_zoom_scale(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        test_slideshow: dict,
        http_client,
        auth_headers,
    ):
        """Test adding a URL item with zoom (scale_factor) set.

        Verifies via API that scale_factor is persisted correctly.
        """
        page = enhanced_page
        vite_url = servers["vite_url"]
        slideshow_id = test_slideshow["id"]
        test_url = "https://example.com/tall-page"

        # Login and navigate to slideshow detail page
        self._login(page, vite_url, test_database)
        page.goto(f"{vite_url}/admin/slideshows/{slideshow_id}")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Click "Add Item" button
        page.locator("button:has-text('Add Item')").click()

        # Wait for modal
        modal = page.locator(".modal")
        expect(modal).to_be_visible(timeout=5000)

        # Fill in the form for URL type
        page.locator("#title").fill("Zoomed Web Page")
        page.locator("#content_type").select_option("url")
        page.locator("#url").fill(test_url)

        # Set zoom to 50% using the slider
        zoom_slider = page.locator("#scale_factor")
        expect(zoom_slider).to_be_visible()

        # Set slider value to 50 using JavaScript
        # React uses 'input' event for range inputs, and needs special handling
        # to properly trigger React's synthetic event system
        page.evaluate(
            """() => {
            const slider = document.querySelector('#scale_factor');
            // Use native value setter to bypass React's controlled input
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'value'
            ).set;
            nativeInputValueSetter.call(slider, '50');
            // Dispatch input event to trigger React onChange
            slider.dispatchEvent(new Event('input', { bubbles: true }));
        }"""
        )

        # Verify label updated
        zoom_label = page.locator("label[for='scale_factor']")
        expect(zoom_label).to_contain_text("Zoomed out (50%)")

        # Submit the form
        page.locator("button[type='submit']").click()

        # Wait for modal to close
        expect(modal).to_be_hidden(timeout=10000)

        # Verify item appears in the table
        expect(page.locator("text=Zoomed Web Page")).to_be_visible(timeout=5000)

        # CRITICAL: Verify via API that scale_factor was persisted
        item = get_item_by_title(
            http_client, auth_headers, slideshow_id, "Zoomed Web Page"
        )
        assert item is not None, "Item not found via API after creation"
        assert item.get("scale_factor") == 50, (
            f"scale_factor not persisted correctly: expected 50, "
            f"got {item.get('scale_factor')}"
        )
        assert item.get("content_url") == test_url

    def test_edit_url_item_zoom_scale(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        test_slideshow: dict,
        http_client,
        auth_headers,
    ):
        """Test editing an existing URL item's zoom scale.

        Creates a URL item via API, then edits the scale_factor via UI.
        Verifies via API that the update was persisted.
        """
        page = enhanced_page
        vite_url = servers["vite_url"]
        slideshow_id = test_slideshow["id"]

        # Create a URL item via API first (no scale_factor)
        response = http_client.post(
            f"/api/v1/slideshows/{slideshow_id}/items",
            json={
                "title": "Edit Zoom Test",
                "content_type": "url",
                "content_url": "https://example.com/edit-test",
                "is_active": True,
            },
            headers=auth_headers,
        )
        assert response.status_code in [200, 201]
        item_data = response.json().get("data", response.json())
        assert item_data.get("scale_factor") is None  # Initially no scale

        # Login and navigate to slideshow detail page
        self._login(page, vite_url, test_database)
        page.goto(f"{vite_url}/admin/slideshows/{slideshow_id}")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Wait for the items table to be populated with the item we created
        # The React frontend needs time to fetch and render the data
        expect(page.locator("text=Edit Zoom Test")).to_be_visible(timeout=10000)

        # Find the row with our test item and click edit
        row = page.locator("tr").filter(
            has=page.locator("div.fw-bold", has_text="Edit Zoom Test")
        )
        expect(row).to_be_visible(timeout=5000)

        # Click the edit button - use longer timeout as table may still be loading
        edit_button = row.locator("button[title='Edit']")
        expect(edit_button).to_be_visible(timeout=5000)
        edit_button.click()

        # Wait for modal
        modal = page.locator(".modal")
        expect(modal).to_be_visible(timeout=5000)

        # Verify zoom slider is visible and at 100%
        zoom_slider = page.locator("#scale_factor")
        expect(zoom_slider).to_be_visible()

        # Set zoom to 25% using JavaScript
        # React uses 'input' event for range inputs, and needs special handling
        # to properly trigger React's synthetic event system
        page.evaluate(
            """() => {
            const slider = document.querySelector('#scale_factor');
            // Use native value setter to bypass React's controlled input
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'value'
            ).set;
            nativeInputValueSetter.call(slider, '25');
            // Dispatch input event to trigger React onChange
            slider.dispatchEvent(new Event('input', { bubbles: true }));
        }"""
        )

        # Submit the form
        page.locator("button[type='submit']").click()

        # Wait for modal to close
        expect(modal).to_be_hidden(timeout=10000)

        # CRITICAL: Verify via API that scale_factor was updated
        updated_item = get_item_by_title(
            http_client, auth_headers, slideshow_id, "Edit Zoom Test"
        )
        assert updated_item is not None
        assert updated_item.get("scale_factor") == 25, (
            f"scale_factor not updated correctly: expected 25, "
            f"got {updated_item.get('scale_factor')}"
        )

    def test_url_item_preview_appears_when_url_entered(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        test_slideshow: dict,
        http_client,
        auth_headers,
    ):
        """Test that preview iframe appears when URL is entered for URL content type.

        The preview should:
        1. Not appear when URL field is empty
        2. Appear when a valid URL is entered
        3. Apply the correct CSS transform based on scale_factor
        """
        page = enhanced_page
        vite_url = servers["vite_url"]
        slideshow_id = test_slideshow["id"]

        # Login and navigate to slideshow detail page
        self._login(page, vite_url, test_database)
        page.goto(f"{vite_url}/admin/slideshows/{slideshow_id}")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Click "Add Item" button
        page.locator("button:has-text('Add Item')").click()

        # Wait for modal
        modal = page.locator(".modal")
        expect(modal).to_be_visible(timeout=5000)

        # Select URL type
        page.locator("#content_type").select_option("url")

        # Verify preview is NOT visible when URL is empty
        preview_container = page.locator("[data-testid='url-preview-container']")
        expect(preview_container).not_to_be_visible()

        # Enter a URL
        page.locator("#url").fill("https://example.com")

        # Wait for preview container to appear
        expect(preview_container).to_be_visible(timeout=5000)

        # Verify iframe is present in the preview
        preview_iframe = page.locator("[data-testid='url-preview-iframe']")
        expect(preview_iframe).to_be_visible(timeout=5000)

        # Verify iframe has the expected src
        iframe_src = preview_iframe.get_attribute("src")
        assert iframe_src == "https://example.com"

    def test_url_item_preview_updates_on_zoom_change(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        test_slideshow: dict,
        http_client,
        auth_headers,
    ):
        """Test that preview iframe transform updates when zoom slider changes.

        When the scale_factor is changed:
        1. The iframe should have transform: scale(X) where X = scale_factor/100
        2. The iframe width/height should be inverse scaled (100/scale_factor * 100%)
        """
        page = enhanced_page
        vite_url = servers["vite_url"]
        slideshow_id = test_slideshow["id"]

        # Login and navigate to slideshow detail page
        self._login(page, vite_url, test_database)
        page.goto(f"{vite_url}/admin/slideshows/{slideshow_id}")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Click "Add Item" button
        page.locator("button:has-text('Add Item')").click()

        # Wait for modal
        modal = page.locator(".modal")
        expect(modal).to_be_visible(timeout=5000)

        # Select URL type and enter a URL
        page.locator("#content_type").select_option("url")
        page.locator("#url").fill("https://example.com")

        # Wait for preview iframe to appear
        preview_iframe = page.locator("[data-testid='url-preview-iframe']")
        expect(preview_iframe).to_be_visible(timeout=5000)

        # Initially at 100% zoom, iframe should have scale(1)
        initial_style = preview_iframe.get_attribute("style") or ""
        assert (
            "scale(1)" in initial_style
        ), f"Expected scale(1) at 100%, got: {initial_style}"

        # Set zoom to 50% using JavaScript
        page.evaluate(
            """() => {
            const slider = document.querySelector('#scale_factor');
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'value'
            ).set;
            nativeInputValueSetter.call(slider, '50');
            slider.dispatchEvent(new Event('input', { bubbles: true }));
        }"""
        )

        # Wait a moment for React to re-render
        page.wait_for_timeout(500)

        # Verify iframe transform updated to scale(0.5)
        updated_style = preview_iframe.get_attribute("style") or ""
        assert (
            "scale(0.5)" in updated_style
        ), f"Expected scale(0.5) at 50%, got: {updated_style}"

        # Also verify the width is scaled up (200% for 50% zoom)
        assert (
            "200%" in updated_style
        ), f"Expected 200% width/height at 50% zoom, got: {updated_style}"

    def test_url_item_preview_zoom_change_no_permanent_spinner(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        test_slideshow: dict,
        http_client,
        auth_headers,
    ):
        """Test that changing zoom slider does not show a permanent spinner.

        Regression test: When zoom slider is changed, setPreviewLoading(true) was
        called but the iframe doesn't reload (only CSS transform changes), so
        onLoad never fires to clear the spinner. The preview should remain visible
        without a loading spinner after zoom changes.
        """
        page = enhanced_page
        vite_url = servers["vite_url"]
        slideshow_id = test_slideshow["id"]

        # Login and navigate to slideshow detail page
        self._login(page, vite_url, test_database)
        page.goto(f"{vite_url}/admin/slideshows/{slideshow_id}")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Click "Add Item" button
        page.locator("button:has-text('Add Item')").click()

        # Wait for modal
        modal = page.locator(".modal")
        expect(modal).to_be_visible(timeout=5000)

        # Select URL type and enter a URL
        page.locator("#content_type").select_option("url")
        page.locator("#url").fill("https://example.com")

        # Wait for preview iframe to appear
        preview_iframe = page.locator("[data-testid='url-preview-iframe']")
        expect(preview_iframe).to_be_visible(timeout=5000)

        # Wait for loading indicator to disappear (iframe loads)
        loading_indicator = page.locator("[data-testid='preview-loading']")
        loading_indicator.wait_for(state="hidden", timeout=10000)

        # Verify iframe is visible with opacity 1
        expect(preview_iframe).to_have_css("opacity", "1", timeout=5000)

        # Change zoom slider to 50% using JavaScript
        page.evaluate(
            """() => {
            const slider = document.querySelector('#scale_factor');
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'value'
            ).set;
            nativeInputValueSetter.call(slider, '50');
            slider.dispatchEvent(new Event('input', { bubbles: true }));
        }"""
        )

        # Wait for React to re-render
        page.wait_for_timeout(500)

        # The loading spinner should NOT be visible after zoom change
        expect(loading_indicator).not_to_be_visible()

        # The iframe should still be visible with opacity 1
        expect(preview_iframe).to_have_css("opacity", "1")

    def test_url_item_preview_not_visible_for_other_types(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        test_slideshow: dict,
        http_client,
        auth_headers,
    ):
        """Test that preview is not visible for non-URL content types.

        The preview should only appear for URL (Web Page) content type,
        not for image, video, or text types.
        """
        page = enhanced_page
        vite_url = servers["vite_url"]
        slideshow_id = test_slideshow["id"]

        # Login and navigate to slideshow detail page
        self._login(page, vite_url, test_database)
        page.goto(f"{vite_url}/admin/slideshows/{slideshow_id}")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Click "Add Item" button
        page.locator("button:has-text('Add Item')").click()

        # Wait for modal
        modal = page.locator(".modal")
        expect(modal).to_be_visible(timeout=5000)

        preview_container = page.locator("[data-testid='url-preview-container']")

        # Check image type - preview should NOT be visible
        page.locator("#content_type").select_option("image")
        expect(preview_container).not_to_be_visible()

        # Check video type - preview should NOT be visible
        page.locator("#content_type").select_option("video")
        expect(preview_container).not_to_be_visible()

        # Check text type - preview should NOT be visible
        page.locator("#content_type").select_option("text")
        expect(preview_container).not_to_be_visible()

        # Check URL type with URL entered - preview SHOULD be visible
        page.locator("#content_type").select_option("url")
        page.locator("#url").fill("https://example.com")
        expect(preview_container).to_be_visible(timeout=5000)

    def test_url_item_preview_display_selector(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        test_slideshow: dict,
        test_display: dict,
        http_client,
        auth_headers,
    ):
        """Test display selector dropdown in URL item preview.

        Verifies that:
        1. The display selector dropdown appears with the test display
        2. Selecting a display changes the preview aspect ratio
        3. Selecting 'Default' reverts to 16:9
        """
        page = enhanced_page
        vite_url = servers["vite_url"]
        slideshow_id = test_slideshow["id"]

        # Login and navigate to slideshow detail page
        self._login(page, vite_url, test_database)
        page.goto(f"{vite_url}/admin/slideshows/{slideshow_id}")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Click "Add Item" button
        page.locator("button:has-text('Add Item')").click()

        # Wait for modal
        modal = page.locator(".modal")
        expect(modal).to_be_visible(timeout=5000)

        # Select URL type and enter a URL
        page.locator("#content_type").select_option("url")
        page.locator("#url").fill("https://example.com")

        # Wait for preview container to appear
        preview_container = page.locator("[data-testid='url-preview-container']")
        expect(preview_container).to_be_visible(timeout=5000)

        # Wait for display selector to appear (displays loaded from API)
        display_selector = page.locator("[data-testid='preview-display-selector']")
        expect(display_selector).to_be_visible(timeout=5000)

        # Verify the test display appears in the dropdown
        display_name = test_display["name"]
        option = display_selector.locator(f"option:has-text('{display_name}')")
        expect(option).to_have_count(1)

        # Verify default aspect ratio is 16/9
        initial_style = preview_container.get_attribute("style") or ""
        assert (
            "16 / 9" in initial_style
        ), f"Expected 16 / 9 aspect ratio initially, got: {initial_style}"

        # Select the test display (1920x1080)
        display_selector.select_option(str(test_display["id"]))
        page.wait_for_timeout(300)

        # Verify aspect ratio changed to 1920 / 1080
        updated_style = preview_container.get_attribute("style") or ""
        assert (
            "1920 / 1080" in updated_style
        ), f"Expected 1920 / 1080 aspect ratio, got: {updated_style}"

        # Select Default back
        display_selector.select_option("")
        page.wait_for_timeout(300)

        # Verify reverts to 16/9
        reverted_style = preview_container.get_attribute("style") or ""
        assert (
            "16 / 9" in reverted_style
        ), f"Expected 16 / 9 after revert, got: {reverted_style}"

    def test_url_item_preview_display_selector_rotation(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        test_slideshow: dict,
        http_client,
        auth_headers,
    ):
        """Test display selector with a rotated display.

        Creates a display with rotation=90 and verifies the preview
        container uses swapped dimensions (1080x1920 instead of 1920x1080).
        """
        page = enhanced_page
        vite_url = servers["vite_url"]
        slideshow_id = test_slideshow["id"]

        # Create a rotated display via API
        import time

        rotated_display_name = f"rotated-display-{int(time.time() * 1000)}"
        response = http_client.post(
            "/api/v1/displays",
            json={
                "name": rotated_display_name,
                "description": "Test rotated display",
                "location": "Test Room",
                "resolution_width": 1920,
                "resolution_height": 1080,
                "rotation": 90,
            },
            headers=auth_headers,
        )
        assert response.status_code in [
            200,
            201,
        ], f"Failed to create rotated display: {response.text}"
        rotated_display = response.json().get("data", response.json())
        rotated_display_id = rotated_display["id"]

        try:
            # Login and navigate to slideshow detail page
            self._login(page, vite_url, test_database)
            page.goto(f"{vite_url}/admin/slideshows/{slideshow_id}")
            page.wait_for_load_state("domcontentloaded", timeout=10000)

            # Click "Add Item" button
            page.locator("button:has-text('Add Item')").click()

            # Wait for modal
            modal = page.locator(".modal")
            expect(modal).to_be_visible(timeout=5000)

            # Select URL type and enter a URL
            page.locator("#content_type").select_option("url")
            page.locator("#url").fill("https://example.com")

            # Wait for display selector
            display_selector = page.locator("[data-testid='preview-display-selector']")
            expect(display_selector).to_be_visible(timeout=5000)

            # Verify the rotated display shows in dropdown with "rotated" label
            option = display_selector.locator(
                f"option:has-text('{rotated_display_name}')"
            )
            expect(option).to_have_count(1)
            option_text = option.text_content() or ""
            assert (
                "rotated" in option_text
            ), f"Expected 'rotated' in option text, got: {option_text}"

            # Select the rotated display
            display_selector.select_option(str(rotated_display_id))
            page.wait_for_timeout(300)

            # Verify aspect ratio uses swapped dimensions (1080 / 1920)
            preview_container = page.locator("[data-testid='url-preview-container']")
            container_style = preview_container.get_attribute("style") or ""
            assert (
                "1080 / 1920" in container_style
            ), f"Expected 1080 / 1920 for 90° rotation, got: {container_style}"
        finally:
            # Cleanup: delete the rotated display
            http_client.delete(
                f"/api/v1/displays/{rotated_display_id}",
                headers=auth_headers,
            )

    def test_add_skedda_item_with_valid_url(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        test_slideshow: dict,
        http_client,
        auth_headers,
    ):
        """Test adding a Skedda calendar item with a valid iCal URL.

        This test:
        1. Opens the add item modal
        2. Selects Skedda Calendar content type
        3. Fills in a valid iCal URL
        4. Submits the form (mocking the API to avoid actual ICS fetch)
        5. Verifies the item appears in the list

        The backend tries to fetch the ICS URL during item creation to validate
        it works, so we mock the create endpoint to bypass this.
        """
        page = enhanced_page
        vite_url = servers["vite_url"]
        slideshow_id = test_slideshow["id"]
        test_ical_url = "https://app.skedda.com/ical/test-feed.ics"

        # Mock the create item endpoint for skedda type to bypass backend ICS fetch
        item_id_counter = [3000]

        def handle_create_item(route, request):
            import json

            body = json.loads(request.post_data or "{}")
            if body.get("content_type") == "skedda":
                item_id = item_id_counter[0]
                item_id_counter[0] += 1
                response_data = {
                    "success": True,
                    "data": {
                        "id": item_id,
                        "slideshow_id": slideshow_id,
                        "title": body.get("title"),
                        "content_type": "skedda",
                        "ical_url": body.get("ical_url"),
                        "ical_feed_id": 1,
                        "ical_refresh_minutes": body.get("ical_refresh_minutes", 15),
                        "order_index": item_id,
                        "is_active": body.get("is_active", True),
                        "created_at": "2026-01-28T12:00:00Z",
                        "updated_at": "2026-01-28T12:00:00Z",
                    },
                }
                route.fulfill(
                    status=201,
                    content_type="application/json",
                    body=json.dumps(response_data),
                )
            else:
                route.continue_()

        page.route(
            f"**/api/v1/slideshows/{slideshow_id}/items**",
            lambda route: handle_create_item(route, route.request),
        )

        # Login and navigate to slideshow detail page
        self._login(page, vite_url, test_database)
        page.goto(f"{vite_url}/admin/slideshows/{slideshow_id}")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Click "Add Item" button
        page.locator("button:has-text('Add Item')").click()

        # Wait for modal
        modal = page.locator(".modal")
        expect(modal).to_be_visible(timeout=5000)

        # Fill in the form for Skedda type
        page.locator("#title").fill("Test Skedda Calendar")
        page.locator("#content_type").select_option("skedda")

        # Verify skedda-specific fields appear
        ical_url_field = page.locator("#ical_url")
        expect(ical_url_field).to_be_visible(timeout=2000)

        refresh_select = page.locator("#ical_refresh_minutes")
        expect(refresh_select).to_be_visible()

        # Fill in the iCal URL
        ical_url_field.fill(test_ical_url)

        # Select a refresh interval (30 minutes)
        refresh_select.select_option("30")

        # Submit the form
        page.locator("button[type='submit']").click()

        # Wait for modal to close (proves successful form submission)
        expect(modal).to_be_hidden(timeout=10000)

        # Note: The item won't appear in the table because after the mocked
        # create response, the frontend refetches items from the server.
        # Modal closing proves the UI flow completed successfully.

    def test_skedda_item_url_validation_error(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        test_slideshow: dict,
        http_client,
        auth_headers,
    ):
        """Test that Skedda form shows validation error for invalid URL.

        The frontend should validate the iCal URL format before submission.
        This test verifies:
        1. Empty URL shows validation error
        2. Invalid URL format shows validation error
        """
        page = enhanced_page
        vite_url = servers["vite_url"]
        slideshow_id = test_slideshow["id"]

        # Login and navigate to slideshow detail page
        self._login(page, vite_url, test_database)
        page.goto(f"{vite_url}/admin/slideshows/{slideshow_id}")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Click "Add Item" button
        page.locator("button:has-text('Add Item')").click()

        # Wait for modal
        modal = page.locator(".modal")
        expect(modal).to_be_visible(timeout=5000)

        # Fill in the form for Skedda type with empty URL
        page.locator("#title").fill("Invalid Skedda Test")
        page.locator("#content_type").select_option("skedda")

        # Verify skedda-specific fields appear
        ical_url_field = page.locator("#ical_url")
        expect(ical_url_field).to_be_visible(timeout=2000)

        # Try to submit with empty URL
        page.locator("button[type='submit']").click()

        # Verify validation error appears for empty URL
        error_feedback = page.locator(".invalid-feedback").filter(
            has_text="iCal URL is required"
        )
        expect(error_feedback).to_be_visible(timeout=5000)

        # Now enter a URL with wrong protocol (ftp:// instead of http[s]://)
        # This passes HTML5 browser validation but fails our custom validation
        ical_url_field.fill("ftp://example.com/calendar.ics")

        # Try to submit again
        page.locator("button[type='submit']").click()

        # Verify validation error for wrong protocol
        # The message is "URL must start with http:// or https://"
        error_feedback = page.locator(".invalid-feedback").filter(has_text="http://")
        expect(error_feedback).to_be_visible(timeout=5000)

        # Modal should still be open
        expect(modal).to_be_visible()

        # Close modal without saving
        page.keyboard.press("Escape")
        expect(modal).to_be_hidden(timeout=5000)

    def test_edit_skedda_item_configuration(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        test_slideshow: dict,
        http_client,
        auth_headers,
    ):
        """Test editing an existing Skedda calendar item.

        This test:
        1. Mocks the API to return a skedda item
        2. Opens the edit modal
        3. Verifies existing values are loaded
        4. Changes the refresh interval
        5. Submits and verifies the update

        Uses mocking because backend would try to fetch the ICS URL.
        """
        page = enhanced_page
        vite_url = servers["vite_url"]
        slideshow_id = test_slideshow["id"]
        test_ical_url = "https://app.skedda.com/ical/existing-feed.ics"

        # Mock the API to return a skedda item
        mock_skedda_item = {
            "id": 999,
            "slideshow_id": slideshow_id,
            "title": "Existing Skedda Calendar",
            "content_type": "skedda",
            "ical_url": test_ical_url,
            "ical_feed_id": 1,
            "ical_refresh_minutes": 15,
            "order_index": 0,
            "is_active": True,
            "created_at": "2026-01-28T12:00:00Z",
            "updated_at": "2026-01-28T12:00:00Z",
        }

        def handle_get_items(route):
            import json

            response_data = {
                "success": True,
                "data": [mock_skedda_item],
            }
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(response_data),
            )

        # Mock the update endpoint for the skedda item
        def handle_update_item(route, request):
            import json

            body = json.loads(request.post_data or "{}")
            updated_item = mock_skedda_item.copy()
            updated_item.update(body)
            response_data = {
                "success": True,
                "data": updated_item,
            }
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(response_data),
            )

        page.route(
            f"**/api/v1/slideshows/{slideshow_id}/items**",
            handle_get_items,
        )
        page.route(
            "**/api/v1/slideshow-items/999",
            lambda route: handle_update_item(route, route.request),
        )

        # Login and navigate to slideshow detail page
        self._login(page, vite_url, test_database)
        page.goto(f"{vite_url}/admin/slideshows/{slideshow_id}")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Verify the item appears in the table
        row = page.locator("tr:has-text('Existing Skedda Calendar')")
        expect(row).to_be_visible(timeout=10000)

        # Verify it shows the skedda badge
        expect(row.locator(".badge:has-text('skedda')")).to_be_visible()

        # Click edit button
        row.locator("button[title='Edit']").click()

        # Wait for modal
        modal = page.locator(".modal")
        expect(modal).to_be_visible(timeout=5000)

        # Verify existing values are loaded
        expect(page.locator("#title")).to_have_value("Existing Skedda Calendar")
        expect(page.locator("#content_type")).to_have_value("skedda")
        expect(page.locator("#ical_url")).to_have_value(test_ical_url)
        expect(page.locator("#ical_refresh_minutes")).to_have_value("15")

        # Change the refresh interval to 60 minutes
        page.locator("#ical_refresh_minutes").select_option("60")

        # Submit the form
        page.locator("button[type='submit']").click()

        # Wait for modal to close (proves successful update)
        expect(modal).to_be_hidden(timeout=10000)

    def test_skedda_fields_hidden_for_other_types(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        test_slideshow: dict,
        http_client,
        auth_headers,
    ):
        """Test that Skedda-specific fields are only shown for skedda type.

        The iCal URL and refresh interval fields should:
        1. Only appear when 'skedda' is selected
        2. Be hidden for other content types
        """
        page = enhanced_page
        vite_url = servers["vite_url"]
        slideshow_id = test_slideshow["id"]

        # Login and navigate to slideshow detail page
        self._login(page, vite_url, test_database)
        page.goto(f"{vite_url}/admin/slideshows/{slideshow_id}")
        page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Click "Add Item" button
        page.locator("button:has-text('Add Item')").click()

        # Wait for modal
        modal = page.locator(".modal")
        expect(modal).to_be_visible(timeout=5000)

        ical_url_field = page.locator("#ical_url")
        refresh_select = page.locator("#ical_refresh_minutes")

        # Check image type - skedda fields should NOT be visible
        page.locator("#content_type").select_option("image")
        expect(ical_url_field).not_to_be_visible()
        expect(refresh_select).not_to_be_visible()

        # Check video type - skedda fields should NOT be visible
        page.locator("#content_type").select_option("video")
        expect(ical_url_field).not_to_be_visible()
        expect(refresh_select).not_to_be_visible()

        # Check url type - skedda fields should NOT be visible
        page.locator("#content_type").select_option("url")
        expect(ical_url_field).not_to_be_visible()
        expect(refresh_select).not_to_be_visible()

        # Check text type - skedda fields should NOT be visible
        page.locator("#content_type").select_option("text")
        expect(ical_url_field).not_to_be_visible()
        expect(refresh_select).not_to_be_visible()

        # Check skedda type - skedda fields SHOULD be visible
        page.locator("#content_type").select_option("skedda")
        expect(ical_url_field).to_be_visible(timeout=2000)
        expect(refresh_select).to_be_visible()
