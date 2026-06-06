"""
Unit tests for the API v1 endpoints.

Tests all REST API functionality including:
- Slideshow CRUD operations
- Slideshow item management
- Display management
- Authentication and authorization
- Error handling and validation
"""

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from kiosk_show_replacement.models import (
    AssignmentHistory,
    Display,
    ICalEvent,
    ICalFeed,
    Slideshow,
    SlideshowItem,
    User,
    db,
)


class TestSlideshowAPI:
    """Test slideshow CRUD API endpoints."""

    def test_list_slideshows_requires_auth(self, client):
        """Test that listing slideshows requires authentication."""
        response = client.get("/api/v1/slideshows")
        assert response.status_code == 401  # API returns 401 Unauthorized

    def test_list_slideshows_empty(self, client, authenticated_user):
        """Test listing slideshows when none exist."""
        response = client.get("/api/v1/slideshows")
        assert response.status_code == 200

        data = response.get_json()
        assert data["success"] is True
        assert data["data"] == []
        assert "message" in data

    def test_list_slideshows_with_data(
        self, client, authenticated_user, sample_slideshow
    ):
        """Test listing slideshows with existing data."""
        response = client.get("/api/v1/slideshows")
        assert response.status_code == 200

        data = response.get_json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["name"] == sample_slideshow.name
        assert "item_count" in data["data"][0]

    def test_create_slideshow_success(self, client, authenticated_user):
        """Test successful slideshow creation."""
        slideshow_data = {
            "name": "Test Slideshow",
            "description": "A test slideshow",
            "default_item_duration": 10,
        }

        response = client.post(
            "/api/v1/slideshows",
            data=json.dumps(slideshow_data),
            content_type="application/json",
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["name"] == "Test Slideshow"
        assert data["data"]["description"] == "A test slideshow"
        assert data["data"]["default_item_duration"] == 10

    def test_create_slideshow_missing_name(self, client, authenticated_user):
        """Test slideshow creation with missing name."""
        slideshow_data = {"description": "No name provided"}

        response = client.post(
            "/api/v1/slideshows",
            data=json.dumps(slideshow_data),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "errors" in data

    def test_create_slideshow_duplicate_name(
        self, client, authenticated_user, sample_slideshow
    ):
        """Test slideshow creation with duplicate name."""
        slideshow_data = {
            "name": sample_slideshow.name,
            "description": "Duplicate name",
        }

        response = client.post(
            "/api/v1/slideshows",
            data=json.dumps(slideshow_data),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "already exists" in data["message"]

    def test_get_slideshow_success(
        self, client, authenticated_user, sample_slideshow_with_items
    ):
        """Test successful slideshow retrieval."""
        slideshow, items = sample_slideshow_with_items

        response = client.get(f"/api/v1/slideshows/{slideshow.id}")
        assert response.status_code == 200

        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["name"] == slideshow.name
        assert "items" in data["data"]
        assert len(data["data"]["items"]) == len(items)

    def test_get_slideshow_not_found(self, client, authenticated_user):
        """Test slideshow retrieval with non-existent ID."""
        response = client.get("/api/v1/slideshows/999")
        assert response.status_code == 404

        data = response.get_json()
        assert data["success"] is False

    def test_get_slideshow_filters_inactive_items_by_default(
        self, client, authenticated_user, sample_slideshow_with_items
    ):
        """Test that inactive items are filtered out by default."""
        slideshow, items = sample_slideshow_with_items

        # Mark one item as inactive
        items[0].is_active = False
        db.session.commit()

        response = client.get(f"/api/v1/slideshows/{slideshow.id}")
        assert response.status_code == 200

        data = response.get_json()
        assert data["success"] is True
        # Should only return active items
        assert len(data["data"]["items"]) == len(items) - 1

        # Verify the inactive item is not in the response
        item_ids = [item["id"] for item in data["data"]["items"]]
        assert items[0].id not in item_ids

    def test_get_slideshow_include_inactive_items(
        self, client, authenticated_user, sample_slideshow_with_items
    ):
        """Test that inactive items are included when include_inactive=true."""
        slideshow, items = sample_slideshow_with_items

        # Mark one item as inactive
        items[0].is_active = False
        db.session.commit()

        response = client.get(
            f"/api/v1/slideshows/{slideshow.id}?include_inactive=true"
        )
        assert response.status_code == 200

        data = response.get_json()
        assert data["success"] is True
        # Should return all items including inactive
        assert len(data["data"]["items"]) == len(items)

        # Verify the inactive item is in the response with is_active=False
        item_ids = [item["id"] for item in data["data"]["items"]]
        assert items[0].id in item_ids

        inactive_item = next(i for i in data["data"]["items"] if i["id"] == items[0].id)
        assert inactive_item["is_active"] is False

    def test_update_slideshow_success(
        self, client, authenticated_user, sample_slideshow
    ):
        """Test successful slideshow update."""
        update_data = {
            "name": "Updated Slideshow",
            "description": "Updated description",
        }

        response = client.put(
            f"/api/v1/slideshows/{sample_slideshow.id}",
            data=json.dumps(update_data),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["name"] == "Updated Slideshow"
        assert data["data"]["description"] == "Updated description"

    def test_update_slideshow_default_item_duration(
        self, client, authenticated_user, sample_slideshow
    ):
        """Test updating slideshow default_item_duration."""
        update_data = {"default_item_duration": 45}

        response = client.put(
            f"/api/v1/slideshows/{sample_slideshow.id}",
            data=json.dumps(update_data),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["default_item_duration"] == 45

        # Verify persisted in database
        slideshow = db.session.get(Slideshow, sample_slideshow.id)
        assert slideshow.default_item_duration == 45

    def test_update_slideshow_default_item_duration_invalid(
        self, client, authenticated_user, sample_slideshow
    ):
        """Test updating slideshow with invalid default_item_duration."""
        # Test negative value
        response = client.put(
            f"/api/v1/slideshows/{sample_slideshow.id}",
            data=json.dumps({"default_item_duration": -5}),
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        # Check that error mentions the field (in error_info.details.field)
        assert (
            data.get("error_info", {}).get("details", {}).get("field")
            == "default_item_duration"
        )

        # Test zero value
        response = client.put(
            f"/api/v1/slideshows/{sample_slideshow.id}",
            data=json.dumps({"default_item_duration": 0}),
            content_type="application/json",
        )
        assert response.status_code == 400

        # Test non-integer value
        response = client.put(
            f"/api/v1/slideshows/{sample_slideshow.id}",
            data=json.dumps({"default_item_duration": "thirty"}),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_update_slideshow_transition_type(
        self, client, authenticated_user, sample_slideshow
    ):
        """Test updating slideshow transition_type."""
        update_data = {"transition_type": "slide"}

        response = client.put(
            f"/api/v1/slideshows/{sample_slideshow.id}",
            data=json.dumps(update_data),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["transition_type"] == "slide"

        # Verify persisted in database
        slideshow = db.session.get(Slideshow, sample_slideshow.id)
        assert slideshow.transition_type == "slide"

    def test_update_slideshow_is_default(
        self, client, authenticated_user, sample_slideshow, sample_user
    ):
        """Test updating slideshow is_default clears other defaults."""
        # Create another slideshow that is default
        other_slideshow = Slideshow(
            name="Other Slideshow",
            owner_id=sample_user.id,
            is_default=True,
        )
        db.session.add(other_slideshow)
        db.session.commit()

        # Set sample_slideshow as default
        update_data = {"is_default": True}
        response = client.put(
            f"/api/v1/slideshows/{sample_slideshow.id}",
            data=json.dumps(update_data),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["is_default"] is True

        # Verify other slideshow is no longer default
        db.session.refresh(other_slideshow)
        assert other_slideshow.is_default is False

    def test_update_slideshow_multiple_fields(
        self, client, authenticated_user, sample_slideshow
    ):
        """Test updating multiple slideshow fields at once."""
        update_data = {
            "name": "Multi-Update Test",
            "description": "Updated desc",
            "default_item_duration": 60,
            "transition_type": "none",
        }

        response = client.put(
            f"/api/v1/slideshows/{sample_slideshow.id}",
            data=json.dumps(update_data),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["name"] == "Multi-Update Test"
        assert data["data"]["description"] == "Updated desc"
        assert data["data"]["default_item_duration"] == 60
        assert data["data"]["transition_type"] == "none"

    def test_update_slideshow_sse_event_includes_slideshow_name(
        self, client, authenticated_user, sample_slideshow
    ):
        """Test that SSE event for slideshow update includes slideshow_name field."""
        update_data = {"name": "SSE Test Slideshow"}

        with patch(
            "kiosk_show_replacement.api.v1.create_slideshow_event"
        ) as mock_create_event:
            # Return a MagicMock that behaves like an SSEEvent
            mock_create_event.return_value = MagicMock()

            response = client.put(
                f"/api/v1/slideshows/{sample_slideshow.id}",
                data=json.dumps(update_data),
                content_type="application/json",
            )

            assert response.status_code == 200

            # Verify create_slideshow_event was called
            mock_create_event.assert_called_once()

            # Get the data argument passed to create_slideshow_event
            call_args = mock_create_event.call_args
            event_data = call_args[0][2]  # Third positional argument is data

            # Verify slideshow_name is present and correct
            assert "slideshow_name" in event_data
            assert event_data["slideshow_name"] == "SSE Test Slideshow"

    def test_delete_slideshow_success(
        self, client, authenticated_user, sample_slideshow
    ):
        """Test successful slideshow deletion."""
        response = client.delete(f"/api/v1/slideshows/{sample_slideshow.id}")
        assert response.status_code == 200

        data = response.get_json()
        assert data["success"] is True

        # Verify slideshow is soft-deleted
        slideshow = db.session.get(Slideshow, sample_slideshow.id)
        assert slideshow.is_active is False

    def test_delete_slideshow_assigned_to_display(
        self, client, authenticated_user, sample_slideshow
    ):
        """Test slideshow deletion when assigned to display."""
        # Create display assigned to slideshow
        display = Display(name="test-display", current_slideshow_id=sample_slideshow.id)
        db.session.add(display)
        db.session.commit()

        response = client.delete(f"/api/v1/slideshows/{sample_slideshow.id}")
        assert response.status_code == 400

        data = response.get_json()
        assert data["success"] is False
        assert "assigned to displays" in data["message"]

    def test_set_default_slideshow(self, client, authenticated_user, sample_slideshow):
        """Test setting slideshow as default."""
        response = client.post(f"/api/v1/slideshows/{sample_slideshow.id}/set-default")
        assert response.status_code == 200

        data = response.get_json()
        assert data["success"] is True

        # Verify slideshow is marked as default
        slideshow = db.session.get(Slideshow, sample_slideshow.id)
        assert slideshow.is_default is True

    def test_create_slideshow_with_is_default(self, client, authenticated_user):
        """Test creating a slideshow with is_default=True."""
        slideshow_data = {
            "name": "Default Slideshow",
            "description": "A slideshow created as default",
            "is_default": True,
        }

        response = client.post(
            "/api/v1/slideshows",
            data=json.dumps(slideshow_data),
            content_type="application/json",
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["name"] == "Default Slideshow"
        assert data["data"]["is_default"] is True

        # Verify in database
        slideshow_id = data["data"]["id"]
        slideshow = db.session.get(Slideshow, slideshow_id)
        assert slideshow.is_default is True

    def test_create_slideshow_with_is_default_clears_existing_default(
        self, client, authenticated_user, sample_slideshow
    ):
        """Test creating a new default slideshow clears existing default."""
        # First, set the sample_slideshow as default
        sample_slideshow.is_default = True
        db.session.commit()

        # Now create a new slideshow with is_default=True
        slideshow_data = {
            "name": "New Default Slideshow",
            "description": "A new default slideshow",
            "is_default": True,
        }

        response = client.post(
            "/api/v1/slideshows",
            data=json.dumps(slideshow_data),
            content_type="application/json",
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["is_default"] is True

        # Verify the old default is no longer default
        db.session.refresh(sample_slideshow)
        assert sample_slideshow.is_default is False

        # Verify the new slideshow is the only default
        new_slideshow_id = data["data"]["id"]
        new_slideshow = db.session.get(Slideshow, new_slideshow_id)
        assert new_slideshow.is_default is True


class TestSlideshowDuplicateAPI:
    """Test the slideshow duplicate API endpoint."""

    def test_duplicate_slideshow_success(
        self, client, authenticated_user, sample_slideshow_with_items
    ):
        """Test duplicating a slideshow copies settings and all items."""
        slideshow, items = sample_slideshow_with_items

        # Make one item inactive to verify inactive items are copied too
        items[1].is_active = False
        db.session.commit()

        response = client.post(
            f"/api/v1/slideshows/{slideshow.id}/duplicate",
            data=json.dumps({"name": "Copied Slideshow"}),
            content_type="application/json",
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["name"] == "Copied Slideshow"
        assert data["data"]["id"] != slideshow.id
        assert data["data"]["is_default"] is False
        assert data["data"]["owner_id"] == authenticated_user.id

        # Verify slideshow settings were copied
        duplicate = db.session.get(Slideshow, data["data"]["id"])
        assert duplicate.description == slideshow.description
        assert duplicate.default_item_duration == slideshow.default_item_duration
        assert duplicate.transition_type == slideshow.transition_type
        assert duplicate.is_active is True

        # Verify all items were copied (including the inactive one),
        # preserving order and content
        source_items = sorted(slideshow.items, key=lambda i: i.order_index)
        copied_items = sorted(duplicate.items, key=lambda i: i.order_index)
        assert len(copied_items) == len(source_items)
        for source_item, copied_item in zip(source_items, copied_items):
            assert copied_item.id != source_item.id
            assert copied_item.title == source_item.title
            assert copied_item.content_type == source_item.content_type
            assert copied_item.content_url == source_item.content_url
            assert copied_item.content_text == source_item.content_text
            assert copied_item.display_duration == source_item.display_duration
            assert copied_item.order_index == source_item.order_index
            assert copied_item.is_active == source_item.is_active
            assert copied_item.scale_factor == source_item.scale_factor

    def test_duplicate_slideshow_does_not_copy_default_flag(
        self, client, authenticated_user, sample_slideshow
    ):
        """Test that duplicating the default slideshow does not copy the flag."""
        sample_slideshow.is_default = True
        db.session.commit()

        response = client.post(
            f"/api/v1/slideshows/{sample_slideshow.id}/duplicate",
            data=json.dumps({"name": "Copy of Default"}),
            content_type="application/json",
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["data"]["is_default"] is False

        # The original is still the default
        db.session.refresh(sample_slideshow)
        assert sample_slideshow.is_default is True

    def test_duplicate_slideshow_duplicate_name(
        self, client, authenticated_user, sample_slideshow
    ):
        """Test duplicating with an existing slideshow name fails."""
        response = client.post(
            f"/api/v1/slideshows/{sample_slideshow.id}/duplicate",
            data=json.dumps({"name": sample_slideshow.name}),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "already exists" in data["message"]

    def test_duplicate_slideshow_missing_name(
        self, client, authenticated_user, sample_slideshow
    ):
        """Test duplicating without a name fails."""
        response = client.post(
            f"/api/v1/slideshows/{sample_slideshow.id}/duplicate",
            data=json.dumps({"name": "   "}),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False

    def test_duplicate_slideshow_no_data(
        self, client, authenticated_user, sample_slideshow
    ):
        """Test duplicating without a request body fails."""
        response = client.post(
            f"/api/v1/slideshows/{sample_slideshow.id}/duplicate",
            data=json.dumps(None),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False

    def test_duplicate_slideshow_name_conflict_with_inactive(
        self, client, authenticated_user, sample_slideshow
    ):
        """Test the unique-constraint backstop for name conflicts.

        An inactive slideshow's name passes the active-only duplicate-name
        check but still violates the (name, owner_id) unique constraint when
        the new row is flushed, exercising the IntegrityError handler.
        """
        inactive = Slideshow(
            name="Shadowed Name",
            owner_id=authenticated_user.id,
            is_active=False,
        )
        db.session.add(inactive)
        db.session.commit()

        response = client.post(
            f"/api/v1/slideshows/{sample_slideshow.id}/duplicate",
            data=json.dumps({"name": "Shadowed Name"}),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "already exists" in data["message"]

    @patch("kiosk_show_replacement.api.v1.get_storage_manager")
    def test_duplicate_slideshow_cleanup_on_failure(
        self,
        mock_get_storage,
        client,
        authenticated_user,
        sample_slideshow,
        tmp_path,
    ):
        """Test that copied files are removed when the duplicate fails."""
        from kiosk_show_replacement.storage import StorageManager

        storage = StorageManager(str(tmp_path))
        mock_get_storage.return_value = storage

        # Give the source a file-backed item so the duplicate copies a file
        source_dir = (
            tmp_path / "images" / str(authenticated_user.id) / str(sample_slideshow.id)
        )
        source_dir.mkdir(parents=True)
        source_file = source_dir / "photo.png"
        source_file.write_bytes(b"fake png content")
        item = SlideshowItem(
            slideshow_id=sample_slideshow.id,
            title="Uploaded Image",
            content_type="image",
            content_file_path=str(source_file.relative_to(tmp_path)),
            order_index=1,
            is_active=True,
        )
        db.session.add(item)
        db.session.commit()

        # Fail the final commit, after items are processed and files copied
        with patch.object(
            db.session, "commit", side_effect=RuntimeError("simulated commit failure")
        ):
            response = client.post(
                f"/api/v1/slideshows/{sample_slideshow.id}/duplicate",
                data=json.dumps({"name": "Doomed Copy"}),
                content_type="application/json",
            )

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False

        # The copied file was cleaned up; only the source file remains
        assert [p for p in tmp_path.rglob("*") if p.is_file()] == [source_file]

        # No duplicate slideshow was persisted
        assert (
            Slideshow.query.filter_by(name="Doomed Copy").first() is None
        )

    def test_duplicate_slideshow_not_found(self, client, authenticated_user):
        """Test duplicating a non-existent slideshow returns 404."""
        response = client.post(
            "/api/v1/slideshows/99999/duplicate",
            data=json.dumps({"name": "Copy of Nothing"}),
            content_type="application/json",
        )

        assert response.status_code == 404

    def test_duplicate_inactive_slideshow_not_found(
        self, client, authenticated_user, sample_slideshow
    ):
        """Test duplicating a soft-deleted slideshow returns 404."""
        sample_slideshow.is_active = False
        db.session.commit()

        response = client.post(
            f"/api/v1/slideshows/{sample_slideshow.id}/duplicate",
            data=json.dumps({"name": "Copy of Deleted"}),
            content_type="application/json",
        )

        assert response.status_code == 404

    def test_duplicate_slideshow_requires_auth(self, client, sample_slideshow):
        """Test duplicating requires authentication."""
        response = client.post(
            f"/api/v1/slideshows/{sample_slideshow.id}/duplicate",
            data=json.dumps({"name": "Unauthenticated Copy"}),
            content_type="application/json",
        )

        assert response.status_code == 401

    @patch("kiosk_show_replacement.api.v1.get_storage_manager")
    def test_duplicate_slideshow_copies_uploaded_files(
        self,
        mock_get_storage,
        client,
        authenticated_user,
        sample_slideshow,
        tmp_path,
    ):
        """Test duplicating copies uploaded media files on disk."""
        from kiosk_show_replacement.storage import StorageManager

        storage = StorageManager(str(tmp_path))
        mock_get_storage.return_value = storage

        # Create a fake uploaded image in the source slideshow's directory
        source_dir = (
            tmp_path / "images" / str(authenticated_user.id) / str(sample_slideshow.id)
        )
        source_dir.mkdir(parents=True)
        source_file = source_dir / "photo.png"
        source_file.write_bytes(b"fake png content")
        relative_path = str(source_file.relative_to(tmp_path))

        item = SlideshowItem(
            slideshow_id=sample_slideshow.id,
            title="Uploaded Image",
            content_type="image",
            content_file_path=relative_path,
            order_index=1,
            is_active=True,
        )
        db.session.add(item)
        db.session.commit()

        response = client.post(
            f"/api/v1/slideshows/{sample_slideshow.id}/duplicate",
            data=json.dumps({"name": "Copy With Files"}),
            content_type="application/json",
        )

        assert response.status_code == 201
        data = response.get_json()
        duplicate = db.session.get(Slideshow, data["data"]["id"])

        copied_item = next(i for i in duplicate.items if i.title == "Uploaded Image")
        # The copy references a new file in the duplicate's directory
        assert copied_item.content_file_path is not None
        assert copied_item.content_file_path != relative_path
        assert copied_item.content_file_path.startswith(
            f"images/{authenticated_user.id}/{duplicate.id}/"
        )
        copied_file = tmp_path / copied_item.content_file_path
        assert copied_file.is_file()
        assert copied_file.read_bytes() == b"fake png content"
        # The original file is untouched
        assert source_file.is_file()

    @patch("kiosk_show_replacement.api.v1.get_storage_manager")
    def test_duplicate_slideshow_tolerates_missing_file(
        self,
        mock_get_storage,
        client,
        authenticated_user,
        sample_slideshow,
        tmp_path,
    ):
        """Test duplicating succeeds even if a source file is missing."""
        from kiosk_show_replacement.storage import StorageManager

        storage = StorageManager(str(tmp_path))
        mock_get_storage.return_value = storage

        item = SlideshowItem(
            slideshow_id=sample_slideshow.id,
            title="Missing File Image",
            content_type="image",
            content_file_path="images/1/1/does_not_exist.png",
            order_index=1,
            is_active=True,
        )
        db.session.add(item)
        db.session.commit()

        response = client.post(
            f"/api/v1/slideshows/{sample_slideshow.id}/duplicate",
            data=json.dumps({"name": "Copy Missing File"}),
            content_type="application/json",
        )

        assert response.status_code == 201
        data = response.get_json()
        duplicate = db.session.get(Slideshow, data["data"]["id"])
        copied_item = next(
            i for i in duplicate.items if i.title == "Missing File Image"
        )
        # The item is copied but without a file reference
        assert copied_item.content_file_path is None


class TestSlideshowItemAPI:
    """Test slideshow item management API endpoints."""

    def test_list_slideshow_items(
        self, client, authenticated_user, sample_slideshow_with_items
    ):
        """Test listing slideshow items."""
        slideshow, items = sample_slideshow_with_items

        response = client.get(f"/api/v1/slideshows/{slideshow.id}/items")
        assert response.status_code == 200

        data = response.get_json()
        assert data["success"] is True
        assert len(data["data"]) == len(items)

    def test_list_slideshow_items_filters_inactive_by_default(
        self, client, authenticated_user, sample_slideshow_with_items
    ):
        """Test that inactive items are filtered out by default."""
        slideshow, items = sample_slideshow_with_items

        # Mark one item as inactive
        items[0].is_active = False
        db.session.commit()

        response = client.get(f"/api/v1/slideshows/{slideshow.id}/items")
        assert response.status_code == 200

        data = response.get_json()
        assert data["success"] is True
        # Should only return active items (all except the one we marked inactive)
        assert len(data["data"]) == len(items) - 1

        # Verify the inactive item is not in the response
        item_ids = [item["id"] for item in data["data"]]
        assert items[0].id not in item_ids

    def test_list_slideshow_items_include_inactive(
        self, client, authenticated_user, sample_slideshow_with_items
    ):
        """Test that inactive items are included when include_inactive=true."""
        slideshow, items = sample_slideshow_with_items

        # Mark one item as inactive
        items[0].is_active = False
        db.session.commit()

        response = client.get(
            f"/api/v1/slideshows/{slideshow.id}/items?include_inactive=true"
        )
        assert response.status_code == 200

        data = response.get_json()
        assert data["success"] is True
        # Should return all items including inactive
        assert len(data["data"]) == len(items)

        # Verify the inactive item is in the response with is_active=False
        item_ids = [item["id"] for item in data["data"]]
        assert items[0].id in item_ids

        inactive_item = next(i for i in data["data"] if i["id"] == items[0].id)
        assert inactive_item["is_active"] is False

    def test_list_skedda_items_includes_ical_url(
        self, app, client, authenticated_user, sample_slideshow
    ):
        """Test that listing items includes ical_url for skedda items.

        Regression test: the list endpoint must include the ical_url field
        from the related ICalFeed so the edit form can populate it.
        """
        with app.app_context():
            feed = ICalFeed(url="https://app.skedda.com/ical/test-feed.ics")
            db.session.add(feed)
            db.session.flush()

            item = SlideshowItem(
                slideshow_id=sample_slideshow.id,
                title="Skedda Calendar",
                content_type="skedda",
                ical_feed_id=feed.id,
                ical_refresh_minutes=15,
                order_index=0,
            )
            db.session.add(item)
            db.session.commit()

            response = client.get(f"/api/v1/slideshows/{sample_slideshow.id}/items")
            assert response.status_code == 200

            data = response.get_json()
            assert data["success"] is True

            # Find the skedda item among all items in the slideshow
            skedda_items = [i for i in data["data"] if i["content_type"] == "skedda"]
            assert len(skedda_items) == 1
            skedda_item = skedda_items[0]
            assert skedda_item["ical_feed_id"] == feed.id
            assert skedda_item["ical_refresh_minutes"] == 15
            assert (
                "ical_url" in skedda_item
            ), "ical_url must be present in list response for skedda items"
            assert skedda_item["ical_url"] == (
                "https://app.skedda.com/ical/test-feed.ics"
            )

    def test_create_slideshow_item_success(
        self, client, authenticated_user, sample_slideshow
    ):
        """Test successful slideshow item creation."""
        item_data = {
            "title": "Test Item",
            "content_type": "image",
            "content_url": "https://example.com/image.jpg",
            "display_duration": 15,
        }

        response = client.post(
            f"/api/v1/slideshows/{sample_slideshow.id}/items",
            data=json.dumps(item_data),
            content_type="application/json",
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["title"] == "Test Item"
        assert data["data"]["content_type"] == "image"

    def test_create_slideshow_item_missing_content_type(
        self, client, authenticated_user, sample_slideshow
    ):
        """Test slideshow item creation with missing content type."""
        item_data = {"title": "Invalid Item"}

        response = client.post(
            f"/api/v1/slideshows/{sample_slideshow.id}/items",
            data=json.dumps(item_data),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "errors" in data

    def test_create_slideshow_item_invalid_content_type(
        self, client, authenticated_user, sample_slideshow
    ):
        """Test slideshow item creation with invalid content type."""
        item_data = {
            "content_type": "invalid_type",
            "content_url": "https://example.com/test",
        }

        response = client.post(
            f"/api/v1/slideshows/{sample_slideshow.id}/items",
            data=json.dumps(item_data),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False

    def test_update_slideshow_item(
        self, client, authenticated_user, sample_slideshow_with_items
    ):
        """Test slideshow item update."""
        slideshow, items = sample_slideshow_with_items
        item = items[0]

        update_data = {"title": "Updated Item", "display_duration": 20}

        response = client.put(
            f"/api/v1/slideshow-items/{item.id}",
            data=json.dumps(update_data),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["title"] == "Updated Item"
        assert data["data"]["display_duration"] == 20

    def test_update_inactive_slideshow_item(
        self, client, authenticated_user, sample_slideshow_with_items
    ):
        """Test that inactive slideshow items can be updated (e.g., reactivated)."""
        slideshow, items = sample_slideshow_with_items
        item = items[0]

        # Mark the item as inactive first
        item.is_active = False
        db.session.commit()

        # Should still be able to update the inactive item
        update_data = {"is_active": True, "title": "Reactivated Item"}

        response = client.put(
            f"/api/v1/slideshow-items/{item.id}",
            data=json.dumps(update_data),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["is_active"] is True
        assert data["data"]["title"] == "Reactivated Item"

    def test_delete_slideshow_item(
        self, client, authenticated_user, sample_slideshow_with_items
    ):
        """Test slideshow item deletion."""
        slideshow, items = sample_slideshow_with_items
        item = items[0]

        response = client.delete(f"/api/v1/slideshow-items/{item.id}")
        assert response.status_code == 200

        data = response.get_json()
        assert data["success"] is True

        # Verify item is soft-deleted
        deleted_item = db.session.get(SlideshowItem, item.id)
        assert deleted_item.is_active is False

    def test_delete_inactive_slideshow_item(
        self, client, authenticated_user, sample_slideshow_with_items
    ):
        """Test that deleting an inactive item permanently removes it."""
        slideshow, items = sample_slideshow_with_items
        item = items[0]
        item_id = item.id

        # Mark the item as inactive first (equivalent to a prior soft delete)
        item.is_active = False
        db.session.commit()

        response = client.delete(f"/api/v1/slideshow-items/{item_id}")
        assert response.status_code == 200

        data = response.get_json()
        assert data["success"] is True

        # Verify the item is permanently removed from the database
        assert db.session.get(SlideshowItem, item_id) is None

    def test_delete_active_then_inactive_slideshow_item(
        self, client, authenticated_user, sample_slideshow_with_items
    ):
        """Test the two-stage delete: first soft-delete, then hard delete."""
        slideshow, items = sample_slideshow_with_items
        item = items[0]
        item_id = item.id

        # First delete: soft delete (item becomes inactive)
        response = client.delete(f"/api/v1/slideshow-items/{item_id}")
        assert response.status_code == 200
        soft_deleted = db.session.get(SlideshowItem, item_id)
        assert soft_deleted is not None
        assert soft_deleted.is_active is False

        # Second delete: hard delete (item is permanently removed)
        response = client.delete(f"/api/v1/slideshow-items/{item_id}")
        assert response.status_code == 200
        assert db.session.get(SlideshowItem, item_id) is None

    def test_reorder_slideshow_item(
        self, client, authenticated_user, sample_slideshow_with_items
    ):
        """Test slideshow item reordering."""
        slideshow, items = sample_slideshow_with_items
        item = items[0]  # First item

        reorder_data = {"new_order": 3}  # Move to position 3

        response = client.post(
            f"/api/v1/slideshow-items/{item.id}/reorder",
            data=json.dumps(reorder_data),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    def test_create_slideshow_item_with_scale_factor(
        self, client, authenticated_user, sample_slideshow
    ):
        """Test creating a URL slideshow item with scale_factor."""
        item_data = {
            "title": "Scaled URL Slide",
            "content_type": "url",
            "content_url": "https://example.com/page",
            "display_duration": 30,
            "scale_factor": 50,
        }

        response = client.post(
            f"/api/v1/slideshows/{sample_slideshow.id}/items",
            data=json.dumps(item_data),
            content_type="application/json",
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["scale_factor"] == 50

    def test_create_slideshow_item_scale_factor_null(
        self, client, authenticated_user, sample_slideshow
    ):
        """Test creating a URL slideshow item with null scale_factor."""
        item_data = {
            "title": "URL Slide No Scale",
            "content_type": "url",
            "content_url": "https://example.com/page",
            "scale_factor": None,
        }

        response = client.post(
            f"/api/v1/slideshows/{sample_slideshow.id}/items",
            data=json.dumps(item_data),
            content_type="application/json",
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["scale_factor"] is None

    def test_create_slideshow_item_scale_factor_invalid_too_low(
        self, client, authenticated_user, sample_slideshow
    ):
        """Test creating slideshow item with scale_factor below 10."""
        item_data = {
            "content_type": "url",
            "content_url": "https://example.com/page",
            "scale_factor": 5,
        }

        response = client.post(
            f"/api/v1/slideshows/{sample_slideshow.id}/items",
            data=json.dumps(item_data),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Scale factor" in data["errors"][0]

    def test_create_slideshow_item_scale_factor_invalid_too_high(
        self, client, authenticated_user, sample_slideshow
    ):
        """Test creating slideshow item with scale_factor above 100."""
        item_data = {
            "content_type": "url",
            "content_url": "https://example.com/page",
            "scale_factor": 150,
        }

        response = client.post(
            f"/api/v1/slideshows/{sample_slideshow.id}/items",
            data=json.dumps(item_data),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Scale factor" in data["errors"][0]

    def test_update_slideshow_item_scale_factor(
        self, client, authenticated_user, sample_slideshow_with_items
    ):
        """Test updating slideshow item scale_factor."""
        slideshow, items = sample_slideshow_with_items
        # Find a URL item or create one
        url_item = next((i for i in items if i.content_type == "url"), None)
        if not url_item:
            # Create a URL item for testing
            url_item = SlideshowItem(
                slideshow_id=slideshow.id,
                content_type="url",
                content_url="https://example.com/test",
                order_index=100,
            )
            db.session.add(url_item)
            db.session.commit()

        update_data = {"scale_factor": 75}

        response = client.put(
            f"/api/v1/slideshow-items/{url_item.id}",
            data=json.dumps(update_data),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["scale_factor"] == 75

    def test_update_slideshow_item_scale_factor_to_null(
        self, client, authenticated_user, sample_slideshow_with_items
    ):
        """Test updating slideshow item scale_factor to null (remove scaling)."""
        slideshow, items = sample_slideshow_with_items
        # Create a URL item with scale_factor
        url_item = SlideshowItem(
            slideshow_id=slideshow.id,
            content_type="url",
            content_url="https://example.com/test",
            order_index=100,
            scale_factor=50,
        )
        db.session.add(url_item)
        db.session.commit()

        update_data = {"scale_factor": None}

        response = client.put(
            f"/api/v1/slideshow-items/{url_item.id}",
            data=json.dumps(update_data),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["scale_factor"] is None

    def test_update_slideshow_item_scale_factor_invalid(
        self, client, authenticated_user, sample_slideshow_with_items
    ):
        """Test updating slideshow item with invalid scale_factor."""
        slideshow, items = sample_slideshow_with_items
        item = items[0]

        update_data = {"scale_factor": 5}  # Below minimum

        response = client.put(
            f"/api/v1/slideshow-items/{item.id}",
            data=json.dumps(update_data),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Scale factor" in data["errors"][0]


class TestVideoURLValidation:
    """Test video URL validation API endpoint and slideshow item validation."""

    @patch("kiosk_show_replacement.api.v1.get_storage_manager")
    def test_validate_video_url_success(
        self, mock_get_storage, client, authenticated_user
    ):
        """Test successful video URL validation."""
        # Mock storage manager
        mock_storage = MagicMock()
        mock_storage.validate_video_url.return_value = (
            True,  # is_valid
            120.5,  # duration
            {"video_codec": "h264", "audio_codec": "aac", "container_format": "mp4"},
            "",  # error_message
        )
        mock_get_storage.return_value = mock_storage

        response = client.post(
            "/api/v1/validate/video-url",
            data=json.dumps({"url": "https://example.com/video.mp4"}),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["valid"] is True
        assert data["data"]["duration_seconds"] == 120  # Rounded (banker's rounding)
        assert data["data"]["duration"] == 120.5  # Exact
        assert data["data"]["codec_info"]["video_codec"] == "h264"

    @patch("kiosk_show_replacement.api.v1.get_storage_manager")
    def test_validate_video_url_no_duration(
        self, mock_get_storage, client, authenticated_user
    ):
        """Test video URL validation when duration cannot be detected."""
        mock_storage = MagicMock()
        mock_storage.validate_video_url.return_value = (
            True,
            None,  # No duration
            {"video_codec": "vp9", "audio_codec": None, "container_format": "webm"},
            "",
        )
        mock_get_storage.return_value = mock_storage

        response = client.post(
            "/api/v1/validate/video-url",
            data=json.dumps({"url": "https://example.com/video.webm"}),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["valid"] is True
        assert data["data"]["duration_seconds"] is None
        assert data["data"]["duration"] is None

    @patch("kiosk_show_replacement.api.v1.get_storage_manager")
    def test_validate_video_url_unsupported_codec(
        self, mock_get_storage, client, authenticated_user
    ):
        """Test video URL validation with unsupported codec."""
        mock_storage = MagicMock()
        mock_storage.validate_video_url.return_value = (
            False,
            None,
            {
                "video_codec": "mpeg2video",
                "audio_codec": "mp2",
                "container_format": "mpeg",
            },
            "Video codec 'mpeg2video' is not supported by web browsers.",
        )
        mock_get_storage.return_value = mock_storage

        response = client.post(
            "/api/v1/validate/video-url",
            data=json.dumps({"url": "https://example.com/video.mpeg"}),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "mpeg2video" in data["errors"][0]

    def test_validate_video_url_missing_url(self, client, authenticated_user):
        """Test validation fails when URL is missing."""
        response = client.post(
            "/api/v1/validate/video-url",
            data=json.dumps({}),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False

    def test_validate_video_url_invalid_format(self, client, authenticated_user):
        """Test validation fails for invalid URL format."""
        response = client.post(
            "/api/v1/validate/video-url",
            data=json.dumps({"url": "/path/to/video.mp4"}),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False

    def test_validate_video_url_requires_auth(self, client):
        """Test validation endpoint requires authentication."""
        response = client.post(
            "/api/v1/validate/video-url",
            data=json.dumps({"url": "https://example.com/video.mp4"}),
            content_type="application/json",
        )

        # Should fail with 401 or redirect to login
        assert response.status_code in [401, 302]

    @patch("kiosk_show_replacement.api.v1.get_storage_manager")
    def test_create_slideshow_item_video_url_valid(
        self, mock_get_storage, client, authenticated_user, sample_slideshow
    ):
        """Test creating video item with valid URL passes validation."""
        mock_storage = MagicMock()
        mock_storage.validate_video_url.return_value = (
            True,
            60.0,
            {"video_codec": "h264", "audio_codec": "aac", "container_format": "mp4"},
            "",
        )
        mock_get_storage.return_value = mock_storage

        item_data = {
            "title": "Video from URL",
            "content_type": "video",
            "content_url": "https://example.com/video.mp4",
            "display_duration": 60,
        }

        response = client.post(
            f"/api/v1/slideshows/{sample_slideshow.id}/items",
            data=json.dumps(item_data),
            content_type="application/json",
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["content_type"] == "video"
        assert data["data"]["content_url"] == "https://example.com/video.mp4"

    @patch("kiosk_show_replacement.api.v1.get_storage_manager")
    def test_create_slideshow_item_video_url_invalid_codec(
        self, mock_get_storage, client, authenticated_user, sample_slideshow
    ):
        """Test creating video item with unsupported codec is rejected."""
        mock_storage = MagicMock()
        mock_storage.validate_video_url.return_value = (
            False,
            None,
            None,
            "Video codec 'wmv3' is not supported by web browsers.",
        )
        mock_get_storage.return_value = mock_storage

        item_data = {
            "title": "WMV Video",
            "content_type": "video",
            "content_url": "https://example.com/video.wmv",
        }

        response = client.post(
            f"/api/v1/slideshows/{sample_slideshow.id}/items",
            data=json.dumps(item_data),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "wmv3" in data["errors"][0]

    def test_create_slideshow_item_video_with_file_skips_url_validation(
        self, client, authenticated_user, sample_slideshow
    ):
        """Test creating video item with file path doesn't validate URL."""
        # When file_path is provided, URL validation should be skipped
        item_data = {
            "title": "Uploaded Video",
            "content_type": "video",
            "content_file_path": "uploads/videos/1/1/video.mp4",
            "display_duration": 30,
        }

        response = client.post(
            f"/api/v1/slideshows/{sample_slideshow.id}/items",
            data=json.dumps(item_data),
            content_type="application/json",
        )

        # Should succeed without trying to validate any URL
        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True

    @patch("kiosk_show_replacement.api.v1.get_storage_manager")
    def test_update_slideshow_item_video_url_valid(
        self, mock_get_storage, client, authenticated_user, sample_slideshow_with_items
    ):
        """Test updating video item to new URL validates the URL."""
        slideshow, items = sample_slideshow_with_items
        item = items[0]

        mock_storage = MagicMock()
        mock_storage.validate_video_url.return_value = (
            True,
            90.0,
            {"video_codec": "vp9", "audio_codec": "opus", "container_format": "webm"},
            "",
        )
        mock_get_storage.return_value = mock_storage

        update_data = {
            "content_type": "video",
            "content_url": "https://example.com/new-video.webm",
            "content_file_path": None,  # Clear file path
        }

        response = client.put(
            f"/api/v1/slideshow-items/{item.id}",
            data=json.dumps(update_data),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    @patch("kiosk_show_replacement.api.v1.get_storage_manager")
    def test_update_slideshow_item_video_url_invalid(
        self, mock_get_storage, client, authenticated_user, sample_slideshow_with_items
    ):
        """Test updating video item to invalid URL is rejected."""
        slideshow, items = sample_slideshow_with_items
        item = items[0]

        mock_storage = MagicMock()
        mock_storage.validate_video_url.return_value = (
            False,
            None,
            None,
            "Could not retrieve video information from the URL.",
        )
        mock_get_storage.return_value = mock_storage

        update_data = {
            "content_type": "video",
            "content_url": "https://example.com/nonexistent.mp4",
        }

        response = client.put(
            f"/api/v1/slideshow-items/{item.id}",
            data=json.dumps(update_data),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False


class TestSkeddaAPI:
    """Test Skedda/iCal API endpoints."""

    def test_create_skedda_item_success(
        self, client, authenticated_user, sample_slideshow
    ):
        """Test successful skedda slideshow item creation."""
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:test-event-123
SUMMARY:Test Event
DTSTART:20260128T120000Z
DTEND:20260128T140000Z
END:VEVENT
END:VCALENDAR"""

        with patch(
            "kiosk_show_replacement.ical_service.fetch_ics_from_url"
        ) as mock_fetch:
            mock_fetch.return_value = ics_content

            item_data = {
                "title": "Machine Schedule",
                "content_type": "skedda",
                "ical_url": "https://example.com/calendar.ics",
                "ical_refresh_minutes": 30,
            }

            response = client.post(
                f"/api/v1/slideshows/{sample_slideshow.id}/items",
                data=json.dumps(item_data),
                content_type="application/json",
            )

            assert response.status_code == 201
            data = response.get_json()
            assert data["success"] is True
            assert data["data"]["content_type"] == "skedda"
            assert data["data"]["ical_url"] == "https://example.com/calendar.ics"
            assert data["data"]["ical_refresh_minutes"] == 30

    def test_create_skedda_item_missing_url(
        self, client, authenticated_user, sample_slideshow
    ):
        """Test skedda item creation without iCal URL fails."""
        item_data = {
            "title": "Machine Schedule",
            "content_type": "skedda",
        }

        response = client.post(
            f"/api/v1/slideshows/{sample_slideshow.id}/items",
            data=json.dumps(item_data),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "iCal URL is required" in data["errors"][0]

    def test_create_skedda_item_invalid_url(
        self, client, authenticated_user, sample_slideshow
    ):
        """Test skedda item creation with invalid URL fails."""
        item_data = {
            "title": "Machine Schedule",
            "content_type": "skedda",
            "ical_url": "not-a-valid-url",
        }

        response = client.post(
            f"/api/v1/slideshows/{sample_slideshow.id}/items",
            data=json.dumps(item_data),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "valid HTTP/HTTPS URL" in data["errors"][0]

    def test_create_skedda_item_unreachable_url(
        self, client, authenticated_user, sample_slideshow
    ):
        """Test skedda item creation with unreachable URL fails."""
        with patch(
            "kiosk_show_replacement.ical_service.fetch_ics_from_url"
        ) as mock_fetch:
            mock_fetch.return_value = None  # Simulate fetch failure

            item_data = {
                "title": "Machine Schedule",
                "content_type": "skedda",
                "ical_url": "https://example.com/calendar.ics",
            }

            response = client.post(
                f"/api/v1/slideshows/{sample_slideshow.id}/items",
                data=json.dumps(item_data),
                content_type="application/json",
            )

            assert response.status_code == 400
            data = response.get_json()
            assert data["success"] is False
            assert "validation failed" in data["errors"][0]

    def test_create_skedda_item_invalid_refresh_minutes(
        self, client, authenticated_user, sample_slideshow
    ):
        """Test skedda item creation with invalid refresh interval fails."""
        item_data = {
            "title": "Machine Schedule",
            "content_type": "skedda",
            "ical_url": "https://example.com/calendar.ics",
            "ical_refresh_minutes": 0,  # Must be >= 1
        }

        response = client.post(
            f"/api/v1/slideshows/{sample_slideshow.id}/items",
            data=json.dumps(item_data),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Refresh interval" in data["errors"][0]

    def test_update_skedda_item_refresh_minutes(
        self, app, client, authenticated_user, sample_slideshow
    ):
        """Test updating skedda item refresh interval."""
        with app.app_context():
            # Create a feed and item first
            feed = ICalFeed(
                url="https://example.com/calendar.ics",
                last_fetched=datetime.now(timezone.utc),
            )
            db.session.add(feed)
            db.session.commit()

            item = SlideshowItem(
                slideshow_id=sample_slideshow.id,
                title="Machine Schedule",
                content_type="skedda",
                ical_feed_id=feed.id,
                ical_refresh_minutes=15,
                order_index=1,
                created_by_id=authenticated_user.id,
                updated_by_id=authenticated_user.id,
            )
            db.session.add(item)
            db.session.commit()
            item_id = item.id

            update_data = {"ical_refresh_minutes": 60}

            response = client.put(
                f"/api/v1/slideshow-items/{item_id}",
                data=json.dumps(update_data),
                content_type="application/json",
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
            assert data["data"]["ical_refresh_minutes"] == 60

    def test_get_skedda_data_success(
        self, app, client, authenticated_user, sample_slideshow
    ):
        """Test getting skedda calendar data."""
        with app.app_context():
            # Create feed with event
            feed = ICalFeed(
                url="https://example.com/calendar.ics",
                last_fetched=datetime.now(timezone.utc),
            )
            db.session.add(feed)
            db.session.commit()

            event = ICalEvent(
                feed_id=feed.id,
                uid="event-1",
                summary="John Doe: Project (Laser Cutter)",
                start_time=datetime(2026, 1, 28, 17, 0, tzinfo=timezone.utc),
                end_time=datetime(2026, 1, 28, 19, 0, tzinfo=timezone.utc),
                resources=json.dumps(["Laser Cutter"]),
            )
            db.session.add(event)

            item = SlideshowItem(
                slideshow_id=sample_slideshow.id,
                title="Machine Schedule",
                content_type="skedda",
                ical_feed_id=feed.id,
                ical_refresh_minutes=15,
                order_index=1,
                created_by_id=authenticated_user.id,
                updated_by_id=authenticated_user.id,
            )
            db.session.add(item)
            db.session.commit()
            item_id = item.id

            with patch(
                "kiosk_show_replacement.ical_service.refresh_feed_if_needed"
            ) as mock_refresh:
                mock_refresh.return_value = False

                response = client.get(
                    f"/api/v1/slideshow-items/{item_id}/skedda-data?date=2026-01-28"
                )

                assert response.status_code == 200
                data = response.get_json()
                assert data["success"] is True
                assert data["data"]["date"] == "2026-01-28"
                assert "Laser Cutter" in data["data"]["spaces"]
                assert len(data["data"]["events"]) == 1

    def test_get_skedda_data_non_skedda_item(
        self, app, client, authenticated_user, sample_slideshow
    ):
        """Test getting skedda data for non-skedda item fails."""
        with app.app_context():
            item = SlideshowItem(
                slideshow_id=sample_slideshow.id,
                title="Regular Image",
                content_type="image",
                content_url="https://example.com/image.jpg",
                order_index=1,
                created_by_id=authenticated_user.id,
                updated_by_id=authenticated_user.id,
            )
            db.session.add(item)
            db.session.commit()
            item_id = item.id

            response = client.get(f"/api/v1/slideshow-items/{item_id}/skedda-data")

            assert response.status_code == 400
            data = response.get_json()
            assert data["success"] is False
            assert "not a Skedda calendar" in data["errors"][0]

    def test_get_skedda_data_invalid_date(
        self, app, client, authenticated_user, sample_slideshow
    ):
        """Test getting skedda data with invalid date format fails."""
        with app.app_context():
            feed = ICalFeed(
                url="https://example.com/calendar.ics",
                last_fetched=datetime.now(timezone.utc),
            )
            db.session.add(feed)
            db.session.commit()

            item = SlideshowItem(
                slideshow_id=sample_slideshow.id,
                title="Machine Schedule",
                content_type="skedda",
                ical_feed_id=feed.id,
                order_index=1,
                created_by_id=authenticated_user.id,
                updated_by_id=authenticated_user.id,
            )
            db.session.add(item)
            db.session.commit()
            item_id = item.id

            response = client.get(
                f"/api/v1/slideshow-items/{item_id}/skedda-data?date=invalid"
            )

            assert response.status_code == 400
            data = response.get_json()
            assert data["success"] is False
            assert "Invalid date format" in data["errors"][0]

    def test_refresh_all_feeds_success(self, app, client, authenticated_user):
        """Test refreshing all iCal feeds."""
        with app.app_context():
            feed1 = ICalFeed(url="https://example.com/cal1.ics")
            feed2 = ICalFeed(url="https://example.com/cal2.ics")
            db.session.add_all([feed1, feed2])
            db.session.commit()

            with patch(
                "kiosk_show_replacement.api.v1.refresh_all_feeds"
            ) as mock_refresh:
                mock_refresh.return_value = {"refreshed": 2, "errors": []}

                response = client.post("/api/v1/ical-feeds/refresh")

                assert response.status_code == 200
                data = response.get_json()
                assert data["success"] is True
                assert data["data"]["refreshed"] == 2
                assert data["data"]["errors"] == []

    def test_refresh_all_feeds_with_errors(self, app, client, authenticated_user):
        """Test refreshing feeds with some errors."""
        with app.app_context():
            feed = ICalFeed(url="https://example.com/cal.ics")
            db.session.add(feed)
            db.session.commit()
            feed_id = feed.id

            with patch(
                "kiosk_show_replacement.api.v1.refresh_all_feeds"
            ) as mock_refresh:
                mock_refresh.return_value = {
                    "refreshed": 0,
                    "errors": [
                        {
                            "feed_id": feed_id,
                            "url": "https://example.com/cal.ics",
                            "error": "Connection timeout",
                        }
                    ],
                }

                response = client.post("/api/v1/ical-feeds/refresh")

                assert response.status_code == 200
                data = response.get_json()
                assert data["success"] is True
                assert data["data"]["refreshed"] == 0
                assert len(data["data"]["errors"]) == 1


class TestDisplayAPI:
    """Test display management API endpoints."""

    def test_list_displays(self, client, authenticated_user):
        """Test listing displays."""
        # Create test display
        display = Display(name="test-display", owner_id=authenticated_user.id)
        db.session.add(display)
        db.session.commit()

        response = client.get("/api/v1/displays")
        assert response.status_code == 200

        data = response.get_json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["name"] == "test-display"

    def test_get_display(self, client, authenticated_user):
        """Test getting display details."""
        display = Display(name="test-display", owner_id=authenticated_user.id)
        db.session.add(display)
        db.session.commit()

        response = client.get(f"/api/v1/displays/{display.id}")
        assert response.status_code == 200

        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["name"] == "test-display"
        assert "online" in data["data"]

    def test_update_display_slideshow_assignment(
        self, client, authenticated_user, sample_slideshow
    ):
        """Test updating display slideshow assignment."""
        display = Display(name="test-display", owner_id=authenticated_user.id)
        db.session.add(display)
        db.session.commit()

        update_data = {"current_slideshow_id": sample_slideshow.id}

        response = client.put(
            f"/api/v1/displays/{display.id}",
            data=json.dumps(update_data),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["current_slideshow_id"] == sample_slideshow.id

    def test_delete_display(self, client, authenticated_user):
        """Test display deletion."""
        display = Display(name="test-display", owner_id=authenticated_user.id)
        db.session.add(display)
        db.session.commit()
        display_id = display.id

        response = client.delete(f"/api/v1/displays/{display_id}")
        assert response.status_code == 200

        data = response.get_json()
        assert data["success"] is True

        # Verify display is deleted
        deleted_display = db.session.get(Display, display_id)
        assert deleted_display is None

    def test_delete_display_with_assignment_history(
        self, client, authenticated_user, sample_slideshow
    ):
        """Test that deleting a display cascades to delete assignment history.

        This test verifies the fix for the bug where deleting a display with
        assignment history records would fail with a foreign key constraint
        violation (HTTP 500 error).
        """
        # Create a display
        display = Display(name="test-display-history", owner_id=authenticated_user.id)
        db.session.add(display)
        db.session.commit()
        display_id = display.id

        # Create assignment history records for this display
        history1 = AssignmentHistory(
            display_id=display_id,
            new_slideshow_id=sample_slideshow.id,
            action="assign",
            created_by_id=authenticated_user.id,
        )
        history2 = AssignmentHistory(
            display_id=display_id,
            previous_slideshow_id=sample_slideshow.id,
            action="unassign",
            created_by_id=authenticated_user.id,
        )
        db.session.add(history1)
        db.session.add(history2)
        db.session.commit()

        history1_id = history1.id
        history2_id = history2.id

        # Verify assignment history exists
        assert db.session.get(AssignmentHistory, history1_id) is not None
        assert db.session.get(AssignmentHistory, history2_id) is not None

        # Delete the display - this should succeed with CASCADE DELETE
        response = client.delete(f"/api/v1/displays/{display_id}")
        assert response.status_code == 200

        data = response.get_json()
        assert data["success"] is True

        # Verify display is deleted
        deleted_display = db.session.get(Display, display_id)
        assert deleted_display is None

        # Verify assignment history is also deleted (CASCADE DELETE)
        assert db.session.get(AssignmentHistory, history1_id) is None
        assert db.session.get(AssignmentHistory, history2_id) is None

    def test_reload_display_success(self, client, authenticated_user):
        """Test successfully sending reload command to a display."""
        display = Display(name="test-display-reload", owner_id=authenticated_user.id)
        db.session.add(display)
        db.session.commit()

        response = client.post(f"/api/v1/displays/{display.id}/reload")
        assert response.status_code == 200

        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["display_id"] == display.id
        assert "connections_notified" in data["data"]
        assert "Reload command sent" in data["message"]

    def test_reload_display_not_found(self, client, authenticated_user):
        """Test reload command for non-existent display returns 404."""
        response = client.post("/api/v1/displays/99999/reload")
        assert response.status_code == 404

        data = response.get_json()
        assert data["success"] is False
        assert "not found" in data["error"].lower()

    def test_reload_display_requires_authentication(self, app):
        """Test that reload endpoint requires authentication."""
        # Create a fresh client without authentication
        with app.test_client() as unauthenticated_client:
            # Create a display for testing
            with app.app_context():
                user = User(username="test-reload-auth", email="reload@test.com")
                user.set_password("password")
                db.session.add(user)
                db.session.commit()

                display = Display(name="test-display-auth", owner_id=user.id)
                db.session.add(display)
                db.session.commit()
                display_id = display.id

            response = unauthenticated_client.post(
                f"/api/v1/displays/{display_id}/reload"
            )
            # Should redirect to login or return 401/302
            assert response.status_code in [302, 401]


class TestAPIAuthentication:
    """Test API authentication and authorization."""

    def test_api_requires_authentication(self, client):
        """Test that all API endpoints require authentication."""
        endpoints = [
            ("/api/v1/slideshows", "GET"),
            ("/api/v1/slideshows", "POST"),
            ("/api/v1/slideshows/1", "GET"),
            ("/api/v1/displays", "GET"),
        ]

        for endpoint, method in endpoints:
            response = getattr(client, method.lower())(endpoint)
            assert response.status_code in [
                302,
                401,
            ]  # Redirect to login or unauthorized

    def test_api_access_control(self, client, app):
        """Test API access control - global access model allows all users to see all data."""  # noqa: E501
        # Create two users
        with app.app_context():
            user1 = User(username="user1", email="user1@example.com")
            user1.set_password("password")
            user2 = User(username="user2", email="user2@example.com")
            user2.set_password("password")
            db.session.add_all([user1, user2])
            db.session.commit()

            # User 1 creates a slideshow
            slideshow = Slideshow(
                name="User1 Slideshow", owner_id=user1.id, is_active=True
            )
            db.session.add(slideshow)
            db.session.commit()
            slideshow_id = slideshow.id

        # Login as user2
        client.post("/auth/login", data={"username": "user2", "password": "password"})

        # User2 should be able to access user1's slideshow (global access model)
        response = client.get(f"/api/v1/slideshows/{slideshow_id}")
        assert response.status_code == 200

        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["name"] == "User1 Slideshow"


class TestAPIStatusEndpoint:
    """Test API status and health endpoints."""

    def test_api_status_endpoint(self, client):
        """Test API status endpoint."""
        response = client.get("/api/v1/status")
        assert response.status_code == 200

        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["api_version"] == "v1"
        assert data["data"]["status"] == "healthy"
        assert "timestamp" in data["data"]


class TestAPIAuthenticationEndpoints:
    """Test API authentication endpoints."""

    def test_api_login_fails_for_nonexistent_user(self, client, app):
        """Test API login returns 401 for non-existent user."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "nonexistent", "password": "password"},
            content_type="application/json",
        )

        assert response.status_code == 401
        data = response.get_json()
        assert data["success"] is False
        assert "Invalid username or password" in data["error"]

    def test_api_login_fails_for_wrong_password(self, client, app):
        """Test API login returns 401 for wrong password."""
        with app.app_context():
            # Create existing user
            user = User(username="existinguser", email="test@example.com")
            user.set_password("correctpassword")
            db.session.add(user)
            db.session.commit()

        # Test login with wrong password
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "existinguser", "password": "wrongpassword"},
            content_type="application/json",
        )

        assert response.status_code == 401
        data = response.get_json()
        assert data["success"] is False
        assert "Invalid username or password" in data["error"]

    def test_api_login_fails_for_inactive_user(self, client, app):
        """Test API login returns 403 for inactive user."""
        with app.app_context():
            # Create inactive user
            user = User(username="inactiveuser", email="inactive@example.com")
            user.set_password("password")
            user.is_active = False
            db.session.add(user)
            db.session.commit()

        response = client.post(
            "/api/v1/auth/login",
            json={"username": "inactiveuser", "password": "password"},
            content_type="application/json",
        )

        assert response.status_code == 403
        data = response.get_json()
        assert data["success"] is False
        assert "inactive" in data["error"].lower()

    def test_api_login_success_existing_user(self, client, app):
        """Test successful API login with existing user."""
        with app.app_context():
            # Create existing user
            user = User(username="existinguser", email="test@example.com")
            user.set_password("password")
            user.is_admin = False
            db.session.add(user)
            db.session.commit()
            user_id = user.id

        # Test login with correct password
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "existinguser", "password": "password"},
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["message"] == "Login successful"

        user_data = data["data"]
        assert user_data["username"] == "existinguser"
        assert user_data["id"] == user_id
        assert user_data["is_admin"] is False

    def test_api_login_session_creation(self, client, app):
        """Test API login creates proper session."""
        with app.app_context():
            # Create user
            user = User(username="sessionuser", email="session@example.com")
            user.set_password("sessionpass")
            user.is_admin = True
            db.session.add(user)
            db.session.commit()

        response = client.post(
            "/api/v1/auth/login",
            json={"username": "sessionuser", "password": "sessionpass"},
            content_type="application/json",
        )

        assert response.status_code == 200

        # Verify session was created
        with client.session_transaction() as sess:
            assert "user_id" in sess
            assert sess["username"] == "sessionuser"
            assert sess["is_admin"] is True

    def test_api_login_no_json_data(self, client):
        """Test API login fails with no JSON data."""
        response = client.post("/api/v1/auth/login")

        assert (
            response.status_code == 415
        )  # Flask returns 415 for missing JSON content type
        # Flask's 415 error doesn't include JSON response body
        assert response.content_type != "application/json"

    def test_api_login_empty_username(self, client):
        """Test API login fails with empty username."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "", "password": "password"},
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert data["error"] == "Username is required"

    def test_api_login_missing_username(self, client):
        """Test API login fails with missing username."""
        response = client.post(
            "/api/v1/auth/login",
            json={"password": "password"},
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert data["error"] == "Username is required"

    def test_api_login_empty_password(self, client):
        """Test API login fails with empty password."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": ""},
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert data["error"] == "Password is required"

    def test_api_login_missing_password(self, client):
        """Test API login fails with missing password."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser"},
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert data["error"] == "Password is required"

    def test_api_login_whitespace_username(self, client, app):
        """Test API login trims whitespace from username."""
        with app.app_context():
            # Create user with trimmed name
            user = User(username="trimuser", email="trim@example.com")
            user.set_password("password")
            db.session.add(user)
            db.session.commit()

        response = client.post(
            "/api/v1/auth/login",
            json={"username": "  trimuser  ", "password": "password"},
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["username"] == "trimuser"

    def test_api_login_real_authentication(self, client, app):
        """Test real authentication rejects invalid credentials."""
        # Test with non-existent users - should all fail
        test_cases = [
            ("admin", "admin"),
            ("user", "password123"),
            ("test@example.com", "complex!Pass"),
            ("newuser123", "simple"),
            ("special-user", "pass with spaces"),
        ]

        for username, password in test_cases:
            response = client.post(
                "/api/v1/auth/login",
                json={"username": username, "password": password},
                content_type="application/json",
            )

            assert response.status_code == 401
            data = response.get_json()
            assert data["success"] is False
            assert "Invalid username or password" in data["error"]

    def test_api_login_requires_correct_password(self, client, app):
        """Test that users must provide correct password to login."""
        with app.app_context():
            # Create user with initial password
            user = User(username="updateuser", email="update@example.com")
            user.set_password("initial_password")
            db.session.add(user)
            db.session.commit()
            user_id = user.id

        # Login with wrong password should fail
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "updateuser", "password": "wrong_password"},
            content_type="application/json",
        )

        assert response.status_code == 401
        data = response.get_json()
        assert data["success"] is False

        # Verify password was NOT updated
        with app.app_context():
            stored_user = db.session.get(User, user_id)
            assert stored_user.check_password("initial_password")
            assert not stored_user.check_password("wrong_password")

    def test_api_login_last_login_timestamp_updated(self, client, app):
        """Test that last_login_at timestamp is updated on successful login."""
        with app.app_context():
            # Create user
            user = User(username="timestampuser", email="timestamp@example.com")
            user.set_password("password")
            original_last_login = user.last_login_at  # Should be None initially
            db.session.add(user)
            db.session.commit()
            user_id = user.id

            assert original_last_login is None

        # Login
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "timestampuser", "password": "password"},
            content_type="application/json",
        )

        assert response.status_code == 200

        # Verify last_login_at was updated
        with app.app_context():
            updated_user = db.session.get(User, user_id)
            assert updated_user.last_login_at is not None
            # Check that last_login_at is recent (within the last 5 seconds)
            # Convert to UTC timezone-aware datetime for comparison
            now = datetime.now(timezone.utc)
            last_login = updated_user.last_login_at
            if last_login.tzinfo is None:
                # If the stored datetime is naive, assume it's UTC
                last_login = last_login.replace(tzinfo=timezone.utc)
            time_diff = now - last_login
            assert time_diff.total_seconds() < 5

    def test_api_login_content_type_requirement(self, client):
        """Test API login requires JSON content type."""
        # Test with form data instead of JSON
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "testuser", "password": "password"},
        )

        assert response.status_code == 415  # Flask returns 415 for wrong content type
        # Flask's 415 error doesn't include JSON response body
        assert response.content_type != "application/json"

    def test_get_current_user_info_success(self, client, authenticated_user):
        """Test successful retrieval of current user info."""
        response = client.get("/api/v1/auth/user")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["message"] == "User information retrieved successfully"
        assert data["data"]["username"] == authenticated_user.username
        assert data["data"]["id"] == authenticated_user.id

    def test_get_current_user_info_requires_auth(self, client):
        """Test that getting current user info requires authentication."""
        response = client.get("/api/v1/auth/user")

        assert response.status_code == 401
        data = response.get_json()
        assert data["success"] is False
        assert data["error"] == "Authentication required"

    def test_api_logout_success(self, client, authenticated_user):
        """Test successful API logout."""
        # Verify user is authenticated
        with client.session_transaction() as sess:
            assert "user_id" in sess

        response = client.post("/api/v1/auth/logout")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["message"] == "Successfully logged out"

        # Verify session was cleared
        with client.session_transaction() as sess:
            assert "user_id" not in sess
            assert "username" not in sess
            assert "is_admin" not in sess

    def test_api_logout_requires_auth(self, client):
        """Test that API logout requires authentication."""
        response = client.post("/api/v1/auth/logout")

        assert response.status_code == 401
        data = response.get_json()
        assert data["success"] is False
        assert data["error"] == "Authentication required"

    def test_api_login_integration_with_other_endpoints(self, client, app):
        """Test that API login enables access to other protected endpoints."""
        # Create a user for this test
        with app.app_context():
            user = User(username="integrationuser", email="integration@example.com")
            user.set_password("password")
            db.session.add(user)
            db.session.commit()

        # First, verify we can't access protected endpoint without auth
        response = client.get("/api/v1/slideshows")
        assert response.status_code == 401

        # Login via API
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "integrationuser", "password": "password"},
            content_type="application/json",
        )
        assert login_response.status_code == 200

        # Now verify we can access protected endpoint
        response = client.get("/api/v1/slideshows")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    def test_api_login_with_existing_user(self, client, app):
        """Test that login works with existing user and correct password."""
        with app.app_context():
            # Create a user manually
            user = User(username="raceuser", email="race@example.com")
            user.set_password("password")
            db.session.add(user)
            db.session.commit()

        # Login should work with correct password
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "raceuser", "password": "password"},
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["username"] == "raceuser"
