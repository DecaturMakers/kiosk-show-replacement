Usage
=====

Web Interface
-------------

The application provides two main interfaces:

1. **Admin Management Interface** - Modern React-based admin panel
2. **Display Kiosk Interface** - Full-screen slideshow display

Admin Management Interface
~~~~~~~~~~~~~~~~~~~~~~~~~~

The admin interface is a modern React application accessible at ``/admin`` (e.g., ``http://localhost:5000/admin``).

**Features:**
* Dashboard with system statistics and quick actions
* Complete slideshow management (create, edit, duplicate, delete, preview)
* Display management and assignment
* Assignment history and audit trails
* Bulk operations for display management
* Drag-and-drop slideshow assignment
* Real-time status monitoring

**Default Login:**
* Username: ``admin``
* Password: ``admin`` (change this in production!)

**Navigation:**
* **Dashboard** - Overview and quick actions
* **Slideshows** - Manage slideshow content and settings
* **Displays** - Monitor and manage display devices
* **Assignment History** - View slideshow assignment audit trail

User Management
~~~~~~~~~~~~~~~

After logging in as admin, you should:

1. **Change the default admin password**: Go to Profile Settings (click username dropdown)
2. **Create user accounts**: Go to User Management (admin only) to create accounts for other administrators

**User Management Features (Admin Only):**

* Create new users with auto-generated temporary passwords
* Edit user email, admin status, and active status
* Reset user passwords (generates new temporary password)
* Deactivate users (prevents login without deleting)

**Profile Settings (All Users):**

* Update email address
* Change password (requires current password)

Creating Slideshows
~~~~~~~~~~~~~~~~~~~

1. Navigate to the admin interface at ``/admin``
2. Click "Create New Slideshow"
3. Enter a name and description
4. Add slides with images, videos, or web content
5. Configure display settings (duration, transitions, etc.)

Duplicating Slideshows
~~~~~~~~~~~~~~~~~~~~~~

To copy an existing slideshow, click the Duplicate button on the Slideshows
page and enter a name for the copy. The duplicate contains the same settings
and slides as the original (uploaded images and videos are copied, so the
two slideshows are fully independent). The copy is never the default
slideshow, regardless of the original's setting.

Managing Slides
~~~~~~~~~~~~~~~

For each slideshow, you can:

* Add new slides
* Reorder slides by dragging and dropping
* Edit slide content and settings
* Remove slides
* Preview the slideshow

Removing a slide deactivates it rather than deleting it, so it can be
restored later by editing the slide and marking it active. Deleting an
inactive slide removes it permanently.

Video Format Requirements
~~~~~~~~~~~~~~~~~~~~~~~~~

When uploading video files, the server validates that the video uses a codec
supported by web browsers. Videos with unsupported codecs will be rejected
with a clear error message.

**Supported Video Codecs:**

* **H.264** (MP4 containers) - Universally supported by all modern browsers
* **VP8** (WebM containers) - Supported by most modern browsers
* **VP9** (WebM containers) - Supported by most modern browsers
* **Theora** (Ogg containers) - Limited browser support
* **AV1** (WebM containers) - Growing browser support

**Recommended Format:**

For maximum compatibility, we recommend using **MP4 files with H.264 video codec
and AAC audio codec**. This format is supported by all modern web browsers
including Chrome, Firefox, Safari, and Edge.

**Converting Videos:**

If you have a video in an unsupported format (e.g., MPEG-1, MPEG-2, WMV, AVI with
older codecs), you can convert it using FFmpeg:

.. code-block:: bash

   # Convert any video to MP4 (H.264)
   ffmpeg -i input.mpeg -c:v libx264 -c:a aac output.mp4

   # Convert to WebM (VP9)
   ffmpeg -i input.avi -c:v libvpx-vp9 -c:a libopus output.webm

Text Slide Formatting
~~~~~~~~~~~~~~~~~~~~~

Text slides support basic HTML formatting for enhanced presentation:

**Supported Tags:**

* ``<b>``, ``<strong>`` - Bold text
* ``<i>``, ``<em>`` - Italic text
* ``<u>`` - Underlined text
* ``<br>`` - Line break
* ``<p>`` - Paragraph

**Examples:**

.. code-block:: html

   This is <b>bold</b> and <i>italic</i> text.
   <p>This is a paragraph.</p>
   Line one<br>Line two

**Security:** All other HTML tags and attributes are automatically stripped
to prevent XSS attacks. Plain text without HTML tags will have newlines
preserved as line breaks.

Skedda Calendar Slides
~~~~~~~~~~~~~~~~~~~~~~

The Skedda calendar slide type displays reservations from a Skedda booking system
(or any compatible iCal/ICS feed) in a visual grid format.

**Setting Up a Skedda Calendar Slide:**

1. Create or edit a slideshow
2. Click "Add Slide"
3. Select "Skedda Calendar" as the content type
4. Enter your Skedda ICS feed URL (e.g., ``https://yourspace.skedda.com/ical/...``)
5. Configure the refresh interval (how often to fetch updated booking data)
6. Save the slide

**Configuration Options:**

* **ICS Feed URL** (required): The URL of your Skedda iCal feed. Find this in your
  Skedda account under Settings > Integrations > iCal.
* **Refresh Interval**: How often to fetch updated booking data from the ICS feed.
  Options: 5, 10, 15 (default), 30, or 60 minutes.

**Calendar Display Features:**

* Grid view showing time slots (rows) and spaces/resources (columns)
* Events displayed with the person's name and booking description
* Current time indicator with auto-scroll to keep current time visible
* Auto-refresh: calendar data is refreshed each time the slide becomes active
* Visual distinction between regular and recurring events (gray background)

Kiosk Display Mode
~~~~~~~~~~~~~~~~~~

Access the full-screen kiosk display at ``/display/<display-name>``:

* Full-screen slideshow display
* Automatic slide transitions
* Touch/click navigation
* Keyboard controls (space bar, arrow keys)

Programmatic Access
-------------------

For programmatic management of slideshows, displays, and other resources,
the application provides a complete REST API. See :doc:`api` for full
API documentation including authentication, endpoints, and examples.
