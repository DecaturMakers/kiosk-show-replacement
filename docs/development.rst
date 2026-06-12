Development
===========

.. note::

   **This guide is for local development only.**

   Local Python/Poetry installation is only supported for development purposes.
   For production deployments, Docker is the only supported method.
   See :doc:`deployment` for production setup instructions.

System Requirements
-------------------

Before setting up the development environment, ensure you have the following
system dependencies installed:

* **Python 3.13+**: Required for the Flask backend
* **Node.js 18+ and npm**: Required for frontend development
* **ffmpeg/ffprobe**: Required for automatic video duration detection

**Installing ffmpeg:**

.. code-block:: bash

   # ArchLinux
   sudo pacman -S ffmpeg

   # Ubuntu/Debian
   sudo apt install ffmpeg

   # Fedora
   sudo dnf install ffmpeg

   # macOS (with Homebrew)
   brew install ffmpeg

**Verifying ffprobe installation:**

.. code-block:: bash

   ffprobe -version
   # Should output version information

Setting up Development Environment
----------------------------------

1. Clone the repository:

   .. code-block:: bash

      git clone https://github.com/Decaturmakers/kiosk-show-replacement.git
      cd kiosk-show-replacement

2. Install Poetry (if not already installed):

   .. code-block:: bash

      curl -sSL https://install.python-poetry.org | python3 -

3. Install dependencies and activate environment:

   .. code-block:: bash

      poetry install
      eval $(poetry env activate)

4. Set up the development environment:

   .. code-block:: bash

      nox -s dev-setup

Development Workflow
--------------------

This project uses `nox <https://nox.thea.codes/>`_ for development automation.

Available Commands
~~~~~~~~~~~~~~~~~~

**Important**: First activate your Poetry environment in any new terminal session:

.. code-block:: bash

   eval $(poetry env activate)

Then run the development commands:

.. code-block:: bash

   # Format code with black and isort
   nox -s format

   # Run linting (flake8, pycodestyle)
   nox -s lint

   # Run type checking with mypy
   nox -s type_check

   # Run unit tests
   nox -s test

   # Run integration tests
   nox -s test-integration

   # Run all tests
   nox -s test-comprehensive

   # Build documentation
   nox -s docs

   # Serve documentation locally
   nox -s docs-serve

   # Clean build artifacts
   nox -s clean

   # Check for security vulnerabilities
   nox -s safety

Default Development Session
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Running ``nox`` without arguments will run the default development session (format, lint, test):

.. code-block:: bash

   # After activating environment
   nox

Code Style
----------

This project uses several tools to maintain code quality:

* **Black**: Code formatting
* **isort**: Import sorting
* **flake8**: Linting and style checking
* **mypy**: Type checking

Configuration files:

* ``.flake8``: flake8 configuration
* ``pyproject.toml``: Black, isort, and mypy configuration

Testing
-------

The project uses pytest for testing with two types of tests:

1. **Unit Tests** (``tests/unit/``): Test individual functions and classes in isolation
2. **Integration Tests** (``tests/integration/``): Full-stack browser tests of React frontend + Flask backend

**Important**: First activate your Poetry environment in any new terminal session:

.. code-block:: bash

   eval $(poetry env activate)

Unit Tests
~~~~~~~~~~

Located in ``tests/unit/``, these test individual functions and classes in isolation.

.. code-block:: bash

   nox -s test

Integration Tests
~~~~~~~~~~~~~~~~~

Located in ``tests/integration/``, these test the complete React frontend + Flask backend integration through a real browser using Playwright.

**What Integration Tests Cover:**

* **Full-Stack Integration**: React frontend communicating with Flask backend through real HTTP requests
* **Real Browser Testing**: Uses Playwright to control system Chrome/Chromium browser
* **Complete User Workflows**: Full user journeys from login to dashboard interaction
* **Authentication Integration**: Tests session-based authentication across frontend and backend
* **API Communication**: Validates REST API endpoints work correctly with React frontend
* **Database Integration**: Tests data persistence across the full application stack

