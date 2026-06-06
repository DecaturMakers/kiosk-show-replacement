API Reference
=============

This section provides detailed documentation for all Flask routes and REST API endpoints.

Base URL
--------

* **Development**: ``http://localhost:5000``
* **Production**: ``https://your-domain.com``

Authentication
--------------

**Session-based Authentication**: All protected routes use Flask sessions. Login via ``/auth/login`` (web) or ``/api/v1/auth/login`` (API).

**User Management**: Users are created by administrators through the admin interface or API. Passwords are securely hashed using bcrypt. Users can be assigned admin privileges, which grants access to user management features.

**Default Admin User**: On first run, a default admin user is created with username ``admin`` and password ``admin`` (or the value of ``KIOSK_ADMIN_PASSWORD`` environment variable). Change this password immediately in production.

Standard Response Format
------------------------

**Success Response:**

.. code-block:: json

   {
     "success": true,
     "data": {},
     "message": "Optional success message"
   }

**Error Response:**

.. code-block:: json

   {
     "success": false,
     "error": "Error message",
     "code": 400
   }

**Status Codes:**

* ``200 OK``: Request successful
* ``201 Created``: Resource created successfully
* ``400 Bad Request``: Invalid request data
* ``401 Unauthorized``: Authentication required
* ``403 Forbidden``: Access denied (admin required)
* ``404 Not Found``: Resource not found
* ``500 Internal Server Error``: Server error

Content Types
-------------

All API endpoints accept and return JSON data with ``Content-Type: application/json``.

Data Models
-----------

**User Model:**

.. code-block:: json

   {
     "id": 1,
     "username": "string",
     "email": "string",
     "is_active": true,
     "is_admin": true,
     "created_at": "2024-01-01T00:00:00Z",
     "updated_at": "2024-01-01T00:00:00Z",
     "last_login_at": "2024-01-01T00:00:00Z"
   }

**Slideshow Model:**

.. code-block:: json

   {
     "id": 1,
     "name": "string",
     "description": "string",
     "is_active": true,
     "is_default": false,
     "default_item_duration": 30,
     "transition_type": "fade",
     "total_duration": 120,
     "active_items_count": 4,
     "owner_id": 1,
     "created_at": "2024-01-01T00:00:00Z",
     "updated_at": "2024-01-01T00:00:00Z"
   }

**Slideshow Item Model:**

.. code-block:: json

   {
     "id": 1,
     "slideshow_id": 1,
     "title": "string",
     "content_type": "image|video|url|text",
     "content_url": "string",
     "content_text": "string",
     "content_file_path": "string",
     "content_source": "string",
     "display_url": "string",
     "display_duration": 30,
     "effective_duration": 30,
     "order_index": 0,
     "is_active": true,
     "created_at": "2024-01-01T00:00:00Z",
     "updated_at": "2024-01-01T00:00:00Z"
   }

**Display Model:**

.. code-block:: json

   {
     "id": 1,
     "name": "string",
     "description": "string",
     "resolution_width": 1920,
     "resolution_height": 1080,
     "resolution_string": "1920x1080",
     "resolution": "1920x1080",
     "rotation": 0,
     "location": "string",
     "is_active": true,
     "is_online": false,
     "online": false,
     "last_seen_at": "2024-01-01T00:00:00Z",
     "heartbeat_interval": 60,
     "owner_id": 1,
     "current_slideshow_id": 1,
     "created_at": "2024-01-01T00:00:00Z",
     "updated_at": "2024-01-01T00:00:00Z"
   }

**Assignment History Model:**

.. code-block:: json

   {
     "id": 1,
     "display_id": 1,
     "display_name": "string",
     "previous_slideshow_id": 1,
     "previous_slideshow_name": "string",
     "new_slideshow_id": 2,
     "new_slideshow_name": "string",
     "action": "assign|unassign|change",
     "reason": "string",
     "created_at": "2024-01-01T00:00:00Z",
     "created_by_id": 1,
     "created_by_username": "string"
   }

Application Routes
==================

Main Application Routes
-----------------------

``GET /``
~~~~~~~~~
**Purpose**: Application home page  
**Authentication**: Optional  
**Returns**: Redirect to ``/admin`` if authenticated, otherwise ``/auth/login``

