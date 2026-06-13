Deployment
==========

This guide covers deploying kiosk-show-replacement in production environments
using Docker.

.. note::

   **Docker is the only supported deployment method for production.**

   For local development setup without Docker, see :doc:`development`.

System Requirements
-------------------

* Docker Engine 20.10 or higher
* Docker Compose 2.0 or higher
* 512MB+ RAM (1GB+ recommended)
* 1GB+ disk space

The application supports both x86_64 and ARM64 architectures, including
Raspberry Pi 4 and newer.

Docker Deployment
-----------------

Docker provides the easiest and most reproducible deployment method. The
application supports both x86_64 and ARM64 architectures (including Raspberry Pi).

Quick Start
~~~~~~~~~~~

1. Clone the repository:

   .. code-block:: bash

      git clone https://github.com/Decaturmakers/kiosk-show-replacement.git
      cd kiosk-show-replacement

2. Copy and configure the environment file:

   .. code-block:: bash

      cp .env.docker.example .env

3. Edit ``.env`` and set required values:

   .. code-block:: bash

      # Generate a secure secret key
      python -c "import secrets; print(secrets.token_hex(32))"

      # Edit .env with your values
      SECRET_KEY=<generated-key>
      MYSQL_ROOT_PASSWORD=<strong-password>
      MYSQL_PASSWORD=<strong-password>
      KIOSK_ADMIN_PASSWORD=<strong-password>

4. Create data directories with correct ownership:

   .. code-block:: bash

      mkdir -p .docker-data/prod/uploads .docker-data/prod/mariadb
      sudo chown -R 1000:1000 .docker-data/prod/uploads .docker-data/prod/mariadb
      chmod 750 .docker-data/prod/mariadb

   .. important::

      The MariaDB container runs as UID:GID 1000:1000 to avoid permission issues
      with bind-mounted volumes. The data directories **must** be owned by this
      UID:GID before starting the containers for the first time. If you need to
      use a different UID:GID, edit the ``user:`` directive in
      ``docker-compose.prod.yml``.

5. Start the application:

   .. code-block:: bash

      docker-compose -f docker-compose.prod.yml --env-file .env up -d

6. Access the application at http://localhost:5000/admin

Verifying Installation
~~~~~~~~~~~~~~~~~~~~~~

Check the application health:

.. code-block:: bash

   curl http://localhost:5000/health

Check container status:

.. code-block:: bash

   docker-compose -f docker-compose.prod.yml ps

View logs:

.. code-block:: bash

   docker-compose -f docker-compose.prod.yml logs -f app

Development with Docker
~~~~~~~~~~~~~~~~~~~~~~~

For development with Docker (using SQLite):

.. code-block:: bash

   # Start development environment
   docker-compose up

   # The application will be available at http://localhost:5000

This uses SQLite and mounts the source code for development visibility.

Production Configuration
------------------------

Environment Variables
~~~~~~~~~~~~~~~~~~~~~

Required variables for production:

========================= ==========================================
Variable                  Description
========================= ==========================================
``SECRET_KEY``            Flask secret key for session security
``MYSQL_ROOT_PASSWORD``   MariaDB root password
``MYSQL_PASSWORD``        MariaDB application user password
``KIOSK_ADMIN_PASSWORD``  Initial admin user password
========================= ==========================================

Optional variables (with defaults):

========================= ==========================================
Variable                  Default
========================= ==========================================
``APP_PORT``              5000
``TZ``                    America/New_York (IANA timezone for calendar
                          display)
``MYSQL_DATABASE``        kiosk_show
``MYSQL_USER``            kiosk
``MYSQL_HOST``            (none; enables MySQL auto-configuration)
``MYSQL_PORT``            3306
``KIOSK_ADMIN_USERNAME``  admin
``KIOSK_ADMIN_EMAIL``     (none)
``GUNICORN_WORKERS``      2
========================= ==========================================

Database Configuration
~~~~~~~~~~~~~~~~~~~~~~

The application supports multiple database backends. There are two ways to
configure the database connection:

**Option 1: Individual MYSQL_* variables (recommended for Docker)**

Set the individual ``MYSQL_*`` environment variables and the application will
automatically construct the ``DATABASE_URL`` connection string. This happens
both in the Docker entrypoint script and in the Python configuration module.

.. code-block:: bash

   MYSQL_HOST=mariadb
   MYSQL_USER=kiosk
   MYSQL_PASSWORD=secretpassword
   MYSQL_DATABASE=kiosk_show
   MYSQL_PORT=3306          # optional, defaults to 3306

