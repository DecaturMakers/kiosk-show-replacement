# Documentation Cleanup

You must read, understand, and follow all instructions in `./README.md` when planning and implementing this feature.

## Overview

The documentation for this project has grown organically over time and is now both duplicative and not well organized.

* We have Sphinx `.rst` docs in `docs/` and a `nox` session to build them, but we're not deploying them to GitHub Pages via github actions like we should.
* The README includes a mix of project structure, API endpoints, and installation docs.
* The `.rst` documents also have overlap.

We need to do the following:

1. Update the `Create Release` job of `.github/workflows/release.yml` so that it also builds the Sphinx documentation and deploys it to GitHub Pages.
2. Update the README.md so that is just contains a high-level description of the project and its features, contributing information, and license, and contains a prominent link near the top of the README to the github pages site for full documentation.
3. Ensure that `docs/api.rst` provides accurate and up-to-date API documentation, and that no API documentation appears in other documentation files; they should link to this file.
4. Remove the `docs/getting-started.rst` and `docs/installation.rst` pages in favor of `docs/deployment.rst`; any relevant information on the getting-started or installation pages that isn't already on the deployment page, should be added to it.
5. Update `docs/usage.rst` so that it just covers normal usage of the application via the frontend: adding/editing/managing slideshows, slides, and displays, and managing users (for admins). Keep the information on video formats and conversion, text slide formatting, and Skedda. Remove the information on API usage (this should go in `api.rst`), database management (this should be handled automatically by the Docker image), and the development server (this is for development only).

Finally, update `docs/index.rst` as needed for the above changes, and then ensure the `docs` nox environment runs successfully.

---

## Implementation Plan

### Current State Analysis

**README.md:**
- Contains detailed Quick Start installation instructions (duplicated in docs)
- Contains API Endpoints section (should only be in api.rst)
- Contains project structure section
- Contains Features, Contributing, License sections (appropriate to keep)

**docs/index.rst:**
- References getting-started, installation, deployment, usage, api, development, modules
- Has Quick Start section (duplicates README)
- Has Features section

**docs/getting-started.rst:**
- 216 lines covering prerequisites, setup, user management, troubleshooting
- Mostly duplicates content from README and deployment.rst
- Should be removed after migrating any unique content

**docs/installation.rst:**
- 89 lines, mostly duplicates deployment.rst
- Should be removed

**docs/deployment.rst:**
- Comprehensive production deployment documentation (485 lines)
- Well-organized: Docker deployment, environment variables, monitoring, troubleshooting
- Good as-is, may receive some content from removed files

**docs/usage.rst:**
- Contains good content about video formats, text formatting, Skedda calendars
- Contains REST API section (should be moved/referenced to api.rst)
- Contains CLI/Database management section (should be removed)
- Contains Development Server section (should be removed)

**docs/api.rst:**
- Very comprehensive API documentation (830 lines)
- Contains outdated "Permissive Authentication" note that needs updating
- Otherwise complete and well-structured

**release.yml:**
- Currently only builds Docker image and creates GitHub release
- Needs GitHub Pages deployment for Sphinx docs

---

### Milestone 1: GitHub Actions for Sphinx Docs Deployment

**Prefix:** `Docs Cleanup - 1`

**Task 1.1:** Update release.yml to build Sphinx documentation
- Add steps to install Python, Poetry, and Sphinx dependencies
- Run `sphinx-build` to generate HTML documentation

**Task 1.2:** Configure GitHub Pages deployment
- Add `pages: write` permission to the workflow
- Use `actions/upload-pages-artifact` to upload built docs
- Use `actions/deploy-pages` to deploy to GitHub Pages

**Task 1.3:** Test workflow by verifying docs build locally with `nox -s docs`

**Status:** Complete (0ae4a5c)

---

### Milestone 2: Simplify README.md

**Prefix:** `Docs Cleanup - 2`

**Task 2.1:** Restructure README to be a high-level overview
- Keep: Project description, Features list, Contributing, License, Acknowledgments
- Remove: Detailed Quick Start/Installation steps, API Endpoints section, Project Structure