``GET /health``
~~~~~~~~~~~~~~~
**Purpose**: Health check endpoint  
**Authentication**: None  
**Returns**: ``{"status": "healthy", "version": "0.1.0"}``

``GET /about``
~~~~~~~~~~~~~~
**Purpose**: About page with application information  
**Authentication**: None  
**Returns**: HTML page with app info

``GET /uploads/<path:filename>``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: Serve uploaded files  
**Authentication**: None  
**Parameters**: 
  - ``filename`` (path): File path to serve
**Returns**: File content or 404

Authentication Routes
---------------------

``GET /auth/login``
~~~~~~~~~~~~~~~~~~~
**Purpose**: Login page  
**Authentication**: None  
**Returns**: HTML login form

``POST /auth/login``
~~~~~~~~~~~~~~~~~~~~
**Purpose**: Process login  
**Authentication**: None  
**Parameters**: 
  - ``username`` (form): Username (any value accepted)
  - ``password`` (form): Password (any value accepted)
**Returns**: Redirect to dashboard or login page with error

``GET /auth/logout``
~~~~~~~~~~~~~~~~~~~~
**Purpose**: Logout current user  
**Authentication**: Required  
**Returns**: Redirect to login page

``GET /auth/status``
~~~~~~~~~~~~~~~~~~~~
**Purpose**: Get authentication status  
**Authentication**: Optional  
**Returns**: ``{"authenticated": true/false, "user": {...}}``

Dashboard Routes
----------------

``GET /``
~~~~~~~~~
**Purpose**: Main dashboard (same as root)  
**Authentication**: Required  
**Returns**: HTML dashboard with slideshow/display stats

``GET /profile``
~~~~~~~~~~~~~~~~
**Purpose**: User profile page  
**Authentication**: Required  
**Returns**: HTML page with user information

``GET /settings``
~~~~~~~~~~~~~~~~~
**Purpose**: Admin settings page  
**Authentication**: Required (Admin)  
**Returns**: HTML page with admin settings

``GET /health``
~~~~~~~~~~~~~~~
**Purpose**: Dashboard health check  
**Authentication**: None  
**Returns**: ``{"status": "healthy", "timestamp": "..."}``

Slideshow Management Routes (Web)
----------------------------------

``GET /slideshow/``
~~~~~~~~~~~~~~~~~~~
**Purpose**: List all slideshows  
**Authentication**: Required  
**Returns**: HTML page with slideshow list

``GET /slideshow/create``
~~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: Show create slideshow form  
**Authentication**: Required  
**Returns**: HTML form for creating slideshow

``POST /slideshow/create``
~~~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: Create new slideshow  
**Authentication**: Required  
**Parameters**: 
  - ``name`` (form): Slideshow name (required)
  - ``description`` (form): Description (optional)
**Returns**: Redirect to edit page or form with errors

``GET /slideshow/<int:slideshow_id>/edit``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: Edit slideshow and its slides  
**Authentication**: Required  
**Parameters**: 
  - ``slideshow_id`` (path): Slideshow ID
**Returns**: HTML edit form with slides

``POST /slideshow/<int:slideshow_id>/delete``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: Delete slideshow (soft delete)  
**Authentication**: Required  
**Parameters**: 
  - ``slideshow_id`` (path): Slideshow ID
**Returns**: Redirect to slideshow list

Display Interface Routes
------------------------

``GET /display/``
~~~~~~~~~~~~~~~~~
**Purpose**: Display interface landing page  
**Authentication**: None  
**Returns**: HTML display configuration page

``GET /display/<string:display_name>``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: Main display interface for kiosk  
**Authentication**: None  
**Parameters**: 
  - ``display_name`` (path): Display identifier
**Returns**: HTML slideshow interface or configuration page
**Side Effects**: Auto-creates display if not exists, updates heartbeat

``GET /display/<string:display_name>/info``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: Display information and status  
**Authentication**: None  
**Parameters**: 
  - ``display_name`` (path): Display identifier
**Returns**: HTML page with display info and slideshow data

``POST /display/<string:display_name>/heartbeat``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: Update display heartbeat and resolution  
**Authentication**: None  
**Parameters**: 
  - ``display_name`` (path): Display identifier
