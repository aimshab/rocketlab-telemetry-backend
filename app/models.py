"""
Pydantic models for satellite telemetry request/response validation.

Using Pydantic (via FastAPI) so ISO 8601 parsing and positive-number
constraints are enforced declaratively at the schema layer.
"""

import re
from datetime import datetime
from typing import Any, Literal, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

# Strict ISO 8601: YYYY-MM-DDTHH:MM:SS[.mmm]Z or ±HH:MM offset
ISO_8601_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?(?:Z|[+-]\d{2}:\d{2})$"
)

TelemetryStatus = Literal["critical", "warning", "healthy"]


class TelemetryCreate(BaseModel):
    """Payload for POST /telemetry."""

    satelliteId: str = Field(..., min_length=1, description="Satellite identifier")
    timestamp: datetime = Field(..., description="ISO 8601 datetime")
    altitude: float = Field(..., gt=0, description="Altitude (must be positive)")
    velocity: float = Field(..., gt=0, description="Velocity (must be positive)")
    status: TelemetryStatus = Field(
        ...,
        description="Health status (critical, warning, or healthy)",
    )

    @field_validator("timestamp", mode="before")
    @classmethod
    def validate_iso8601_timestamp(cls, value: Any) -> Union[datetime, str]:
        """
        Require a valid ISO 8601 datetime string (or an already-parsed datetime).

        mode="before" runs on the raw input so we can enforce the string format
        before Pydantic's more permissive datetime coercion.
        """
        if isinstance(value, datetime):
            return value

        if not isinstance(value, str) or not ISO_8601_PATTERN.match(value):
            raise ValueError(
                "timestamp must be a valid ISO 8601 datetime "
                "(e.g. 2026-08-06T12:00:00.000Z)"
            )

        # Confirm the calendar values are real (rejects e.g. month 13)
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("timestamp must be a valid ISO 8601 datetime") from exc

        return value

    @field_validator("satelliteId", "status", mode="before")
    @classmethod
    def strip_nonempty(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError("must be a non-empty string")
        return stripped


class Telemetry(TelemetryCreate):
    """Full telemetry entry including generated ID."""

    id: UUID


class PaginatedTelemetry(BaseModel):
    """Paginated list response for GET /telemetry."""

    items: list[Telemetry]
    page: int = Field(..., description="Current page (1-based)")
    limit: int = Field(..., description="Page size")
    hasMore: bool = Field(
        ...,
        description="True when more matches exist beyond this page",
    )


class ErrorResponse(BaseModel):
    error: str
    details: Optional[list[str]] = None
