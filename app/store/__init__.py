"""
Telemetry store package.

The concrete backend is selected from configuration at import time
(STORAGE_BACKEND=list|sqlite) so it is fixed before the app starts.
"""

from app.config import get_settings
from app.store.base import TelemetryStore
from app.store.list_store import ListTelemetryStore
from app.store.sqlite_store import SqliteTelemetryStore


def create_store() -> TelemetryStore:
    backend = get_settings().storage_backend
    if backend == "sqlite":
        return SqliteTelemetryStore()
    return ListTelemetryStore()


# Module-level singleton shared by the FastAPI app
store = create_store()

__all__ = [
    "TelemetryStore",
    "ListTelemetryStore",
    "SqliteTelemetryStore",
    "create_store",
    "store",
]
