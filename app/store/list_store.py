"""
In-memory list/dict telemetry store.

A dict keyed by UUID gives O(1) get/delete. Filtering and pagination use the
shared FilterChain / paginate helpers (single pass with early stop).

Concurrency: a reentrant lock serializes access to the shared dict so
uvicorn worker threads can insert/read/delete safely.
"""

from __future__ import annotations

import threading
from typing import Optional
from uuid import UUID, uuid4

from app.filters import FilterChain, paginate
from app.models import Telemetry, TelemetryCreate
from app.store.base import TelemetryStore


class ListTelemetryStore(TelemetryStore):
    def __init__(self) -> None:
        self._entries: dict[UUID, Telemetry] = {}
        self._lock = threading.RLock()

    def create(self, data: TelemetryCreate) -> Telemetry:
        entry_id = uuid4()
        entry = Telemetry(id=entry_id, **data.model_dump())
        with self._lock:
            self._entries[entry_id] = entry
        return entry

    def find_all(
        self,
        telemetry_filter: Optional[FilterChain] = None,
        *,
        page: int = 1,
        limit: int = 10,
    ) -> tuple[list[Telemetry], bool]:
        offset = (page - 1) * limit
        # Snapshot under the lock so iteration is not racing with writers.
        with self._lock:
            entries = list(self._entries.values())
        return paginate(
            entries,
            offset=offset,
            limit=limit,
            telemetry_filter=telemetry_filter,
        )

    def find_by_id(self, entry_id: UUID) -> Optional[Telemetry]:
        with self._lock:
            return self._entries.get(entry_id)

    def remove(self, entry_id: UUID) -> bool:
        with self._lock:
            if entry_id not in self._entries:
                return False
            del self._entries[entry_id]
            return True

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
