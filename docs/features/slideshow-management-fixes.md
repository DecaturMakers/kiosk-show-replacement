# Slideshow Management Fixes

You must read, understand, and follow all instructions in `./README.md` when planning and implementing this feature.

## Overview

We need to make two improvements to management of slideshows and items, ensuring we also provide full test coverage for these changes:

1. Currently, inactive items cannot be deleted from a slideshow. Fix this so that inactive items can be deleted.
2. Add functionality to the Slideshows admin page (`/admin/slideshows`) to duplicate/copy a slideshow. This would create an exact copy of the slideshow with a different name.

When all work is complete and all tests are passing, make a minor version bump to `pyproject.toml`, commit all changes, push the branch to origin, open a PR, and wait for all PR builds to succeed.

## Design Decisions (human-approved)

1. **Inactive item deletion semantics**: Deleting an *inactive* item performs a **hard delete** (permanent removal from the database). Deleting an *active* item keeps the current soft-delete behavior (sets `is_active=False`). Net effect: first delete deactivates, second delete permanently removes.
2. **Duplicate naming**: The user is **prompted for a name** for the new slideshow when duplicating (pre-filled with `"{Original Name} (Copy)"` as a convenience).
3. **Uploaded media files**: Duplication **physically copies** uploaded image/video files into the new slideshow's upload directory (`uploads/{content_type}/{user_id}/{new_slideshow_id}/`), so the copy is fully independent of the original.
4. **Copy scope**: Duplication copies **all items, including inactive (soft-deleted) ones**; they remain inactive in the copy. The copy is an exact copy except: new `name`, `is_default=False` (only one default slideshow may exist), `owner_id`/`created_by_id`/`updated_by_id` set to the current user, and fresh timestamps.

## Background / Root Cause Analysis

### Fix 1: Inactive items cannot be deleted

- `DELETE /api/v1/slideshow-items/<id>` (`kiosk_show_replacement/api/v1.py`, `delete_slideshow_item()`) performs a soft delete, but rejects inactive items with a 404: `if not item or not item.is_active`. An item that has already been soft-deleted can therefore never be removed.
- The frontend (`frontend/src/pages/SlideshowDetail.tsx`) fetches items with `include_inactive=true` and renders a Delete button for *all* items, so users see a Delete button on inactive items that always fails.
- The update endpoint (`update_slideshow_item()`) intentionally allows operating on inactive items (for reactivation), so the delete endpoint's behavior is also inconsistent with its sibling.

### Fix 2: Duplicate slideshow

- No duplicate/copy capability exists. Relevant building blocks:
  - `Slideshow` model fields to copy: `description`, `default_item_duration`, `transition_type`. Not copied: `is_default` (forced `False`), audit/ownership fields (set to current user).
  - `SlideshowItem` fields to copy: `title`, `content_type`, `content_url`, `content_text`, `content_file_path` (rewritten for copied files), `display_duration`, `order_index`, `is_active`, `scale_factor`, `ical_feed_id`, `ical_refresh_minutes`.
  - Slideshow names are validated as globally unique among active slideshows (`create_slideshow()` in `api/v1.py`), with a DB `UniqueConstraint("name", "owner_id")` backstop. The duplicate endpoint must apply the same validation.
  - Uploaded files live at `uploads/{content_type}/{user_id}/{slideshow_id}/` (`kiosk_show_replacement/storage.py`), so file-backed items need their files copied to the new slideshow's directory and `content_file_path` rewritten.

## Implementation Plan

Commit message prefix: `Slideshow Management Fixes - {Milestone}.{Task}`

### Milestone 1: Allow deletion of inactive slideshow items

This is a bug fix, so per the feature guidelines it begins with regression tests that initially fail.

- **Task 1.1 — Regression tests (initially failing)**
  - Unit tests in `tests/unit/test_api.py`:
    - Deleting an inactive item returns 200 and the item row is permanently removed from the database.
    - Deleting an active item still soft-deletes (row remains, `is_active=False`) — guard against regression of existing behavior.
  - Integration test (Playwright) in `tests/integration/test_slideshow_items.py`: soft-delete an item via the UI, then delete it again from the inactive state; verify it disappears from the item list entirely and no error is shown.
  - Run the new tests and confirm they fail for the expected reason (404 from the API).
- **Task 1.2 — Backend fix**
  - In `delete_slideshow_item()` (`api/v1.py`): remove the `not item.is_active` 404 condition. If the item is active, soft-delete as today; if it is already inactive, hard-delete via `db.session.delete(item)`. Keep the SSE `broadcast_slideshow_update()` call and audit logging for both paths (hard delete of an inactive item does not affect what displays show, but the admin UI listens for updates).
  - Update the endpoint docstring to describe the two-stage behavior.
- **Task 1.3 — Frontend clarity**
  - In `SlideshowDetail.tsx`, make the delete confirmation message for inactive items say the deletion is permanent (e.g. "...permanently delete..."), so users understand the difference.
  - Update/extend `frontend/src/test/SlideshowDetail.test.tsx` accordingly.