**Key Characteristics:**

* Use Playwright to automate a real Chrome/Chromium browser
* Start both Flask backend (port 5000) and Vite frontend (port 3001) servers
* Test actual user interactions (clicking, typing, form submission)
* Verify complete authentication workflows and dashboard functionality
* Include multi-step user journeys that span multiple application components
* Test real-world scenarios that users actually experience

**Examples:**

* Complete login workflow (visit frontend → authenticate → access dashboard → see content)
* Frontend-backend authentication integration (session cookies, API calls)
* Dashboard data loading from Flask backend APIs
* User interface responsiveness and error handling

.. code-block:: bash

   nox -s test-integration

**Integration Test Server Logs:**

Integration tests automatically capture comprehensive logs from both Flask and Vite servers during test execution. These logs are saved for debugging purposes and can be found in:

* **Log File Location**: ``test-results/integration-server-logs.txt`` (created in project root)
* **Log Contents**: 
  
  - Flask server startup, requests, and error messages
  - Vite development server output and build information
  - Timestamped entries for easy debugging
  - Complete server lifecycle from startup to shutdown

* **Automatic Capture**: Logs are automatically saved after each integration test session
* **Debug Access**: Server logs are also dumped to console when tests fail for immediate debugging

**Example log file structure:**

.. code-block:: text

   === INTEGRATION TEST SERVER LOGS ===

   === FLASK SERVER LOGS ===
   [14:32:15.123] Flask: Starting development server...
   [14:32:15.456] Flask: * Running on http://localhost:5000
   [14:32:16.789] Flask: GET /api/v1/auth/login - 200

   === VITE SERVER LOGS ===
   [14:32:20.123] Vite: Local:   http://localhost:3001/
   [14:32:20.456] Vite: ready in 1.2s

   === END OF LOGS ===

**System Requirements for Integration Tests:**

Integration tests require a system-installed Chrome or Chromium browser and Node.js for the frontend development server. The test framework automatically detects and uses the first available browser from these common locations:

* ``/usr/bin/google-chrome-stable`` (Google Chrome on most Linux distributions)
* ``/usr/bin/chromium-browser`` (Chromium on Ubuntu/Debian)
* ``/usr/bin/google-chrome`` (Alternative Chrome location)
* ``/usr/bin/chromium`` (Chromium on Arch/Fedora)

**Debugging Integration Test Failures:**

When integration tests fail, several debugging resources are automatically generated:

1. **Server Logs**: Check ``test-results/integration-server-logs.txt`` for detailed Flask and Vite server output
2. **Screenshots**: Failed tests capture screenshots in ``test-results/`` directory
3. **Console Output**: Server logs are also dumped to the terminal on test failures
4. **Real-time Debugging**: Run tests with ``-s`` flag to see live server output

**Common Integration Test Issues:**

* **Server Startup Failures**: Check server logs for port conflicts or missing dependencies
* **Authentication Issues**: Look for API authentication errors in Flask logs
* **Frontend Build Issues**: Check Vite logs for compilation errors or missing assets
* **Network Timeouts**: Increase timeouts or check server health in logs

**Example debugging workflow:**

.. code-block:: bash

   # Run integration tests with verbose output
   nox -s test-integration -- -s -v
   
   # If tests fail, check the server logs
   cat test-results/integration-server-logs.txt
   
   # Run specific test for focused debugging
   nox -s test-integration -- -k "test_user_login" -s

Test Configuration
~~~~~~~~~~~~~~~~~~

* ``pytest.ini``: Pytest configuration
* ``tests/conftest.py``: Shared test fixtures

Coverage
~~~~~~~~

Code coverage is measured using pytest-cov. Coverage reports are generated in:

* Terminal output (with ``--cov-report=term-missing``)
* HTML report in ``htmlcov/`` directory
* XML report as ``coverage.xml``

