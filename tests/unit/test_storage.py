"""
Test file upload and storage functionality.

Tests for file upload API endpoints, storage management, and file serving.
"""

import shutil
import tempfile
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from werkzeug.datastructures import FileStorage

from kiosk_show_replacement.storage import (
    StorageManager,
    get_storage_manager,
    init_storage,
)


class TestStorageManager:
    """Test the StorageManager class functionality."""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def storage_manager(self, temp_storage_dir):
        """Create a StorageManager instance with temporary directory."""
        return StorageManager(temp_storage_dir)

    @pytest.fixture
    def sample_image_file(self):
        """Create a sample image file for testing."""
        # Create a minimal PNG file (1x1 pixel)
        png_data = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc```\x00\x00"
            b"\x00\x04\x00\x01\xdd\x8d\xb4\x1c\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        file_obj = BytesIO(png_data)
        return FileStorage(
            file_obj, filename="test_image.png", content_type="image/png"
        )

    @pytest.fixture
    def sample_video_file(self):
        """Create a sample video file for testing."""
        # Create a minimal MP4 file header
        mp4_data = (
            b"\x00\x00\x00\x20ftypmp42\x00\x00\x00\x20mp41mp42isom"
            b"\x00\x00\x00\x08free\x00\x00\x00\x28mdat"
        )
        file_obj = BytesIO(mp4_data)
        return FileStorage(
            file_obj, filename="test_video.mp4", content_type="video/mp4"
        )

    def test_ensure_directory(self, storage_manager, temp_storage_dir):
        """Test directory creation."""
        test_dir = Path(temp_storage_dir) / "test" / "nested" / "directory"
        storage_manager.ensure_directory(test_dir)

        assert test_dir.exists()
        assert test_dir.is_dir()

    def test_get_upload_path(self, storage_manager, temp_storage_dir):
        """Test upload path generation."""
        path = storage_manager.get_upload_path("images", 1, 2)
        expected_path = Path(temp_storage_dir) / "images" / "1" / "2"

        assert path == expected_path
        assert path.exists()
        assert path.is_dir()

    def test_validate_file_image_success(self, storage_manager, sample_image_file, app):
        """Test successful image file validation."""
        with app.app_context():
            is_valid, error = storage_manager.validate_file(sample_image_file, "image")
            assert is_valid
            assert error == ""

    def test_validate_file_video_success(self, storage_manager, sample_video_file, app):
        """Test successful video file validation."""
        with app.app_context():
            is_valid, error = storage_manager.validate_file(sample_video_file, "video")
            assert is_valid
            assert error == ""

    def test_validate_file_no_file(self, storage_manager, app):
        """Test validation with no file."""
        with app.app_context():
            is_valid, error = storage_manager.validate_file(None, "image")
            assert not is_valid
            assert "No file provided" in error

    def test_validate_file_empty_filename(self, storage_manager, app):
        """Test validation with empty filename."""
        with app.app_context():
            file_obj = FileStorage(BytesIO(b"test"), filename="")
            is_valid, error = storage_manager.validate_file(file_obj, "image")
            assert not is_valid
            assert "No file provided" in error

    def test_validate_file_no_extension(self, storage_manager, app):
        """Test validation with no file extension."""
        with app.app_context():
            file_obj = FileStorage(BytesIO(b"test"), filename="noextension")
            is_valid, error = storage_manager.validate_file(file_obj, "image")
            assert not is_valid
            assert "must have an extension" in error

    def test_validate_file_invalid_extension(self, storage_manager, app):
        """Test validation with invalid extension."""
        with app.app_context():
            file_obj = FileStorage(BytesIO(b"test"), filename="test.exe")
            is_valid, error = storage_manager.validate_file(file_obj, "image")
            assert not is_valid
            assert "extension 'exe' not allowed" in error

    def test_validate_file_unsupported_type(
        self, storage_manager, sample_image_file, app
    ):
        """Test validation with unsupported content type."""
        with app.app_context():
            is_valid, error = storage_manager.validate_file(
                sample_image_file, "document"
            )
            assert not is_valid
            assert "Unsupported content type" in error

    def test_generate_secure_filename(self, storage_manager):
        """Test secure filename generation."""
        filename = storage_manager.generate_secure_filename("test file.jpg", 1, 2)

        assert filename.endswith(".jpg")
        assert "test_file" in filename
        assert len(filename.split("_")) >= 3  # name, timestamp, hash

    def test_save_file_success(self, storage_manager, sample_image_file, app):
        """Test successful file saving."""
        with app.app_context():
            success, message, file_info = storage_manager.save_file(
                sample_image_file, "image", 1, 2
            )

            assert success
            assert "uploaded successfully" in message
            assert file_info is not None
            assert file_info["content_type"] == "image"
            assert file_info["original_filename"] == "test_image.png"
            assert file_info["user_id"] == 1
            assert file_info["slideshow_id"] == 2

    def test_save_file_validation_failure(self, storage_manager, app):
        """Test file saving with validation failure."""
        with app.app_context():
            invalid_file = FileStorage(BytesIO(b"test"), filename="test.exe")
            success, message, file_info = storage_manager.save_file(
                invalid_file, "image", 1, 2
            )

            assert not success
            assert "not allowed" in message
            assert file_info is None

    def test_delete_file_success(self, storage_manager, sample_image_file, app):
        """Test successful file deletion."""
        with app.app_context():
            # First save a file
            success, _, file_info = storage_manager.save_file(
                sample_image_file, "image", 1, 2
            )
            assert success

            # Then delete it
            file_path = file_info["file_path"]
            success, message = storage_manager.delete_file(file_path)

            assert success
            assert "deleted successfully" in message

    def test_delete_file_not_found(self, storage_manager):
        """Test deleting non-existent file."""
        success, message = storage_manager.delete_file("non/existent/file.jpg")

        assert not success
        assert "not found" in message

    def test_copy_file_to_slideshow_success(
        self, storage_manager, sample_image_file, temp_storage_dir, app
    ):
        """Test copying an uploaded file to another slideshow's directory."""
        with app.app_context():
            # Save a file for user 1, slideshow 2
            success, _, file_info = storage_manager.save_file(
                sample_image_file, "image", 1, 2
            )
            assert success
            source_path = file_info["file_path"]

            # Copy it to slideshow 5
            new_path = storage_manager.copy_file_to_slideshow(source_path, 1, 5)

            assert new_path is not None
            assert new_path != source_path
            assert new_path.startswith("images/1/5/")

            # Both source and copy exist and have identical content
            source_file = Path(temp_storage_dir) / source_path
            copied_file = Path(temp_storage_dir) / new_path
            assert source_file.is_file()
            assert copied_file.is_file()
            assert copied_file.read_bytes() == source_file.read_bytes()

    def test_copy_file_to_slideshow_handles_uploads_prefix(
        self, storage_manager, sample_image_file, temp_storage_dir, app
    ):
        """Test copying when the stored path has a leading uploads/ prefix."""
        with app.app_context():
            success, _, file_info = storage_manager.save_file(
                sample_image_file, "image", 1, 2
            )
            assert success

            prefixed_path = f"/uploads/{file_info['file_path']}"
            new_path = storage_manager.copy_file_to_slideshow(prefixed_path, 1, 5)

            assert new_path is not None
            assert new_path.startswith("images/1/5/")
            assert (Path(temp_storage_dir) / new_path).is_file()

    def test_copy_file_to_slideshow_missing_source(self, storage_manager):
        """Test copying a non-existent source file returns None."""
        new_path = storage_manager.copy_file_to_slideshow(
            "images/1/2/does_not_exist.png", 1, 5
        )
        assert new_path is None

    def test_copy_file_to_slideshow_rejects_path_traversal(
        self, storage_manager, temp_storage_dir
    ):
        """Test that paths resolving outside the upload folder are refused."""
        # Create a real file outside the upload folder that a crafted
        # content_file_path could try to reach
        outside_dir = Path(temp_storage_dir).parent / "outside"
        outside_dir.mkdir(exist_ok=True)
        secret_file = outside_dir / "secret.txt"
        secret_file.write_text("secret data")

        try:
            new_path = storage_manager.copy_file_to_slideshow(
                "images/../../outside/secret.txt", 1, 5
            )
            assert new_path is None
            # Nothing was copied into the upload folder
            assert [p for p in Path(temp_storage_dir).rglob("*") if p.is_file()] == []
        finally:
            secret_file.unlink()
            outside_dir.rmdir()

    def test_cleanup_slideshow_files(self, storage_manager, sample_image_file, app):
        """Test cleanup of slideshow files."""
        with app.app_context():
            # Save some files for slideshow
            storage_manager.save_file(sample_image_file, "image", 1, 2)
            sample_image_file.seek(0)  # Reset file pointer
            storage_manager.save_file(sample_image_file, "image", 3, 2)

            # Cleanup slideshow 2
            deleted_count, errors = storage_manager.cleanup_slideshow_files(2)

            assert deleted_count >= 2
            assert len(errors) == 0

    def test_get_file_url(self, storage_manager):
        """Test file URL generation."""
        url = storage_manager.get_file_url("images/1/2/test.jpg")
        assert url == "/uploads/images%2F1%2F2%2Ftest.jpg"

    def test_get_storage_stats(self, storage_manager, sample_image_file, app):
        """Test storage statistics."""
        with app.app_context():
            # Save some files
            storage_manager.save_file(sample_image_file, "image", 1, 2)
            sample_image_file.seek(0)
            storage_manager.save_file(sample_image_file, "image", 1, 3)

            stats = storage_manager.get_storage_stats()

            assert stats["total_files"] >= 2
            assert stats["image_files"] >= 2
            assert stats["video_files"] == 0
            assert stats["users_with_files"] >= 1
            assert stats["slideshows_with_files"] >= 2


class TestVideoDurationExtraction:
    """Test video duration extraction using ffprobe.

    All tests mock subprocess.run to avoid requiring ffprobe to be installed.
    """

    @pytest.fixture
    def temp_storage_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def storage_manager(self, temp_storage_dir):
        """Create a StorageManager instance with temporary directory."""
        return StorageManager(temp_storage_dir)

    @patch("kiosk_show_replacement.storage.subprocess.run")
    def test_get_video_duration_success(
        self, mock_run, storage_manager, temp_storage_dir
    ):
        """Test successful video duration extraction."""
        # Mock ffprobe returning valid JSON with duration
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"format": {"duration": "5.023000"}}',
            stderr="",
        )

        video_path = Path(temp_storage_dir) / "test_video.mp4"
        video_path.write_bytes(b"fake video data")

        duration = storage_manager.get_video_duration(video_path)

        assert duration is not None
        assert abs(duration - 5.023) < 0.001
        mock_run.assert_called_once()

    @patch("kiosk_show_replacement.storage.subprocess.run")
    def test_get_video_duration_integer_duration(
        self, mock_run, storage_manager, temp_storage_dir
    ):
        """Test duration extraction with integer duration value."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"format": {"duration": "10"}}',
            stderr="",
        )

        video_path = Path(temp_storage_dir) / "test_video.mp4"
        video_path.write_bytes(b"fake video data")

        duration = storage_manager.get_video_duration(video_path)

        assert duration == 10.0

    @patch("kiosk_show_replacement.storage.subprocess.run")
    def test_get_video_duration_ffprobe_failure(
        self, mock_run, storage_manager, temp_storage_dir
    ):
        """Test handling when ffprobe returns non-zero exit code."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="ffprobe: Invalid data found",
        )

        video_path = Path(temp_storage_dir) / "invalid.mp4"
        video_path.write_bytes(b"not a video")

        duration = storage_manager.get_video_duration(video_path)

        assert duration is None

    @patch("kiosk_show_replacement.storage.subprocess.run")
    def test_get_video_duration_no_duration_in_output(
        self, mock_run, storage_manager, temp_storage_dir
    ):
        """Test handling when ffprobe output has no duration field."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"format": {"filename": "test.mp4"}}',
            stderr="",
        )

        video_path = Path(temp_storage_dir) / "test_video.mp4"
        video_path.write_bytes(b"fake video data")

        duration = storage_manager.get_video_duration(video_path)

        assert duration is None

    @patch("kiosk_show_replacement.storage.subprocess.run")
    def test_get_video_duration_invalid_json(
        self, mock_run, storage_manager, temp_storage_dir
    ):
        """Test handling when ffprobe returns invalid JSON."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="not valid json",
            stderr="",
        )

        video_path = Path(temp_storage_dir) / "test_video.mp4"
        video_path.write_bytes(b"fake video data")

        duration = storage_manager.get_video_duration(video_path)

        assert duration is None

    @patch("kiosk_show_replacement.storage.subprocess.run")
    def test_get_video_duration_ffprobe_not_found(
        self, mock_run, storage_manager, temp_storage_dir
    ):
        """Test handling when ffprobe is not installed."""
        mock_run.side_effect = FileNotFoundError("ffprobe not found")

        video_path = Path(temp_storage_dir) / "video.mp4"
        video_path.write_bytes(b"fake video data")

        duration = storage_manager.get_video_duration(video_path)

        assert duration is None

    @patch("kiosk_show_replacement.storage.subprocess.run")
    def test_get_video_duration_timeout(
        self, mock_run, storage_manager, temp_storage_dir
    ):
        """Test handling when ffprobe times out."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="ffprobe", timeout=30)

        video_path = Path(temp_storage_dir) / "video.mp4"
        video_path.write_bytes(b"fake video data")

        duration = storage_manager.get_video_duration(video_path)

        assert duration is None


class TestVideoCodecExtraction:
    """Test video codec information extraction using ffprobe.

    All tests mock subprocess.run to avoid requiring ffprobe to be installed.
    """

    @pytest.fixture
    def temp_storage_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def storage_manager(self, temp_storage_dir):
        """Create a StorageManager instance with temporary directory."""
        return StorageManager(temp_storage_dir)

    @patch("kiosk_show_replacement.storage.subprocess.run")
    def test_get_video_codec_info_success(
        self, mock_run, storage_manager, temp_storage_dir
    ):
        """Test successful video codec extraction."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="""{
                "streams": [
                    {"codec_type": "video", "codec_name": "h264"},
                    {"codec_type": "audio", "codec_name": "aac"}
                ],
                "format": {"format_name": "mov,mp4,m4a,3gp,3g2,mj2"}
            }""",
            stderr="",
        )

        video_path = Path(temp_storage_dir) / "test.mp4"
        video_path.write_bytes(b"fake video data")

        codec_info = storage_manager.get_video_codec_info(video_path)

        assert codec_info is not None
        assert codec_info["video_codec"] == "h264"
        assert codec_info["audio_codec"] == "aac"
        assert codec_info["container_format"] == "mov,mp4,m4a,3gp,3g2,mj2"

    @patch("kiosk_show_replacement.storage.subprocess.run")
    def test_get_video_codec_info_video_only(
        self, mock_run, storage_manager, temp_storage_dir
    ):
        """Test codec extraction for video-only file (no audio)."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="""{
                "streams": [
                    {"codec_type": "video", "codec_name": "vp9"}
                ],
                "format": {"format_name": "webm"}
            }""",
            stderr="",
        )

        video_path = Path(temp_storage_dir) / "test.webm"
        video_path.write_bytes(b"fake video data")

        codec_info = storage_manager.get_video_codec_info(video_path)

        assert codec_info is not None
        assert codec_info["video_codec"] == "vp9"
        assert codec_info["audio_codec"] is None
        assert codec_info["container_format"] == "webm"

    @patch("kiosk_show_replacement.storage.subprocess.run")
    def test_get_video_codec_info_mpeg1(
        self, mock_run, storage_manager, temp_storage_dir
    ):
        """Test codec extraction for MPEG-1 video (unsupported codec)."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="""{
                "streams": [
                    {"codec_type": "video", "codec_name": "mpeg1video"}
                ],
                "format": {"format_name": "mpeg"}
            }""",
            stderr="",
        )

        video_path = Path(temp_storage_dir) / "test.mpeg"
        video_path.write_bytes(b"fake video data")

        codec_info = storage_manager.get_video_codec_info(video_path)

        assert codec_info is not None
        assert codec_info["video_codec"] == "mpeg1video"
        assert codec_info["container_format"] == "mpeg"

    @patch("kiosk_show_replacement.storage.subprocess.run")
    def test_get_video_codec_info_ffprobe_failure(
        self, mock_run, storage_manager, temp_storage_dir
    ):
        """Test handling when ffprobe fails."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="ffprobe: Invalid data found",
        )

        video_path = Path(temp_storage_dir) / "invalid.mp4"
        video_path.write_bytes(b"not a video")

        codec_info = storage_manager.get_video_codec_info(video_path)

        assert codec_info is None

    @patch("kiosk_show_replacement.storage.subprocess.run")
    def test_get_video_codec_info_invalid_json(
        self, mock_run, storage_manager, temp_storage_dir
    ):
        """Test handling when ffprobe returns invalid JSON."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="not valid json",
            stderr="",
        )

        video_path = Path(temp_storage_dir) / "test.mp4"
        video_path.write_bytes(b"fake video data")

        codec_info = storage_manager.get_video_codec_info(video_path)

        assert codec_info is None

    @patch("kiosk_show_replacement.storage.subprocess.run")
    def test_get_video_codec_info_ffprobe_not_found(
        self, mock_run, storage_manager, temp_storage_dir
    ):
        """Test handling when ffprobe is not installed."""
        mock_run.side_effect = FileNotFoundError("ffprobe not found")

        video_path = Path(temp_storage_dir) / "video.mp4"
        video_path.write_bytes(b"fake video data")

        codec_info = storage_manager.get_video_codec_info(video_path)

        assert codec_info is None

    @patch("kiosk_show_replacement.storage.subprocess.run")
    def test_get_video_codec_info_timeout(
        self, mock_run, storage_manager, temp_storage_dir
    ):
        """Test handling when ffprobe times out."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="ffprobe", timeout=30)

        video_path = Path(temp_storage_dir) / "video.mp4"
        video_path.write_bytes(b"fake video data")

        codec_info = storage_manager.get_video_codec_info(video_path)

        assert codec_info is None


class TestVideoFormatValidation:
    """Test video format validation for browser-compatible codecs."""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def storage_manager(self, temp_storage_dir):
        """Create a StorageManager instance with temporary directory."""
        return StorageManager(temp_storage_dir)

    @patch.object(StorageManager, "get_video_codec_info")
    def test_validate_video_format_h264_success(
        self, mock_get_codec, storage_manager, temp_storage_dir
    ):
        """Test validation passes for H.264 codec."""
        mock_get_codec.return_value = {
            "video_codec": "h264",
            "audio_codec": "aac",
            "container_format": "mov,mp4,m4a,3gp,3g2,mj2",
        }

        video_path = Path(temp_storage_dir) / "test.mp4"
        video_path.write_bytes(b"fake video data")

        is_valid, error = storage_manager.validate_video_format(video_path, "test.mp4")

        assert is_valid is True
        assert error == ""

    @patch.object(StorageManager, "get_video_codec_info")
    def test_validate_video_format_vp8_success(
        self, mock_get_codec, storage_manager, temp_storage_dir
    ):
        """Test validation passes for VP8 codec."""
        mock_get_codec.return_value = {
            "video_codec": "vp8",
            "audio_codec": "vorbis",
            "container_format": "webm",
        }

        video_path = Path(temp_storage_dir) / "test.webm"
        video_path.write_bytes(b"fake video data")

        is_valid, error = storage_manager.validate_video_format(video_path, "test.webm")

        assert is_valid is True
        assert error == ""

    @patch.object(StorageManager, "get_video_codec_info")
    def test_validate_video_format_vp9_success(
        self, mock_get_codec, storage_manager, temp_storage_dir
    ):
        """Test validation passes for VP9 codec."""
        mock_get_codec.return_value = {
            "video_codec": "vp9",
            "audio_codec": "opus",
            "container_format": "webm",
        }

        video_path = Path(temp_storage_dir) / "test.webm"
        video_path.write_bytes(b"fake video data")

        is_valid, error = storage_manager.validate_video_format(video_path, "test.webm")

        assert is_valid is True
        assert error == ""

    @patch.object(StorageManager, "get_video_codec_info")
    def test_validate_video_format_theora_success(
        self, mock_get_codec, storage_manager, temp_storage_dir
    ):
        """Test validation passes for Theora codec."""
        mock_get_codec.return_value = {
            "video_codec": "theora",
            "audio_codec": "vorbis",
            "container_format": "ogg",
        }

        video_path = Path(temp_storage_dir) / "test.ogv"
        video_path.write_bytes(b"fake video data")

        is_valid, error = storage_manager.validate_video_format(video_path, "test.ogv")

        assert is_valid is True
        assert error == ""

    @patch.object(StorageManager, "get_video_codec_info")
    def test_validate_video_format_av1_success(
        self, mock_get_codec, storage_manager, temp_storage_dir
    ):
        """Test validation passes for AV1 codec."""
        mock_get_codec.return_value = {
            "video_codec": "av1",
            "audio_codec": "opus",
            "container_format": "webm",
        }

        video_path = Path(temp_storage_dir) / "test.webm"
        video_path.write_bytes(b"fake video data")

        is_valid, error = storage_manager.validate_video_format(video_path, "test.webm")

        assert is_valid is True
        assert error == ""

    @patch.object(StorageManager, "get_video_codec_info")
    def test_validate_video_format_mpeg1_rejected(
        self, mock_get_codec, storage_manager, temp_storage_dir
    ):
        """Test validation fails for MPEG-1 codec."""
        mock_get_codec.return_value = {
            "video_codec": "mpeg1video",
            "audio_codec": None,
            "container_format": "mpeg",
        }

        video_path = Path(temp_storage_dir) / "test.mpeg"
        video_path.write_bytes(b"fake video data")

        is_valid, error = storage_manager.validate_video_format(video_path, "test.mpeg")

        assert is_valid is False
        assert "mpeg1video" in error
        assert "not supported" in error
        assert "h264" in error.lower() or "H.264" in error

    @patch.object(StorageManager, "get_video_codec_info")
    def test_validate_video_format_mpeg2_rejected(
        self, mock_get_codec, storage_manager, temp_storage_dir
    ):
        """Test validation fails for MPEG-2 codec."""
        mock_get_codec.return_value = {
            "video_codec": "mpeg2video",
            "audio_codec": "mp2",
            "container_format": "mpeg",
        }

        video_path = Path(temp_storage_dir) / "test.mpg"
        video_path.write_bytes(b"fake video data")

        is_valid, error = storage_manager.validate_video_format(video_path, "test.mpg")

        assert is_valid is False
        assert "mpeg2video" in error
        assert "not supported" in error

    @patch.object(StorageManager, "get_video_codec_info")
    def test_validate_video_format_wmv_rejected(
        self, mock_get_codec, storage_manager, temp_storage_dir
    ):
        """Test validation fails for WMV codec."""
        mock_get_codec.return_value = {
            "video_codec": "wmv3",
            "audio_codec": "wmav2",
            "container_format": "asf",
        }

        video_path = Path(temp_storage_dir) / "test.wmv"
        video_path.write_bytes(b"fake video data")

        is_valid, error = storage_manager.validate_video_format(video_path, "test.wmv")

        assert is_valid is False
        assert "wmv3" in error
        assert "not supported" in error

    @patch.object(StorageManager, "get_video_codec_info")
    def test_validate_video_format_no_video_stream(
        self, mock_get_codec, storage_manager, temp_storage_dir
    ):
        """Test validation fails when no video stream is found."""
        mock_get_codec.return_value = {
            "video_codec": None,
            "audio_codec": "mp3",
            "container_format": "mp3",
        }

        video_path = Path(temp_storage_dir) / "test.mp4"
        video_path.write_bytes(b"fake video data")

        is_valid, error = storage_manager.validate_video_format(video_path, "test.mp4")

        assert is_valid is False
        assert "No video stream found" in error

    @patch.object(StorageManager, "get_video_codec_info")
    def test_validate_video_format_ffprobe_unavailable(
        self, mock_get_codec, storage_manager, temp_storage_dir
    ):
        """Test validation passes gracefully when ffprobe is unavailable."""
        mock_get_codec.return_value = None  # ffprobe not available

        video_path = Path(temp_storage_dir) / "test.mp4"
        video_path.write_bytes(b"fake video data")

        is_valid, error = storage_manager.validate_video_format(video_path, "test.mp4")

        # Should allow upload when ffprobe is unavailable
        assert is_valid is True
        assert error == ""

    @patch.object(StorageManager, "get_video_codec_info")
    def test_validate_video_format_case_insensitive(
        self, mock_get_codec, storage_manager, temp_storage_dir
    ):
        """Test that codec comparison is case-insensitive."""
        mock_get_codec.return_value = {
            "video_codec": "H264",  # Uppercase
            "audio_codec": "AAC",
            "container_format": "mp4",
        }

        video_path = Path(temp_storage_dir) / "test.mp4"
        video_path.write_bytes(b"fake video data")

        is_valid, error = storage_manager.validate_video_format(video_path, "test.mp4")

        assert is_valid is True
        assert error == ""


class TestVideoURLSupport:
    """Test video URL support for duration extraction, codec info, and validation.

    Tests verify that get_video_duration(), get_video_codec_info(), and
    validate_video_url() work correctly with remote URLs (http/https).
    """

    @pytest.fixture
    def temp_storage_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def storage_manager(self, temp_storage_dir):
        """Create a StorageManager instance with temporary directory."""
        return StorageManager(temp_storage_dir)

    # Tests for _is_url() helper method

    def test_is_url_with_https(self, storage_manager):
        """Test _is_url returns True for https URLs."""
        assert StorageManager._is_url("https://example.com/video.mp4") is True

    def test_is_url_with_http(self, storage_manager):
        """Test _is_url returns True for http URLs."""
        assert StorageManager._is_url("http://example.com/video.mp4") is True

    def test_is_url_with_path_object(self, storage_manager, temp_storage_dir):
        """Test _is_url returns False for Path objects."""
        video_path = Path(temp_storage_dir) / "video.mp4"
        assert StorageManager._is_url(video_path) is False

    def test_is_url_with_file_path_string(self, storage_manager):
        """Test _is_url returns False for file path strings."""
        assert StorageManager._is_url("/path/to/video.mp4") is False

    def test_is_url_with_relative_path_string(self, storage_manager):
        """Test _is_url returns False for relative path strings."""
        assert StorageManager._is_url("video.mp4") is False

    # Tests for get_video_duration() with URLs

    @patch("kiosk_show_replacement.storage.subprocess.run")
    def test_get_video_duration_url_success(self, mock_run, storage_manager):
        """Test successful video duration extraction from URL."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"format": {"duration": "120.5"}}',
            stderr="",
        )

        url = "https://example.com/video.mp4"
        duration = storage_manager.get_video_duration(url)

        assert duration is not None
        assert abs(duration - 120.5) < 0.001
        mock_run.assert_called_once()
        # Verify URL was passed to ffprobe
        call_args = mock_run.call_args[0][0]
        assert url in call_args

    @patch("kiosk_show_replacement.storage.subprocess.run")
    def test_get_video_duration_url_uses_longer_timeout(
        self, mock_run, storage_manager
    ):
        """Test that URL duration extraction uses the longer timeout."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"format": {"duration": "60.0"}}',
            stderr="",
        )

        url = "https://example.com/video.mp4"
        storage_manager.get_video_duration(url)

        # Verify the longer timeout was used for URLs
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["timeout"] == StorageManager.FFPROBE_URL_TIMEOUT

    @patch("kiosk_show_replacement.storage.subprocess.run")
    def test_get_video_duration_local_file_uses_shorter_timeout(
        self, mock_run, storage_manager, temp_storage_dir
    ):
        """Test that local file duration extraction uses the shorter timeout."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"format": {"duration": "60.0"}}',
            stderr="",
        )

        video_path = Path(temp_storage_dir) / "video.mp4"
        video_path.write_bytes(b"fake data")
        storage_manager.get_video_duration(video_path)

        # Verify the shorter timeout was used for local files
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["timeout"] == StorageManager.FFPROBE_LOCAL_TIMEOUT

    @patch("kiosk_show_replacement.storage.subprocess.run")
    def test_get_video_duration_url_failure(self, mock_run, storage_manager):
        """Test handling when ffprobe fails for URL."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="https://example.com/video.mp4: Server returned 404 Not Found",
        )

        url = "https://example.com/video.mp4"
        duration = storage_manager.get_video_duration(url)

        assert duration is None

    # Tests for get_video_codec_info() with URLs

    @patch("kiosk_show_replacement.storage.subprocess.run")
    def test_get_video_codec_info_url_success(self, mock_run, storage_manager):
        """Test successful codec info extraction from URL."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="""{
                "streams": [
                    {"codec_type": "video", "codec_name": "h264"},
                    {"codec_type": "audio", "codec_name": "aac"}
                ],
                "format": {"format_name": "mov,mp4,m4a,3gp,3g2,mj2"}
            }""",
            stderr="",
        )

        url = "https://example.com/video.mp4"
        codec_info = storage_manager.get_video_codec_info(url)

        assert codec_info is not None
        assert codec_info["video_codec"] == "h264"
        assert codec_info["audio_codec"] == "aac"
        # Verify URL was passed to ffprobe
        call_args = mock_run.call_args[0][0]
        assert url in call_args

    @patch("kiosk_show_replacement.storage.subprocess.run")
    def test_get_video_codec_info_url_uses_longer_timeout(
        self, mock_run, storage_manager
    ):
        """Test that URL codec info extraction uses the longer timeout."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"streams": [], "format": {}}',
            stderr="",
        )

        url = "http://example.com/video.mp4"
        storage_manager.get_video_codec_info(url)

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["timeout"] == StorageManager.FFPROBE_URL_TIMEOUT

    # Tests for validate_video_url()

    @patch.object(StorageManager, "get_video_codec_info")
    @patch.object(StorageManager, "get_video_duration")
    def test_validate_video_url_success(
        self, mock_duration, mock_codec, storage_manager
    ):
        """Test successful video URL validation."""
        mock_codec.return_value = {
            "video_codec": "h264",
            "audio_codec": "aac",
            "container_format": "mov,mp4,m4a,3gp,3g2,mj2",
        }
        mock_duration.return_value = 120.5

        url = "https://example.com/video.mp4"
        is_valid, duration, codec_info, error = storage_manager.validate_video_url(url)

        assert is_valid is True
        assert duration == 120.5
        assert codec_info["video_codec"] == "h264"
        assert error == ""

    @patch.object(StorageManager, "get_video_codec_info")
    @patch.object(StorageManager, "get_video_duration")
    def test_validate_video_url_vp9_success(
        self, mock_duration, mock_codec, storage_manager
    ):
        """Test validation passes for VP9 codec URL."""
        mock_codec.return_value = {
            "video_codec": "vp9",
            "audio_codec": "opus",
            "container_format": "webm",
        }
        mock_duration.return_value = 60.0

        url = "https://example.com/video.webm"
        is_valid, duration, codec_info, error = storage_manager.validate_video_url(url)

        assert is_valid is True
        assert duration == 60.0
        assert error == ""

    @patch.object(StorageManager, "get_video_codec_info")
    @patch.object(StorageManager, "get_video_duration")
    def test_validate_video_url_no_duration_still_valid(
        self, mock_duration, mock_codec, storage_manager
    ):
        """Test URL validation succeeds even if duration can't be detected."""
        mock_codec.return_value = {
            "video_codec": "h264",
            "audio_codec": None,
            "container_format": "mp4",
        }
        mock_duration.return_value = None  # Duration not available

        url = "https://example.com/video.mp4"
        is_valid, duration, codec_info, error = storage_manager.validate_video_url(url)

        assert is_valid is True
        assert duration is None
        assert codec_info["video_codec"] == "h264"
        assert error == ""

    def test_validate_video_url_invalid_url_format(self, storage_manager):
        """Test validation fails for invalid URL format."""
        is_valid, duration, codec_info, error = storage_manager.validate_video_url(
            "/path/to/video.mp4"
        )

        assert is_valid is False
        assert duration is None
        assert codec_info is None
        assert "Invalid URL format" in error

    def test_validate_video_url_relative_path_rejected(self, storage_manager):
        """Test validation fails for relative file paths."""
        is_valid, duration, codec_info, error = storage_manager.validate_video_url(
            "video.mp4"
        )

        assert is_valid is False
        assert "Invalid URL format" in error

    @patch.object(StorageManager, "get_video_codec_info")
    def test_validate_video_url_inaccessible(self, mock_codec, storage_manager):
        """Test validation fails when URL is inaccessible."""
        mock_codec.return_value = None  # ffprobe failed to access URL

        url = "https://example.com/nonexistent.mp4"
        is_valid, duration, codec_info, error = storage_manager.validate_video_url(url)

        assert is_valid is False
        assert duration is None
        assert codec_info is None
        assert "Could not retrieve video information" in error

    @patch.object(StorageManager, "get_video_codec_info")
    def test_validate_video_url_no_video_stream(self, mock_codec, storage_manager):
        """Test validation fails when URL has no video stream."""
        mock_codec.return_value = {
            "video_codec": None,  # No video stream
            "audio_codec": "aac",
            "container_format": "mp4",
        }

        url = "https://example.com/audio-only.mp4"
        is_valid, duration, codec_info, error = storage_manager.validate_video_url(url)

        assert is_valid is False
        assert codec_info is not None  # Codec info is returned even on failure
        assert "No video stream found" in error

    @patch.object(StorageManager, "get_video_codec_info")
    def test_validate_video_url_unsupported_codec(self, mock_codec, storage_manager):
        """Test validation fails for unsupported video codec."""
        mock_codec.return_value = {
            "video_codec": "mpeg2video",  # Not browser-compatible
            "audio_codec": "mp2",
            "container_format": "mpeg",
        }

        url = "https://example.com/video.mpeg"
        is_valid, duration, codec_info, error = storage_manager.validate_video_url(url)

        assert is_valid is False
        assert codec_info is not None
        assert "mpeg2video" in error
        assert "not supported by web browsers" in error

    @patch.object(StorageManager, "get_video_codec_info")
    def test_validate_video_url_wmv_rejected(self, mock_codec, storage_manager):
        """Test validation fails for WMV codec."""
        mock_codec.return_value = {
            "video_codec": "wmv3",
            "audio_codec": "wma",
            "container_format": "asf",
        }

        url = "https://example.com/video.wmv"
        is_valid, duration, codec_info, error = storage_manager.validate_video_url(url)

        assert is_valid is False
        assert "wmv3" in error


class TestFileUploadAPI:
    """Test file upload API endpoints."""

    @pytest.fixture
    def sample_image_data(self):
        """Create sample image data for upload."""
        # Minimal PNG data
        return (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc```\x00\x00"
            b"\x00\x04\x00\x01\xdd\x8d\xb4\x1c\x00\x00\x00\x00IEND\xaeB`\x82"
        )

    @pytest.fixture
    def sample_video_data(self):
        """Create sample video data for upload."""
        # Minimal MP4 header
        return (
            b"\x00\x00\x00\x20ftypmp42\x00\x00\x00\x20mp41mp42isom"
            b"\x00\x00\x00\x08free\x00\x00\x00\x28mdat"
        )

    def test_upload_image_success(
        self, client, authenticated_user, sample_slideshow, sample_image_data
    ):
        """Test successful image upload."""
        data = {
            "file": (BytesIO(sample_image_data), "test.png"),
            "slideshow_id": str(sample_slideshow.id),
        }

        response = client.post(
            "/api/v1/uploads/image", data=data, content_type="multipart/form-data"
        )

        assert response.status_code == 201
        json_data = response.get_json()
        assert json_data["success"] is True
        assert "data" in json_data
        assert json_data["data"]["content_type"] == "image"
        assert json_data["data"]["original_filename"] == "test.png"

    def test_upload_image_no_auth(self, client, sample_image_data):
        """Test image upload without authentication."""
        data = {"file": (BytesIO(sample_image_data), "test.png"), "slideshow_id": "1"}

        response = client.post(
            "/api/v1/uploads/image", data=data, content_type="multipart/form-data"
        )

        assert response.status_code == 401
        json_data = response.get_json()
        assert json_data["success"] is False

    def test_upload_image_no_file(self, client, authenticated_user, sample_slideshow):
        """Test image upload without file."""
        data = {"slideshow_id": str(sample_slideshow.id)}

        response = client.post(
            "/api/v1/uploads/image", data=data, content_type="multipart/form-data"
        )

        assert response.status_code == 400
        json_data = response.get_json()
        assert json_data["success"] is False
        assert "No file provided" in json_data["error"]

    def test_upload_image_no_slideshow_id(
        self, client, authenticated_user, sample_image_data
    ):
        """Test image upload without slideshow_id."""
        data = {"file": (BytesIO(sample_image_data), "test.png")}

        response = client.post(
            "/api/v1/uploads/image", data=data, content_type="multipart/form-data"
        )

        assert response.status_code == 400
        json_data = response.get_json()
        assert json_data["success"] is False
        assert "slideshow_id is required" in json_data["error"]

    def test_upload_image_invalid_slideshow_id(
        self, client, authenticated_user, sample_image_data
    ):
        """Test image upload with invalid slideshow_id."""
        data = {
            "file": (BytesIO(sample_image_data), "test.png"),
            "slideshow_id": "invalid",
        }

        response = client.post(
            "/api/v1/uploads/image", data=data, content_type="multipart/form-data"
        )

        assert response.status_code == 400
        json_data = response.get_json()
        assert json_data["success"] is False
        assert "Invalid slideshow_id" in json_data["error"]

    def test_upload_image_nonexistent_slideshow(
        self, client, authenticated_user, sample_image_data
    ):
        """Test image upload with non-existent slideshow."""
        data = {
            "file": (BytesIO(sample_image_data), "test.png"),
            "slideshow_id": "99999",
        }

        response = client.post(
            "/api/v1/uploads/image", data=data, content_type="multipart/form-data"
        )

        assert response.status_code == 404
        json_data = response.get_json()
        assert json_data["success"] is False
        assert "Slideshow not found" in json_data["error"]

    def test_upload_video_success(
        self, client, authenticated_user, sample_slideshow, sample_video_data
    ):
        """Test successful video upload."""
        data = {
            "file": (BytesIO(sample_video_data), "test.mp4"),
            "slideshow_id": str(sample_slideshow.id),
        }

        response = client.post(
            "/api/v1/uploads/video", data=data, content_type="multipart/form-data"
        )

        assert response.status_code == 201
        json_data = response.get_json()
        assert json_data["success"] is True
        assert "data" in json_data
        assert json_data["data"]["content_type"] == "video"
        assert json_data["data"]["original_filename"] == "test.mp4"

    def test_upload_video_invalid_extension(
        self, client, authenticated_user, sample_slideshow
    ):
        """Test video upload with invalid extension."""
        data = {
            "file": (BytesIO(b"fake video data"), "test.txt"),
            "slideshow_id": str(sample_slideshow.id),
        }

        response = client.post(
            "/api/v1/uploads/video", data=data, content_type="multipart/form-data"
        )

        assert response.status_code == 400
        json_data = response.get_json()
        assert json_data["success"] is False
        assert "not allowed" in json_data["error"]

    def test_get_upload_stats(self, client, authenticated_user):
        """Test upload statistics endpoint."""
        response = client.get("/api/v1/uploads/stats")

        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data["success"] is True
        assert "data" in json_data

        # Check that all expected fields are present
        data = json_data["data"]
        expected_fields = [
            "total_size",
            "total_size_formatted",
            "image_size",
            "image_size_formatted",
            "video_size",
            "video_size_formatted",
            "total_files",
            "image_files",
            "video_files",
            "users_with_files",
            "slideshows_with_files",
        ]
        for field in expected_fields:
            assert field in data

    def test_get_upload_stats_no_auth(self, client):
        """Test upload statistics endpoint without authentication."""
        response = client.get("/api/v1/uploads/stats")

        assert response.status_code == 401
        json_data = response.get_json()
        assert json_data["success"] is False

    def test_file_info_endpoint_not_implemented(self, client, authenticated_user):
        """Test file info endpoint (placeholder)."""
        response = client.get("/api/v1/uploads/1")

        assert response.status_code == 501
        json_data = response.get_json()
        assert json_data["success"] is False
        assert "not yet implemented" in json_data["error"]

    def test_delete_file_endpoint_not_implemented(self, client, authenticated_user):
        """Test file deletion endpoint (placeholder)."""
        response = client.delete("/api/v1/uploads/1")

        assert response.status_code == 501
        json_data = response.get_json()
        assert json_data["success"] is False
        assert "not yet implemented" in json_data["error"]