**Request Body**: 
  .. code-block:: json

     {
       "resolution": {"width": 1920, "height": 1080},
       "user_agent": "Browser info",
       "timestamp": "ISO timestamp"
     }

**Returns**: ``{"status": "success", "timestamp": "..."}``

``GET /display/<string:display_name>/status``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: Get display status and configuration  
**Authentication**: None  
**Parameters**: 
  - ``display_name`` (path): Display identifier
**Returns**: JSON with display status and current slideshow

``GET /display/<string:display_name>/slideshow/current``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: Get current slideshow data for AJAX updates  
**Authentication**: None  
**Parameters**: 
  - ``display_name`` (path): Display identifier
**Returns**: JSON with current slideshow and slides

``POST /display/<string:display_name>/assign/<int:slideshow_id>``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: Assign slideshow to display  
**Authentication**: Required  
**Parameters**: 
  - ``display_name`` (path): Display identifier
  - ``slideshow_id`` (path): Slideshow ID
**Returns**: Redirect with success/error message

``GET /display/slideshow/<int:slideshow_id>``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: Display slideshow by ID  
**Authentication**: None  
**Parameters**: 
  - ``slideshow_id`` (path): Slideshow ID
**Returns**: HTML slideshow interface

``GET /display/<string:display_name>/slideshow/<int:slideshow_id>``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: Display specific slideshow on named display  
**Authentication**: None  
**Parameters**: 
  - ``display_name`` (path): Display identifier
  - ``slideshow_id`` (path): Slideshow ID
**Returns**: HTML slideshow interface

Admin Interface Routes
----------------------

``GET /admin``
~~~~~~~~~~~~~~
**Purpose**: React admin interface entry point  
**Authentication**: Required  
**Returns**: React SPA (production) or redirect to dev server

``GET /admin/<path:path>``
~~~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: React admin interface routes  
**Authentication**: Required  
**Parameters**: 
  - ``path`` (path): React route path
**Returns**: React SPA content

REST API Endpoints
==================

API Root
--------

``GET /api/``
~~~~~~~~~~~~~
**Purpose**: API version information  
**Authentication**: None  
**Returns**: 
  .. code-block:: json

     {
       "message": "Kiosk.show Replacement API",
       "versions": {"v1": "/api/v1/"},
       "documentation": "/api/v1/docs"
     }

``GET /api/health``
~~~~~~~~~~~~~~~~~~~
**Purpose**: API health check  
**Authentication**: None  
**Returns**:
  .. code-block:: json

     {
       "status": "healthy",
       "api_version": "v1",
       "endpoints": [...]
     }

API v1 Authentication
---------------------

``POST /api/v1/auth/login``
~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: API login endpoint  
**Authentication**: None  
**Request Body**: 
  .. code-block:: json

     {
       "username": "string",
       "password": "string"
     }

**Returns**: User object on success, or 401 error if credentials are invalid
**Side Effects**: Establishes session cookie on successful authentication

``GET /api/v1/auth/user``
~~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: Get current user information  
**Authentication**: Required  
**Returns**: Current user object

``POST /api/v1/auth/logout``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: Logout current user  
**Authentication**: Required  
**Returns**: ``{"success": true, "message": "Successfully logged out"}``

API v1 Status
-------------

``GET /api/v1/status``
~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: API status check  
**Authentication**: None  
**Returns**:
  .. code-block:: json

     {
       "status": "healthy",
       "api_version": "v1",
       "timestamp": "2024-01-01T00:00:00Z"
     }

API v1 Slideshows
-----------------

``GET /api/v1/slideshows``
~~~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: List all slideshows  
**Authentication**: Required  
**Returns**: Array of slideshow objects

``POST /api/v1/slideshows``
~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: Create new slideshow  
**Authentication**: Required  
**Request Body**: 
  .. code-block:: json

     {
       "name": "string",
       "description": "string",
       "default_item_duration": 30
     }

**Returns**: Created slideshow object (201)

``GET /api/v1/slideshows/<int:slideshow_id>``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: Get specific slideshow with items  
**Authentication**: Required  
**Parameters**: 
  - ``slideshow_id`` (path): Slideshow ID
**Returns**: Slideshow object with items array