- **Task 1.4 — Milestone wrap-up**
  - Update this document's Progress section; run all nox sessions (`format`, `lint`, `type_check`, `test-3.14`, `test-integration`) and frontend tests; commit; open the PR (draft of the overall feature branch).

### Milestone 2: Duplicate slideshow

- **Task 2.1 — Storage support for copying files**
  - Add a method to `storage.py` (e.g. `copy_file_to_slideshow(source_path, content_type, user_id, dest_slideshow_id) -> Optional[str]`) that copies an uploaded file on disk into the destination slideshow's upload directory (generating a secure filename via the existing helper) and returns the new web path. Missing source files are tolerated (log a warning, return `None` → the copied item keeps a `NULL` file path rather than failing the whole duplicate).
  - Unit tests for the new storage method (happy path, missing source).
- **Task 2.2 — Backend duplicate endpoint**
  - New endpoint: `POST /api/v1/slideshows/<int:slideshow_id>/duplicate` with JSON body `{"name": "..."}`.
    - 404 if the source slideshow doesn't exist or is inactive.
    - Validate `name` exactly like `create_slideshow()` (required, trimmed, no active slideshow with the same name; rely on the unique constraint + `IntegrityError` handling as backstop).
    - Create the new `Slideshow` (fields per Design Decisions), flush to obtain its id, then copy every item (including inactive), copying uploaded files via the new storage method and rewriting `content_file_path`.
    - Single transaction: any failure rolls back the whole duplicate (best-effort cleanup of any files already copied).
    - Return 201 with the new slideshow's `to_dict()`.
  - Unit tests in `tests/unit/test_api.py`: success (all fields and items copied, ordering preserved, inactive items remain inactive, `is_default` not copied, owner is current user); duplicate-name rejection; missing/blank name rejection; source-not-found 404; file-backed item gets a *new* file path and the file exists on disk; auth required.
- **Task 2.3 — Frontend**
  - `frontend/src/utils/apiClient.ts`: add `duplicateSlideshow(id, name)`.
  - `frontend/src/pages/Slideshows.tsx`: add a "Duplicate" action button (copy icon) to the per-row action group. On click, `window.prompt()` for the new name (pre-filled `"{name} (Copy)"`, matching the page's existing native-dialog pattern); on success refresh the list; on API error (e.g. duplicate name) show the existing error alert.
  - Frontend unit tests for the new button/flow in the Slideshows page test file.
- **Task 2.4 — Integration tests (Playwright)**
  - In `tests/integration/test_slideshow_management.py`: duplicate a slideshow with items via the UI; verify the new slideshow appears in the list with the entered name and correct item count, and that its detail page shows the copied items. Also test cancelling the prompt (no-op) and a duplicate-name error surfaced to the user.
- **Task 2.5 — Milestone wrap-up**
  - Update this document's Progress section; run all nox sessions and frontend tests; commit; push.

### Milestone 3: Acceptance Criteria

- **Task 3.1 — Documentation**: Update `README.md`, `docs/*.rst` (user/admin documentation covering slideshow management), and `CLAUDE.md` as needed for the two-stage item deletion and the duplicate feature, matching existing style and verbosity.
- **Task 3.2 — Test coverage review**: Confirm all code changes have appropriate unit test coverage; add any missing tests.
- **Task 3.3 — Full test pass**: All nox sessions passing (`format`, `lint`, `type_check`, `test-3.14`, `test-integration`) plus frontend `npm run test:run`, `type-check`, and `lint`.
- **Task 3.4 — Release & PR**: Minor version bump in `pyproject.toml`; move this file to `docs/features/completed/`; commit; push the branch; ensure the PR to `main` is open and wait for all GitHub Actions checks to pass.

## Progress

- [x] Planning complete; design decisions approved by human (2026-06-06)
- [x] Milestone 1: Allow deletion of inactive slideshow items (2026-06-06)
  - Task 1.1: Regression tests added (2 unit, 1 Playwright); confirmed initially failing with 404.
  - Task 1.2: `delete_slideshow_item()` now implements two-stage delete (active → soft delete, inactive → hard delete).
  - Task 1.3: Admin UI shows a "permanently delete ... cannot be undone" confirmation for inactive items; frontend unit test added.
  - Task 1.4: All tests passing — 671 unit, 173 integration, 133 frontend; `format`, `lint`, `type_check`, frontend `type-check`/`lint` clean.
  - Side quest (human-approved): black 26.5.x formats for Python 3.14 (PEP 758 except clauses, string hugging) which mypy rejected under `mypy.ini` `python_version = 3.13`. Resolved by embracing the new black style: `mypy.ini` now targets 3.14 and the stale `black!=26.1.0` exclusion was removed from `noxfile.py`.
- [ ] Milestone 2: Duplicate slideshow
- [ ] Milestone 3: Acceptance Criteria
