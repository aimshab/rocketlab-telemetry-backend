from app.filters.base import TelemetryFilter
from app.models import Telemetry


class SatelliteIdFilter(TelemetryFilter):
    """Exact-match filter on satelliteId."""

    def __init__(self, satellite_id: str) -> None:
        self._satellite_id = satellite_id

    def matches(self, entry: Telemetry) -> bool:
        return entry.satelliteId == self._satellite_id

    def sql_clause(self) -> tuple[str, tuple]:
        return "satellite_id = ?", (self._satellite_id,)
