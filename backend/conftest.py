import os

os.environ.setdefault("PYTEST_RUNNING", "1")
# Tests must never use a real key or hit real providers.
os.environ["GOOGLE_ROUTES_API_KEY"] = "test-key-not-real"
