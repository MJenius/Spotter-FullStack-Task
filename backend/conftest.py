import os

import pytest

os.environ.setdefault("PYTEST_RUNNING", "1")
# Tests must never use a real key or hit real providers.
os.environ.setdefault("GOOGLE_ROUTES_API_KEY", "test-key-not-real")


@pytest.fixture(autouse=True)
def configure_test_settings(settings):
    """Ensure tests run with a safe test-only routing key unless explicitly overridden."""
    if not settings.GOOGLE_ROUTES_API_KEY:
        settings.GOOGLE_ROUTES_API_KEY = "test-key-not-real"