Database Testing
~~~~~~~~~~~~~~~~

**Test Database Isolation:**

Tests use completely isolated databases that are separate from your development database:

* **Unit tests**: Use a temporary SQLite database in a pytest temp directory
* **Integration tests**: Use a fresh SQLite database per test session
* **Your development database**: Located at ``kiosk_show.db`` (default) is never touched by tests

This means running tests will **never** affect your development database or its data.

**How it works:**

The test fixtures in ``tests/conftest.py`` override ``SQLALCHEMY_DATABASE_URI`` to point
to a temporary file, ensuring complete isolation from your development environment.

Test Type Summary
~~~~~~~~~~~~~~~~~

**When to use each test type:**

* **Unit Tests** (``nox -s test``): Testing individual functions, classes, or small components in isolation. Fast and focused.
* **Integration Tests** (``nox -s test-integration``): Testing the complete React + Flask application stack through a real browser. Use for validating user experiences and frontend-backend integration.

**Test execution speed:** Unit < Integration (Integration tests are slowest due to starting both servers)

Troubleshooting Browser Tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Playwright Browser Dependencies on Arch Linux**

Playwright browser tests (integration tests) may encounter issues on Arch Linux due to browser dependency conflicts. This section documents the successful solution.

**Problem:** Playwright fails with browser executable errors:

.. code-block:: text

   playwright._impl._errors.Error: Executable doesn't exist at 
   /home/user/.cache/ms-playwright/chromium_headless_shell-1179/chrome-linux/headless_shell

**Root Cause:** Playwright's bundled browsers don't work properly on Arch Linux due to:

* Missing system library versions (libicudata.so.66, libicui18n.so.66, etc.)
* Arch Linux has newer library versions than Playwright expects
* Playwright doesn't officially support Arch Linux

**Failed Solutions to Avoid:**

* **Playwright Version Downgrade**: Attempting to downgrade Playwright to 1.30.0 fails due to Python 3.13 incompatibility with older dependency versions (greenlet, etc.)
* **System Library Symlinks**: Creating global symlinks pollutes the system and is not recommended
* **Playwright Install Commands**: ``playwright install`` fails due to missing library versions

**✅ Working Solution: System Chrome Integration**

Configure Playwright to use the system-installed Google Chrome instead of bundled browsers:

1. **Install Google Chrome:**

   .. code-block:: bash

      # Install Google Chrome on Arch Linux
      yay -S google-chrome
      # or using AUR helper of choice

2. **Configure Playwright:** Update ``playwright.config.js`` to use system Chrome:

   .. code-block:: javascript

      projects: [
        {
          name: 'chromium',
          use: { 
            ...require('@playwright/test').devices['Desktop Chrome'],
            channel: 'chrome',  // Use system Chrome
            executablePath: '/usr/bin/google-chrome-stable'  // Explicit path
          },
        },
      ],

3. **Verify Installation:**

   .. code-block:: bash

      # Confirm Chrome is installed
      which google-chrome-stable
      # Should output: /usr/bin/google-chrome-stable

4. **Run Tests:**

   .. code-block:: bash

      eval $(poetry env activate)
      nox -s test-integration
      nox -s test-e2e

**Alternative Browser Paths:**

If ``google-chrome-stable`` is not available, try these alternatives:

.. code-block:: bash

   # Check available browsers
   which chromium
   which google-chrome
   which chromium-browser

Update ``executablePath`` in ``playwright.config.js`` accordingly:

.. code-block:: javascript

   executablePath: '/usr/bin/chromium'           // For Chromium
   executablePath: '/usr/bin/google-chrome'     // Alternative Chrome path

**Testing the Fix:**

After configuration, verify browser tests work:

.. code-block:: bash

   # Test with verbose output
   eval $(poetry env activate)
   nox -s test-integration -- -v

   # Should see browser startup without executable errors
   # Look for: "Browser launched successfully" in logs