When ``MYSQL_HOST`` is set and ``DATABASE_URL`` is not, the application
constructs: ``mysql+pymysql://user:password@host:port/database``

**Option 2: Direct DATABASE_URL**

Set the ``DATABASE_URL`` environment variable directly to a full connection
string. This takes precedence over individual ``MYSQL_*`` variables.

**SQLite** (development/single-node):

.. code-block:: bash

   DATABASE_URL=sqlite:///kiosk_show.db

**MariaDB/MySQL** (production):

.. code-block:: bash

   DATABASE_URL=mysql+pymysql://user:password@host:3306/database

**PostgreSQL**:

.. code-block:: bash

   DATABASE_URL=postgresql://user:password@host:5432/database

The production Docker Compose file automatically configures MariaDB.

.. important::

   In production mode, the application **will not start** if the database
   resolves to SQLite. You must configure either ``DATABASE_URL`` or the
   ``MYSQL_*`` variables. This prevents silent data loss from an ephemeral
   SQLite database inside a container.

NewRelic Monitoring
~~~~~~~~~~~~~~~~~~~

The application supports optional NewRelic monitoring for performance insights
and error tracking. Both APM (backend) and Browser (frontend) monitoring are
automatically enabled when the ``NEW_RELIC_LICENSE_KEY`` environment variable
is set.

**What's Included:**

* **APM Monitoring** - Backend performance, database queries, external calls
* **Browser Monitoring** - Frontend page load times, JavaScript errors, user sessions
* **Distributed Tracing** - Automatic correlation between browser requests and backend transactions

**Enabling NewRelic:**

1. Obtain a license key from `NewRelic <https://one.newrelic.com/admin-portal/api-keys/home>`_

2. Add the following to your ``.env`` file:

   .. code-block:: bash

      NEW_RELIC_LICENSE_KEY=your-license-key-here
      NEW_RELIC_APP_NAME=kiosk-show-replacement

3. Restart the application:

   .. code-block:: bash

      docker-compose -f docker-compose.prod.yml restart app

**NewRelic Environment Variables:**

*Required:*

=========================================== ==========================================
Variable                                    Description
=========================================== ==========================================
``NEW_RELIC_LICENSE_KEY``                   Your NewRelic license key.
``NEW_RELIC_APP_NAME``                      Application name in dashboard
                                            (default: kiosk-show-replacement)
=========================================== ==========================================

*Optional (general):*

=========================================== ==========================================
Variable                                    Description
=========================================== ==========================================
``NEW_RELIC_ENVIRONMENT``                   Environment tag (e.g., production, staging)
``NEW_RELIC_LOG_LEVEL``                     Agent log level: critical, error, warning,
                                            info, debug (default: info)
``NEW_RELIC_API_KEY``                       NewRelic User API key (if needed)
=========================================== ==========================================

*Feature toggles (all default to true when not set):*

.. note::

   The NewRelic Python agent controls these features locally via environment
   variables (or a config file). In the NewRelic UI, these appear as managed
   "per server configuration." To enable them, set the corresponding
   environment variable to ``true``.

====================================================== ==========================================
Variable                                               Description
====================================================== ==========================================
``NEW_RELIC_BROWSER_MONITORING_AUTO_INSTRUMENT``       Auto-inject the NewRelic Browser JavaScript
                                                       agent into HTML pages for Real User
                                                       Monitoring (page loads, JS errors, sessions)
``NEW_RELIC_DISTRIBUTED_TRACING_ENABLED``              Correlate requests across services and
                                                       between browser and backend transactions
``NEW_RELIC_TRANSACTION_TRACER_ENABLED``               Capture deep information about slow
                                                       transactions (response time, DB queries)
``NEW_RELIC_SLOW_SQL_ENABLED``                         Capture details from long-running SQL
                                                       database queries
``NEW_RELIC_ERROR_COLLECTOR_ENABLED``                  Capture uncaught and logged exceptions
                                                       for viewing in the NewRelic UI
``NEW_RELIC_THREAD_PROFILER_ENABLED``                  Allow thread profiling sessions to be
                                                       scheduled via the NewRelic UI
====================================================== ==========================================

**Verifying NewRelic is Active:**

Check the application logs for NewRelic activation:

.. code-block:: bash

   docker-compose -f docker-compose.prod.yml logs app | grep -i newrelic

You should see "NewRelic monitoring enabled" if properly configured.

