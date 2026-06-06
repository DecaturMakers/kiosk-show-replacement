"""
Nox configuration for kiosk-show-replacement.

This file defines automated tasks for testing, linting, formatting,
and other development activities using nox.
"""

import os

import nox

# Python versions to test against
PYTHON_VERSIONS = ["3.14"]
# Default Python version for development tasks
DEFAULT_PYTHON = "3.14"

# Locations of source code
PACKAGE_DIR = "kiosk_show_replacement"
TEST_DIR = "tests"
DOCS_DIR = "docs"


@nox.session(python=DEFAULT_PYTHON)
def format(session):
    """Format code with black and isort."""
    session.install("black", "isort")
    session.run("black", PACKAGE_DIR, TEST_DIR, "noxfile.py")
    session.run("isort", PACKAGE_DIR, TEST_DIR, "noxfile.py")


@nox.session(python=DEFAULT_PYTHON)
def lint(session):
    """Lint code with flake8 and pycodestyle."""
    session.install("flake8", "pycodestyle")
    session.run("flake8", PACKAGE_DIR, TEST_DIR)
    session.run(
        "pycodestyle",
        "--max-line-length=88",
        "--ignore=E501,W503,E226",
        PACKAGE_DIR,
        TEST_DIR,
    )


@nox.session(python=DEFAULT_PYTHON, name="lint-frontend")
def lint_frontend(session):
    """Lint frontend code with ESLint and TypeScript."""
    frontend_dir = "frontend"

    # Check if frontend directory exists
    if not os.path.exists(frontend_dir):
        session.log("Frontend directory not found, skipping frontend linting")
        return

    # Check if Node.js and npm are available
    try:
        session.run("node", "--version", external=True)
        session.run("npm", "--version", external=True)
    except Exception as e:
        session.error(f"Node.js/npm not available: {e}")

    # Change to frontend directory
    session.chdir(frontend_dir)

    # Install dependencies if node_modules doesn't exist
    if not os.path.exists("node_modules"):
        session.log("Installing frontend dependencies...")
        session.run("npm", "install", external=True)

    # Run TypeScript type checking
    session.log("Running TypeScript type checking...")
    session.run("npm", "run", "type-check", external=True)

    # Run ESLint
    session.log("Running ESLint...")
    session.run("npm", "run", "lint", external=True)


@nox.session(python=DEFAULT_PYTHON, name="lint-all")
def lint_all(session):
    """Lint all code: backend (Python) and frontend (TypeScript/JavaScript)."""
    session.log("=== Running Comprehensive Linting ===")

    # 1. Lint backend code
    session.log("1. Linting backend code...")
    session.notify("lint")

    # 2. Lint frontend code if available
    if os.path.exists("frontend"):
        session.log("2. Linting frontend code...")
        session.notify("lint-frontend")
    else:
        session.log("2. Skipping frontend linting (frontend directory not found)")

    session.log("=== Comprehensive Linting Complete ===")


@nox.session(python=DEFAULT_PYTHON)
def type_check(session):
    """Type check with mypy."""
    session.install("mypy")
    # Install type stubs
    session.install("types-requests", "types-Flask-Cors", "types-Flask-Migrate")
    # Install package dependencies for type checking
    session.install("-e", ".")
    session.run("mypy", PACKAGE_DIR)


@nox.session(python=PYTHON_VERSIONS, name="test")
def test(session):
    """Run unit tests with pytest."""
    session.install("-e", ".")
    session.install(
        "pytest",
        "pytest-blockage",
        "pytest-cov",
        "pytest-flask",
        "pytest-html",
        "pytest-mock",
    )

    # Run tests with coverage
    session.run(
        "pytest",
        TEST_DIR + "/unit",
        "--cov=" + PACKAGE_DIR,
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        "--cov-report=xml:reports/coverage.xml",  # XML coverage report for CI
        "--cov-fail-under=30",
        "--durations=25",  # Show slowest 25 tests
        "--junitxml=reports/test_results.xml",  # JUnit XML report for CI
        "--html=reports/test.html",  # Generate HTML report
        "--blockage",
        "-v",
        *session.posargs,
    )


def _setup_playwright_browser_testing(session):
    """Set up Playwright dependencies and browser configuration for testing."""
    # Install Playwright dependencies
    session.install("playwright", "pytest-playwright")
    session.install("pytest-asyncio")  # Required for async test functions
    session.install("pytest-timeout")  # Required for test timeouts

    # Create ffmpeg symlink for Playwright video recording
    playwright_ffmpeg_dir = os.path.expanduser("~/.cache/ms-playwright/ffmpeg-1011")
    playwright_ffmpeg_path = os.path.join(playwright_ffmpeg_dir, "ffmpeg-linux")
    system_ffmpeg = "/usr/bin/ffmpeg"

    if os.path.exists(system_ffmpeg) and not os.path.exists(playwright_ffmpeg_path):
        session.log("Creating ffmpeg symlink for Playwright video recording...")
        os.makedirs(playwright_ffmpeg_dir, exist_ok=True)
        os.symlink(system_ffmpeg, playwright_ffmpeg_path)
        session.log(f"Created symlink: {playwright_ffmpeg_path} -> {system_ffmpeg}")


