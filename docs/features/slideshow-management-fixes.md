# Slideshow Management Fixes

You must read, understand, and follow all instructions in `./README.md` when planning and implementing this feature.

## Overview

We need to make two improvements to management of slideshows and items, ensuring we also provide full test coverage for these changes:

1. Currently, inactive items cannot be deleted from a slideshow. Fix this so that inactive items can be deleted.
2. Add functionality to the Slideshows admin page (`/admin/slideshows`) to duplicate/copy a slideshow. This would create an exact copy of the slideshow with a different name.

When all work is complete and all tests are passing, make a minor version bump to `pyproject.toml`, commit all changes, push the branch to origin, open a PR, and wait for all PR builds to succeed.
