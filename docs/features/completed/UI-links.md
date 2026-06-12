# UI Links

You must read, understand, and follow all instructions in `./README.md` when planning and implementing this feature.

## Overview

We need to add a footer to all UI pages (everything except the actual kiosk slideshow display view) bearing the text "kiosk-show-replacement v{x.y.z} is Free and Open Source Software, Copyright 2026 Jason Antman." where `v{x.y.z}` is the current version number, `kiosk-show-replacement v{x.y.z}` is a link to https://github.com/Decaturmakers/kiosk-show-replacement and `Free and Open Source Software` is a link to https://opensource.org/license/mit.

Additionally, in the admin UI, we need to add a prominent "Help" link (in the top nav bar, perhaps?) that links to https://decaturmakers.github.io/kiosk-show-replacement/usage.html

When this is complete we must use `poetry` to bump the patch version.

## Implementation Plan

### Current State

- **React admin UI**: No footer exists. Navigation component (`frontend/src/components/Navigation.tsx`) has no Help link.
- **Flask templates**: `base.html` has a footer with hardcoded `v0.1.0` and minimal GitHub link. Display templates `index.html`, `configure.html`, `no_content.html` extend `base.html` (get footer). `slideshow.html` does NOT extend `base.html` (no footer - correct).
- **Login page** (`frontend/src/pages/Login.tsx`): No footer, rendered outside AdminLayout.
- **Version**: `0.3.0` in `kiosk_show_replacement/__init__.py` and `pyproject.toml`. Already exposed via `/health/ready` endpoint but requires DB to be healthy.

### Milestone 1: Implementation (prefix: `UI Links - 1`) - COMPLETE

#### Task 1.1: Add version API endpoint
- **File**: `kiosk_show_replacement/api/v1.py`
- Add `GET /api/v1/version` endpoint (unauthenticated) returning `{"version": "x.y.z"}`
- Import `__version__` from `kiosk_show_replacement`

#### Task 1.2: Update Flask template footer
- **File**: `kiosk_show_replacement/templates/base.html`
- Update footer text to: `kiosk-show-replacement v{version}` (link to GitHub) + `is Free and Open Source Software` (link to MIT license) + `, Copyright 2026 Jason Antman.`
- Add `__version__` to template context via a context processor in `app.py`
- **File**: `kiosk_show_replacement/app.py` - add context processor injecting `app_version`

#### Task 1.3: Create React Footer component
- **File**: `frontend/src/components/Footer.tsx` (new)
- Fetches version from `/api/v1/version` on mount (cached, one call)
- Renders footer matching the spec text with correct links
- Styled consistently with the Flask template footer (Bootstrap `bg-light`, `text-muted`)

#### Task 1.4: Add Footer to React layouts
- **File**: `frontend/src/components/AdminLayout.tsx` - add `<Footer />` inside the layout wrapper
- **File**: `frontend/src/pages/Login.tsx` - add `<Footer />` below the login card

#### Task 1.5: Add Help link to React navbar
- **File**: `frontend/src/components/Navigation.tsx`
- Add a "Help" `Nav.Link` to the right side of the navbar (before user dropdown), linking to `https://decaturmakers.github.io/kiosk-show-replacement/usage.html` with `target="_blank"` and `rel="noopener noreferrer"`

#### Task 1.6: Add tests
- **Unit test** for version API endpoint in `tests/unit/` (verify it returns correct version, no auth required)
- **Integration tests** in `tests/integration/`:
  - Footer visible on admin dashboard (with correct text and links)
  - Footer visible on login page
  - Help link visible in navbar
  - Footer NOT visible on display slideshow view

#### Task 1.7: Run all tests, commit

### Milestone 2: Acceptance Criteria (prefix: `UI Links - 2`) - COMPLETE

#### Task 2.1: Bump patch version
- Run `poetry version patch` to bump to `0.3.1`
- Update `kiosk_show_replacement/__init__.py` to match

#### Task 2.2: Update documentation
- Update `CLAUDE.md` if needed
- Update any relevant docs

#### Task 2.3: Final test run
- Run all nox sessions, ensure passing

#### Task 2.4: Move feature doc
- Move `docs/features/UI-links.md` to `docs/features/completed/`

#### Task 2.5: Open PR

### Key Files

| File | Action |
|------|--------|
| `kiosk_show_replacement/api/v1.py` | Add version endpoint |
| `kiosk_show_replacement/app.py` | Add context processor for version |
| `kiosk_show_replacement/templates/base.html` | Update footer |
| `frontend/src/components/Footer.tsx` | Create new |
| `frontend/src/components/AdminLayout.tsx` | Add Footer |
| `frontend/src/components/Navigation.tsx` | Add Help link |
| `frontend/src/pages/Login.tsx` | Add Footer |
| `tests/unit/test_api_version.py` | New unit test |
| `tests/integration/test_ui_links.py` | New integration test |

### Verification

1. Run `poetry run -- nox -s test-3.14` for backend unit tests
2. Build frontend: `cd frontend && npm run build`
3. Run `poetry run -- nox -s test-integration` for integration tests
4. Manual verification: start Flask + Vite, check footer on login page, admin pages, and absence on slideshow display