**Success Indicators:**

* No more "Executable doesn't exist" errors
* Browser tests launch Chrome successfully
* Tests can navigate to React frontend and Flask backend
* Screenshots and videos are captured properly on test failures

**What This Solution Provides:**

* ✅ **Browser tests work on Arch Linux**
* ✅ **Uses stable, system-managed Chrome**
* ✅ **No global system modifications required**
* ✅ **Easy to maintain and update**
* ✅ **Works with automatic browser updates**

Project Structure
-----------------

.. code-block:: text

   kiosk-show-replacement/
   ├── kiosk_show_replacement/       # Main package
   │   ├── __init__.py
   │   ├── app.py                    # Flask application factory
   │   ├── api/                      # REST API blueprints
   │   ├── auth/                     # Authentication (future)
   │   ├── cli/                      # Command-line interface
   │   ├── config/                   # Configuration management
   │   ├── display/                  # Display/kiosk blueprints
   │   ├── models/                   # Database models
   │   ├── slideshow/                # Slideshow management
   │   ├── static/                   # Static files
   │   ├── templates/                # Jinja2 templates
   │   └── utils/                    # Utility functions
   ├── tests/                        # Test suite
   │   ├── unit/                     # Unit tests
   │   └── integration/              # Integration tests
   ├── docs/                         # Documentation
   ├── scripts/                      # Utility scripts
   ├── noxfile.py                    # Development automation
   ├── pyproject.toml               # Poetry configuration
   └── README.md

Adding New Features
-------------------

1. Create a new branch for your feature
2. Write tests first (TDD approach)
3. Implement the feature
4. Run the full test suite
5. Update documentation
6. Submit a pull request

Database Migrations
-------------------

This project uses Flask-Migrate for database migrations.

**Important**: First activate your Poetry environment in any new terminal session:

.. code-block:: bash

   eval $(poetry env activate)

Then run migration commands:

.. code-block:: bash

   # Create a new migration
   flask db migrate -m "Description of changes"

   # Apply migrations
   flask db upgrade

   # Rollback migrations
   flask db downgrade

Frontend Development
--------------------

The kiosk-show-replacement project includes a modern React-based admin interface alongside the Flask backend. This section covers everything you need to know about developing and maintaining the frontend.

Frontend Technology Stack
~~~~~~~~~~~~~~~~~~~~~~~~~~

The frontend uses modern web technologies:

**Core Technologies:**

* **React 18**: Modern React with hooks and functional components
* **TypeScript**: Type-safe JavaScript for better development experience
* **Vite**: Fast build tool and development server
* **React Router**: Client-side routing for single-page application

**UI Framework:**

* **React Bootstrap**: Bootstrap 5 components for React
* **Bootstrap 5**: CSS framework for responsive design
* **React Router Bootstrap**: Integration between React Router and Bootstrap

**Development Tools:**

* **npm**: Package manager for JavaScript dependencies
* **ESLint**: JavaScript/TypeScript linting (future enhancement)
* **Prettier**: Code formatting (future enhancement)

Frontend Project Structure
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   frontend/                         # Frontend application root
   ├── package.json                  # npm dependencies and scripts
   ├── tsconfig.json                 # TypeScript configuration
   ├── vite.config.ts               # Vite build configuration
   ├── index.html                   # HTML entry point
   └── src/                         # Source code
       ├── main.tsx                 # Application entry point
       ├── App.tsx                  # Main app component
       ├── components/              # Reusable UI components
       │   ├── common/              # Common components (buttons, forms)
       │   ├── layout/              # Layout components (header, sidebar)
       │   └── ui/                  # Basic UI elements
       ├── pages/                   # Page components
       │   ├── Dashboard.tsx        # Admin dashboard
       │   ├── Login.tsx           # Login page
       │   ├── Slideshows.tsx      # Slideshow management
       │   └── Displays.tsx        # Display management
       ├── contexts/                # React contexts
       │   └── AuthContext.tsx     # Authentication state
       ├── hooks/                   # Custom React hooks
       │   ├── useAuth.ts          # Authentication hook
       │   ├── useApi.ts           # API client hook
       │   └── useLocalStorage.ts  # Local storage hook
       └── types/                   # TypeScript type definitions
           ├── api.ts              # API response types
           ├── auth.ts             # Authentication types
           └── slideshow.ts        # Slideshow data types

