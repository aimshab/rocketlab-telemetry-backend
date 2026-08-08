from typing import Optional

from app.filters.base import FilterChain, TelemetryFilter, combine_filters, paginate
from app.filters.satellite_id import SatelliteIdFilter
from app.filters.status import StatusFilter
from app.models import TelemetryStatus

__all__ = [
    "TelemetryFilter",
    "FilterChain",
    "SatelliteIdFilter",
    "StatusFilter",
    "combine_filters",
    "build_telemetry_filter",
    "paginate",
]


def build_telemetry_filter(
    satellite_id: Optional[str] = None,
    status: Optional[TelemetryStatus] = None,
) -> Optional[FilterChain]:
    """Build a FilterChain from optional query criteria."""
    return combine_filters(
        SatelliteIdFilter(satellite_id) if satellite_id is not None else None,
        StatusFilter(status) if status is not None else None,
    )
