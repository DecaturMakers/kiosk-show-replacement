"""
Integration tests for display view slideshow playback.

Tests verify that slideshows play correctly on display views:
- All slides display in correct order
- Slide durations are respected (both default and overridden)
- Different content types render properly
- Uploaded images load successfully
- SSE events trigger display reload on assignment change
- Text slides only show content, not title
- Text slides preserve line breaks
- Info overlay visibility based on display settings

Run with: nox -s test-integration
"""

import os
import time
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

# Path to test assets
ASSETS_DIR = Path(__file__).parent.parent / "assets"


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("SKIP_BROWSER_TESTS", "false").lower() == "true",
    reason="Browser tests skipped",
)
class TestDisplayPlayback:
    """Test slideshow playback on display views."""

    def test_all_slides_display_with_mixed_durations(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        http_client,
        auth_headers,
    ):
        """Test that all slides display correctly with mixed default and override durations.

        Creates a slideshow with 3 text slides:
        - Slide 1: uses default duration (10 seconds from slideshow)
        - Slide 2: has 2-second override duration
        - Slide 3: uses default duration (10 seconds from slideshow)

        The test verifies that all 3 slides are shown, not just the one with
        an override duration. This tests the bug where slides with null
        display_duration were being skipped (0ms timeout).

        We use short durations and verify slide transitions occur.
        """
        page = enhanced_page
        flask_url = servers["flask_url"]

        # Create a slideshow with a short default duration for faster testing
        slideshow_response = http_client.post(
            "/api/v1/slideshows",
            json={
                "name": "Duration Test Slideshow",
                "description": "Test slideshow for duration handling",
                "default_item_duration": 2,  # 2 second default
                "transition_type": "fade",
                "is_active": True,
            },
            headers=auth_headers,
        )
        assert slideshow_response.status_code in [
            200,
            201,
        ], f"Failed to create slideshow: {slideshow_response.text}"
        slideshow_data = slideshow_response.json().get(
            "data", slideshow_response.json()
        )
        slideshow_id = slideshow_data["id"]

        try:
            # Create 3 text slides with mixed durations
            # Slide 1: NO duration override (uses slideshow default)
            slide1_response = http_client.post(
                f"/api/v1/slideshows/{slideshow_id}/items",
                json={
                    "title": "Slide One",
                    "content_type": "text",
                    "content_text": "This is the first slide with DEFAULT duration",
                    "is_active": True,
                    # No display_duration - should use slideshow default (2s)
                },
                headers=auth_headers,
            )
            assert slide1_response.status_code in [200, 201]

            # Slide 2: Has 1-second override duration
            slide2_response = http_client.post(
                f"/api/v1/slideshows/{slideshow_id}/items",
                json={
                    "title": "Slide Two",
                    "content_type": "text",
                    "content_text": "This is the second slide with OVERRIDE duration",
                    "display_duration": 1,  # 1 second override
                    "is_active": True,
                },
                headers=auth_headers,
            )
            assert slide2_response.status_code in [200, 201]

            # Slide 3: NO duration override (uses slideshow default)
            slide3_response = http_client.post(
                f"/api/v1/slideshows/{slideshow_id}/items",
                json={
                    "title": "Slide Three",
                    "content_type": "text",
                    "content_text": "This is the third slide with DEFAULT duration",
                    "is_active": True,
                    # No display_duration - should use slideshow default (2s)
                },
                headers=auth_headers,
            )
            assert slide3_response.status_code in [200, 201]

            # Create a display
            display_name = f"test-duration-display-{int(time.time() * 1000)}"
            display_response = http_client.post(
                "/api/v1/displays",
                json={
                    "name": display_name,
                    "description": "Test display for duration testing",
                },
                headers=auth_headers,
            )
            assert display_response.status_code in [200, 201]
            display_data = display_response.json().get("data", display_response.json())
            display_id = display_data["id"]

            try:
                # Assign slideshow to display
                assign_response = http_client.post(
                    f"/api/v1/displays/{display_name}/assign-slideshow",
                    json={"slideshow_id": slideshow_id},
                    headers=auth_headers,
                )
                assert assign_response.status_code == 200

                # Navigate to display view
                page.goto(f"{flask_url}/display/{display_name}")
                page.wait_for_load_state("domcontentloaded", timeout=15000)

                # Wait for slideshow to initialize
                page.wait_for_selector("#slideshowContainer", timeout=10000)

                # Track which slides we see
                slides_seen = set()

                # Watch for slide changes over 8 seconds
                # With durations of 2s, 1s, 2s we should see all 3 slides cycle
                start_time = time.time()
                max_wait = (
                    8  # 8 seconds should be enough for 2+1+2 = 5 seconds of slides
                )

                while time.time() - start_time < max_wait and len(slides_seen) < 3:
                    # Check for each slide's content
                    if page.locator("text=first slide with DEFAULT").is_visible():
                        slides_seen.add("Slide One")
                    if page.locator("text=second slide with OVERRIDE").is_visible():
                        slides_seen.add("Slide Two")
                    if page.locator("text=third slide with DEFAULT").is_visible():
                        slides_seen.add("Slide Three")

                    # Small delay between checks
                    time.sleep(0.2)

                # Verify all 3 slides were displayed
                assert "Slide One" in slides_seen, (
                    f"Slide One (default duration) was never shown. "
                    f"Slides seen: {slides_seen}"
                )
                assert "Slide Two" in slides_seen, (
                    f"Slide Two (override duration) was never shown. "
                    f"Slides seen: {slides_seen}"
                )
                assert "Slide Three" in slides_seen, (
                    f"Slide Three (default duration) was never shown. "
                    f"Slides seen: {slides_seen}"
                )

            finally:
                # Cleanup display (test_all_slides_display_with_mixed_durations)
                http_client.delete(
                    f"/api/v1/displays/{display_id}",
                    headers=auth_headers,
                )

        finally:
            # Cleanup slideshow (test_all_slides_display_with_mixed_durations)
            http_client.delete(
                f"/api/v1/slideshows/{slideshow_id}",
                headers=auth_headers,
            )

    def test_uploaded_image_displays_on_display_view(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        http_client,
        auth_headers,
    ):
        """Test that uploaded images display correctly on the display view.

        This test:
        1. Creates a slideshow
        2. Uploads an image file via the API
        3. Creates a slideshow item with the uploaded image
        4. Assigns the slideshow to a display
        5. Navigates to the display view
        6. Verifies the image loads successfully (no error shown)

        This tests the bug where uploaded images showed "Failed to load image"
        even though the files existed on the server.
        """
        page = enhanced_page
        flask_url = servers["flask_url"]

        # Verify test asset exists
        image_path = ASSETS_DIR / "smallPhoto.jpg"
        assert image_path.exists(), f"Test asset not found: {image_path}"

        # Create a slideshow
        slideshow_response = http_client.post(
            "/api/v1/slideshows",
            json={
                "name": "Image Display Test Slideshow",
                "description": "Test slideshow for image display",
                "default_item_duration": 10,
                "transition_type": "fade",
                "is_active": True,
            },
            headers=auth_headers,
        )
        assert slideshow_response.status_code in [200, 201]
        slideshow_data = slideshow_response.json().get(
            "data", slideshow_response.json()
        )
        slideshow_id = slideshow_data["id"]

        try:
            # Upload an image
            with open(image_path, "rb") as f:
                files = {"file": ("smallPhoto.jpg", f, "image/jpeg")}
                data = {"slideshow_id": str(slideshow_id)}
                # Need to remove Content-Type from headers for multipart
                upload_headers = {
                    k: v for k, v in auth_headers.items() if k != "Content-Type"
                }
                upload_response = http_client.post(
                    "/api/v1/uploads/image",
                    files=files,
                    data=data,
                    headers=upload_headers,
                )

            assert upload_response.status_code in [
                200,
                201,
            ], f"Failed to upload image: {upload_response.text}"
            upload_data = upload_response.json().get("data", upload_response.json())
            file_path = upload_data.get("file_path")
            assert file_path, f"No file_path in upload response: {upload_data}"

            # Create a slideshow item with the uploaded image
            item_response = http_client.post(
                f"/api/v1/slideshows/{slideshow_id}/items",
                json={
                    "title": "Test Uploaded Image",
                    "content_type": "image",
                    "content_file_path": file_path,
                    "is_active": True,
                },
                headers=auth_headers,
            )
            assert item_response.status_code in [200, 201]

            # Verify the item was created with the file path
            item_data = item_response.json().get("data", item_response.json())
            assert item_data.get("content_file_path") == file_path
            assert item_data.get(
                "display_url"
            ), f"display_url should be set for uploaded image: {item_data}"

            # Create a display
            display_name = f"test-image-display-{int(time.time() * 1000)}"
            display_response = http_client.post(
                "/api/v1/displays",
                json={
                    "name": display_name,
                    "description": "Test display for image display testing",
                },
                headers=auth_headers,
            )
            assert display_response.status_code in [200, 201]
            display_data = display_response.json().get("data", display_response.json())
            display_id = display_data["id"]

            try:
                # Assign slideshow to display
                assign_response = http_client.post(
                    f"/api/v1/displays/{display_name}/assign-slideshow",
                    json={"slideshow_id": slideshow_id},
                    headers=auth_headers,
                )
                assert assign_response.status_code == 200

                # Track network requests to detect image loading
                image_requests = []
                failed_requests = []

                def track_request(request):
                    if "/uploads/" in request.url:
                        image_requests.append(request.url)

                def track_failed(request):
                    if "/uploads/" in request.url:
                        failed_requests.append(
                            {"url": request.url, "failure": request.failure}
                        )

                def track_response(response):
                    if "/uploads/" in response.url and response.status >= 400:
                        failed_requests.append(
                            {"url": response.url, "status": response.status}
                        )

                page.on("request", track_request)
                page.on("requestfailed", track_failed)
                page.on("response", track_response)

                # Navigate to display view
                page.goto(f"{flask_url}/display/{display_name}")
                page.wait_for_load_state("domcontentloaded", timeout=15000)

                # Wait for slideshow to initialize
                page.wait_for_selector("#slideshowContainer", timeout=10000)

                # Wait a moment for image to load
                time.sleep(2)

                # Check that the image element exists and doesn't show error
                img_element = page.locator("img").first
                assert img_element.is_visible(), "Image element should be visible"

                # Check that we don't see the error message
                error_visible = page.locator("text=Failed to load image").is_visible()
                assert not error_visible, (
                    f"Image failed to load. "
                    f"Image requests: {image_requests}, "
                    f"Failed requests: {failed_requests}"
                )

                # Verify an image request was made to /uploads/
                assert (
                    len(image_requests) > 0
                ), "No image requests were made to /uploads/ endpoint"

                # Verify no requests failed
                assert (
                    len(failed_requests) == 0
                ), f"Image request(s) failed: {failed_requests}"

            finally:
                # Cleanup display (test_uploaded_image_displays_on_display_view)
                http_client.delete(
                    f"/api/v1/displays/{display_id}",
                    headers=auth_headers,
                )

        finally:
            # Cleanup slideshow (test_uploaded_image_displays_on_display_view)
            http_client.delete(
                f"/api/v1/slideshows/{slideshow_id}",
                headers=auth_headers,
            )

    def test_display_reloads_on_slideshow_assignment_change(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        http_client,
        auth_headers,
    ):
        """Test that display automatically reloads when slideshow assignment changes.

        This test:
        1. Creates two slideshows with different content
        2. Creates a display and assigns the first slideshow
        3. Navigates to the display view
        4. Changes the slideshow assignment via API
        5. Verifies the display view automatically updates to show new slideshow content

        This tests the bug where slideshow assignment changes didn't reach displays
        via SSE, requiring manual page refresh.
        """
        page = enhanced_page
        flask_url = servers["flask_url"]

        # Create first slideshow
        slideshow1_response = http_client.post(
            "/api/v1/slideshows",
            json={
                "name": "SSE Test Slideshow 1",
                "description": "First slideshow for SSE test",
                "default_item_duration": 30,
                "is_active": True,
            },
            headers=auth_headers,
        )
        assert slideshow1_response.status_code in [200, 201]
        slideshow1_data = slideshow1_response.json().get(
            "data", slideshow1_response.json()
        )
        slideshow1_id = slideshow1_data["id"]

        # Create second slideshow
        slideshow2_response = http_client.post(
            "/api/v1/slideshows",
            json={
                "name": "SSE Test Slideshow 2",
                "description": "Second slideshow for SSE test",
                "default_item_duration": 30,
                "is_active": True,
            },
            headers=auth_headers,
        )
        assert slideshow2_response.status_code in [200, 201]
        slideshow2_data = slideshow2_response.json().get(
            "data", slideshow2_response.json()
        )
        slideshow2_id = slideshow2_data["id"]

        try:
            # Add a text slide to first slideshow with distinctive content
            http_client.post(
                f"/api/v1/slideshows/{slideshow1_id}/items",
                json={
                    "title": "First Slideshow Unique Content",
                    "content_type": "text",
                    "content_text": "THIS IS SLIDESHOW ONE - ORIGINAL ASSIGNMENT",
                    "is_active": True,
                },
                headers=auth_headers,
            )

            # Add a text slide to second slideshow with different distinctive content
            http_client.post(
                f"/api/v1/slideshows/{slideshow2_id}/items",
                json={
                    "title": "Second Slideshow Unique Content",
                    "content_type": "text",
                    "content_text": "THIS IS SLIDESHOW TWO - NEW ASSIGNMENT",
                    "is_active": True,
                },
                headers=auth_headers,
            )

            # Create a display
            display_name = f"test-sse-display-{int(time.time() * 1000)}"
            display_response = http_client.post(
                "/api/v1/displays",
                json={
                    "name": display_name,
                    "description": "Test display for SSE assignment change",
                },
                headers=auth_headers,
            )
            assert display_response.status_code in [200, 201]
            display_data = display_response.json().get("data", display_response.json())
            display_id = display_data["id"]

            try:
                # Assign first slideshow to display
                assign_response = http_client.post(
                    f"/api/v1/displays/{display_name}/assign-slideshow",
                    json={"slideshow_id": slideshow1_id},
                    headers=auth_headers,
                )
                assert assign_response.status_code == 200

                # Navigate to display view
                page.goto(f"{flask_url}/display/{display_name}")
                page.wait_for_load_state("domcontentloaded", timeout=15000)
                page.wait_for_selector("#slideshowContainer", timeout=10000)

                # Verify first slideshow content is visible
                first_content_visible = page.locator(
                    "text=THIS IS SLIDESHOW ONE"
                ).is_visible()
                assert (
                    first_content_visible
                ), "First slideshow content should be visible"

                # Wait for SSE connection to establish
                time.sleep(1)

                # Now change the slideshow assignment via API
                reassign_response = http_client.post(
                    f"/api/v1/displays/{display_name}/assign-slideshow",
                    json={"slideshow_id": slideshow2_id},
                    headers=auth_headers,
                )
                assert reassign_response.status_code == 200

                # Wait for SSE event to trigger page reload
                # The display should receive the assignment_changed event and reload
                max_wait = 10  # 10 seconds should be plenty for SSE
                start_time = time.time()
                second_content_visible = False

                while (
                    time.time() - start_time < max_wait and not second_content_visible
                ):
                    # Check if second slideshow content becomes visible
                    try:
                        second_content_visible = page.locator(
                            "text=THIS IS SLIDESHOW TWO"
                        ).is_visible()
                    except Exception:
                        # Page might be reloading
                        pass
                    time.sleep(0.5)

                # Verify the display now shows the second slideshow
                assert second_content_visible, (
                    "Display should have automatically switched to second slideshow "
                    "via SSE after assignment change. "
                    "If this fails, SSE events are not reaching the display."
                )

            finally:
                # Cleanup display (test_display_reloads_on_slideshow_assignment_change)
                http_client.delete(
                    f"/api/v1/displays/{display_id}",
                    headers=auth_headers,
                )

        finally:
            # Cleanup slideshows (test_display_reloads_on_slideshow_assignment_change)
            http_client.delete(
                f"/api/v1/slideshows/{slideshow1_id}",
                headers=auth_headers,
            )
            http_client.delete(
                f"/api/v1/slideshows/{slideshow2_id}",
                headers=auth_headers,
            )

    def test_display_reloads_on_zoom_change(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        http_client,
        auth_headers,
    ):
        """Test that display reloads and applies new scale_factor when zoom is changed.

        Regression test for: Zoom slider changes not reaching displays.

        This test:
        1. Creates a slideshow with a URL slide (no scale_factor initially)
        2. Creates a display and assigns the slideshow
        3. Navigates to the display view
        4. Verifies iframe has no transform or scale(1)
        5. Updates scale_factor to 50 via API
        6. Waits for SSE-triggered reload
        7. Verifies iframe now has transform: scale(0.5) applied
        """
        page = enhanced_page
        flask_url = servers["flask_url"]

        # Create a slideshow
        slideshow_response = http_client.post(
            "/api/v1/slideshows",
            json={
                "name": "Zoom Test Slideshow",
                "description": "Test slideshow for zoom/scale changes",
                "default_item_duration": 60,
                "is_active": True,
            },
            headers=auth_headers,
        )
        assert slideshow_response.status_code in [200, 201]
        slideshow_data = slideshow_response.json().get(
            "data", slideshow_response.json()
        )
        slideshow_id = slideshow_data["id"]

        try:
            # Add a URL slide with NO scale_factor initially
            item_response = http_client.post(
                f"/api/v1/slideshows/{slideshow_id}/items",
                json={
                    "title": "Test URL Slide for Zoom",
                    "content_type": "url",
                    "content_url": "https://example.com",
                    "is_active": True,
                    "scale_factor": None,  # No zoom initially
                },
                headers=auth_headers,
            )
            assert item_response.status_code in [200, 201]
            item_data = item_response.json().get("data", item_response.json())
            item_id = item_data["id"]

            # Create a display
            display_name = f"test-zoom-display-{int(time.time() * 1000)}"
            display_response = http_client.post(
                "/api/v1/displays",
                json={
                    "name": display_name,
                    "description": "Test display for zoom change SSE",
                },
                headers=auth_headers,
            )
            assert display_response.status_code in [200, 201]
            display_data = display_response.json().get("data", display_response.json())
            display_id = display_data["id"]

            try:
                # Assign slideshow to display
                assign_response = http_client.post(
                    f"/api/v1/displays/{display_name}/assign-slideshow",
                    json={"slideshow_id": slideshow_id},
                    headers=auth_headers,
                )
                assert assign_response.status_code == 200

                # Navigate to display view
                page.goto(f"{flask_url}/display/{display_name}")
                page.wait_for_load_state("domcontentloaded", timeout=15000)
                page.wait_for_selector("#slideshowContainer", timeout=10000)

                # Wait for slide to render and SSE connection to establish
                time.sleep(2)

                # Verify initial state: iframe should NOT have scale(0.5) transform
                # (it should have no transform or scale(1))
                iframe_locator = page.locator("iframe")
                initial_style = iframe_locator.get_attribute("style") or ""
                assert (
                    "scale(0.5)" not in initial_style
                ), f"Initial iframe should not have scale(0.5), got style: {initial_style}"

                # Now update the scale_factor via API
                update_response = http_client.put(
                    f"/api/v1/slideshow-items/{item_id}",
                    json={"scale_factor": 50},
                    headers=auth_headers,
                )
                assert update_response.status_code == 200

                # Wait for SSE event to trigger page reload and re-render
                # The display should receive the slideshow.updated event and reload
                max_wait = 15  # 15 seconds should be plenty for SSE
                start_time = time.time()
                scale_applied = False

                while time.time() - start_time < max_wait and not scale_applied:
                    try:
                        # Re-find the iframe (page might have reloaded)
                        iframe_locator = page.locator("iframe")
                        if iframe_locator.count() > 0:
                            new_style = iframe_locator.get_attribute("style") or ""
                            if "scale(0.5)" in new_style:
                                scale_applied = True
                                break
                    except Exception:
                        # Page might be reloading
                        pass
                    time.sleep(0.5)

                # Verify the display now shows the scaled iframe
                assert scale_applied, (
                    "Display should have automatically applied scale(0.5) transform "
                    "via SSE after scale_factor change. "
                    "If this fails, SSE events for zoom changes are not reaching the display."
                )

            finally:
                # Cleanup display (test_display_reloads_on_zoom_change)
                http_client.delete(
                    f"/api/v1/displays/{display_id}",
                    headers=auth_headers,
                )

        finally:
            # Cleanup slideshow (test_display_reloads_on_zoom_change)
            http_client.delete(
                f"/api/v1/slideshows/{slideshow_id}",
                headers=auth_headers,
            )

    def test_text_slide_shows_only_content_not_title(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        http_client,
        auth_headers,
    ):
        """Test that text slides only display content_text, not the title.

        This test:
        1. Creates a slideshow with a text slide that has both title and content_text
        2. Assigns the slideshow to a display
        3. Navigates to the display view
        4. Verifies the content_text is shown
        5. Verifies the title is NOT shown

        This tests the bug where text slides were incorrectly displaying both
        the title and the text content, when they should only show content_text.
        """
        page = enhanced_page
        flask_url = servers["flask_url"]

        # Create a slideshow
        slideshow_response = http_client.post(
            "/api/v1/slideshows",
            json={
                "name": "Text Title Test Slideshow",
                "description": "Test slideshow for text title display",
                "default_item_duration": 30,
                "is_active": True,
            },
            headers=auth_headers,
        )
        assert slideshow_response.status_code in [200, 201]
        slideshow_data = slideshow_response.json().get(
            "data", slideshow_response.json()
        )
        slideshow_id = slideshow_data["id"]

        try:
            # Create a text slide with BOTH title AND content_text
            # The title should NOT be displayed on the display view
            distinctive_title = "TITLE_SHOULD_NOT_BE_DISPLAYED_XYZ123"
            distinctive_content = "CONTENT_SHOULD_BE_DISPLAYED_ABC789"

            item_response = http_client.post(
                f"/api/v1/slideshows/{slideshow_id}/items",
                json={
                    "title": distinctive_title,
                    "content_type": "text",
                    "content_text": distinctive_content,
                    "is_active": True,
                },
                headers=auth_headers,
            )
            assert item_response.status_code in [200, 201]

            # Create a display
            display_name = f"test-text-title-display-{int(time.time() * 1000)}"
            display_response = http_client.post(
                "/api/v1/displays",
                json={
                    "name": display_name,
                    "description": "Test display for text title testing",
                },
                headers=auth_headers,
            )
            assert display_response.status_code in [200, 201]
            display_data = display_response.json().get("data", display_response.json())
            display_id = display_data["id"]

            try:
                # Assign slideshow to display
                assign_response = http_client.post(
                    f"/api/v1/displays/{display_name}/assign-slideshow",
                    json={"slideshow_id": slideshow_id},
                    headers=auth_headers,
                )
                assert assign_response.status_code == 200

                # Navigate to display view
                page.goto(f"{flask_url}/display/{display_name}")
                page.wait_for_load_state("domcontentloaded", timeout=15000)

                # Wait for slideshow to initialize
                page.wait_for_selector("#slideshowContainer", timeout=10000)

                # Wait a moment for content to render
                time.sleep(1)

                # Verify the content_text IS displayed
                content_visible = page.locator(
                    f"text={distinctive_content}"
                ).is_visible()
                assert content_visible, (
                    f"Text content '{distinctive_content}' should be displayed on "
                    "the display view"
                )

                # Verify the title is NOT displayed
                title_visible = page.locator(f"text={distinctive_title}").is_visible()
                assert not title_visible, (
                    f"Title '{distinctive_title}' should NOT be displayed on "
                    "the display view for text slides. Only content_text should "
                    "be shown."
                )

            finally:
                # Cleanup display (test_text_slide_shows_only_content_not_title)
                http_client.delete(
                    f"/api/v1/displays/{display_id}",
                    headers=auth_headers,
                )

        finally:
            # Cleanup slideshow (test_text_slide_shows_only_content_not_title)
            http_client.delete(
                f"/api/v1/slideshows/{slideshow_id}",
                headers=auth_headers,
            )

    def test_text_slide_preserves_line_breaks(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        http_client,
        auth_headers,
    ):
        """Test that text slides preserve line breaks/newlines.

        This test:
        1. Creates a slideshow with a text slide that has multiple lines
        2. Assigns the slideshow to a display
        3. Navigates to the display view
        4. Verifies the line breaks are preserved (text appears on separate lines)

        This tests the bug where text slides collapsed all line breaks.
        """
        page = enhanced_page
        flask_url = servers["flask_url"]

        # Create a slideshow
        slideshow_response = http_client.post(
            "/api/v1/slideshows",
            json={
                "name": "Text Formatting Test Slideshow",
                "description": "Test slideshow for text formatting",
                "default_item_duration": 30,
                "is_active": True,
            },
            headers=auth_headers,
        )
        assert slideshow_response.status_code in [200, 201]
        slideshow_data = slideshow_response.json().get(
            "data", slideshow_response.json()
        )
        slideshow_id = slideshow_data["id"]

        try:
            # Create a text slide with multiple lines
            # Each line has distinctive content so we can verify they're on separate lines
            line1 = "LINE_ONE_CONTENT"
            line2 = "LINE_TWO_CONTENT"
            line3 = "LINE_THREE_CONTENT"
            multiline_content = f"{line1}\n{line2}\n{line3}"

            item_response = http_client.post(
                f"/api/v1/slideshows/{slideshow_id}/items",
                json={
                    "title": "Multiline Test",
                    "content_type": "text",
                    "content_text": multiline_content,
                    "is_active": True,
                },
                headers=auth_headers,
            )
            assert item_response.status_code in [200, 201]

            # Create a display
            display_name = f"test-text-format-display-{int(time.time() * 1000)}"
            display_response = http_client.post(
                "/api/v1/displays",
                json={
                    "name": display_name,
                    "description": "Test display for text formatting testing",
                },
                headers=auth_headers,
            )
            assert display_response.status_code in [200, 201]
            display_data = display_response.json().get("data", display_response.json())
            display_id = display_data["id"]

            try:
                # Assign slideshow to display
                assign_response = http_client.post(
                    f"/api/v1/displays/{display_name}/assign-slideshow",
                    json={"slideshow_id": slideshow_id},
                    headers=auth_headers,
                )
                assert assign_response.status_code == 200

                # Navigate to display view
                page.goto(f"{flask_url}/display/{display_name}")
                page.wait_for_load_state("domcontentloaded", timeout=15000)

                # Wait for slideshow to initialize
                page.wait_for_selector("#slideshowContainer", timeout=10000)

                # Wait a moment for content to render
                time.sleep(1)

                # Verify all three lines are visible
                for line in [line1, line2, line3]:
                    assert page.locator(
                        f"text={line}"
                    ).is_visible(), f"Line '{line}' should be visible in the text slide"

                # Verify lines are on separate lines by checking that the content element
                # has line breaks preserved (via CSS white-space or <br> tags)
                content_element = page.locator(".text-content .content")
                expect(content_element).to_be_visible()

                # Get the computed style to verify white-space is set to preserve line breaks
                # or check that text appears on multiple lines by examining bounding boxes
                html_content = content_element.inner_html()

                # Check if line breaks are preserved either by <br> tags or by CSS
                # The content should either have <br> tags between lines, or the
                # white-space CSS property should be 'pre-wrap' or 'pre-line'
                has_br_tags = "<br" in html_content.lower()

                # Get computed style
                computed_style = page.evaluate(
                    """(el) => window.getComputedStyle(el).whiteSpace""",
                    content_element.element_handle(),
                )
                has_whitespace_css = computed_style in ["pre-wrap", "pre-line", "pre"]

                assert has_br_tags or has_whitespace_css, (
                    f"Text content should preserve line breaks. "
                    f"HTML content: '{html_content}', "
                    f"computed white-space: '{computed_style}'. "
                    f"Expected <br> tags or white-space: pre-wrap/pre-line/pre."
                )

            finally:
                # Cleanup display (test_text_slide_preserves_line_breaks)
                http_client.delete(
                    f"/api/v1/displays/{display_id}",
                    headers=auth_headers,
                )

        finally:
            # Cleanup slideshow (test_text_slide_preserves_line_breaks)
            http_client.delete(
                f"/api/v1/slideshows/{slideshow_id}",
                headers=auth_headers,
            )

    def test_info_overlay_respects_display_setting(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        http_client,
        auth_headers,
    ):
        """Test that info overlay visibility respects the display's show_info_overlay setting.

        This test:
        1. Creates a display with show_info_overlay=False
        2. Creates a slideshow and assigns it to the display
        3. Navigates to the display view
        4. Verifies the info overlay is NOT visible
        5. Updates the display to show_info_overlay=True
        6. Reloads and verifies the info overlay IS visible

        The info overlay shows slideshow name, slide counter, and display name.
        """
        page = enhanced_page
        flask_url = servers["flask_url"]

        # Create a slideshow
        slideshow_response = http_client.post(
            "/api/v1/slideshows",
            json={
                "name": "Info Overlay Test Slideshow",
                "description": "Test slideshow for info overlay",
                "default_item_duration": 30,
                "is_active": True,
            },
            headers=auth_headers,
        )
        assert slideshow_response.status_code in [200, 201]
        slideshow_data = slideshow_response.json().get(
            "data", slideshow_response.json()
        )
        slideshow_id = slideshow_data["id"]

        try:
            # Create a text slide
            item_response = http_client.post(
                f"/api/v1/slideshows/{slideshow_id}/items",
                json={
                    "title": "Test Slide",
                    "content_type": "text",
                    "content_text": "Test content for info overlay test",
                    "is_active": True,
                },
                headers=auth_headers,
            )
            assert item_response.status_code in [200, 201]

            # Create a display with show_info_overlay=False (default)
            display_name = f"test-overlay-display-{int(time.time() * 1000)}"
            display_response = http_client.post(
                "/api/v1/displays",
                json={
                    "name": display_name,
                    "description": "Test display for info overlay testing",
                    "show_info_overlay": False,  # Explicitly disable
                },
                headers=auth_headers,
            )
            assert display_response.status_code in [200, 201]
            display_data = display_response.json().get("data", display_response.json())
            display_id = display_data["id"]

            try:
                # Assign slideshow to display
                assign_response = http_client.post(
                    f"/api/v1/displays/{display_name}/assign-slideshow",
                    json={"slideshow_id": slideshow_id},
                    headers=auth_headers,
                )
                assert assign_response.status_code == 200

                # Navigate to display view
                page.goto(f"{flask_url}/display/{display_name}")
                page.wait_for_load_state("domcontentloaded", timeout=15000)
                page.wait_for_selector("#slideshowContainer", timeout=10000)
                time.sleep(1)

                # Verify the info overlay is NOT visible when show_info_overlay=False
                slide_info = page.locator("#slideInfo")
                overlay_visible = slide_info.is_visible()
                assert (
                    not overlay_visible
                ), "Info overlay should NOT be visible when show_info_overlay=False"

                # Update the display to show_info_overlay=True.
                # The display page has an SSE client that listens for
                # display.configuration_changed events and automatically reloads
                # the page when the configuration changes. We use expect_navigation
                # to wait for this SSE-triggered reload instead of calling
                # page.reload() explicitly, which would cause a race condition.
                with page.expect_navigation(timeout=15000):
                    update_response = http_client.put(
                        f"/api/v1/displays/{display_id}",
                        json={"show_info_overlay": True},
                        headers=auth_headers,
                    )
                    assert update_response.status_code == 200

                # Wait for page to fully load after SSE-triggered reload
                page.wait_for_load_state("domcontentloaded", timeout=15000)
                page.wait_for_selector("#slideshowContainer", timeout=10000)
                time.sleep(1)

                # Verify the info overlay IS visible when show_info_overlay=True
                slide_info = page.locator("#slideInfo")
                overlay_visible = slide_info.is_visible()
                assert (
                    overlay_visible
                ), "Info overlay should be visible when show_info_overlay=True"

                # Verify the overlay contains expected information
                expect(slide_info).to_contain_text(display_name)
                expect(slide_info).to_contain_text("Info Overlay Test Slideshow")

            finally:
                # Cleanup display (test_info_overlay_respects_display_setting)
                http_client.delete(
                    f"/api/v1/displays/{display_id}",
                    headers=auth_headers,
                )

        finally:
            # Cleanup slideshow (test_info_overlay_respects_display_setting)
            http_client.delete(
                f"/api/v1/slideshows/{slideshow_id}",
                headers=auth_headers,
            )

    def test_uploaded_video_displays_on_display_view(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        http_client,
        auth_headers,
    ):
        """Test that uploaded videos display and play correctly on the display view.

        This test:
        1. Creates a slideshow
        2. Uploads a video file via the API
        3. Creates a slideshow item with the uploaded video
        4. Assigns the slideshow to a display
        5. Navigates to the display view
        6. Verifies the video element becomes visible (loaded class applied)
        7. Verifies no error message is shown

        This tests the bug where video slides showed a black screen instead of
        playing the video, due to incorrect <source> element configuration.
        """
        page = enhanced_page
        flask_url = servers["flask_url"]

        # Verify test asset exists
        video_path = ASSETS_DIR / "test_video_5s.mp4"
        assert video_path.exists(), f"Test asset not found: {video_path}"

        # Create a slideshow
        slideshow_response = http_client.post(
            "/api/v1/slideshows",
            json={
                "name": "Video Display Test Slideshow",
                "description": "Test slideshow for video display",
                "default_item_duration": 10,
                "transition_type": "fade",
                "is_active": True,
            },
            headers=auth_headers,
        )
        assert slideshow_response.status_code in [200, 201]
        slideshow_data = slideshow_response.json().get(
            "data", slideshow_response.json()
        )
        slideshow_id = slideshow_data["id"]

        try:
            # Upload a video
            with open(video_path, "rb") as f:
                files = {"file": ("test_video_5s.mp4", f, "video/mp4")}
                data = {"slideshow_id": str(slideshow_id)}
                # Need to remove Content-Type from headers for multipart
                upload_headers = {
                    k: v for k, v in auth_headers.items() if k != "Content-Type"
                }
                upload_response = http_client.post(
                    "/api/v1/uploads/video",
                    files=files,
                    data=data,
                    headers=upload_headers,
                )

            assert upload_response.status_code in [
                200,
                201,
            ], f"Failed to upload video: {upload_response.text}"
            upload_data = upload_response.json().get("data", upload_response.json())
            file_path = upload_data.get("file_path")
            assert file_path, f"No file_path in upload response: {upload_data}"

            # Create a slideshow item with the uploaded video
            item_response = http_client.post(
                f"/api/v1/slideshows/{slideshow_id}/items",
                json={
                    "title": "Test Uploaded Video",
                    "content_type": "video",
                    "content_file_path": file_path,
                    "is_active": True,
                },
                headers=auth_headers,
            )
            assert item_response.status_code in [200, 201]

            # Verify the item was created with the file path
            item_data = item_response.json().get("data", item_response.json())
            assert item_data.get("content_file_path") == file_path
            assert item_data.get(
                "display_url"
            ), f"display_url should be set for uploaded video: {item_data}"

            # Create a display
            display_name = f"test-video-display-{int(time.time() * 1000)}"
            display_response = http_client.post(
                "/api/v1/displays",
                json={
                    "name": display_name,
                    "description": "Test display for video display testing",
                },
                headers=auth_headers,
            )
            assert display_response.status_code in [200, 201]
            display_data = display_response.json().get("data", display_response.json())
            display_id = display_data["id"]

            try:
                # Assign slideshow to display
                assign_response = http_client.post(
                    f"/api/v1/displays/{display_name}/assign-slideshow",
                    json={"slideshow_id": slideshow_id},
                    headers=auth_headers,
                )
                assert assign_response.status_code == 200

                # Track network requests to detect video loading
                video_requests = []
                failed_requests = []

                def track_request(request):
                    if "/uploads/" in request.url:
                        video_requests.append(request.url)

                def track_failed(request):
                    if "/uploads/" in request.url:
                        failed_requests.append(
                            {"url": request.url, "failure": request.failure}
                        )

                def track_response(response):
                    if "/uploads/" in response.url and response.status >= 400:
                        failed_requests.append(
                            {"url": response.url, "status": response.status}
                        )

                page.on("request", track_request)
                page.on("requestfailed", track_failed)
                page.on("response", track_response)

                # Navigate to display view
                page.goto(f"{flask_url}/display/{display_name}")
                page.wait_for_load_state("domcontentloaded", timeout=15000)

                # Wait for slideshow to initialize
                page.wait_for_selector("#slideshowContainer", timeout=10000)

                # Wait for video to load - give it up to 5 seconds
                video_element = page.locator("video").first
                video_element.wait_for(state="attached", timeout=5000)

                # Wait for the video to become visible (loaded class applied)
                # The video should have opacity: 1 and the loaded class after loading
                max_wait = 5  # seconds
                start_time = time.time()
                video_visible = False

                while time.time() - start_time < max_wait:
                    # Check if video has loaded class (opacity: 1)
                    has_loaded_class = page.evaluate("""() => {
                            const video = document.querySelector('video');
                            return video && video.classList.contains('loaded');
                        }""")
                    if has_loaded_class:
                        video_visible = True
                        break
                    time.sleep(0.2)

                # Check that we don't see the error message
                error_visible = page.locator("text=Failed to load video").is_visible()
                assert not error_visible, (
                    f"Video failed to load. "
                    f"Video requests: {video_requests}, "
                    f"Failed requests: {failed_requests}"
                )

                # Verify video element has loaded class (is visible)
                assert video_visible, (
                    f"Video element should have 'loaded' class (be visible). "
                    f"Video requests: {video_requests}, "
                    f"Failed requests: {failed_requests}. "
                    f"This indicates the video didn't load properly."
                )

                # Verify a video request was made to /uploads/
                assert (
                    len(video_requests) > 0
                ), "No video requests were made to /uploads/ endpoint"

                # Verify no requests failed
                assert (
                    len(failed_requests) == 0
                ), f"Video request(s) failed: {failed_requests}"

            finally:
                # Cleanup display (test_uploaded_video_displays_on_display_view)
                http_client.delete(
                    f"/api/v1/displays/{display_id}",
                    headers=auth_headers,
                )

        finally:
            # Cleanup slideshow (test_uploaded_video_displays_on_display_view)
            http_client.delete(
                f"/api/v1/slideshows/{slideshow_id}",
                headers=auth_headers,
            )

    def test_text_slide_renders_basic_html_tags(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        http_client,
        auth_headers,
    ):
        """Test that text slides render basic HTML formatting tags.

        This test:
        1. Creates a slideshow with a text slide containing HTML tags
        2. Assigns the slideshow to a display
        3. Navigates to the display view
        4. Verifies the HTML tags are rendered (not displayed literally)

        Allowed tags: <b>, <strong>, <i>, <em>, <u>, <br>, <p>
        """
        page = enhanced_page
        flask_url = servers["flask_url"]

        # Create a slideshow
        slideshow_response = http_client.post(
            "/api/v1/slideshows",
            json={
                "name": "HTML Rendering Test Slideshow",
                "description": "Test slideshow for HTML rendering",
                "default_item_duration": 30,
                "is_active": True,
            },
            headers=auth_headers,
        )
        assert slideshow_response.status_code in [200, 201]
        slideshow_data = slideshow_response.json().get(
            "data", slideshow_response.json()
        )
        slideshow_id = slideshow_data["id"]

        try:
            # Create a text slide with HTML formatting tags
            # Include all supported tags to verify they render
            html_content = (
                "This is <b>bold</b> and <strong>strong</strong> text. "
                "This is <i>italic</i> and <em>emphasized</em> text. "
                "This is <u>underlined</u> text."
            )

            item_response = http_client.post(
                f"/api/v1/slideshows/{slideshow_id}/items",
                json={
                    "title": "HTML Test Slide",
                    "content_type": "text",
                    "content_text": html_content,
                    "is_active": True,
                },
                headers=auth_headers,
            )
            assert item_response.status_code in [200, 201]

            # Create a display
            display_name = f"test-html-display-{int(time.time() * 1000)}"
            display_response = http_client.post(
                "/api/v1/displays",
                json={
                    "name": display_name,
                    "description": "Test display for HTML rendering testing",
                },
                headers=auth_headers,
            )
            assert display_response.status_code in [200, 201]
            display_data = display_response.json().get("data", display_response.json())
            display_id = display_data["id"]

            try:
                # Assign slideshow to display
                assign_response = http_client.post(
                    f"/api/v1/displays/{display_name}/assign-slideshow",
                    json={"slideshow_id": slideshow_id},
                    headers=auth_headers,
                )
                assert assign_response.status_code == 200

                # Navigate to display view
                page.goto(f"{flask_url}/display/{display_name}")
                page.wait_for_load_state("domcontentloaded", timeout=15000)

                # Wait for slideshow to initialize
                page.wait_for_selector("#slideshowContainer", timeout=10000)

                # Wait a moment for content to render
                time.sleep(1)

                # Get the content element
                content_element = page.locator(".text-content .content")
                expect(content_element).to_be_visible()

                # Get the inner HTML to check rendered tags
                inner_html = content_element.inner_html()

                # Verify HTML tags are rendered (present in innerHTML)
                # not displayed as literal text
                assert "<b>" in inner_html, (
                    f"<b> tag should be rendered in HTML. "
                    f"Got innerHTML: {inner_html}"
                )
                assert "<strong>" in inner_html, (
                    f"<strong> tag should be rendered in HTML. "
                    f"Got innerHTML: {inner_html}"
                )
                assert "<i>" in inner_html, (
                    f"<i> tag should be rendered in HTML. "
                    f"Got innerHTML: {inner_html}"
                )
                assert "<em>" in inner_html, (
                    f"<em> tag should be rendered in HTML. "
                    f"Got innerHTML: {inner_html}"
                )
                assert "<u>" in inner_html, (
                    f"<u> tag should be rendered in HTML. "
                    f"Got innerHTML: {inner_html}"
                )

                # Verify the literal tag text is NOT visible to the user
                # (i.e., user doesn't see "<b>" as text)
                visible_text = content_element.inner_text()
                assert "&lt;b&gt;" not in visible_text, (
                    f"Escaped <b> tag should not be visible as text. "
                    f"Got visible text: {visible_text}"
                )
                assert "<b>" not in visible_text, (
                    f"Literal <b> tag should not be visible as text. "
                    f"Got visible text: {visible_text}"
                )

            finally:
                # Cleanup display (test_text_slide_renders_basic_html_tags)
                http_client.delete(
                    f"/api/v1/displays/{display_id}",
                    headers=auth_headers,
                )

        finally:
            # Cleanup slideshow (test_text_slide_renders_basic_html_tags)
            http_client.delete(
                f"/api/v1/slideshows/{slideshow_id}",
                headers=auth_headers,
            )

    def test_text_slide_strips_unsafe_html(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        http_client,
        auth_headers,
    ):
        """Test that text slides strip unsafe HTML tags and attributes.

        This test:
        1. Creates a slideshow with a text slide containing unsafe HTML
        2. Assigns the slideshow to a display
        3. Navigates to the display view
        4. Verifies unsafe tags (<script>) are stripped
        5. Verifies unsafe attributes (onclick, style) are stripped

        This prevents XSS attacks.
        """
        page = enhanced_page
        flask_url = servers["flask_url"]

        # Create a slideshow
        slideshow_response = http_client.post(
            "/api/v1/slideshows",
            json={
                "name": "XSS Test Slideshow",
                "description": "Test slideshow for XSS prevention",
                "default_item_duration": 30,
                "is_active": True,
            },
            headers=auth_headers,
        )
        assert slideshow_response.status_code in [200, 201]
        slideshow_data = slideshow_response.json().get(
            "data", slideshow_response.json()
        )
        slideshow_id = slideshow_data["id"]

        try:
            # Create a text slide with unsafe HTML
            # Include script tags, event handlers, and style attributes
            unsafe_content = (
                '<script>alert("XSS")</script>'
                "<b onclick=\"alert('XSS')\">Click me</b> "
                '<i style="color:red">Styled text</i> '
                '<img src="x" onerror="alert(\'XSS\')">'
                "Safe text here"
            )

            item_response = http_client.post(
                f"/api/v1/slideshows/{slideshow_id}/items",
                json={
                    "title": "XSS Test Slide",
                    "content_type": "text",
                    "content_text": unsafe_content,
                    "is_active": True,
                },
                headers=auth_headers,
            )
            assert item_response.status_code in [200, 201]

            # Create a display
            display_name = f"test-xss-display-{int(time.time() * 1000)}"
            display_response = http_client.post(
                "/api/v1/displays",
                json={
                    "name": display_name,
                    "description": "Test display for XSS testing",
                },
                headers=auth_headers,
            )
            assert display_response.status_code in [200, 201]
            display_data = display_response.json().get("data", display_response.json())
            display_id = display_data["id"]

            try:
                # Assign slideshow to display
                assign_response = http_client.post(
                    f"/api/v1/displays/{display_name}/assign-slideshow",
                    json={"slideshow_id": slideshow_id},
                    headers=auth_headers,
                )
                assert assign_response.status_code == 200

                # Navigate to display view
                page.goto(f"{flask_url}/display/{display_name}")
                page.wait_for_load_state("domcontentloaded", timeout=15000)

                # Wait for slideshow to initialize
                page.wait_for_selector("#slideshowContainer", timeout=10000)

                # Wait a moment for content to render
                time.sleep(1)

                # Get the content element
                content_element = page.locator(".text-content .content")
                expect(content_element).to_be_visible()

                # Get the inner HTML
                inner_html = content_element.inner_html()

                # Verify unsafe tags are stripped
                assert "<script>" not in inner_html.lower(), (
                    f"<script> tag should be stripped. " f"Got innerHTML: {inner_html}"
                )
                assert "alert(" not in inner_html, (
                    f"JavaScript alert should be stripped. "
                    f"Got innerHTML: {inner_html}"
                )

                # Verify unsafe attributes are stripped
                assert "onclick" not in inner_html.lower(), (
                    f"onclick attribute should be stripped. "
                    f"Got innerHTML: {inner_html}"
                )
                assert "onerror" not in inner_html.lower(), (
                    f"onerror attribute should be stripped. "
                    f"Got innerHTML: {inner_html}"
                )
                assert 'style="' not in inner_html.lower(), (
                    f"style attribute should be stripped. "
                    f"Got innerHTML: {inner_html}"
                )

                # Verify <img> tag is stripped (not in allowed list)
                assert "<img" not in inner_html.lower(), (
                    f"<img> tag should be stripped. " f"Got innerHTML: {inner_html}"
                )

                # Verify safe text is still present
                visible_text = content_element.inner_text()
                assert "Safe text here" in visible_text, (
                    f"Safe text should still be visible. "
                    f"Got visible text: {visible_text}"
                )

                # Verify the safe <b> and <i> tags are preserved (just without attributes)
                assert "<b>" in inner_html, (
                    f"Safe <b> tag should be preserved. " f"Got innerHTML: {inner_html}"
                )
                assert "<i>" in inner_html, (
                    f"Safe <i> tag should be preserved. " f"Got innerHTML: {inner_html}"
                )

            finally:
                # Cleanup display (test_text_slide_strips_unsafe_html)
                http_client.delete(
                    f"/api/v1/displays/{display_id}",
                    headers=auth_headers,
                )

        finally:
            # Cleanup slideshow (test_text_slide_strips_unsafe_html)
            http_client.delete(
                f"/api/v1/slideshows/{slideshow_id}",
                headers=auth_headers,
            )

    def test_text_slide_plain_text_still_works(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        http_client,
        auth_headers,
    ):
        """Test that plain text without HTML tags still works correctly.

        This test verifies backwards compatibility - text without any HTML
        tags should continue to work as before, with line breaks preserved.
        """
        page = enhanced_page
        flask_url = servers["flask_url"]

        # Create a slideshow
        slideshow_response = http_client.post(
            "/api/v1/slideshows",
            json={
                "name": "Plain Text Test Slideshow",
                "description": "Test slideshow for plain text",
                "default_item_duration": 30,
                "is_active": True,
            },
            headers=auth_headers,
        )
        assert slideshow_response.status_code in [200, 201]
        slideshow_data = slideshow_response.json().get(
            "data", slideshow_response.json()
        )
        slideshow_id = slideshow_data["id"]

        try:
            # Create a text slide with plain text and line breaks
            plain_content = "Line one\nLine two\nLine three"

            item_response = http_client.post(
                f"/api/v1/slideshows/{slideshow_id}/items",
                json={
                    "title": "Plain Text Slide",
                    "content_type": "text",
                    "content_text": plain_content,
                    "is_active": True,
                },
                headers=auth_headers,
            )
            assert item_response.status_code in [200, 201]

            # Create a display
            display_name = f"test-plain-display-{int(time.time() * 1000)}"
            display_response = http_client.post(
                "/api/v1/displays",
                json={
                    "name": display_name,
                    "description": "Test display for plain text testing",
                },
                headers=auth_headers,
            )
            assert display_response.status_code in [200, 201]
            display_data = display_response.json().get("data", display_response.json())
            display_id = display_data["id"]

            try:
                # Assign slideshow to display
                assign_response = http_client.post(
                    f"/api/v1/displays/{display_name}/assign-slideshow",
                    json={"slideshow_id": slideshow_id},
                    headers=auth_headers,
                )
                assert assign_response.status_code == 200

                # Navigate to display view
                page.goto(f"{flask_url}/display/{display_name}")
                page.wait_for_load_state("domcontentloaded", timeout=15000)

                # Wait for slideshow to initialize
                page.wait_for_selector("#slideshowContainer", timeout=10000)

                # Wait a moment for content to render
                time.sleep(1)

                # Verify all three lines are visible
                for line in ["Line one", "Line two", "Line three"]:
                    assert page.locator(
                        f"text={line}"
                    ).is_visible(), f"Line '{line}' should be visible in the text slide"

                # Verify line breaks are preserved
                content_element = page.locator(".text-content .content")
                expect(content_element).to_be_visible()

                # Check if line breaks are preserved either by <br> tags or by CSS
                html_content = content_element.inner_html()
                has_br_tags = "<br" in html_content.lower()

                # Get computed style
                computed_style = page.evaluate(
                    """(el) => window.getComputedStyle(el).whiteSpace""",
                    content_element.element_handle(),
                )
                has_whitespace_css = computed_style in ["pre-wrap", "pre-line", "pre"]

                assert has_br_tags or has_whitespace_css, (
                    f"Text content should preserve line breaks. "
                    f"HTML content: '{html_content}', "
                    f"computed white-space: '{computed_style}'. "
                    f"Expected <br> tags or white-space: pre-wrap/pre-line/pre."
                )

            finally:
                # Cleanup display (test_text_slide_plain_text_still_works)
                http_client.delete(
                    f"/api/v1/displays/{display_id}",
                    headers=auth_headers,
                )

        finally:
            # Cleanup slideshow (test_text_slide_plain_text_still_works)
            http_client.delete(
                f"/api/v1/slideshows/{slideshow_id}",
                headers=auth_headers,
            )

    def test_url_slide_with_scale_factor_applies_css_transform(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        http_client,
        auth_headers,
    ):
        """Test that URL slides with scale_factor apply CSS transform scaling.

        This test:
        1. Creates a slideshow with a URL slide that has scale_factor=50
        2. Assigns the slideshow to a display
        3. Navigates to the display view
        4. Verifies the iframe has:
           - transform: scale(0.5) applied
           - Expanded dimensions (200vw × 200vh)
           - A container wrapper with overflow: hidden

        This tests the webpage slide scaling feature for zooming out to show
        more content.
        """
        page = enhanced_page
        flask_url = servers["flask_url"]

        # Create a slideshow
        slideshow_response = http_client.post(
            "/api/v1/slideshows",
            json={
                "name": "URL Scale Test Slideshow",
                "description": "Test slideshow for URL scale factor",
                "default_item_duration": 30,
                "is_active": True,
            },
            headers=auth_headers,
        )
        assert slideshow_response.status_code in [200, 201]
        slideshow_data = slideshow_response.json().get(
            "data", slideshow_response.json()
        )
        slideshow_id = slideshow_data["id"]

        try:
            # Create a URL slide with scale_factor=50 (zoom out to 50%)
            item_response = http_client.post(
                f"/api/v1/slideshows/{slideshow_id}/items",
                json={
                    "title": "Scaled URL Slide",
                    "content_type": "url",
                    "content_url": "https://example.com",
                    "scale_factor": 50,
                    "is_active": True,
                },
                headers=auth_headers,
            )
            assert item_response.status_code in [200, 201]
            item_data = item_response.json().get("data", item_response.json())
            assert item_data["scale_factor"] == 50

            # Create a display
            display_name = f"test-url-scale-display-{int(time.time() * 1000)}"
            display_response = http_client.post(
                "/api/v1/displays",
                json={
                    "name": display_name,
                    "description": "Test display for URL scale testing",
                },
                headers=auth_headers,
            )
            assert display_response.status_code in [200, 201]
            display_data = display_response.json().get("data", display_response.json())
            display_id = display_data["id"]

            try:
                # Assign slideshow to display
                assign_response = http_client.post(
                    f"/api/v1/displays/{display_name}/assign-slideshow",
                    json={"slideshow_id": slideshow_id},
                    headers=auth_headers,
                )
                assert assign_response.status_code == 200

                # Navigate to display view
                page.goto(f"{flask_url}/display/{display_name}")
                page.wait_for_load_state("domcontentloaded", timeout=15000)

                # Wait for slideshow to initialize
                page.wait_for_selector("#slideshowContainer", timeout=10000)

                # Wait a moment for content to render
                time.sleep(1)

                # Verify the scaled iframe container exists
                container = page.locator(".scaled-iframe-container")
                assert container.is_visible(), (
                    "Scaled iframe container should exist for URL slides with "
                    "scale_factor < 100"
                )

                # Verify the iframe has the correct transform scale
                iframe = container.locator("iframe")
                assert iframe.is_visible(), "Iframe should be visible"

                # Check the inline style for transform
                transform_style = iframe.evaluate("""(el) => el.style.transform""")
                assert "scale(0.5)" in transform_style, (
                    f"Iframe should have transform: scale(0.5) for scale_factor=50. "
                    f"Got: {transform_style}"
                )

                # Check the inline style for dimensions (should be 200vw × 200vh)
                width_style = iframe.evaluate("""(el) => el.style.width""")
                height_style = iframe.evaluate("""(el) => el.style.height""")
                assert "200vw" in width_style, (
                    f"Iframe width should be 200vw for scale_factor=50. "
                    f"Got: {width_style}"
                )
                assert "200vh" in height_style, (
                    f"Iframe height should be 200vh for scale_factor=50. "
                    f"Got: {height_style}"
                )

            finally:
                # Cleanup display (test_url_slide_with_scale_factor_applies_css_transform)
                http_client.delete(
                    f"/api/v1/displays/{display_id}",
                    headers=auth_headers,
                )

        finally:
            # Cleanup slideshow (test_url_slide_with_scale_factor_applies_css_transform)
            http_client.delete(
                f"/api/v1/slideshows/{slideshow_id}",
                headers=auth_headers,
            )

    def test_slideshow_transition_type_fade_applies_correct_css_class(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        http_client,
        auth_headers,
    ):
        """Test that fade transition type applies fade-transition CSS class to slides.

        This regression test verifies that when a slideshow is configured with
        transition_type="fade", the display renders slides with the correct
        CSS class for fade animations.
        """
        page = enhanced_page
        flask_url = servers["flask_url"]

        # Create a slideshow with fade transition
        slideshow_response = http_client.post(
            "/api/v1/slideshows",
            json={
                "name": "Fade Transition Test Slideshow",
                "description": "Test slideshow for fade transition",
                "default_item_duration": 30,
                "transition_type": "fade",
                "is_active": True,
            },
            headers=auth_headers,
        )
        assert slideshow_response.status_code in [200, 201]
        slideshow_data = slideshow_response.json().get(
            "data", slideshow_response.json()
        )
        slideshow_id = slideshow_data["id"]

        try:
            # Create a text slide
            item_response = http_client.post(
                f"/api/v1/slideshows/{slideshow_id}/items",
                json={
                    "title": "Fade Test Slide",
                    "content_type": "text",
                    "content_text": "Testing fade transition",
                    "is_active": True,
                },
                headers=auth_headers,
            )
            assert item_response.status_code in [200, 201]

            # Create a display
            display_name = f"test-fade-transition-{int(time.time() * 1000)}"
            display_response = http_client.post(
                "/api/v1/displays",
                json={
                    "name": display_name,
                    "description": "Test display for fade transition",
                },
                headers=auth_headers,
            )
            assert display_response.status_code in [200, 201]
            display_data = display_response.json().get("data", display_response.json())
            display_id = display_data["id"]

            try:
                # Assign slideshow to display
                assign_response = http_client.post(
                    f"/api/v1/displays/{display_name}/assign-slideshow",
                    json={"slideshow_id": slideshow_id},
                    headers=auth_headers,
                )
                assert assign_response.status_code == 200

                # Navigate to display view
                page.goto(f"{flask_url}/display/{display_name}")
                page.wait_for_load_state("domcontentloaded", timeout=15000)
                page.wait_for_selector("#slideshowContainer", timeout=10000)
                time.sleep(1)

                # Verify slide has fade-transition class
                slide_element = page.locator(".slide.active")
                assert slide_element.is_visible(), "Active slide should be visible"

                has_fade_class = page.evaluate("""() => {
                        const slide = document.querySelector('.slide.active');
                        return slide && slide.classList.contains('fade-transition');
                    }""")
                assert (
                    has_fade_class
                ), "Slide with transition_type='fade' should have 'fade-transition' class"

            finally:
                http_client.delete(
                    f"/api/v1/displays/{display_id}",
                    headers=auth_headers,
                )

        finally:
            http_client.delete(
                f"/api/v1/slideshows/{slideshow_id}",
                headers=auth_headers,
            )

    def test_slideshow_transition_type_slide_applies_correct_css_class(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        http_client,
        auth_headers,
    ):
        """Test that slide transition type applies slide-transition CSS class.

        This regression test verifies that when a slideshow is configured with
        transition_type="slide", the display renders slides with the correct
        CSS class for slide animations.
        """
        page = enhanced_page
        flask_url = servers["flask_url"]

        # Create a slideshow with slide transition
        slideshow_response = http_client.post(
            "/api/v1/slideshows",
            json={
                "name": "Slide Transition Test Slideshow",
                "description": "Test slideshow for slide transition",
                "default_item_duration": 30,
                "transition_type": "slide",
                "is_active": True,
            },
            headers=auth_headers,
        )
        assert slideshow_response.status_code in [200, 201]
        slideshow_data = slideshow_response.json().get(
            "data", slideshow_response.json()
        )
        slideshow_id = slideshow_data["id"]

        try:
            # Create a text slide
            item_response = http_client.post(
                f"/api/v1/slideshows/{slideshow_id}/items",
                json={
                    "title": "Slide Test Slide",
                    "content_type": "text",
                    "content_text": "Testing slide transition",
                    "is_active": True,
                },
                headers=auth_headers,
            )
            assert item_response.status_code in [200, 201]

            # Create a display
            display_name = f"test-slide-transition-{int(time.time() * 1000)}"
            display_response = http_client.post(
                "/api/v1/displays",
                json={
                    "name": display_name,
                    "description": "Test display for slide transition",
                },
                headers=auth_headers,
            )
            assert display_response.status_code in [200, 201]
            display_data = display_response.json().get("data", display_response.json())
            display_id = display_data["id"]

            try:
                # Assign slideshow to display
                assign_response = http_client.post(
                    f"/api/v1/displays/{display_name}/assign-slideshow",
                    json={"slideshow_id": slideshow_id},
                    headers=auth_headers,
                )
                assert assign_response.status_code == 200

                # Navigate to display view
                page.goto(f"{flask_url}/display/{display_name}")
                page.wait_for_load_state("domcontentloaded", timeout=15000)
                page.wait_for_selector("#slideshowContainer", timeout=10000)
                time.sleep(1)

                # Verify slide has slide-transition class
                slide_element = page.locator(".slide.active")
                assert slide_element.is_visible(), "Active slide should be visible"

                has_slide_class = page.evaluate("""() => {
                        const slide = document.querySelector('.slide.active');
                        return slide && slide.classList.contains('slide-transition');
                    }""")
                assert has_slide_class, (
                    "Slide with transition_type='slide' should have 'slide-transition' "
                    "class"
                )

            finally:
                http_client.delete(
                    f"/api/v1/displays/{display_id}",
                    headers=auth_headers,
                )

        finally:
            http_client.delete(
                f"/api/v1/slideshows/{slideshow_id}",
                headers=auth_headers,
            )

    def test_slideshow_transition_type_zoom_applies_correct_css_class(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        http_client,
        auth_headers,
    ):
        """Test that zoom transition type applies zoom-transition CSS class.

        This regression test verifies that when a slideshow is configured with
        transition_type="zoom", the display renders slides with the correct
        CSS class for zoom animations.
        """
        page = enhanced_page
        flask_url = servers["flask_url"]

        # Create a slideshow with zoom transition
        slideshow_response = http_client.post(
            "/api/v1/slideshows",
            json={
                "name": "Zoom Transition Test Slideshow",
                "description": "Test slideshow for zoom transition",
                "default_item_duration": 30,
                "transition_type": "zoom",
                "is_active": True,
            },
            headers=auth_headers,
        )
        assert slideshow_response.status_code in [200, 201]
        slideshow_data = slideshow_response.json().get(
            "data", slideshow_response.json()
        )
        slideshow_id = slideshow_data["id"]

        try:
            # Create a text slide
            item_response = http_client.post(
                f"/api/v1/slideshows/{slideshow_id}/items",
                json={
                    "title": "Zoom Test Slide",
                    "content_type": "text",
                    "content_text": "Testing zoom transition",
                    "is_active": True,
                },
                headers=auth_headers,
            )
            assert item_response.status_code in [200, 201]

            # Create a display
            display_name = f"test-zoom-transition-{int(time.time() * 1000)}"
            display_response = http_client.post(
                "/api/v1/displays",
                json={
                    "name": display_name,
                    "description": "Test display for zoom transition",
                },
                headers=auth_headers,
            )
            assert display_response.status_code in [200, 201]
            display_data = display_response.json().get("data", display_response.json())
            display_id = display_data["id"]

            try:
                # Assign slideshow to display
                assign_response = http_client.post(
                    f"/api/v1/displays/{display_name}/assign-slideshow",
                    json={"slideshow_id": slideshow_id},
                    headers=auth_headers,
                )
                assert assign_response.status_code == 200

                # Navigate to display view
                page.goto(f"{flask_url}/display/{display_name}")
                page.wait_for_load_state("domcontentloaded", timeout=15000)
                page.wait_for_selector("#slideshowContainer", timeout=10000)
                time.sleep(1)

                # Verify slide has zoom-transition class
                slide_element = page.locator(".slide.active")
                assert slide_element.is_visible(), "Active slide should be visible"

                has_zoom_class = page.evaluate("""() => {
                        const slide = document.querySelector('.slide.active');
                        return slide && slide.classList.contains('zoom-transition');
                    }""")
                assert has_zoom_class, (
                    "Slide with transition_type='zoom' should have 'zoom-transition' "
                    "class"
                )

            finally:
                http_client.delete(
                    f"/api/v1/displays/{display_id}",
                    headers=auth_headers,
                )

        finally:
            http_client.delete(
                f"/api/v1/slideshows/{slideshow_id}",
                headers=auth_headers,
            )

    def test_slideshow_transition_type_none_applies_correct_css_class(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        http_client,
        auth_headers,
    ):
        """Test that none transition type applies none-transition CSS class.

        This regression test verifies that when a slideshow is configured with
        transition_type="none", the display renders slides with the correct
        CSS class for no animation (immediate switch).
        """
        page = enhanced_page
        flask_url = servers["flask_url"]

        # Create a slideshow with no transition
        slideshow_response = http_client.post(
            "/api/v1/slideshows",
            json={
                "name": "None Transition Test Slideshow",
                "description": "Test slideshow for no transition",
                "default_item_duration": 30,
                "transition_type": "none",
                "is_active": True,
            },
            headers=auth_headers,
        )
        assert slideshow_response.status_code in [200, 201]
        slideshow_data = slideshow_response.json().get(
            "data", slideshow_response.json()
        )
        slideshow_id = slideshow_data["id"]

        try:
            # Create a text slide
            item_response = http_client.post(
                f"/api/v1/slideshows/{slideshow_id}/items",
                json={
                    "title": "None Test Slide",
                    "content_type": "text",
                    "content_text": "Testing no transition",
                    "is_active": True,
                },
                headers=auth_headers,
            )
            assert item_response.status_code in [200, 201]

            # Create a display
            display_name = f"test-none-transition-{int(time.time() * 1000)}"
            display_response = http_client.post(
                "/api/v1/displays",
                json={
                    "name": display_name,
                    "description": "Test display for no transition",
                },
                headers=auth_headers,
            )
            assert display_response.status_code in [200, 201]
            display_data = display_response.json().get("data", display_response.json())
            display_id = display_data["id"]

            try:
                # Assign slideshow to display
                assign_response = http_client.post(
                    f"/api/v1/displays/{display_name}/assign-slideshow",
                    json={"slideshow_id": slideshow_id},
                    headers=auth_headers,
                )
                assert assign_response.status_code == 200

                # Navigate to display view
                page.goto(f"{flask_url}/display/{display_name}")
                page.wait_for_load_state("domcontentloaded", timeout=15000)
                page.wait_for_selector("#slideshowContainer", timeout=10000)
                time.sleep(1)

                # Verify slide has none-transition class
                slide_element = page.locator(".slide.active")
                assert slide_element.is_visible(), "Active slide should be visible"

                has_none_class = page.evaluate("""() => {
                        const slide = document.querySelector('.slide.active');
                        return slide && slide.classList.contains('none-transition');
                    }""")
                assert has_none_class, (
                    "Slide with transition_type='none' should have 'none-transition' "
                    "class"
                )

            finally:
                http_client.delete(
                    f"/api/v1/displays/{display_id}",
                    headers=auth_headers,
                )

        finally:
            http_client.delete(
                f"/api/v1/slideshows/{slideshow_id}",
                headers=auth_headers,
            )

    def test_url_slide_without_scale_factor_has_no_transform(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        http_client,
        auth_headers,
    ):
        """Test that URL slides without scale_factor render normally (no transform).

        This test verifies backwards compatibility - URL slides without scale_factor
        (or scale_factor=100) should render as before without any transform.
        """
        page = enhanced_page
        flask_url = servers["flask_url"]

        # Create a slideshow
        slideshow_response = http_client.post(
            "/api/v1/slideshows",
            json={
                "name": "URL No Scale Test Slideshow",
                "description": "Test slideshow for URL without scale",
                "default_item_duration": 30,
                "is_active": True,
            },
            headers=auth_headers,
        )
        assert slideshow_response.status_code in [200, 201]
        slideshow_data = slideshow_response.json().get(
            "data", slideshow_response.json()
        )
        slideshow_id = slideshow_data["id"]

        try:
            # Create a URL slide without scale_factor (default behavior)
            item_response = http_client.post(
                f"/api/v1/slideshows/{slideshow_id}/items",
                json={
                    "title": "Normal URL Slide",
                    "content_type": "url",
                    "content_url": "https://example.com",
                    # No scale_factor - should be null/100 (no scaling)
                    "is_active": True,
                },
                headers=auth_headers,
            )
            assert item_response.status_code in [200, 201]
            item_data = item_response.json().get("data", item_response.json())
            assert item_data["scale_factor"] is None

            # Create a display
            display_name = f"test-url-noscale-display-{int(time.time() * 1000)}"
            display_response = http_client.post(
                "/api/v1/displays",
                json={
                    "name": display_name,
                    "description": "Test display for URL no scale testing",
                },
                headers=auth_headers,
            )
            assert display_response.status_code in [200, 201]
            display_data = display_response.json().get("data", display_response.json())
            display_id = display_data["id"]

            try:
                # Assign slideshow to display
                assign_response = http_client.post(
                    f"/api/v1/displays/{display_name}/assign-slideshow",
                    json={"slideshow_id": slideshow_id},
                    headers=auth_headers,
                )
                assert assign_response.status_code == 200

                # Navigate to display view
                page.goto(f"{flask_url}/display/{display_name}")
                page.wait_for_load_state("domcontentloaded", timeout=15000)

                # Wait for slideshow to initialize
                page.wait_for_selector("#slideshowContainer", timeout=10000)

                # Wait a moment for content to render
                time.sleep(1)

                # Verify NO scaled iframe container exists
                container = page.locator(".scaled-iframe-container")
                assert not container.is_visible(), (
                    "Scaled iframe container should NOT exist for URL slides "
                    "without scale_factor"
                )

                # Verify the iframe exists directly in the slide (not wrapped)
                iframe = page.locator(".slide.active iframe")
                assert iframe.is_visible(), "Iframe should be visible"

                # Verify no transform scale is applied
                transform_style = iframe.evaluate(
                    """(el) => window.getComputedStyle(el).transform"""
                )
                # "none" or "matrix(1, 0, 0, 1, 0, 0)" = no transform
                has_no_transform = (
                    transform_style == "none"
                    or "matrix(1, 0, 0, 1, 0, 0)" in transform_style
                )
                assert has_no_transform, (
                    f"Iframe should have no transform for URL slides without scale_factor. "
                    f"Got: {transform_style}"
                )

            finally:
                # Cleanup display (test_url_slide_without_scale_factor_has_no_transform)
                http_client.delete(
                    f"/api/v1/displays/{display_id}",
                    headers=auth_headers,
                )

        finally:
            # Cleanup slideshow (test_url_slide_without_scale_factor_has_no_transform)
            http_client.delete(
                f"/api/v1/slideshows/{slideshow_id}",
                headers=auth_headers,
            )

    def test_url_slide_lazy_loads_iframe_when_active(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        http_client,
        auth_headers,
    ):
        """Test that URL slides lazy-load iframes only when becoming active.

        This test verifies the lazy-loading behavior implemented to fix auto-scroll
        issues with embedded web pages. When a URL slide becomes active:
        1. The placeholder is replaced with the actual iframe
        2. The iframe loads when the slide is visible (proper dimensions)

        This ensures auto-scroll JavaScript in embedded pages works correctly.
        """
        page = enhanced_page
        flask_url = servers["flask_url"]

        # Create a slideshow
        slideshow_response = http_client.post(
            "/api/v1/slideshows",
            json={
                "name": "URL Lazy Load Test Slideshow",
                "description": "Test slideshow for URL lazy loading",
                "default_item_duration": 30,
                "is_active": True,
            },
            headers=auth_headers,
        )
        assert slideshow_response.status_code in [200, 201]
        slideshow_data = slideshow_response.json().get(
            "data", slideshow_response.json()
        )
        slideshow_id = slideshow_data["id"]

        try:
            # Create a text slide first (so URL slide is not immediately active)
            text_item_response = http_client.post(
                f"/api/v1/slideshows/{slideshow_id}/items",
                json={
                    "title": "First Text Slide",
                    "content_type": "text",
                    "content_text": "This is the first slide",
                    "is_active": True,
                },
                headers=auth_headers,
            )
            assert text_item_response.status_code in [200, 201]

            # Create a URL slide second
            url_item_response = http_client.post(
                f"/api/v1/slideshows/{slideshow_id}/items",
                json={
                    "title": "URL Slide",
                    "content_type": "url",
                    "content_url": "https://example.com",
                    "is_active": True,
                },
                headers=auth_headers,
            )
            assert url_item_response.status_code in [200, 201]

            # Create a display
            display_name = f"test-url-lazy-load-{int(time.time() * 1000)}"
            display_response = http_client.post(
                "/api/v1/displays",
                json={
                    "name": display_name,
                    "description": "Test display for URL lazy loading",
                },
                headers=auth_headers,
            )
            assert display_response.status_code in [200, 201]
            display_data = display_response.json().get("data", display_response.json())
            display_id = display_data["id"]

            try:
                # Assign slideshow to display
                assign_response = http_client.post(
                    f"/api/v1/displays/{display_name}/assign-slideshow",
                    json={"slideshow_id": slideshow_id},
                    headers=auth_headers,
                )
                assert assign_response.status_code == 200

                # Navigate to display view
                page.goto(f"{flask_url}/display/{display_name}")
                page.wait_for_load_state("domcontentloaded", timeout=15000)

                # Wait for slideshow to initialize
                page.wait_for_selector("#slideshowContainer", timeout=10000)

                # First slide (text) should be active
                time.sleep(0.5)

                # Verify first slide is active and is text content
                first_slide = page.locator("#slide-0")
                assert first_slide.get_attribute("class") is not None
                assert "active" in (first_slide.get_attribute("class") or "")

                # Second slide (URL) should have placeholder, not iframe
                second_slide = page.locator("#slide-1")
                placeholder = second_slide.locator(".url-slide-placeholder")
                iframe_in_second = second_slide.locator("iframe")

                # URL slide should have placeholder initially (not yet active)
                assert (
                    placeholder.count() > 0
                ), "URL slide should have placeholder when not active"
                assert (
                    iframe_in_second.count() == 0
                ), "URL slide should NOT have iframe when not active"

            finally:
                # Cleanup display (test_url_slide_lazy_loads_iframe_when_active)
                http_client.delete(
                    f"/api/v1/displays/{display_id}",
                    headers=auth_headers,
                )

        finally:
            # Cleanup slideshow (test_url_slide_lazy_loads_iframe_when_active)
            http_client.delete(
                f"/api/v1/slideshows/{slideshow_id}",
                headers=auth_headers,
            )

    def test_url_slide_iframe_loads_when_slide_becomes_active(
        self,
        enhanced_page: Page,
        servers: dict,
        test_database: dict,
        http_client,
        auth_headers,
    ):
        """Test that URL slide iframe loads when the slide becomes active.

        This test verifies:
        1. URL slide starts with placeholder
        2. When slide becomes active, placeholder is replaced with iframe
        3. Iframe is properly visible and has correct src

        This tests the core lazy-loading mechanism for URL slides.
        """
        page = enhanced_page
        flask_url = servers["flask_url"]

        # Create a slideshow with short duration for quick transition
        slideshow_response = http_client.post(
            "/api/v1/slideshows",
            json={
                "name": "URL Active Load Test Slideshow",
                "description": "Test slideshow for URL loading on active",
                "default_item_duration": 3,  # Short duration for faster test
                "is_active": True,
            },
            headers=auth_headers,
        )
        assert slideshow_response.status_code in [200, 201]
        slideshow_data = slideshow_response.json().get(
            "data", slideshow_response.json()
        )
        slideshow_id = slideshow_data["id"]

        try:
            # Create a text slide first
            text_item_response = http_client.post(
                f"/api/v1/slideshows/{slideshow_id}/items",
                json={
                    "title": "First Slide",
                    "content_type": "text",
                    "content_text": "Wait for URL slide...",
                    "is_active": True,
                },
                headers=auth_headers,
            )
            assert text_item_response.status_code in [200, 201]

            # Create a URL slide second
            url_item_response = http_client.post(
                f"/api/v1/slideshows/{slideshow_id}/items",
                json={
                    "title": "URL Slide",
                    "content_type": "url",
                    "content_url": "https://example.com",
                    "is_active": True,
                },
                headers=auth_headers,
            )
            assert url_item_response.status_code in [200, 201]

            # Create a display
            display_name = f"test-url-active-load-{int(time.time() * 1000)}"
            display_response = http_client.post(
                "/api/v1/displays",
                json={
                    "name": display_name,
                    "description": "Test display for URL active loading",
                },
                headers=auth_headers,
            )
            assert display_response.status_code in [200, 201]
            display_data = display_response.json().get("data", display_response.json())
            display_id = display_data["id"]

            try:
                # Assign slideshow to display
                assign_response = http_client.post(
                    f"/api/v1/displays/{display_name}/assign-slideshow",
                    json={"slideshow_id": slideshow_id},
                    headers=auth_headers,
                )
                assert assign_response.status_code == 200

                # Navigate to display view
                page.goto(f"{flask_url}/display/{display_name}")
                page.wait_for_load_state("domcontentloaded", timeout=15000)

                # Wait for slideshow to initialize
                page.wait_for_selector("#slideshowContainer", timeout=10000)

                # Wait for transition to URL slide (3 second duration + buffer)
                time.sleep(4)

                # Now URL slide should be active with iframe loaded
                second_slide = page.locator("#slide-1")
                assert second_slide.get_attribute("class") is not None
                assert "active" in (
                    second_slide.get_attribute("class") or ""
                ), "URL slide should be active after transition"

                # Iframe should now exist (placeholder was replaced)
                iframe = second_slide.locator("iframe")
                assert iframe.count() > 0, "URL slide should have iframe when active"
                assert iframe.is_visible(), "Iframe should be visible when active"

                # Verify iframe has correct src
                iframe_src = iframe.get_attribute("src")
                assert (
                    iframe_src == "https://example.com"
                ), f"Iframe src should be https://example.com, got: {iframe_src}"

                # Placeholder should no longer exist
                placeholder = second_slide.locator(".url-slide-placeholder")
                assert (
                    placeholder.count() == 0
                ), "Placeholder should be removed when iframe is loaded"

            finally:
                # Cleanup display (test_url_slide_iframe_loads_when_slide_becomes_active)
                http_client.delete(
                    f"/api/v1/displays/{display_id}",
                    headers=auth_headers,
                )

        finally:
            # Cleanup slideshow (test_url_slide_iframe_loads_when_slide_becomes_active)
            http_client.delete(
                f"/api/v1/slideshows/{slideshow_id}",
                headers=auth_headers,
            )


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("SKIP_BROWSER_TESTS", "false").lower() == "true",
    reason="Browser tests skipped",
)
class TestSkeddaCalendarDisplay:
    """Test Skedda calendar display rendering on kiosk display page.

    These tests verify that the Skedda calendar slide type correctly renders
    calendar data on the kiosk display page, including the calendar grid,
    events, space columns, and recurring event styling.
    """

    @pytest.fixture
    def skedda_test_data(self, db_session, http_client, auth_headers):
        """Create test data for Skedda calendar display tests.

        Creates an ICalFeed, ICalEvents, Slideshow with Skedda item, and Display.

        IMPORTANT: API calls and db_session operations must be carefully ordered
        to avoid SQLite database locks. We create slideshow/display via API first,
        then do all db_session work and commit in one transaction.
        """
        from datetime import datetime, timedelta, timezone

        from kiosk_show_replacement.models import (
            ICalEvent,
            ICalFeed,
            SlideshowItem,
        )

        # Use unique ID for this test run
        unique_id = int(time.time() * 1000)

        # Step 1: Create slideshow and display via API FIRST
        # (no db_session transaction active yet to avoid locks)
        slideshow_response = http_client.post(
            "/api/v1/slideshows",
            json={
                "name": f"Skedda Test Slideshow {unique_id}",
                "description": "Slideshow with Skedda calendar for testing",
                "default_item_duration": 30,
                "is_active": True,
            },
            headers=auth_headers,
        )
        assert slideshow_response.status_code in [
            200,
            201,
        ], f"Failed to create slideshow: {slideshow_response.text}"
        slideshow_data = slideshow_response.json().get(
            "data", slideshow_response.json()
        )
        slideshow_id = slideshow_data["id"]

        display_name = f"skedda-test-display-{unique_id}"
        display_response = http_client.post(
            "/api/v1/displays",
            json={
                "name": display_name,
                "description": "Display for Skedda calendar testing",
            },
            headers=auth_headers,
        )
        assert display_response.status_code in [
            200,
            201,
        ], f"Failed to create display: {display_response.text}"
        display_data = display_response.json().get("data", display_response.json())
        display_id = display_data["id"]

        # Step 2: Now do all db_session work and commit immediately
        # Create ICalFeed
        feed = ICalFeed(
            url=f"https://test.skedda.com/ical/test-feed-{unique_id}.ics",
            last_fetched=datetime.now(timezone.utc),
            last_error=None,
        )
        db_session.add(feed)
        db_session.flush()

        # Create test events for today (use UTC to match API behavior)
        today = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        events = [
            ICalEvent(
                feed_id=feed.id,
                uid=f"event-1-{unique_id}",
                summary="Alice: Laser Cutting",
                description="Laser workshop",
                start_time=today + timedelta(hours=10),
                end_time=today + timedelta(hours=12),
                resources='["Glowforge Laser Cutter"]',
                attendee_name="Alice",
                attendee_email="alice@example.com",
            ),
            ICalEvent(
                feed_id=feed.id,
                uid=f"event-2-{unique_id}",
                summary="Bob: CNC Project",
                description="Custom parts",
                start_time=today + timedelta(hours=14),
                end_time=today + timedelta(hours=16),
                resources='["CNC Milling Machine"]',
                attendee_name="Bob",
                attendee_email="bob@example.com",
            ),
            ICalEvent(
                feed_id=feed.id,
                uid=f"event-3-{unique_id}",
                summary="Open Build Night",
                description="Open Build Night",
                start_time=today + timedelta(hours=18),
                end_time=today + timedelta(hours=21),
                resources='["Glowforge Laser Cutter", "CNC Milling Machine"]',
                attendee_name=None,  # No attendee for recurring/group events
                attendee_email=None,
            ),
            # Event on a DIFFERENT date with a unique space - verifies that
            # all known spaces appear as columns even with no events today
            ICalEvent(
                feed_id=feed.id,
                uid=f"event-4-{unique_id}",
                summary="Charlie: 3D Printing",
                description="Prototype parts",
                start_time=today + timedelta(days=3, hours=10),
                end_time=today + timedelta(days=3, hours=12),
                resources='["3D Printer"]',
                attendee_name="Charlie",
                attendee_email="charlie@example.com",
            ),
        ]
        for event in events:
            db_session.add(event)

        # Create skedda slideshow item linking slideshow to the feed
        skedda_item = SlideshowItem(
            slideshow_id=slideshow_id,
            title="Equipment Calendar",
            content_type="skedda",
            ical_feed_id=feed.id,
            ical_refresh_minutes=15,
            order_index=0,
            is_active=True,
            display_duration=30,
        )
        db_session.add(skedda_item)

        # Commit all db_session changes
        db_session.commit()

        # Step 3: Assign slideshow to display via API
        # (db_session transaction is now complete)
        assign_response = http_client.post(
            f"/api/v1/displays/{display_name}/assign-slideshow",
            json={"slideshow_id": slideshow_id},
            headers=auth_headers,
        )
        assert (
            assign_response.status_code == 200
        ), f"Failed to assign slideshow: {assign_response.text}"

        yield {
            "feed": feed,
            "events": events,
            "slideshow_id": slideshow_id,
            "slideshow_item": skedda_item,
            "display_id": display_id,
            "display_name": display_name,
        }

        # Cleanup - best effort, don't fail tests if cleanup fails
        # (resources may already be deleted if test failed mid-way, and
        # database isolation ensures leftover data won't affect other tests)
        try:
            http_client.delete(
                f"/api/v1/displays/{display_id}",
                headers=auth_headers,
            )
        except Exception:
            pass  # Ignore cleanup failures - see comment above

        try:
            http_client.delete(
                f"/api/v1/slideshows/{slideshow_id}",
                headers=auth_headers,
            )
        except Exception:
            pass  # Ignore cleanup failures - see comment above

        # Clean up database records - rollback on failure to release any locks
        try:
            db_session.query(ICalEvent).filter(ICalEvent.feed_id == feed.id).delete()
            db_session.query(ICalFeed).filter(ICalFeed.id == feed.id).delete()
            db_session.commit()
        except Exception:
            db_session.rollback()  # Release locks if cleanup query failed

    def test_skedda_calendar_renders_grid(
        self,
        enhanced_page: Page,
        servers: dict,
        skedda_test_data: dict,
    ):
        """Test that Skedda calendar slide renders the calendar grid.

        Verifies:
        1. Calendar container is present
        2. Date header is displayed
        3. Space headers are shown
        4. Time slots are rendered
        """
        page = enhanced_page
        flask_url = servers["flask_url"]
        display_name = skedda_test_data["display_name"]

        # Navigate to the display page
        page.goto(f"{flask_url}/display/{display_name}")
        page.wait_for_load_state("load")

        # Verify the skedda calendar container appears
        calendar = page.locator(".skedda-calendar")
        expect(calendar).to_be_visible(timeout=10000)

        # Verify the date header is present
        date_header = page.locator(".skedda-date-header")
        expect(date_header).to_be_visible()
        date_text = date_header.inner_text()
        assert len(date_text) > 0, "Date header should have text"

        # Verify space headers are rendered
        space_headers = page.locator(".skedda-space-header")
        expect(space_headers.first).to_be_visible(timeout=5000)

        # Verify time slots are rendered
        time_slots = page.locator(".skedda-time-slot")
        expect(time_slots.first).to_be_visible()

    def test_skedda_calendar_displays_events(
        self,
        enhanced_page: Page,
        servers: dict,
        skedda_test_data: dict,
    ):
        """Test that Skedda calendar displays event blocks.

        Verifies:
        1. Event elements are rendered
        2. Event person name is displayed
        3. Event has text content
        """
        page = enhanced_page
        flask_url = servers["flask_url"]
        display_name = skedda_test_data["display_name"]

        # Navigate to the display page
        page.goto(f"{flask_url}/display/{display_name}")
        page.wait_for_load_state("load")

        # Wait for calendar to load
        calendar = page.locator(".skedda-calendar")
        expect(calendar).to_be_visible(timeout=10000)

        # Wait for events to be rendered
        event_elements = page.locator(".skedda-event")
        expect(event_elements.first).to_be_visible(timeout=10000)

        # Verify at least one event is displayed
        event_count = event_elements.count()
        assert event_count >= 1, f"Expected at least 1 event, found {event_count}"

        # Check that event content is present (person name or description)
        event_person = page.locator(".skedda-event-person")
        expect(event_person.first).to_be_visible()

        # Verify event has text content
        first_event_text = event_person.first.inner_text()
        assert len(first_event_text) > 0, "Event should have person name or description"

    def test_skedda_calendar_space_columns(
        self,
        enhanced_page: Page,
        servers: dict,
        skedda_test_data: dict,
    ):
        """Test that Skedda calendar displays correct space columns.

        Verifies that space headers match the equipment/resources from events.
        """
        page = enhanced_page
        flask_url = servers["flask_url"]
        display_name = skedda_test_data["display_name"]

        # Navigate to the display page
        page.goto(f"{flask_url}/display/{display_name}")
        page.wait_for_load_state("load")

        # Wait for calendar to load
        calendar = page.locator(".skedda-calendar")
        expect(calendar).to_be_visible(timeout=10000)

        # Get all space headers
        space_headers = page.locator(".skedda-space-header")
        expect(space_headers.first).to_be_visible(timeout=10000)

        # Collect space names
        header_count = space_headers.count()
        space_names = []
        for i in range(header_count):
            space_names.append(space_headers.nth(i).inner_text())

        # Should have at least 2 spaces (from our test events)
        assert len(space_names) >= 2, f"Expected at least 2 spaces, found {space_names}"

        # Check that expected spaces are present
        all_text = " ".join(space_names)
        assert (
            "Glowforge" in all_text or "CNC" in all_text
        ), f"Expected equipment names in headers, got: {space_names}"

    def test_skedda_calendar_shows_recurring_events_differently(
        self,
        enhanced_page: Page,
        servers: dict,
        skedda_test_data: dict,
    ):
        """Test that recurring/group events (no person name) are styled differently.

        The 'Open Build Night' event has no attendee_name, so it should have
        the 'skedda-event-recurring' class for different styling.
        """
        page = enhanced_page
        flask_url = servers["flask_url"]
        display_name = skedda_test_data["display_name"]

        # Navigate to the display page
        page.goto(f"{flask_url}/display/{display_name}")
        page.wait_for_load_state("load")

        # Wait for calendar to load
        calendar = page.locator(".skedda-calendar")
        expect(calendar).to_be_visible(timeout=10000)

        # Wait for events
        events = page.locator(".skedda-event")
        expect(events.first).to_be_visible(timeout=10000)

        # Look for recurring event styling
        recurring_events = page.locator(".skedda-event-recurring")

        # Should have at least one recurring event (Open Build Night)
        recurring_count = recurring_events.count()
        assert (
            recurring_count >= 1
        ), "Expected at least one recurring event with different styling"

    def test_skedda_calendar_loading_state(
        self,
        enhanced_page: Page,
        servers: dict,
        skedda_test_data: dict,
    ):
        """Test that loading state transitions to calendar successfully.

        Verifies that the calendar loads and the loading indicator disappears.
        """
        page = enhanced_page
        flask_url = servers["flask_url"]
        display_name = skedda_test_data["display_name"]

        # Navigate to the display page
        page.goto(f"{flask_url}/display/{display_name}")

        # The calendar should eventually appear
        calendar = page.locator(".skedda-calendar")
        expect(calendar).to_be_visible(timeout=10000)

        # Verify calendar loaded successfully (loading element should be hidden)
        loading = page.locator(".skedda-loading")
        try:
            expect(loading).to_be_hidden(timeout=5000)
        except Exception:
            # If loading is still visible, the calendar didn't render properly
            assert False, "Calendar should have loaded - loading state still visible"

    def test_skedda_calendar_shows_all_spaces(
        self,
        enhanced_page: Page,
        servers: dict,
        skedda_test_data: dict,
    ):
        """Test that all known spaces appear as columns, even with no events today.

        The fixture includes a '3D Printer' event on a future date with no events
        today. The calendar should still show a '3D Printer' column.
        """
        page = enhanced_page
        flask_url = servers["flask_url"]
        display_name = skedda_test_data["display_name"]

        # Navigate to the display page
        page.goto(f"{flask_url}/display/{display_name}")
        page.wait_for_load_state("load")

        # Wait for calendar to load
        calendar = page.locator(".skedda-calendar")
        expect(calendar).to_be_visible(timeout=10000)

        # Get all space headers
        space_headers = page.locator(".skedda-space-header")
        expect(space_headers.first).to_be_visible(timeout=10000)

        # Collect space names
        header_count = space_headers.count()
        space_names = []
        for i in range(header_count):
            space_names.append(space_headers.nth(i).inner_text())

        # Should have 3 spaces: Glowforge, CNC, and 3D Printer
        assert (
            len(space_names) == 3
        ), f"Expected 3 space columns (including empty ones), found {space_names}"

        all_text = " ".join(space_names)
        assert "3D Printer" in all_text, (
            f"Expected '3D Printer' column for space with no events today, "
            f"got: {space_names}"
        )
