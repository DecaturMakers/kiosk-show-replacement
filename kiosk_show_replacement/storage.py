"""
File storage management for kiosk-show-replacement.

This module handles file upload storage, directory management, and file operations
with proper security and organization.
"""

import hashlib
import json
import logging
import mimetypes
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union
from urllib.parse import quote_plus

from flask import current_app

if TYPE_CHECKING:
    from flask import Flask
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)


class StorageManager:
    """
    Manages file storage operations for uploaded content.

    Handles file validation, secure storage, directory creation,
    and cleanup operations.
    """

    # Timeout for ffprobe when processing local files (seconds)
    FFPROBE_LOCAL_TIMEOUT = 30
    # Timeout for ffprobe when processing remote URLs (seconds)
    # Longer timeout to account for network latency and buffering
    FFPROBE_URL_TIMEOUT = 60

    @staticmethod
    def _is_url(source: Union[Path, str]) -> bool:
        """
        Check if a source is a URL (http:// or https://).

        Args:
            source: Either a Path object or a string (file path or URL)

        Returns:
            True if source is a URL, False if it's a file path
        """
        if isinstance(source, Path):
            return False
        return isinstance(source, str) and (
            source.startswith("http://") or source.startswith("https://")
        )

    def __init__(self, upload_folder: Optional[str] = None):
        """
        Initialize the storage manager.

        Args:
            upload_folder: Base upload directory path. If None, uses Flask config.
        """
        self.upload_folder = upload_folder or current_app.config.get(
            "UPLOAD_FOLDER", "instance/uploads"
        )
        self.base_path = Path(self.upload_folder)

        # Ensure base upload directory exists
        self.ensure_directory(self.base_path)

    def ensure_directory(self, path: Path) -> None:
        """
        Ensure a directory exists, creating it if necessary.

        Args:
            path: Directory path to ensure exists

        Raises:
            OSError: If directory cannot be created
        """
        try:
            path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {path}")
        except OSError as e:
            logger.error(f"Failed to create directory {path}: {e}")
            raise

    def get_upload_path(
        self, content_type: str, user_id: int, slideshow_id: int
    ) -> Path:
        """
        Get the organized upload path for a file.

        Directory structure: uploads/{content_type}/{user_id}/{slideshow_id}/

        Args:
            content_type: Type of content ('images' or 'videos')
            user_id: ID of the user uploading the file
            slideshow_id: ID of the slideshow the file belongs to

        Returns:
            Path object for the upload directory
        """
        upload_path = self.base_path / content_type / str(user_id) / str(slideshow_id)
        self.ensure_directory(upload_path)
        return upload_path

    def validate_file(self, file: FileStorage, content_type: str) -> Tuple[bool, str]:
        """
        Validate an uploaded file for security and type constraints.

        Args:
            file: Uploaded file object
            content_type: Expected content type ('image' or 'video')

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not file or not file.filename:
            return False, "No file provided"

        filename = file.filename.lower()

        # Check file extension
        if "." not in filename:
            return False, "File must have an extension"

        extension = filename.rsplit(".", 1)[1]

        if content_type == "image":
            allowed_extensions = current_app.config.get(
                "ALLOWED_IMAGE_EXTENSIONS", {"jpg", "jpeg", "png", "gif"}
            )
            max_size = current_app.config.get("MAX_IMAGE_SIZE", 50 * 1024 * 1024)
        elif content_type == "video":
            allowed_extensions = current_app.config.get(
                "ALLOWED_VIDEO_EXTENSIONS", {"mp4", "webm", "avi"}
            )
            max_size = current_app.config.get("MAX_VIDEO_SIZE", 500 * 1024 * 1024)
        else:
            return False, f"Unsupported content type: {content_type}"

        if extension not in allowed_extensions:
            return False, f"File extension '{extension}' not allowed for {content_type}"

        # Check file size (seek to end to get size)
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning

        if file_size > max_size:
            size_mb = max_size / (1024 * 1024)
            return False, f"File size exceeds maximum allowed size of {size_mb:.1f}MB"

        # Basic MIME type validation
        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type:
            if content_type == "image" and not mime_type.startswith("image/"):
                return (
                    False,
                    f"File MIME type '{mime_type}' does not match expected image type",
                )
            elif content_type == "video" and not mime_type.startswith("video/"):
                return (
                    False,
                    f"File MIME type '{mime_type}' does not match expected video type",
                )

        return True, ""

    def get_video_codec_info(
        self, source: Union[Path, str]
    ) -> Optional[Dict[str, Optional[str]]]:
        """
        Extract video codec information using ffprobe.

        Supports both local file paths and remote URLs (http/https).
        ffprobe natively supports remote URLs.

        Args:
            source: Path to a local video file, or a URL string (http/https)

        Returns:
            Dictionary with 'video_codec', 'audio_codec', and 'container_format',
            or None if extraction fails. Individual values may be None if not found.
        """
        is_url = self._is_url(source)
        timeout = self.FFPROBE_URL_TIMEOUT if is_url else self.FFPROBE_LOCAL_TIMEOUT
        source_str = str(source)

        try:
            # Run ffprobe to get stream and format information
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "quiet",
                    "-print_format",
                    "json",
                    "-show_streams",
                    "-show_format",
                    source_str,
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            if result.returncode != 0:
                logger.warning(
                    f"ffprobe failed to get codec info for {source_str}: {result.stderr}"
                )
                return None

            # Parse JSON output
            data = json.loads(result.stdout)

            # Extract codec information from streams
            video_codec: Optional[str] = None
            audio_codec: Optional[str] = None

            for stream in data.get("streams", []):
                codec_type = stream.get("codec_type")
                codec_name = stream.get("codec_name")

                if codec_type == "video" and video_codec is None:
                    video_codec = codec_name
                elif codec_type == "audio" and audio_codec is None:
                    audio_codec = codec_name

            # Extract container format
            container_format = data.get("format", {}).get("format_name")

            codec_info = {
                "video_codec": video_codec,
                "audio_codec": audio_codec,
                "container_format": container_format,
            }

            logger.debug(f"Video codec info for {source_str}: {codec_info}")
            return codec_info

        except FileNotFoundError:
            logger.error(
                "ffprobe not found. Please install ffmpeg to enable "
                "video codec detection."
            )
            return None
        except subprocess.TimeoutExpired:
            logger.error(f"ffprobe timed out getting codec info for {source_str}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse ffprobe codec output for {source_str}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting video codec info for {source_str}: {e}")
            return None

    # Browser-compatible video codecs for HTML5 <video> element
    SUPPORTED_VIDEO_CODECS = {"h264", "vp8", "vp9", "theora", "av1"}

    def validate_video_format(
        self, file_path: Path, original_filename: str
    ) -> Tuple[bool, str]:
        """
        Validate that a video file uses browser-compatible codecs.

        Checks if the video codec is supported by HTML5 <video> element.
        Supported codecs: H.264, VP8, VP9, Theora, AV1.

        Args:
            file_path: Path to the video file to validate
            original_filename: Original filename for error messages

        Returns:
            Tuple of (is_valid, error_message). If valid, error_message is empty.
        """
        codec_info = self.get_video_codec_info(file_path)

        if codec_info is None:
            # If we can't get codec info, log warning but allow the upload
            # This maintains backwards compatibility if ffprobe is unavailable
            logger.warning(
                f"Could not determine video codec for '{original_filename}' "
                f"at {file_path}. Allowing upload but video may not play in browser."
            )
            return True, ""

        video_codec = codec_info.get("video_codec")
        container_format = codec_info.get("container_format")

        if video_codec is None:
            logger.warning(
                f"No video stream found in '{original_filename}' at {file_path}. "
                f"Container format: {container_format}"
            )
            return False, (
                "No video stream found in the uploaded file. "
                "Please upload a valid video file."
            )

        # Check if codec is supported
        if video_codec.lower() not in self.SUPPORTED_VIDEO_CODECS:
            # Log detailed warning for troubleshooting
            logger.warning(
                f"Rejected video upload: unsupported codec. "
                f"Filename: '{original_filename}', "
                f"Video codec: '{video_codec}', "
                f"Container format: '{container_format}', "
                f"File path: {file_path}"
            )

            supported_list = ", ".join(sorted(self.SUPPORTED_VIDEO_CODECS))
            return False, (
                f"Video codec '{video_codec}' is not supported by web browsers. "
                f"Supported codecs: {supported_list}. "
                f"Please convert your video to MP4 (H.264) or WebM (VP8/VP9) format."
            )

        logger.debug(
            f"Video format validation passed for '{original_filename}': "
            f"codec={video_codec}, container={container_format}"
        )
        return True, ""

    def validate_video_url(
        self, url: str
    ) -> Tuple[bool, Optional[float], Optional[Dict[str, Optional[str]]], str]:
        """
        Validate a video URL for browser compatibility and extract metadata.

        This function combines codec validation and duration detection for video URLs.
        It uses ffprobe to probe the remote URL directly.

        Args:
            url: The video URL to validate (must be http:// or https://)

        Returns:
            A tuple of (is_valid, duration_seconds, codec_info, error_message):
            - is_valid: True if the video is valid and browser-compatible
            - duration_seconds: Video duration in seconds, or None if not detected
            - codec_info: Dict with video_codec, audio_codec, container_format
            - error_message: Empty string if valid, otherwise describes the error
        """
        # Validate URL format
        if not self._is_url(url):
            return (
                False,
                None,
                None,
                "Invalid URL format. URL must start with http:// or https://",
            )

        # Get codec info (this also validates the URL is accessible)
        codec_info = self.get_video_codec_info(url)

        if codec_info is None:
            # Could be network error, invalid URL, or ffprobe unavailable
            logger.warning(
                f"Could not retrieve video information from URL: {url}. "
                f"The URL may be inaccessible, invalid, or ffprobe may not be installed."
            )
            return (
                False,
                None,
                None,
                (
                    "Could not retrieve video information from the URL. "
                    "Please verify the URL is accessible and points to a valid video file."
                ),
            )

        video_codec = codec_info.get("video_codec")
        container_format = codec_info.get("container_format")

        # Check for video stream
        if video_codec is None:
            logger.warning(
                f"No video stream found at URL: {url}. "
                f"Container format: {container_format}"
            )
            return (
                False,
                None,
                codec_info,
                (
                    "No video stream found at the URL. "
                    "Please provide a URL to a valid video file."
                ),
            )

        # Check codec compatibility
        if video_codec.lower() not in self.SUPPORTED_VIDEO_CODECS:
            logger.warning(
                f"Rejected video URL: unsupported codec. "
                f"URL: '{url}', "
                f"Video codec: '{video_codec}', "
                f"Container format: '{container_format}'"
            )

            supported_list = ", ".join(sorted(self.SUPPORTED_VIDEO_CODECS))
            return (
                False,
                None,
                codec_info,
                (
                    f"Video codec '{video_codec}' is not supported by web browsers. "
                    f"Supported codecs: {supported_list}. "
                    f"Please use a video with MP4 (H.264) or WebM (VP8/VP9) format."
                ),
            )

        # Get duration (optional - video is still valid if duration can't be detected)
        duration = self.get_video_duration(url)

        logger.info(
            f"Video URL validation passed: {url}, "
            f"codec={video_codec}, duration={duration}s"
        )

        return True, duration, codec_info, ""

    def get_video_duration(self, source: Union[Path, str]) -> Optional[float]:
        """
        Extract video duration using ffprobe.

        Supports both local file paths and remote URLs (http/https).
        ffprobe natively supports remote URLs.

        Args:
            source: Path to a local video file, or a URL string (http/https)

        Returns:
            Duration in seconds as a float, or None if extraction fails
        """
        is_url = self._is_url(source)
        timeout = self.FFPROBE_URL_TIMEOUT if is_url else self.FFPROBE_LOCAL_TIMEOUT
        source_str = str(source)

        try:
            # Run ffprobe to get video duration
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "quiet",
                    "-print_format",
                    "json",
                    "-show_format",
                    source_str,
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            if result.returncode != 0:
                logger.warning(f"ffprobe failed for {source_str}: {result.stderr}")
                return None

            # Parse JSON output
            data = json.loads(result.stdout)
            duration_str = data.get("format", {}).get("duration")

            if duration_str:
                duration = float(duration_str)
                logger.debug(f"Video duration for {source_str}: {duration} seconds")
                return duration

            logger.warning(f"No duration found in ffprobe output for {source_str}")
            return None

        except FileNotFoundError:
            logger.error(
                "ffprobe not found. Please install ffmpeg to enable "
                "automatic video duration detection."
            )
            return None
        except subprocess.TimeoutExpired:
            logger.error(f"ffprobe timed out for {source_str}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse ffprobe output for {source_str}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting video duration for {source_str}: {e}")
            return None

    def generate_secure_filename(
        self, original_filename: str, user_id: int, slideshow_id: int
    ) -> str:
        """
        Generate a secure filename that prevents conflicts and security issues.

        Args:
            original_filename: Original uploaded filename
            user_id: ID of the user uploading
            slideshow_id: ID of the slideshow

        Returns:
            Secure filename with timestamp and hash
        """
        # Get file extension
        if "." in original_filename:
            name, ext = original_filename.rsplit(".", 1)
            ext = ext.lower()
        else:
            name, ext = original_filename, ""

        # Create a secure base name
        secure_name = secure_filename(name)[:50]  # Limit length

        # Add timestamp and hash for uniqueness
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        hash_input = f"{user_id}_{slideshow_id}_{original_filename}_{timestamp}"
        file_hash = hashlib.md5(hash_input.encode()).hexdigest()[:8]

        # Construct final filename
        if ext:
            return f"{secure_name}_{timestamp}_{file_hash}.{ext}"
        else:
            return f"{secure_name}_{timestamp}_{file_hash}"

    def save_file(
        self, file: FileStorage, content_type: str, user_id: int, slideshow_id: int
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Save an uploaded file to the organized storage structure.

        Args:
            file: Uploaded file object
            content_type: Type of content ('image' or 'video')
            user_id: ID of the user uploading
            slideshow_id: ID of the slideshow

        Returns:
            Tuple of (success, message, file_info_dict)
        """
        try:
            # Validate the file
            is_valid, error_message = self.validate_file(file, content_type)
            if not is_valid:
                return False, error_message, None

            # Get upload path and create directories
            content_dir = "images" if content_type == "image" else "videos"
            upload_path = self.get_upload_path(content_dir, user_id, slideshow_id)

            # Generate secure filename
            filename = file.filename or "unnamed"
            secure_name = self.generate_secure_filename(filename, user_id, slideshow_id)
            file_path = upload_path / secure_name

            # Get file size
            file.seek(0, 2)
            file_size = file.tell()
            file.seek(0)

            # Save the file
            file.save(str(file_path))

            # For videos, validate the codec is browser-compatible
            if content_type == "video":
                is_format_valid, format_error = self.validate_video_format(
                    file_path, filename
                )
                if not is_format_valid:
                    # Delete the saved file since validation failed
                    try:
                        file_path.unlink()
                    except Exception as delete_err:
                        logger.error(
                            f"Failed to delete invalid video file {file_path}: "
                            f"{delete_err}"
                        )
                    return False, format_error, None

            # Get MIME type
            mime_type, _ = mimetypes.guess_type(str(file_path))

            # Create file info
            file_info = {
                "filename": secure_name,
                "original_filename": file.filename,
                "file_path": str(file_path.relative_to(self.base_path)),
                "absolute_path": str(file_path),
                "content_type": content_type,
                "mime_type": mime_type,
                "file_size": file_size,
                "user_id": user_id,
                "slideshow_id": slideshow_id,
                "upload_date": datetime.now(timezone.utc).isoformat(),
            }

            # For videos, extract duration using ffprobe
            if content_type == "video":
                duration = self.get_video_duration(file_path)
                if duration is not None:
                    # Round to nearest integer for display_duration
                    file_info["duration"] = duration
                    file_info["duration_seconds"] = int(round(duration))
                    logger.info(
                        f"Detected video duration: {duration:.2f}s "
                        f"(rounded to {file_info['duration_seconds']}s)"
                    )

            logger.info(
                f"Successfully saved file: {secure_name} for user {user_id}, "
                f"slideshow {slideshow_id}"
            )
            return True, f"File '{file.filename}' uploaded successfully", file_info

        except Exception as e:
            logger.error(f"Failed to save file {file.filename}: {e}")
            return False, f"Failed to save file: {str(e)}", None

    def copy_file_to_slideshow(
        self, file_path: str, user_id: int, dest_slideshow_id: int
    ) -> Optional[str]:
        """
        Copy an existing uploaded file into another slideshow's directory.

        Used when duplicating a slideshow so the duplicate owns independent
        copies of uploaded media files rather than referencing the original
        slideshow's files.

        Args:
            file_path: Relative path of the source file from the upload
                folder (as stored in SlideshowItem.content_file_path)
            user_id: ID of the user owning the destination slideshow
            dest_slideshow_id: ID of the destination slideshow

        Returns:
            The new relative file path on success, or None if the source
            file does not exist, resolves outside the upload folder, or
            the copy fails.
        """
        try:
            relative = file_path.lstrip("/").removeprefix("uploads/")
            source = (self.base_path / relative).resolve()

            # Guard against path traversal: content_file_path is writable
            # via the API, so the resolved source must stay inside the
            # upload folder.
            if not source.is_relative_to(self.base_path.resolve()):
                logger.warning(
                    f"Refusing to copy file outside upload folder: {file_path}"
                )
                return None

            if not source.is_file():
                logger.warning(f"Source file not found for copy: {file_path}")
                return None

            # First path component is the content directory
            # ('images' or 'videos')
            content_dir = Path(relative).parts[0]
            dest_dir = self.get_upload_path(content_dir, user_id, dest_slideshow_id)
            secure_name = self.generate_secure_filename(
                source.name, user_id, dest_slideshow_id
            )
            dest = dest_dir / secure_name
            shutil.copy2(source, dest)

            new_path = str(dest.relative_to(self.base_path))
            logger.info(
                f"Copied file {file_path} to {new_path} for "
                f"slideshow {dest_slideshow_id}"
            )
            return new_path
        except Exception as e:
            logger.error(
                f"Failed to copy file {file_path} to slideshow "
                f"{dest_slideshow_id}: {e}"
            )
            return None

    def delete_file(self, file_path: str) -> Tuple[bool, str]:
        """
        Delete a file from storage.

        Args:
            file_path: Relative path to the file from upload folder

        Returns:
            Tuple of (success, message)
        """
        try:
            full_path = self.base_path / file_path
            if full_path.exists():
                full_path.unlink()
                logger.info(f"Deleted file: {file_path}")
                return True, "File deleted successfully"
            else:
                logger.warning(f"File not found for deletion: {file_path}")
                return False, "File not found"
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {e}")
            return False, f"Failed to delete file: {str(e)}"

    def cleanup_slideshow_files(self, slideshow_id: int) -> Tuple[int, List[str]]:
        """
        Clean up all files associated with a slideshow.

        Args:
            slideshow_id: ID of the slideshow to clean up

        Returns:
            Tuple of (files_deleted_count, error_messages)
        """
        deleted_count = 0
        errors = []

        # Find all directories that might contain files for this slideshow
        for content_type in ["images", "videos"]:
            content_path = self.base_path / content_type
            if not content_path.exists():
                continue

            # Look through all user directories
            for user_dir in content_path.iterdir():
                if user_dir.is_dir():
                    slideshow_dir = user_dir / str(slideshow_id)
                    if slideshow_dir.exists():
                        try:
                            # Delete all files in the slideshow directory
                            for file_path in slideshow_dir.iterdir():
                                if file_path.is_file():
                                    file_path.unlink()
                                    deleted_count += 1

                            # Remove the directory if empty
                            slideshow_dir.rmdir()
                            logger.info(
                                f"Cleaned up slideshow {slideshow_id} files "
                                f"in {slideshow_dir}"
                            )

                        except Exception as e:
                            error_msg = f"Failed to cleanup {slideshow_dir}: {e}"
                            errors.append(error_msg)
                            logger.error(error_msg)

        return deleted_count, errors

    def get_file_url(self, file_path: str) -> str:
        """
        Generate a URL for accessing an uploaded file.

        Args:
            file_path: Relative path to the file from upload folder

        Returns:
            URL path for accessing the file
        """
        # URL-encode the file path for safety
        encoded_path = quote_plus(file_path.replace("\\", "/"))
        return f"/uploads/{encoded_path}"

    def get_directory_size(self, path: Optional[Path] = None) -> int:
        """
        Get the total size of files in a directory.

        Args:
            path: Directory path to measure. If None, measures entire upload folder.

        Returns:
            Total size in bytes
        """
        if path is None:
            path = self.base_path

        total_size = 0
        try:
            for file_path in path.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except Exception as e:
            logger.error(f"Failed to calculate directory size for {path}: {e}")

        return total_size

    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive storage statistics.

        Returns:
            Dictionary with storage statistics
        """
        total_size = 0
        image_size = 0
        video_size = 0
        total_files = 0
        image_files = 0
        video_files = 0
        users_with_files: set[str] = set()
        slideshows_with_files: set[str] = set()

        try:
            for content_type in ["images", "videos"]:
                content_path = self.base_path / content_type
                if not content_path.exists():
                    continue

                for user_dir in content_path.iterdir():
                    if user_dir.is_dir():
                        user_id = user_dir.name
                        users_with_files.add(user_id)

                        for slideshow_dir in user_dir.iterdir():
                            if slideshow_dir.is_dir():
                                slideshow_id = slideshow_dir.name
                                slideshows_with_files.add(slideshow_id)

                                for file_path in slideshow_dir.iterdir():
                                    if file_path.is_file():
                                        file_size = file_path.stat().st_size
                                        total_size += file_size
                                        total_files += 1

                                        if content_type == "images":
                                            image_size += file_size
                                            image_files += 1
                                        else:
                                            video_size += file_size
                                            video_files += 1

        except Exception as e:
            logger.error(f"Failed to calculate storage stats: {e}")

        return {
            "total_size": total_size,
            "image_size": image_size,
            "video_size": video_size,
            "total_files": total_files,
            "image_files": image_files,
            "video_files": video_files,
            "users_with_files": len(users_with_files),
            "slideshows_with_files": len(slideshows_with_files),
        }


# Global storage manager instance
storage_manager = None


def get_storage_manager() -> StorageManager:
    """
    Get the global storage manager instance.

    Returns:
        StorageManager instance
    """
    global storage_manager
    if storage_manager is None:
        storage_manager = StorageManager()
    return storage_manager


def init_storage(app: "Flask") -> None:
    """
    Initialize storage system with Flask app.

    Args:
        app: Flask application instance
    """
    global storage_manager
    upload_folder = app.config.get("UPLOAD_FOLDER", "instance/uploads")
    storage_manager = StorageManager(upload_folder)

    # Ensure base directories exist
    base_path = Path(upload_folder)
    for content_type in ["images", "videos"]:
        content_path = base_path / content_type
        storage_manager.ensure_directory(content_path)

    logger.info(f"Storage system initialized with upload folder: {upload_folder}")