To verify browser monitoring, view page source in your browser and look for
the NewRelic browser agent script in the ``<head>`` section. The script is
automatically injected into all HTML pages when the APM agent is active.

Prometheus Metrics
~~~~~~~~~~~~~~~~~~

The application exposes a ``/metrics`` endpoint in Prometheus text format for
scraping by Prometheus or compatible monitoring systems.

**Endpoint:** ``GET /metrics``

**Authentication:** None required (publicly accessible)

**Metrics Exposed:**

*HTTP Metrics:*

* ``http_requests_total`` - Total HTTP requests (labels: method, endpoint, status)
* ``http_request_duration_seconds`` - Request duration histogram (label: endpoint)

*System Metrics:*

* ``active_sse_connections`` - Current number of Server-Sent Events connections
* ``database_errors_total`` - Total database errors
* ``storage_errors_total`` - Total storage errors

*Display Metrics (per-display, labels: display_id, display_name):*

* ``display_info`` - Info gauge (always 1) with slideshow_id/name labels
* ``display_online`` - Online status (1=online, 0=offline)
* ``display_resolution_width_pixels`` - Display width in pixels
* ``display_resolution_height_pixels`` - Display height in pixels
* ``display_rotation_degrees`` - Rotation (0, 90, 180, 270)
* ``display_last_seen_timestamp_seconds`` - Unix timestamp of last heartbeat
* ``display_heartbeat_interval_seconds`` - Configured heartbeat interval
* ``display_heartbeat_age_seconds`` - Seconds since last heartbeat
* ``display_missed_heartbeats`` - Number of missed heartbeats
* ``display_sse_connected`` - SSE connection status (1=connected, 0=disconnected)
* ``display_is_active`` - Active status (1=active, 0=inactive)

*Summary Metrics:*

* ``displays_total`` - Total number of displays
* ``displays_online_total`` - Number of online displays
* ``displays_active_total`` - Number of active (not disabled) displays
* ``slideshows_total`` - Total number of slideshows

**Example Prometheus Configuration:**

.. code-block:: yaml

   scrape_configs:
     - job_name: 'kiosk-show'
       static_configs:
         - targets: ['localhost:5000']
       metrics_path: '/metrics'

**Example Queries:**

.. code-block:: promql

   # Percentage of online displays
   displays_online_total / displays_total * 100

   # Displays with missed heartbeats
   display_missed_heartbeats > 0

   # Request rate by endpoint
   rate(http_requests_total[5m])

Resource Limits
~~~~~~~~~~~~~~~

The production Docker Compose file includes resource limits:

**Application container:**

* CPU: 2 cores max, 0.5 cores reserved
* Memory: 1GB max, 256MB reserved

**Database container:**

* CPU: 1 core max, 0.25 cores reserved
* Memory: 512MB max, 128MB reserved

For Raspberry Pi deployments, consider reducing these limits:

.. code-block:: yaml

   # In docker-compose.prod.yml
   deploy:
     resources:
       limits:
         cpus: '1'
         memory: 512M

Production Checklist
--------------------

Before deploying to production:

1. **Security**

   * [ ] Generate a strong ``SECRET_KEY``
   * [ ] Set strong passwords for database and admin user
   * [ ] **Change the default admin password** immediately after first login
   * [ ] Create individual user accounts for each administrator
   * [ ] Deactivate or change credentials for any default/test accounts
   * [ ] Review and restrict network access
   * [ ] Consider adding a reverse proxy (nginx, Caddy) with TLS

2. **Database**

   * [ ] Configure database backups
   * [ ] Consider using external managed database for critical deployments

3. **Monitoring**

   * [ ] Set up container health monitoring
   * [ ] Configure log aggregation if needed
   * [ ] Set up alerts for container failures
   * [ ] Consider enabling NewRelic APM for performance monitoring

4. **Data Persistence**

   * [ ] Verify volume mounts are working
   * [ ] Test backup and restore procedures
   * [ ] Document recovery procedures

Upgrade Procedures
------------------

To upgrade to a new version:

1. **Backup your data**:

   .. code-block:: bash

      # Stop the application
      docker-compose -f docker-compose.prod.yml down

      # Backup database (MariaDB)
      docker-compose -f docker-compose.prod.yml run --rm db \
        mysqldump -u root -p$MYSQL_ROOT_PASSWORD $MYSQL_DATABASE > backup.sql

      # Backup uploads
      tar -czf uploads_backup.tar.gz ./data/uploads

2. **Pull new version**:

   .. code-block:: bash

      git pull origin main

