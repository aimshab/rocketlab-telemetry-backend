"""Tests for storage backend and seed settings from configuration."""

from datetime import timezone

import pytest

from app.config import get_settings
from app.store import create_store
from app.store.list_store import ListTelemetryStore
from app.store.sqlite_store import SqliteTelemetryStore


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_default_backend_is_list(monkeypatch):
    monkeypatch.delenv("STORAGE_BACKEND", raising=False)
    assert get_settings().storage_backend == "list"
    assert isinstance(create_store(), ListTelemetryStore)


def test_list_backend(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "list")
    assert isinstance(create_store(), ListTelemetryStore)


def test_sqlite_backend(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "sqlite")
    assert isinstance(create_store(), SqliteTelemetryStore)


def test_invalid_backend_raises(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "redis")
    with pytest.raises(ValueError, match="STORAGE_BACKEND"):
        get_settings()


def test_default_seed_settings(monkeypatch):
    for key in (
        "SEED_ENABLED",
        "SEED_SATELLITE_COUNT",
        "SEED_ENTRY_COUNT",
        "SEED_TIME_START",
        "SEED_TIME_END",
        "SEED_ALTITUDE_MIN",
        "SEED_ALTITUDE_MAX",
        "SEED_VELOCITY_MIN",
        "SEED_VELOCITY_MAX",
        "SEED_STATUS_HEALTHY_PCT",
        "SEED_STATUS_WARNING_PCT",
        "SEED_STATUS_CRITICAL_PCT",
        "SEED_RANDOM_SEED",
    ):
        monkeypatch.delenv(key, raising=False)

    seed = get_settings().seed
    assert seed.enabled is True
    assert seed.satellite_count == 3
    assert seed.entry_count == 3
    assert seed.time_start.tzinfo == timezone.utc
    assert seed.status_healthy_pct == 70.0
    assert seed.random_seed == 42


def test_seed_settings_from_env(monkeypatch):
    monkeypatch.setenv("SEED_ENABLED", "false")
    monkeypatch.setenv("SEED_SATELLITE_COUNT", "5")
    monkeypatch.setenv("SEED_ENTRY_COUNT", "20")
    monkeypatch.setenv("SEED_ALTITUDE_MIN", "100")
    monkeypatch.setenv("SEED_ALTITUDE_MAX", "200")
    monkeypatch.setenv("SEED_VELOCITY_MIN", "1.5")
    monkeypatch.setenv("SEED_VELOCITY_MAX", "2.5")
    monkeypatch.setenv("SEED_STATUS_HEALTHY_PCT", "40")
    monkeypatch.setenv("SEED_STATUS_WARNING_PCT", "40")
    monkeypatch.setenv("SEED_STATUS_CRITICAL_PCT", "20")
    monkeypatch.setenv("SEED_RANDOM_SEED", "none")

    seed = get_settings().seed
    assert seed.enabled is False
    assert seed.satellite_count == 5
    assert seed.entry_count == 20
    assert seed.altitude_min == 100.0
    assert seed.velocity_max == 2.5
    assert seed.status_critical_pct == 20.0
    assert seed.random_seed is None


def test_invalid_seed_percentages_raise(monkeypatch):
    monkeypatch.setenv("SEED_STATUS_HEALTHY_PCT", "50")
    monkeypatch.setenv("SEED_STATUS_WARNING_PCT", "50")
    monkeypatch.setenv("SEED_STATUS_CRITICAL_PCT", "50")
    with pytest.raises(ValueError, match="sum to 100"):
        get_settings()
