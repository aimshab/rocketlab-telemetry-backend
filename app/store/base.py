"""Telemetry store interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, Optional
from uuid import UUID

from app.filters import FilterChain
from app.models import Telemetry, TelemetryCreate


class TelemetryStore(ABC):
    """Interface for telemetry persistence backends."""

    def seed(self, entries: Iterable[TelemetryCreate]) -> None:
        """Insert the given seed payloads into the store."""
        for entry in entries:
            self.create(entry)

    @abstractmethod
    def create(self, data: TelemetryCreate) -> Telemetry:
        ...

    @abstractmethod
    def find_all(
        self,
        telemetry_filter: Optional[FilterChain] = None,
        *,
        page: int = 1,
        limit: int = 10,
    ) -> tuple[list[Telemetry], bool]:
        ...

    @abstractmethod
    def find_by_id(self, entry_id: UUID) -> Optional[Telemetry]:
        ...

    @abstractmethod
    def remove(self, entry_id: UUID) -> bool:
        ...

    @abstractmethod
    def clear(self) -> None:
        """Wipe all entries (primarily for tests)."""
        ...
