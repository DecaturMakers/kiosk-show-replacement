"""
Kiosk.show Replacement - A self-hosted digital signage solution.

This package provides a Flask-based web application for managing digital signage
displays and slideshows, serving as a replacement for the defunct kiosk.show service.

The application serves two primary functions:
1. Allow users to create and manage slideshows through a web interface
2. Serve slideshow content to connected display devices

Key Components:
- Flask web application with both API and server-side rendered interfaces
- SQLAlchemy-based data models for users, displays, slideshows, and content
- File upload and management for images and videos
- Real-time updates via Server-Sent Events
- Responsive admin interface built with React
- Display interface optimized for kiosk devices

This package is designed for collaborative human-AI development with comprehensive
testing, documentation, and deployment automation.
"""

# Import main application factory and database for convenience
from .app import create_app, db

__version__ = "0.5.0"
__author__ = "Jason Antman / Decatur Makers"
__email__ = "jason@jasonantman.com"
__license__ = "MIT"

# Package metadata for programmatic access
__package_name__ = "kiosk-show-replacement"
__description__ = "A self-hosted replacement for kiosk.show"
__url__ = "https://github.com/Decaturmakers/kiosk-show-replacement"

# Version information tuple for easy comparison
VERSION_INFO = tuple(int(x) for x in __version__.split("."))

# Define public API
__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "__license__",
    "__package_name__",
    "__description__",
    "__url__",
    "VERSION_INFO",
    "create_app",
    "db",
]
