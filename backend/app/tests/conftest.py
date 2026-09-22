"""A bare `TestClient(app)` spins up a new event loop per request on Windows'
ProactorEventLoop, while the async SQLAlchemy engine's pooled asyncpg
connections stay bound to whichever loop created them -- the second request
in a test then fails trying to reuse/clean up a connection from an
already-closed loop. Using TestClient as a context manager keeps one
persistent loop for the whole test session, which is the documented fix.
"""
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client