``PUT /api/v1/slideshows/<int:slideshow_id>``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: Update slideshow  
**Authentication**: Required  
**Parameters**: 
  - ``slideshow_id`` (path): Slideshow ID
**Request Body**: 
  .. code-block:: json

     {
       "name": "string",
       "description": "string",
       "default_item_duration": 30,
       "is_active": true
     }

**Returns**: Updated slideshow object

``DELETE /api/v1/slideshows/<int:slideshow_id>``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: Delete slideshow (soft delete)  
**Authentication**: Required  
**Parameters**: 
  - ``slideshow_id`` (path): Slideshow ID
**Returns**: Success message

``POST /api/v1/slideshows/<int:slideshow_id>/set-default``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: Set slideshow as default
**Authentication**: Required
**Parameters**:
  - ``slideshow_id`` (path): Slideshow ID
**Returns**: Success message
**Side Effects**: Unsets previous default slideshow

``POST /api/v1/slideshows/<int:slideshow_id>/duplicate``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: Duplicate slideshow under a new name
**Authentication**: Required
**Parameters**:
  - ``slideshow_id`` (path): Slideshow ID
**Request Body**:
  .. code-block:: json

     {
       "name": "string"
     }

**Returns**: Created slideshow object (201)
**Side Effects**: Copies all items (including inactive ones) and uploaded
media files into the new slideshow. The duplicate is owned by the current
user and is never the default slideshow.

API v1 Slideshow Items
----------------------

``GET /api/v1/slideshows/<int:slideshow_id>/items``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: Get slideshow items  
**Authentication**: Required  
**Parameters**: 
  - ``slideshow_id`` (path): Slideshow ID
**Returns**: Array of slideshow item objects

``POST /api/v1/slideshows/<int:slideshow_id>/items``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: Create slideshow item  
**Authentication**: Required  
**Parameters**: 
  - ``slideshow_id`` (path): Slideshow ID
**Request Body**: 
  .. code-block:: json

     {
       "title": "string",
       "content_type": "image|video|url|text",
       "content_url": "string",
       "content_text": "string",
       "display_duration": 30,
       "order_index": 0
     }

**Returns**: Created item object (201)

``PUT /api/v1/slideshow-items/<int:item_id>``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: Update slideshow item  
**Authentication**: Required  
**Parameters**: 
  - ``item_id`` (path): Item ID
**Request Body**: Same as create
**Returns**: Updated item object

``DELETE /api/v1/slideshow-items/<int:item_id>``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: Delete slideshow item (two-stage)
**Authentication**: Required
**Parameters**:
  - ``item_id`` (path): Item ID
**Returns**: Success message
**Side Effects**: Deleting an active item soft-deletes it (it can be
reactivated by editing it); deleting an already-inactive item permanently
removes it.

``POST /api/v1/slideshow-items/<int:item_id>/reorder``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: Reorder slideshow item  
**Authentication**: Required  
**Parameters**: 
  - ``item_id`` (path): Item ID
**Request Body**: 
  .. code-block:: json

     {
       "new_order": 2
     }

**Returns**: Success message
**Side Effects**: Reorders other items as needed

API v1 Displays
---------------

``GET /api/v1/displays``
~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: List all displays  
**Authentication**: Required  
**Returns**: Array of display objects

``GET /api/v1/displays/<int:display_id>``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: Get specific display  
**Authentication**: Required  
**Parameters**: 
  - ``display_id`` (path): Display ID
**Returns**: Display object

``PUT /api/v1/displays/<int:display_id>``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: Update display  
**Authentication**: Required  
**Parameters**: 
  - ``display_id`` (path): Display ID
**Request Body**: 
  .. code-block:: json

     {
       "name": "string",
       "description": "string",
       "location": "string",
       "rotation": 0,
       "is_active": true
     }

**Returns**: Updated display object

``DELETE /api/v1/displays/<int:display_id>``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: Delete display (soft delete)  
**Authentication**: Required  
**Parameters**: 
  - ``display_id`` (path): Display ID
**Returns**: Success message

``POST /api/v1/displays/<string:display_name>/assign-slideshow``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: Assign slideshow to display by name
**Authentication**: Required
**Parameters**:
  - ``display_name`` (path): Display name
**Request Body**:
  .. code-block:: json

     {
       "slideshow_id": 1,
       "reason": "string"
     }