Running the Application Locally
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. important::

   **In development mode, you MUST run BOTH Flask and Vite servers.**

   Flask redirects ``/admin/`` requests to the Vite dev server on port 3000.
   If Vite is not running, the admin interface will not load.

**Port Summary:**

+------+---------+------------------------------------------------+
| Port | Service | Purpose                                        |
+======+=========+================================================+
| 5000 | Flask   | Backend API, redirects /admin/ to Vite in dev  |
+------+---------+------------------------------------------------+
| 3000 | Vite    | React frontend with hot reload (dev only)      |
+------+---------+------------------------------------------------+

**First-time Setup:**

1. Initialize the database:

   .. code-block:: bash

      FLASK_APP=kiosk_show_replacement.app poetry run flask cli init-db
      # Default credentials: admin / admin

**Starting for Development:**

1. Start Flask backend (Terminal 1):

   .. code-block:: bash

      # From project root
      poetry run python run.py
      # API available at http://localhost:5000/api/

2. Start Vite frontend (Terminal 2):

   .. code-block:: bash

      cd frontend
      npm run dev
      # Admin interface at http://localhost:3000/admin/

3. Access the admin interface at http://localhost:3000/admin/ (or http://localhost:5000/admin/ which redirects to port 3000)

Setting Up Frontend Development
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Prerequisites:**

* Node.js 18+ and npm (for frontend development)
* Python 3.13+ and Poetry (for backend integration)

**Initial Setup:**

1. Navigate to the frontend directory:

   .. code-block:: bash

      cd frontend

2. Install frontend dependencies:

   .. code-block:: bash

      npm install

The frontend development server runs on http://localhost:3000 and proxies API requests to the Flask backend on http://localhost:5000.

Frontend Development Commands
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Development Server:**

.. code-block:: bash

   cd frontend
   npm run dev          # Start development server with hot reload

**Building for Production:**

.. code-block:: bash

   cd frontend
   npm run build        # Build optimized production assets
   npm run preview      # Preview production build locally

**Package Management:**

.. code-block:: bash

   cd frontend
   npm install          # Install dependencies
   npm install <package>    # Add new dependency
   npm install --save-dev <package>  # Add development dependency
   npm update           # Update dependencies
   npm audit            # Check for security vulnerabilities

**TypeScript:**

.. code-block:: bash

   cd frontend
   npx tsc --noEmit     # Type check without building
   npx tsc --watch      # Watch mode type checking

Frontend-Backend Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The frontend integrates with the Flask backend through several mechanisms:

**Development Mode:**
* Vite dev server runs on port 3000
* API requests are proxied to Flask backend on port 5000
* Hot reload for immediate feedback during development

**Production Mode:**
* Frontend builds to ``kiosk_show_replacement/static/dist/``
* Flask serves the built React app at ``/admin`` routes
* All assets served through Flask for single-server deployment