class TestFileServing:
    """Test file serving functionality."""

    def test_file_serving_route_exists(self, app):
        """Test that file serving route is registered."""
        with app.test_request_context():
            # The route should exist
            rules = [rule.rule for rule in app.url_map.iter_rules()]
            assert "/uploads/<path:filename>" in rules

    @patch("kiosk_show_replacement.app.send_from_directory")
    def test_file_serving_success(self, mock_send, client):
        """Test successful file serving."""
        mock_send.return_value = MagicMock()

        client.get("/uploads/images/1/2/test.jpg")

        # The route should call send_from_directory
        mock_send.assert_called_once()

    def test_file_serving_not_found(self, client):
        """Test file serving with non-existent file."""
        response = client.get("/uploads/nonexistent/file.jpg")

        assert response.status_code == 404


class TestStorageInitialization:
    """Test storage system initialization."""

    def test_init_storage(self, app):
        """Test storage initialization."""
        with app.app_context():
            # Storage should initialize without error
            init_storage(app)

            # Should be able to get storage manager
            manager = get_storage_manager()
            assert manager is not None
            assert isinstance(manager, StorageManager)

    def test_storage_directories_created(self, app):
        """Test that required directories are created during initialization."""
        with app.app_context():
            init_storage(app)

            upload_folder = Path(app.config["UPLOAD_FOLDER"])
            assert (upload_folder / "images").exists()
            assert (upload_folder / "videos").exists()