3. **Rebuild and restart**:

   .. code-block:: bash

      docker-compose -f docker-compose.prod.yml build
      docker-compose -f docker-compose.prod.yml up -d

4. **Verify**:

   .. code-block:: bash

      # Check health
      curl http://localhost:5000/health

      # Check logs for errors
      docker-compose -f docker-compose.prod.yml logs -f app

Database migrations run automatically on container startup.

Troubleshooting
---------------

Container won't start
~~~~~~~~~~~~~~~~~~~~~

Check the logs:

.. code-block:: bash

   docker-compose -f docker-compose.prod.yml logs app

Common issues:

* **Missing environment variables**: Ensure all required variables are set
* **Database not ready**: The entrypoint waits up to 60 seconds for database
* **Port already in use**: Change ``APP_PORT`` or stop conflicting service

Database connection errors
~~~~~~~~~~~~~~~~~~~~~~~~~~

Verify database is healthy:

.. code-block:: bash

   docker-compose -f docker-compose.prod.yml exec db \
     mysql -u root -p$MYSQL_ROOT_PASSWORD -e "SELECT 1"

Check database logs:

.. code-block:: bash

   docker-compose -f docker-compose.prod.yml logs db

Permission issues with uploads
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The container runs as non-root user (UID 1000). Ensure volume permissions:

.. code-block:: bash

   # Fix permissions on host
   sudo chown -R 1000:1000 ./data/uploads

MariaDB healthcheck failing
~~~~~~~~~~~~~~~~~~~~~~~~~~~

If the MariaDB container shows repeated "Access denied for user 'root'@'localhost'
(using password: NO)" errors and never becomes healthy, this is typically a
permission issue with the healthcheck credentials file.

**Cause:** MariaDB creates a ``.my-healthcheck.cnf`` file in the data directory
during initialization. If the data directory has overly permissive permissions
(e.g., 777), MariaDB will ignore the config file as a security measure.

**Solution:**

1. Stop the containers:

   .. code-block:: bash

      docker-compose -f docker-compose.prod.yml down

2. Fix the permissions on the healthcheck file:

   .. code-block:: bash

      sudo chmod 600 .docker-data/prod/mariadb/.my-healthcheck.cnf

3. Ensure the data directory has correct ownership and permissions:

   .. code-block:: bash

      sudo chown -R 1000:1000 .docker-data/prod/mariadb
      chmod 750 .docker-data/prod/mariadb

4. Restart the containers:

   .. code-block:: bash

      docker-compose -f docker-compose.prod.yml up -d

**Prevention:** Always create the data directories with correct ownership before
first run (see Quick Start step 4).

Data disappearing after container restart
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If your data disappears after restarting the container, the application is
likely using an ephemeral SQLite database inside the container instead of your
configured MySQL/MariaDB database.

**Symptoms:**

* Data lost on container restart
* MySQL database has no tables
* Health check ``/health/db`` shows ``database_type: "sqlite"``

**Cause:** The application only reads the ``DATABASE_URL`` environment variable
for its connection string. If you set individual ``MYSQL_*`` variables but not
``DATABASE_URL``, and are not using ``docker-compose.prod.yml`` (which constructs
it automatically), the app falls back to SQLite.

**Solution:**

As of version 0.3.0, the application automatically constructs ``DATABASE_URL``
from ``MYSQL_*`` variables. For older versions, either:

1. Set ``DATABASE_URL`` explicitly, or
2. Use ``docker-compose.prod.yml`` which constructs it for you

You can verify which database is in use via the health endpoint:

.. code-block:: bash

   curl http://localhost:5000/health/db | jq .database_type

Health check failing
~~~~~~~~~~~~~~~~~~~~

The health check uses ``/health`` endpoint:

.. code-block:: bash

   # Test manually
   curl http://localhost:5000/health

   # Check container health status
   docker inspect --format='{{.State.Health.Status}}' \
     $(docker-compose -f docker-compose.prod.yml ps -q app)

SQLite to MariaDB Migration
---------------------------

If you're migrating from a SQLite development database to MariaDB production:

1. **Export data from SQLite**:

   .. code-block:: bash

      # Using Flask shell
      flask shell
      >>> from kiosk_show_replacement.models import *
      >>> # Export your data using SQLAlchemy queries

2. **Start fresh with MariaDB**:

   The application will create tables and a default admin user automatically
   on first start.

3. **Re-import data** (if needed):

   Use the admin interface or API to recreate slideshows and content.

For large datasets, consider using database migration tools like ``pgloader``
or custom scripts.