**API Communication:**
* REST API endpoints at ``/api/v1/*``
* Session-based authentication shared between frontend and backend
* Axios client with automatic authentication handling

**Configuration in vite.config.ts:**

.. code-block:: typescript

   export default defineConfig({
     plugins: [react()],
     server: {
       port: 3000,
       proxy: {
         '/api': 'http://localhost:5000',
         '/auth': 'http://localhost:5000',
         '/uploads': 'http://localhost:5000'
       }
     },
     build: {
       outDir: '../kiosk_show_replacement/static/dist'
     }
   })

Authentication Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~

The frontend uses the same session-based authentication as the Flask backend:

**Login Flow:**
1. User submits credentials to ``/api/v1/auth/login``
2. Flask creates session and returns user data
3. Frontend stores authentication state in React context
4. Subsequent API requests include session cookies automatically

**Protected Routes:**
* React Router guards routes requiring authentication
* Redirects to login page if not authenticated
* Preserves intended destination for post-login redirect

**API Client (useApi hook):**

.. code-block:: typescript

   const api = useApi();
   
   // Authenticated requests automatically include session
   const slideshows = await api.get('/api/v1/slideshows');
   const newSlideshow = await api.post('/api/v1/slideshows', data);

Adding New Frontend Features
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**1. Adding a New Page:**

.. code-block:: typescript

   // src/pages/NewPage.tsx
   import React from 'react';
   import { Container } from 'react-bootstrap';
   
   const NewPage: React.FC = () => {
     return (
       <Container>
         <h1>New Page</h1>
         {/* Page content */}
       </Container>
     );
   };
   
   export default NewPage;

**2. Adding to Navigation:**

.. code-block:: typescript

   // src/components/layout/Sidebar.tsx
   import { LinkContainer } from 'react-router-bootstrap';
   import { Nav } from 'react-bootstrap';
   
   <LinkContainer to="/new-page">
     <Nav.Link>New Page</Nav.Link>
   </LinkContainer>

**3. Adding Route:**

.. code-block:: typescript

   // src/App.tsx
   import { Routes, Route } from 'react-router-dom';
   import NewPage from './pages/NewPage';
   
   <Routes>
     <Route path="/new-page" element={<NewPage />} />
   </Routes>

**4. Adding API Integration:**

.. code-block:: typescript

   // Custom hook for API operations
   const useNewFeature = () => {
     const api = useApi();
     
     const fetchData = async () => {
       return await api.get('/api/v1/new-endpoint');
     };
     
     const createItem = async (data: NewItemType) => {
       return await api.post('/api/v1/new-endpoint', data);
     };
     
     return { fetchData, createItem };
   };

Common Frontend Development Tasks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Managing State:**

* Use React Context for global state (authentication, settings)
* Use useState for local component state
* Use useEffect for side effects and API calls

**Handling Forms:**

.. code-block:: typescript

   const [formData, setFormData] = useState({ name: '', description: '' });
   
   const handleSubmit = async (e: React.FormEvent) => {
     e.preventDefault();
     try {
       await api.post('/api/v1/endpoint', formData);
       // Handle success
     } catch (error) {
       // Handle error
     }
   };

**Error Handling:**

.. code-block:: typescript

   const [error, setError] = useState<string | null>(null);
   const [loading, setLoading] = useState(false);
   
   const handleApiCall = async () => {
     setLoading(true);
     setError(null);
     try {
       const result = await api.get('/api/v1/data');
       // Handle success
     } catch (err) {
       setError(err instanceof Error ? err.message : 'An error occurred');
     } finally {
       setLoading(false);
     }
   };

**Responsive Design:**

Use Bootstrap classes and React Bootstrap components for responsive layouts:

.. code-block:: typescript

   <Container>
     <Row>
       <Col xs={12} md={6} lg={4}>
         <Card>
           <Card.Body>Content</Card.Body>
         </Card>
       </Col>
     </Row>
   </Container>

TypeScript Best Practices
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Define Types for API Responses:**

.. code-block:: typescript

   // src/types/api.ts
   export interface ApiResponse<T> {
     success: boolean;
     data: T;
     message?: string;
   }
   
   export interface Slideshow {
     id: number;
     name: string;
     description: string;
     active: boolean;
     items: SlideshowItem[];
   }

**Use Proper Component Props Types:**

