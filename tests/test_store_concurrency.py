"""Concurrency smoke tests for both telemetry store backends."""

from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from app.models import TelemetryCreate
from app.store.list_store import ListTelemetryStore
from app.store.sqlite_store import SqliteTelemetryStore


def _payload(i: int) -> TelemetryCreate:
    return TelemetryCreate(
        satelliteId=f"SAT-{i:03d}",
        timestamp="2026-08-06T12:00:00.000Z",
        altitude=500.0 + i,
        velocity=7.5,
        status="healthy",
    )


@pytest.mark.parametrize(
    "store_factory",
    [ListTelemetryStore, SqliteTelemetryStore],
    ids=["list", "sqlite"],
)
def test_concurrent_creates(store_factory):
    store = store_factory()
    store.clear()
    n = 50

    def insert(i: int):
        return store.create(_payload(i))

    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = [pool.submit(insert, i) for i in range(n)]
        created = [f.result() for f in as_completed(futures)]

    assert len(created) == n
    assert len({entry.id for entry in created}) == n

    items, has_more = store.find_all(page=1, limit=n)
    assert len(items) == n
    assert has_more is False


@pytest.mark.parametrize(
    "store_factory",
    [ListTelemetryStore, SqliteTelemetryStore],
    ids=["list", "sqlite"],
)
def test_concurrent_create_and_read(store_factory):
    store = store_factory()
    store.clear()

    def writer(i: int):
        return store.create(_payload(i))

    def reader():
        items, _ = store.find_all(page=1, limit=100)
        return len(items)

    with ThreadPoolExecutor(max_workers=16) as pool:
        write_futures = [pool.submit(writer, i) for i in range(30)]
        read_futures = [pool.submit(reader) for _ in range(30)]
        for f in as_completed(write_futures + read_futures):
            f.result()  # raise if any worker failed

    items, _ = store.find_all(page=1, limit=100)
    assert len(items) == 30