**Returns**: Success message
**Side Effects**: Creates assignment history record

``POST /api/v1/displays/<int:display_id>/reload``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: Send reload command to display via SSE
**Authentication**: Required
**Parameters**:
  - ``display_id`` (path): Display ID
**Returns**:
  .. code-block:: json

     {
       "success": true,
       "data": {
         "display_id": 1,
         "connections_notified": 1
       },
       "message": "Reload command sent to display 'display-name'"
     }

**Side Effects**: Sends ``display.reload_requested`` SSE event to display

API v1 Assignment History
-------------------------

``GET /api/v1/displays/<int:display_id>/assignment-history``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: Get assignment history for display  
**Authentication**: Required  
**Parameters**: 
  - ``display_id`` (path): Display ID
**Returns**: Array of assignment history objects

``GET /api/v1/assignment-history``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: Get global assignment history  
**Authentication**: Required  
**Query Parameters**: 
  - ``limit`` (optional): Number of records to return
  - ``offset`` (optional): Offset for pagination  
**Returns**: Array of assignment history objects

``POST /api/v1/assignment-history``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: Create assignment history record  
**Authentication**: Required  
**Request Body**: 
  .. code-block:: json

     {
       "display_id": 1,
       "previous_slideshow_id": 1,
       "new_slideshow_id": 2,
       "reason": "string"
     }

**Returns**: Created assignment history object (201)

API v1 Video URL Validation
---------------------------

``POST /api/v1/validate/video-url``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: Validate a video URL for browser compatibility and extract duration
**Authentication**: Required
**Request Body**:
  .. code-block:: json

     {
       "url": "https://example.com/video.mp4"
     }

**Returns** (Success):
  .. code-block:: json

     {
       "success": true,
       "data": {
         "valid": true,
         "duration_seconds": 120,
         "duration": 120.5,
         "codec_info": {
           "video_codec": "h264",
           "audio_codec": "aac",
           "container_format": "mp4"
         }
       }
     }

**Returns** (Invalid Codec):
  .. code-block:: json

     {
       "success": false,
       "error": "Video codec 'mpeg2video' is not supported by web browsers. Supported: h264, vp8, vp9, theora, av1"
     }

**Returns** (Inaccessible URL):
  .. code-block:: json

     {
       "success": false,
       "error": "Could not retrieve video information from the URL. The URL may be inaccessible."
     }

**Notes**:
  - Uses ``ffprobe`` to validate the video URL
  - Timeout is 60 seconds for remote URLs
  - Browser-compatible video codecs: H.264, VP8, VP9, Theora, AV1

API v1 File Uploads
-------------------

``POST /api/v1/uploads/image``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: Upload image file  
**Authentication**: Required  
**Content-Type**: ``multipart/form-data``
**Form Data**: 
  - ``file``: Image file
  - ``slideshow_id``: Slideshow ID (required)
**Returns**: File information object (201)
**Limits**: Max 50MB per image

``POST /api/v1/uploads/video``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: Upload video file  
**Authentication**: Required  
**Content-Type**: ``multipart/form-data``
**Form Data**: 
  - ``file``: Video file
  - ``slideshow_id``: Slideshow ID (required)
**Returns**: File information object (201) 
**Limits**: Max 500MB per video

``GET /api/v1/uploads/<int:file_id>``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: Get file information  
**Authentication**: Required  
**Parameters**: 
  - ``file_id`` (path): File ID
**Returns**: Not implemented (501)

``DELETE /api/v1/uploads/<int:file_id>``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: Delete uploaded file  
**Authentication**: Required  
**Parameters**: 
  - ``file_id`` (path): File ID  
**Returns**: Not implemented (501)

``GET /api/v1/uploads/stats``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Purpose**: Get storage statistics  
**Authentication**: Required  
**Returns**: 
  .. code-block:: json

     {
       "total_size": 1024000,
       "total_size_formatted": "1.0 MB",
       "image_size": 512000,
       "image_size_formatted": "512.0 KB",
       "video_size": 512000,
       "video_size_formatted": "512.0 KB",
       "total_files": 10,
       "image_files": 5,
       "video_files": 5,
       "users_with_files": 2,
       "slideshows_with_files": 3
     }
