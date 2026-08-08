"""Unit tests for chainable telemetry filters."""

from app.filters import (
    FilterChain,
    SatelliteIdFilter,
    StatusFilter,
    build_telemetry_filter,
    combine_filters,
    paginate,
)
from app.models import Telemetry


def _entries(*pairs: tuple[str, str]) -> list[Telemetry]:
    return [
        Telemetry(
            id=f"00000000-0000-0000-0000-00000000000{i}",
            satelliteId=satellite_id,
            timestamp="2026-08-06T12:00:00.000Z",
            altitude=500.0,
            velocity=7.5,
            status=status,
        )
        for i, (satellite_id, status) in enumerate(pairs, start=1)
    ]


def _entry(satellite_id: str, status: str) -> Telemetry:
    return _entries((satellite_id, status))[0]


class TestSatelliteIdFilter:
    def test_matches(self):
        assert SatelliteIdFilter("SAT-001").matches(_entry("SAT-001", "healthy"))

    def test_rejects_other_id(self):
        assert not SatelliteIdFilter("SAT-001").matches(_entry("SAT-002", "healthy"))


class TestStatusFilter:
    def test_matches(self):
        assert StatusFilter("critical").matches(_entry("SAT-001", "critical"))

    def test_rejects_other_status(self):
        assert not StatusFilter("critical").matches(_entry("SAT-001", "healthy"))


class TestFilterChaining:
    def test_and_requires_both(self):
        chained = SatelliteIdFilter("SAT-001") & StatusFilter("critical")
        assert chained.matches(_entry("SAT-001", "critical"))
        assert not chained.matches(_entry("SAT-001", "healthy"))
        assert not chained.matches(_entry("SAT-002", "critical"))

    def test_combine_filters_and(self):
        combined = combine_filters(
            SatelliteIdFilter("SAT-001"),
            StatusFilter("healthy"),
        )
        assert combined is not None
        assert combined.matches(_entry("SAT-001", "healthy"))
        assert not combined.matches(_entry("SAT-001", "critical"))

    def test_combine_filters_empty(self):
        assert combine_filters(None, None) is None

    def test_build_telemetry_filter_chains(self):
        built = build_telemetry_filter(satellite_id="SAT-001", status="critical")
        assert built is not None
        assert built.matches(_entry("SAT-001", "critical"))
        assert not built.matches(_entry("SAT-001", "healthy"))

    def test_apply_filters_collection(self):
        entries = _entries(
            ("SAT-001", "healthy"),
            ("SAT-001", "critical"),
            ("SAT-002", "critical"),
        )
        chain = SatelliteIdFilter("SAT-001") & StatusFilter("critical")
        filtered = chain.apply(entries)
        assert len(filtered) == 1
        assert filtered[0].satelliteId == "SAT-001"
        assert filtered[0].status == "critical"

    def test_single_filter_wrapped_in_chain(self):
        chain = combine_filters(SatelliteIdFilter("SAT-002"))
        assert isinstance(chain, FilterChain)
        entries = _entries(("SAT-001", "healthy"), ("SAT-002", "healthy"))
        assert chain is not None
        filtered = chain.apply(entries)
        assert len(filtered) == 1
        assert filtered[0].satelliteId == "SAT-002"

    def test_sql_clause_chain(self):
        chain = SatelliteIdFilter("SAT-001") & StatusFilter("critical")
        clause, params = chain.sql_clause()
        assert clause == "(satellite_id = ?) AND (status = ?)"
        assert params == ("SAT-001", "critical")



class TestPaginateEarlyStop:
    def test_stops_after_page_is_full(self):
        entries = _entries(
            ("SAT-001", "healthy"),
            ("SAT-001", "healthy"),
            ("SAT-001", "healthy"),
            ("SAT-001", "healthy"),
            ("SAT-001", "healthy"),
        )
        chain = FilterChain(SatelliteIdFilter("SAT-001"))
        visited = {"count": 0}

        def counting(entries_iter):
            for entry in entries_iter:
                visited["count"] += 1
                yield entry

        items, has_more = chain.apply_page(
            counting(entries),
            offset=0,
            limit=2,
        )
        assert len(items) == 2
        assert has_more is True
        # 2 collected + 1 peek for hasMore; remaining matches are not visited
        assert visited["count"] == 3

    def test_offset_skips_then_collects(self):
        entries = _entries(
            ("SAT-001", "healthy"),
            ("SAT-001", "warning"),
            ("SAT-001", "critical"),
            ("SAT-001", "healthy"),
        )
        items, has_more = paginate(
            entries,
            offset=2,
            limit=1,
            telemetry_filter=SatelliteIdFilter("SAT-001"),
        )
        assert len(items) == 1
        assert items[0].status == "critical"
        assert has_more is True
