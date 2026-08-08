"""
Configurable generator for startup telemetry seed data.

Produces TelemetryCreate payloads from SeedConfig (counts, value ranges,
and status mix). Deterministic when random_seed is set.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from app.models import TelemetryCreate, TelemetryStatus


@dataclass(frozen=True)
class SeedConfig:
    """Parameters that control how seed telemetry entries are generated."""

    enabled: bool = True
    satellite_count: int = 3
    entry_count: int = 3
    time_start: datetime = datetime(2026, 8, 6, tzinfo=timezone.utc)
    time_end: datetime = datetime(2026, 8, 7, tzinfo=timezone.utc)
    altitude_min: float = 400.0
    altitude_max: float = 600.0
    velocity_min: float = 7.0
    velocity_max: float = 8.0
    status_healthy_pct: float = 70.0
    status_warning_pct: float = 20.0
    status_critical_pct: float = 10.0
    random_seed: Optional[int] = 42

    def validate(self) -> None:
        """Raise ValueError when configuration is inconsistent."""
        if self.satellite_count < 1:
            raise ValueError("SEED_SATELLITE_COUNT must be >= 1")
        if self.entry_count < 0:
            raise ValueError("SEED_ENTRY_COUNT must be >= 0")
        if self.time_start >= self.time_end:
            raise ValueError("SEED_TIME_START must be before SEED_TIME_END")
        if self.altitude_min <= 0 or self.altitude_max <= 0:
            raise ValueError("altitude range bounds must be > 0")
        if self.altitude_min > self.altitude_max:
            raise ValueError("SEED_ALTITUDE_MIN must be <= SEED_ALTITUDE_MAX")
        if self.velocity_min <= 0 or self.velocity_max <= 0:
            raise ValueError("velocity range bounds must be > 0")
        if self.velocity_min > self.velocity_max:
            raise ValueError("SEED_VELOCITY_MIN must be <= SEED_VELOCITY_MAX")

        for name, pct in (
            ("SEED_STATUS_HEALTHY_PCT", self.status_healthy_pct),
            ("SEED_STATUS_WARNING_PCT", self.status_warning_pct),
            ("SEED_STATUS_CRITICAL_PCT", self.status_critical_pct),
        ):
            if pct < 0 or pct > 100:
                raise ValueError(f"{name} must be between 0 and 100")

        total = (
            self.status_healthy_pct
            + self.status_warning_pct
            + self.status_critical_pct
        )
        if abs(total - 100.0) > 1e-6:
            raise ValueError(
                "status percentages must sum to 100 "
                f"(got healthy={self.status_healthy_pct}, "
                f"warning={self.status_warning_pct}, "
                f"critical={self.status_critical_pct}, total={total})"
            )


class TelemetrySeedGenerator:
    """Generate TelemetryCreate entries from a SeedConfig."""

    def __init__(self, config: SeedConfig) -> None:
        config.validate()
        self._config = config
        self._rng = random.Random(config.random_seed)

    def generate(self) -> list[TelemetryCreate]:
        """Build seed payloads; empty when seeding is disabled or count is 0."""
        if not self._config.enabled or self._config.entry_count == 0:
            return []

        statuses = self._status_sequence(self._config.entry_count)
        satellites = [
            f"SAT-{index:03d}" for index in range(1, self._config.satellite_count + 1)
        ]
        span = self._config.time_end - self._config.time_start

        entries: list[TelemetryCreate] = []
        for status in statuses:
            offset = span * self._rng.random()
            timestamp = self._config.time_start + offset
            entries.append(
                TelemetryCreate(
                    satelliteId=self._rng.choice(satellites),
                    timestamp=self._to_iso8601(timestamp),
                    altitude=self._rng.uniform(
                        self._config.altitude_min, self._config.altitude_max
                    ),
                    velocity=self._rng.uniform(
                        self._config.velocity_min, self._config.velocity_max
                    ),
                    status=status,
                )
            )

        entries.sort(key=lambda entry: entry.timestamp)
        return entries

    def _status_sequence(self, count: int) -> list[TelemetryStatus]:
        """Allocate statuses by percentage, then shuffle."""
        weights: tuple[tuple[TelemetryStatus, float], ...] = (
            ("healthy", self._config.status_healthy_pct),
            ("warning", self._config.status_warning_pct),
            ("critical", self._config.status_critical_pct),
        )
        # Largest-remainder method so counts always sum to `count`.
        exact = [(status, count * pct / 100.0) for status, pct in weights]
        allocated = {status: int(value) for status, value in exact}
        remainder = count - sum(allocated.values())
        by_fraction = sorted(
            exact, key=lambda item: item[1] - int(item[1]), reverse=True
        )
        for status, _ in by_fraction[:remainder]:
            allocated[status] += 1

        sequence: list[TelemetryStatus] = []
        for status, n in allocated.items():
            sequence.extend([status] * n)
        self._rng.shuffle(sequence)
        return sequence

    @staticmethod
    def _to_iso8601(value: datetime) -> str:
        """Format as strict ISO 8601 UTC for TelemetryCreate validation."""
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        else:
            value = value.replace(tzinfo=None)
        millis = value.microsecond // 1000
        if millis:
            return value.strftime("%Y-%m-%dT%H:%M:%S.") + f"{millis:03d}Z"
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")
