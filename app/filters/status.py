from app.filters.base import TelemetryFilter
from app.models import Telemetry


class StatusFilter(TelemetryFilter):
    """Exact-match filter on health status."""

    def __init__(self, status: str) -> None:
        self._status = status

    def matches(self, entry: Telemetry) -> bool:
        return entry.status == self._status

    def sql_clause(self) -> tuple[str, tuple]:
        return "status = ?", (self._status,)
