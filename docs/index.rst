Kiosk Show Replacement
======================

A self-hosted replacement for kiosk.show - a web application for managing and displaying slideshow presentations on kiosk displays.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   deployment
   usage
   api
   development
   modules

Features
--------

* **Web-based slideshow management**: Create and manage slideshows through a modern React admin interface
* **Kiosk display mode**: Full-screen slideshow display for kiosk installations
* **REST API**: Complete API for programmatic management of slideshows and slides
* **Multiple media types**: Support for images, videos, web content, text slides, and Skedda calendars
* **User management**: Role-based access with admin and regular user accounts
* **Responsive design**: Works on desktop, tablet, and mobile devices
* **Multi-database support**: SQLite for development, MariaDB/PostgreSQL for production
* **Docker deployment**: Easy production deployment with Docker and Docker Compose
* **Multi-architecture**: Supports x86_64 and ARM64 (including Raspberry Pi)

Quick Start
-----------

Docker is the only supported deployment method for production. See :doc:`deployment` for
detailed instructions including environment configuration, monitoring setup, and troubleshooting.

.. code-block:: bash

   # Clone and configure
   git clone https://github.com/Decaturmakers/kiosk-show-replacement.git
   cd kiosk-show-replacement
   cp .env.docker.example .env
   # Edit .env with your settings (SECRET_KEY, passwords, etc.)

   # Start the application
   docker-compose -f docker-compose.prod.yml up -d

   # Access at http://localhost:5000/admin (default: admin/admin)

For local development setup (Python/Poetry), see :doc:`development`.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