.. code-block:: typescript

   interface SlideshowCardProps {
     slideshow: Slideshow;
     onEdit: (slideshow: Slideshow) => void;
     onDelete: (id: number) => void;
   }
   
   const SlideshowCard: React.FC<SlideshowCardProps> = ({
     slideshow,
     onEdit,
     onDelete
   }) => {
     // Component implementation
   };

**Custom Hook Type Safety:**

.. code-block:: typescript

   interface UseApiResult {
     get: <T>(url: string) => Promise<T>;
     post: <T>(url: string, data: any) => Promise<T>;
     put: <T>(url: string, data: any) => Promise<T>;
     delete: (url: string) => Promise<void>;
   }
   
   const useApi = (): UseApiResult => {
     // Hook implementation
   };

Troubleshooting Frontend Issues
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Common Issues:**

1. **Build Errors:**
   - Check TypeScript errors: ``npx tsc --noEmit``
   - Verify all dependencies are installed: ``npm install``
   - Clear node_modules and reinstall: ``rm -rf node_modules package-lock.json && npm install``

2. **API Connection Issues:**
   - Ensure Flask backend is running on port 5000
   - Check Vite proxy configuration in ``vite.config.ts``
   - Verify CORS is enabled in Flask app

3. **Authentication Problems:**
   - Check browser cookies and session storage
   - Verify API endpoints return proper status codes
   - Test authentication flow in browser dev tools

4. **Hot Reload Not Working:**
   - Restart Vite dev server: ``npm run dev``
   - Check file permissions and paths
   - Clear browser cache

5. **Database Not Initialized:**
   - The login page will show a clear error if the database is not initialized
   - Run: ``FLASK_APP=kiosk_show_replacement.app poetry run flask cli init-db``
   - Check the health endpoint: ``curl http://localhost:5000/health/ready``
   - The ``/health/ready`` endpoint returns ``"reason": "database_not_initialized"`` if setup is needed

**Debugging Tools:**

* Browser DevTools for inspecting network requests and React components
* React Developer Tools browser extension
* TypeScript compiler for type checking
* Flask debug toolbar for backend API issues

Frontend Testing (Future Enhancement)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When adding frontend tests, consider:

* **Unit Tests**: Jest and React Testing Library for component testing
* **Integration Tests**: Testing API integration and user workflows
* **E2E Tests**: Playwright or Cypress for full application testing

**Example test structure:**

.. code-block:: typescript

   // src/components/__tests__/SlideshowCard.test.tsx
   import { render, screen, fireEvent } from '@testing-library/react';
   import SlideshowCard from '../SlideshowCard';
   
   test('renders slideshow name', () => {
     const slideshow = { id: 1, name: 'Test Slideshow' };
     render(<SlideshowCard slideshow={slideshow} />);
     expect(screen.getByText('Test Slideshow')).toBeInTheDocument();
   });

Deployment Considerations
~~~~~~~~~~~~~~~~~~~~~~~~~

**Production Build:**

.. code-block:: bash

   cd frontend
   npm run build

This creates optimized assets in ``kiosk_show_replacement/static/dist/`` that Flask serves in production.

**Environment Variables:**

Create ``.env`` files for different environments:

.. code-block:: bash

   # frontend/.env.development
   VITE_API_BASE_URL=http://localhost:5000
   
   # frontend/.env.production
   VITE_API_BASE_URL=

**Build Optimization:**

* Vite automatically optimizes bundle size
* Tree shaking removes unused code
* Assets are fingerprinted for caching
* Source maps available for debugging

Contributing
------------

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Update documentation
7. Submit a pull request

Code Review Process
~~~~~~~~~~~~~~~~~~~

All contributions go through code review:

1. Automated checks (linting, testing, type checking)
2. Manual review by maintainers
3. Discussion and iteration
4. Approval and merge

Release Process
---------------

1. Update version in ``pyproject.toml``
2. Update ``CHANGELOG.md``
3. Create a Git tag
4. Build and publish to PyPI
5. Create GitHub release