def _run_playwright_tests_with_timeout(
    session,
    test_dir: str,
    timeout_seconds: int = 60,
    extra_args: list[str] | None = None,
    enable_asyncio: bool = False,
):
    """Run Playwright tests with process-level timeout to prevent hanging."""

    # Base pytest arguments for all browser tests
    base_args = [
        "timeout",
        f"{timeout_seconds}s",  # Process-level timeout
        "pytest",
        test_dir,
        "--video",
        "retain-on-failure",
        "--screenshot",
        "only-on-failure",
        "-v",
        # REMOVED: "-x",  # Don't stop on first failure to allow proper cleanup
    ]

    # Add asyncio configuration if needed
    if enable_asyncio:
        base_args.extend(["--asyncio-mode=auto"])

    # Add extra arguments if provided
    if extra_args:
        base_args.extend(extra_args)

    session.log(f"Tests will timeout after {timeout_seconds} seconds")
    session.log("Using system Chrome via executable_path configuration")
    session.log(
        "Running tests without -x flag to ensure proper cleanup and log capture"
    )
    session.run(
        *base_args,
        *session.posargs,
        external=True,  # Use external=True for timeout command
    )


def _run_playwright_tests(
    session,
    test_dir: str,
    extra_args: list[str] | None = None,
    enable_asyncio: bool = False,
):
    """Run Playwright tests with proper browser configuration."""

    # Base pytest arguments for all browser tests
    base_args = [
        "pytest",
        test_dir,
        "--video",
        "retain-on-failure",
        "--screenshot",
        "only-on-failure",
        "-v",
    ]

    # Add asyncio configuration if needed
    if enable_asyncio:
        base_args.extend(["--asyncio-mode=auto"])

    # Add extra arguments if provided
    if extra_args:
        base_args.extend(extra_args)

    session.log("Using system Chrome via executable_path configuration")
    session.run(
        *base_args,
        *session.posargs,
    )


@nox.session(python=DEFAULT_PYTHON, name="test-integration")
def test_integration(session):
    """Run integration tests: React frontend + Flask backend through real browser."""
    session.install("-e", ".")
    session.install("pytest", "pytest-flask", "requests", "pytest-html")

    # Set up Playwright browser environment
    _setup_playwright_browser_testing(session)

    # Create test-results directory for logs and screenshots
    import os

    os.makedirs("test-results", exist_ok=True)

    session.log("Running integration tests with proper cleanup enabled...")
    session.log("Server logs will be saved to test-results/integration-server-logs.txt")

    # Run integration tests with timeout to prevent hanging
    _run_playwright_tests_with_timeout(
        session,
        TEST_DIR + "/integration",
        timeout_seconds=300,  # 5 minutes for full test suite
        extra_args=[
            "--tb=short",
            "--durations=25",  # Show slowest 25 tests
            "--junitxml=reports/integration_results.xml",  # JUnit XML report for CI
            "--html=reports/integration.html",  # Generate HTML report
        ],  # Shorter traceback for better error visibility, allow cleanup
        enable_asyncio=True,  # Enable asyncio support for integration tests
    )


@nox.session(python=DEFAULT_PYTHON, name="test-comprehensive")
def test_comprehensive(session):
    """Run all tests: backend unit tests, integration tests, and frontend tests."""
    session.log("=== Running Comprehensive Test Suite ===")
    session.notify("test")
    session.notify("test-integration")
    session.notify("test-frontend")


@nox.session(python=DEFAULT_PYTHON, name="test-frontend")
def test_frontend(session):
    """Run frontend tests with Vitest and verify build."""
    frontend_dir = "frontend"

    # Check if frontend directory exists
    if not os.path.exists(frontend_dir):
        session.log("Frontend directory not found, skipping frontend tests")
        return

    # Check if Node.js and npm are available
    try:
        session.run("node", "--version", external=True)
        session.run("npm", "--version", external=True)
    except Exception as e:
        session.error(f"Node.js/npm not available: {e}")

    # Change to frontend directory
    session.chdir(frontend_dir)

    # Install dependencies if node_modules doesn't exist
    if not os.path.exists("node_modules"):
        session.log("Installing frontend dependencies...")
        session.run("npm", "install", external=True)

    # Run comprehensive frontend CI tests (lint, type-check, test, build)
    session.log("Running comprehensive frontend tests...")
    session.run("npm", "run", "test:ci", external=True)