**Task 2.2:** Add prominent documentation link
- Add a "Documentation" section near the top with link to GitHub Pages
- Format: `https://decaturmakers.github.io/kiosk-show-replacement/`

**Task 2.3:** Add brief Docker quick-start reference
- Just enough to point users to full docs (1-2 sentences)

**Status:** Complete (187945f)

---

### Milestone 3: Update api.rst

**Prefix:** `Docs Cleanup - 3`

**Task 3.1:** Update authentication documentation
- Remove outdated "Permissive Authentication" note
- Document actual session-based authentication with password hashing
- Note that users are created by admins (not auto-created)

**Task 3.2:** Review and ensure API documentation is comprehensive
- Verify all endpoints are documented
- Ensure consistency in documentation format

**Task 3.3:** Ensure no other docs contain API documentation
- Add reference links from usage.rst to api.rst where appropriate

**Status:** Complete (e54413b) - API section in usage.rst will be removed in Milestone 5

---

### Milestone 4: Remove getting-started.rst and installation.rst

**Prefix:** `Docs Cleanup - 4`

**Task 4.1:** Review getting-started.rst for unique content
- Check User Management section (may need to go to usage.rst or deployment.rst)
- Check Troubleshooting section (may have unique content for deployment.rst)

**Task 4.2:** Review installation.rst for unique content
- Check System Requirements section
- Check Verifying Installation section

**Task 4.3:** Migrate any unique content to appropriate locations
- User management info → usage.rst or deployment.rst
- System requirements → deployment.rst
- Verification steps → deployment.rst (if not already present)

**Task 4.4:** Delete getting-started.rst and installation.rst files

**Task 4.5:** Update index.rst to remove references to deleted files

**Status:** Complete (7f42b7b)

---

### Milestone 5: Update usage.rst

**Prefix:** `Docs Cleanup - 5`

**Task 5.1:** Keep and organize frontend usage content
- Admin Management Interface section
- Creating Slideshows section
- Managing Slides section
- Kiosk Display Mode section

**Task 5.2:** Keep media format documentation
- Video Format Requirements section
- Text Slide Formatting section
- Skedda Calendar Slides section

**Task 5.3:** Add user management section (if migrated from getting-started.rst)
- User Management Features for admins
- Profile Settings for all users

**Task 5.4:** Remove inappropriate sections
- Remove REST API section (reference api.rst instead)
- Remove Command Line Interface section (development only)
- Remove Database Management section (handled by Docker)
- Remove Development Server section (development only)

**Task 5.5:** Add cross-reference to api.rst for programmatic access

**Status:** Complete (29f0ef7)

---

### Milestone 6: Acceptance Criteria

**Prefix:** `Docs Cleanup - 6`

**Task 6.1:** Update index.rst
- Remove references to deleted files (getting-started, installation)
- Simplify Quick Start section to reference deployment.rst
- Verify all remaining pages are properly linked

**Task 6.2:** Verify Sphinx documentation builds
- Run `nox -s docs` and verify no errors/warnings
- Review generated HTML for proper rendering

**Task 6.3:** Verify all nox sessions pass
- Run full test suite to ensure no regressions
- Verify lint, format, type_check sessions pass

**Task 6.4:** Final review
- Read through all updated documentation for consistency
- Verify cross-references work correctly
- Ensure no duplicate content remains

**Task 6.5:** Move feature file to completed/
- Move `docs/features/docs-cleanup.md` to `docs/features/completed/`

**Status:** Complete

---

## Progress Log

- **Milestone 1 Complete** (0ae4a5c): Added GitHub Pages deployment workflow to release.yml
- **Milestone 2 Complete** (187945f): Simplified README.md with prominent documentation link
- **Milestone 3 Complete** (e54413b): Updated api.rst authentication documentation
- **Milestone 4 Complete** (7f42b7b): Removed getting-started.rst and installation.rst, migrated content
- **Milestone 5 Complete** (29f0ef7): Updated usage.rst to focus on frontend usage only
- **Milestone 6 Complete**: All nox sessions pass (format, lint, type_check, test-3.14, docs)
