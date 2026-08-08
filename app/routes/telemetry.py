"""
Telemetry route handlers.

Kept separate from main.py so endpoint logic stays easy to locate and extend.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi import status as http_status

from app.filters import build_telemetry_filter
from app.models import PaginatedTelemetry, Telemetry, TelemetryCreate, TelemetryStatus
from app.store import store

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.get("", response_model=PaginatedTelemetry)
def list_telemetry(
    satelliteId: Optional[str] = Query(None, description="Filter by satellite ID"),
    status: Optional[TelemetryStatus] = Query(
        None, description="Filter by health status (critical, warning, or healthy)"
    ),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
) -> PaginatedTelemetry:
    """Retrieve telemetry entries with optional filters and pagination."""
    telemetry_filter = build_telemetry_filter(
        satellite_id=satelliteId,
        status=status,
    )
    items, has_more = store.find_all(
        telemetry_filter,
        page=page,
        limit=limit,
    )
    return PaginatedTelemetry(
        items=items,
        page=page,
        limit=limit,
        hasMore=has_more,
    )


@router.post("", response_model=Telemetry, status_code=http_status.HTTP_201_CREATED)
def create_telemetry(payload: TelemetryCreate) -> Telemetry:
    """
    Add a new telemetry entry.

    Request body validation (ISO 8601 timestamp, positive altitude/velocity,
    allowed status values) is handled by the TelemetryCreate Pydantic model.
    """
    return store.create(payload)


@router.get("/{entry_id}", response_model=Telemetry)
def get_telemetry(entry_id: UUID) -> Telemetry:
    """Retrieve a specific telemetry entry by ID."""
    entry = store.find_by_id(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Telemetry entry not found")
    return entry


@router.delete("/{entry_id}", status_code=http_status.HTTP_204_NO_CONTENT)
def delete_telemetry(entry_id: UUID) -> Response:
    """Delete a specific telemetry entry by ID."""
    deleted = store.remove(entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Telemetry entry not found")
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)
