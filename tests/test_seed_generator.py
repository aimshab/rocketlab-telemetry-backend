"""Tests for configurable telemetry seed generation."""

from datetime import datetime, timezone

import pytest

from app.seed import SeedConfig, TelemetrySeedGenerator


def _config(**overrides) -> SeedConfig:
    base = SeedConfig(
        enabled=True,
        satellite_count=2,
        entry_count=10,
        time_start=datetime(2026, 8, 6, tzinfo=timezone.utc),
        time_end=datetime(2026, 8, 7, tzinfo=timezone.utc),
        altitude_min=400.0,
        altitude_max=500.0,
        velocity_min=7.0,
        velocity_max=7.5,
        status_healthy_pct=50.0,
        status_warning_pct=30.0,
        status_critical_pct=20.0,
        random_seed=1,
    )
    return SeedConfig(**{**base.__dict__, **overrides})


class TestSeedConfigValidation:
    def test_percentages_must_sum_to_100(self):
        with pytest.raises(ValueError, match="sum to 100"):
            _config(status_healthy_pct=50, status_warning_pct=50, status_critical_pct=50).validate()

    def test_time_range_order(self):
        with pytest.raises(ValueError, match="SEED_TIME_START"):
            _config(
                time_start=datetime(2026, 8, 7, tzinfo=timezone.utc),
                time_end=datetime(2026, 8, 6, tzinfo=timezone.utc),
            ).validate()

    def test_altitude_bounds(self):
        with pytest.raises(ValueError, match="SEED_ALTITUDE_MIN"):
            _config(altitude_min=600, altitude_max=400).validate()


class TestTelemetrySeedGenerator:
    def test_disabled_returns_empty(self):
        entries = TelemetrySeedGenerator(_config(enabled=False)).generate()
        assert entries == []

    def test_zero_entries_returns_empty(self):
        entries = TelemetrySeedGenerator(_config(entry_count=0)).generate()
        assert entries == []

    def test_respects_counts_and_ranges(self):
        entries = TelemetrySeedGenerator(_config(entry_count=10, satellite_count=2)).generate()
        assert len(entries) == 10

        satellite_ids = {entry.satelliteId for entry in entries}
        assert satellite_ids <= {"SAT-001", "SAT-002"}

        for entry in entries:
            assert 400.0 <= entry.altitude <= 500.0
            assert 7.0 <= entry.velocity <= 7.5
            assert entry.status in {"healthy", "warning", "critical"}
            assert (
                datetime(2026, 8, 6, tzinfo=timezone.utc)
                <= entry.timestamp
                <= datetime(2026, 8, 7, tzinfo=timezone.utc)
            )

    def test_status_percentages(self):
        entries = TelemetrySeedGenerator(
            _config(
                entry_count=10,
                status_healthy_pct=50,
                status_warning_pct=30,
                status_critical_pct=20,
            )
        ).generate()
        counts = {"healthy": 0, "warning": 0, "critical": 0}
        for entry in entries:
            counts[entry.status] += 1
        assert counts == {"healthy": 5, "warning": 3, "critical": 2}

    def test_deterministic_with_random_seed(self):
        a = TelemetrySeedGenerator(_config(random_seed=99)).generate()
        b = TelemetrySeedGenerator(_config(random_seed=99)).generate()
        assert [e.model_dump() for e in a] == [e.model_dump() for e in b]

    def test_sorted_by_timestamp(self):
        entries = TelemetrySeedGenerator(_config(entry_count=20)).generate()
        timestamps = [entry.timestamp for entry in entries]
        assert timestamps == sorted(timestamps)
