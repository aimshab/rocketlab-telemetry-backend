"""
SQLite-backed telemetry store (in-memory).

Uses a shared in-memory SQLite database so data persists for the process
lifetime and resets when the server restarts.

Concurrency model:
  - Each operation opens its own connection and closes it when done, so
    request threads never share a sqlite3 Connection/cursor.
  - A keep-alive connection holds the shared in-memory DB between requests.
  - A write lock + busy retries serialize writers (SQLite shared-cache still
    uses table locks; without this, concurrent INSERTs can raise
    "database table is locked").
"""

from __future__ import annotations

import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Callable, Iterator, Optional, TypeVar
from uuid import UUID, uuid4

from app.filters import FilterChain
from app.models import Telemetry, TelemetryCreate
from app.store.base import TelemetryStore

# Shared cache: all connections see the same in-memory database.
_DB_URI = "file:telemetry?mode=memory&cache=shared"
_T = TypeVar("_T")


def _to_iso8601(value: datetime) -> str:
    """Serialize datetimes to the strict ISO 8601 form our models accept."""
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    millis = value.microsecond // 1000
    if millis:
        return value.strftime("%Y-%m-%dT%H:%M:%S.") + f"{millis:03d}Z"
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


class SqliteTelemetryStore(TelemetryStore):
    def __init__(self) -> None:
        # Keep one connection open for the process lifetime. With cache=shared,
        # closing the last connection would wipe the in-memory database.
        self._keepalive = self._open_connection()
        self._init_schema(self._keepalive)
        self._write_lock = threading.Lock()

    @staticmethod
    def _open_connection() -> sqlite3.Connection:
        conn = sqlite3.connect(
            _DB_URI,
            uri=True,
            check_same_thread=False,
            timeout=30.0,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 30000")
        return conn

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        """Per-operation connection — not shared across request threads."""
        conn = self._open_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _retry_locked(self, operation: Callable[[], _T]) -> _T:
        """Retry when SQLite reports a transient lock contention."""
        delays = (0.001, 0.005, 0.01, 0.05, 0.1, 0.2)
        last_error: Optional[sqlite3.OperationalError] = None
        for delay in delays:
            try:
                return operation()
            except sqlite3.OperationalError as exc:
                if "locked" not in str(exc).lower():
                    raise
                last_error = exc
                time.sleep(delay)
        assert last_error is not None
        raise last_error

    def _init_schema(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS telemetry (
                id TEXT PRIMARY KEY,
                satellite_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                altitude REAL NOT NULL,
                velocity REAL NOT NULL,
                status TEXT NOT NULL
            )
            """
        )
        conn.commit()

    def create(self, data: TelemetryCreate) -> Telemetry:
        entry_id = uuid4()
        entry = Telemetry(id=entry_id, **data.model_dump())

        def _insert() -> Telemetry:
            with self._write_lock:
                with self._connection() as conn:
                    conn.execute(
                        """
                        INSERT INTO telemetry (
                            id, satellite_id, timestamp, altitude, velocity, status
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            str(entry.id),
                            entry.satelliteId,
                            _to_iso8601(entry.timestamp),
                            entry.altitude,
                            entry.velocity,
                            entry.status,
                        ),
                    )
            return entry

        return self._retry_locked(_insert)

    def find_all(
        self,
        telemetry_filter: Optional[FilterChain] = None,
        *,
        page: int = 1,
        limit: int = 10,
    ) -> tuple[list[Telemetry], bool]:
        """
        Return one page of entries plus whether more matches exist.

        Fetches limit+1 rows so hasMore can be set without a separate COUNT.
        """
        offset = (page - 1) * limit
        where = "1=1"
        params: list = []

        if telemetry_filter is not None:
            where, filter_params = telemetry_filter.sql_clause()
            params.extend(filter_params)

        def _select() -> tuple[list[Telemetry], bool]:
            with self._connection() as conn:
                rows = conn.execute(
                    f"""
                    SELECT id, satellite_id, timestamp, altitude, velocity, status
                    FROM telemetry
                    WHERE {where}
                    ORDER BY rowid ASC
                    LIMIT ? OFFSET ?
                    """,
                    (*params, limit + 1, offset),
                ).fetchall()
            has_more = len(rows) > limit
            page_rows = rows[:limit]
            return [self._row_to_telemetry(row) for row in page_rows], has_more

        return self._retry_locked(_select)

    def find_by_id(self, entry_id: UUID) -> Optional[Telemetry]:
        def _select() -> Optional[Telemetry]:
            with self._connection() as conn:
                row = conn.execute(
                    """
                    SELECT id, satellite_id, timestamp, altitude, velocity, status
                    FROM telemetry
                    WHERE id = ?
                    """,
                    (str(entry_id),),
                ).fetchone()
            if row is None:
                return None
            return self._row_to_telemetry(row)

        return self._retry_locked(_select)

    def remove(self, entry_id: UUID) -> bool:
        def _delete() -> bool:
            with self._write_lock:
                with self._connection() as conn:
                    cursor = conn.execute(
                        "DELETE FROM telemetry WHERE id = ?",
                        (str(entry_id),),
                    )
                    return cursor.rowcount > 0

        return self._retry_locked(_delete)

    def clear(self) -> None:
        def _clear() -> None:
            with self._write_lock:
                with self._connection() as conn:
                    conn.execute("DELETE FROM telemetry")

        self._retry_locked(_clear)

    @staticmethod
    def _row_to_telemetry(row: sqlite3.Row) -> Telemetry:
        return Telemetry(
            id=row["id"],
            satelliteId=row["satellite_id"],
            timestamp=row["timestamp"],
            altitude=row["altitude"],
            velocity=row["velocity"],
            status=row["status"],
        )
