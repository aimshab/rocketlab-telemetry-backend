"""
Shared pytest fixtures.

Module-scoped TestClient starts the app (and lifespan seed) once; each test
then clears the store so cases start from a known empty state.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import TelemetryCreate
from app.store import store


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_store():
    """Reset in-memory data before every test."""
    store.clear()
    yield
    store.clear()


@pytest.fixture
def sample_payload() -> dict:
    return {
        "satelliteId": "SAT-100",
        "timestamp": "2026-08-06T12:00:00.000Z",
        "altitude": 500.0,
        "velocity": 7.5,
        "status": "healthy",
    }


@pytest.fixture
def seeded_entries():
    """Insert a known set of entries and return them."""
    payloads = [
        TelemetryCreate(
            satelliteId="SAT-001",
            timestamp="2026-08-06T10:00:00.000Z",
            altitude=420.5,
            velocity=7.66,
            status="healthy",
        ),
        TelemetryCreate(
            satelliteId="SAT-002",
            timestamp="2026-08-06T10:05:00.000Z",
            altitude=550.2,
            velocity=7.58,
            status="healthy",
        ),
        TelemetryCreate(
            satelliteId="SAT-001",
            timestamp="2026-08-06T10:15:00.000Z",
            altitude=418.1,
            velocity=7.7,
            status="critical",
        ),
        TelemetryCreate(
            satelliteId="SAT-003",
            timestamp="2026-08-06T10:20:00.000Z",
            altitude=600.0,
            velocity=7.4,
            status="healthy",
        ),
        TelemetryCreate(
            satelliteId="SAT-002",
            timestamp="2026-08-06T10:25:00.000Z",
            altitude=548.0,
            velocity=7.55,
            status="critical",
        ),
    ]
    return [store.create(p) for p in payloads]