@nox.session(python=DEFAULT_PYTHON, name="test-frontend-watch")
def test_frontend_watch(session):
    """Run frontend tests in watch mode with Vitest."""
    frontend_dir = "frontend"

    # Check if frontend directory exists
    if not os.path.exists(frontend_dir):
        session.log("Frontend directory not found, skipping frontend tests")
        return

    # Check if Node.js and npm are available
    try:
        session.run("node", "--version", external=True)
        session.run("npm", "--version", external=True)
    except Exception as e:
        session.error(f"Node.js/npm not available: {e}")

    # Change to frontend directory
    session.chdir(frontend_dir)

    # Install dependencies if node_modules doesn't exist
    if not os.path.exists("node_modules"):
        session.log("Installing frontend dependencies...")
        session.run("npm", "install", external=True)

    # Run frontend tests in watch mode
    session.log("Running frontend tests in watch mode...")
    session.run("npm", "run", "test", external=True)


@nox.session(python=DEFAULT_PYTHON)
def safety(session):
    """Check dependencies for security vulnerabilities."""
    session.install("safety")
    session.run("safety", "check", "--json")


@nox.session(python=DEFAULT_PYTHON)
def docs(session):
    """Build documentation with Sphinx."""
    session.install("-e", ".")
    session.install("sphinx", "sphinx-rtd-theme", "sphinx-autodoc-typehints")

    session.chdir(DOCS_DIR)
    session.run("sphinx-build", "-b", "html", ".", "_build/html")


@nox.session(python=DEFAULT_PYTHON, name="docs-serve")
def docs_serve(session):
    """Build and serve documentation locally."""
    session.install("-e", ".")
    session.install(
        "sphinx", "sphinx-rtd-theme", "sphinx-autodoc-typehints", "sphinx-autobuild"
    )

    session.chdir(DOCS_DIR)
    session.run(
        "sphinx-autobuild", ".", "_build/html", "--host", "0.0.0.0", "--port", "8000"
    )


@nox.session(python=DEFAULT_PYTHON)
def clean(session):
    """Clean up build artifacts and cache files."""
    import shutil

    directories_to_clean = [
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        "htmlcov",
        "build",
        "dist",
        "*.egg-info",
        DOCS_DIR + "/_build",
    ]

    for pattern in directories_to_clean:
        if "*" in pattern:
            # Handle glob patterns
            import glob

            for path in glob.glob(pattern, recursive=True):
                if os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)
                    session.log(f"Removed directory: {path}")
        else:
            # Handle direct directory paths
            for root, dirs, files in os.walk("."):
                if pattern in dirs:
                    dir_path = os.path.join(root, pattern)
                    shutil.rmtree(dir_path, ignore_errors=True)
                    session.log(f"Removed directory: {dir_path}")


@nox.session(python=DEFAULT_PYTHON, name="dev-setup")
def dev_setup(session):
    """Set up development environment."""
    # Install Python dependencies
    session.install("-e", ".")
    session.install(
        "black",
        "isort",
        "flake8",
        "pycodestyle",
        "mypy",
        "pytest",
        "pytest-cov",
        "pytest-flask",
        "pytest-mock",
    )

    # Initialize database
    session.run("kiosk-init-db", "--sample-data")

    # Set up frontend dependencies if frontend directory exists
    if os.path.exists("frontend"):
        session.log("Setting up frontend dependencies...")
        session.chdir("frontend")
        try:
            session.run("npm", "install", external=True)
            session.log("Frontend dependencies installed successfully!")
        except Exception as e:
            session.log(f"Warning: Could not install frontend dependencies: {e}")
            session.log("Make sure Node.js and npm are installed")
        session.chdir("..")

    session.log("Development environment setup complete!")
    session.log("Available commands:")
    session.log("  Backend:")
    session.log("    nox -s format          # Format code")
    session.log("    nox -s lint            # Check code style")
    session.log("    nox -s test            # Run unit tests")
    session.log("    nox -s test-integration # Run integration tests")
    if os.path.exists("frontend"):
        session.log("  Frontend:")
        session.log("    nox -s test-frontend   # Run frontend tests")
        session.log("    nox -s test-frontend-watch # Run frontend tests in watch mode")
    session.log("  Comprehensive:")
    session.log(
        "    nox -s test-comprehensive # Run all tests (backend + frontend + integration)"
    )


# Default session when no session is specified
nox.options.sessions = ["format", "lint", "test"]
