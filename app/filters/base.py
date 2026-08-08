"""
Telemetry filter interface and filter chain composition.

Leaf filters evaluate a single entry in Python and also expose a SQL clause
so the SQLite store can push filtering down to the database.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Optional

from app.models import Telemetry


class TelemetryFilter(ABC):
    """Interface for matching a single telemetry entry."""

    @abstractmethod
    def matches(self, entry: Telemetry) -> bool:
        """Return True when the entry satisfies this filter."""

    @abstractmethod
    def sql_clause(self) -> tuple[str, tuple]:
        """
        Return a parameterized SQL predicate and its bind values.

        Example: ("satellite_id = ?", ("SAT-001",))
        """

    def __and__(self, other: TelemetryFilter) -> FilterChain:
        """Chain filters: `a & b` keeps entries matching both (logical AND)."""
        return FilterChain(self, other)


class FilterChain(TelemetryFilter):
    """
    Ordered chain of filters.

    Entries must match every filter (logical AND). sql_clause() joins child
    predicates with AND for use in SQLite queries.
    """

    def __init__(self, *filters: TelemetryFilter) -> None:
        if not filters:
            raise ValueError("FilterChain requires at least one filter")
        self._filters = filters

    def matches(self, entry: Telemetry) -> bool:
        """Push one entry through every filter; fail fast on the first miss."""
        for telemetry_filter in self._filters:
            if not telemetry_filter.matches(entry):
                return False
        return True

    def sql_clause(self) -> tuple[str, tuple]:
        clauses: list[str] = []
        params: list = []
        for telemetry_filter in self._filters:
            clause, clause_params = telemetry_filter.sql_clause()
            clauses.append(f"({clause})")
            params.extend(clause_params)
        return " AND ".join(clauses), tuple(params)

    def apply(self, entries: Iterable[Telemetry]) -> list[Telemetry]:
        """Collect every matching entry (in-memory helper for unit tests)."""
        return [entry for entry in entries if self.matches(entry)]

    def apply_page(
        self,
        entries: Iterable[Telemetry],
        *,
        offset: int,
        limit: int,
    ) -> tuple[list[Telemetry], bool]:
        """Paginate matches in one pass; stop once the page is filled."""
        return paginate(
            entries,
            offset=offset,
            limit=limit,
            telemetry_filter=self,
        )

    def __and__(self, other: TelemetryFilter) -> FilterChain:
        # Flatten nested chains so long sequences stay a single FilterChain
        return FilterChain(*self._filters, other)


def paginate(
    entries: Iterable[Telemetry],
    *,
    offset: int,
    limit: int,
    telemetry_filter: Optional[TelemetryFilter] = None,
) -> tuple[list[Telemetry], bool]:
    """
    Single-pass in-memory pagination (used by filter unit tests).

    The SQLite store uses LIMIT/OFFSET instead; this keeps the FilterChain
    API usable without a database.
    """
    if offset < 0:
        raise ValueError("offset must be >= 0")
    if limit < 1:
        raise ValueError("limit must be >= 1")

    skip_remaining = offset
    items: list[Telemetry] = []

    for entry in entries:
        if telemetry_filter is not None and not telemetry_filter.matches(entry):
            continue

        if skip_remaining > 0:
            skip_remaining -= 1
            continue

        if len(items) < limit:
            items.append(entry)
            continue

        return items, True

    return items, False


def combine_filters(*filters: Optional[TelemetryFilter]) -> Optional[FilterChain]:
    """
    Combine non-None filters into a FilterChain (logical AND).

    Always returns a FilterChain (even for one filter). Returns None when no
    filters are provided.
    """
    active = [f for f in filters if f is not None]
    if not active:
        return None
    return FilterChain(*active)
