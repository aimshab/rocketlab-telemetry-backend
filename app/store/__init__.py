"""
Telemetry store package.

Uses an in-memory SQLite backend for the process lifetime.
"""

from app.store.base import TelemetryStore
from app.store.sqlite_store import SqliteTelemetryStore

# Module-level singleton shared by the FastAPI app
store = SqliteTelemetryStore()

__all__ = [
    "TelemetryStore",
    "SqliteTelemetryStore",
    "store",
]
