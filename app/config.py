"""
Application configuration loaded once before the app starts.

Seed generation is controlled by SEED_* environment variables (see SeedConfig).
CORS allowed origins are controlled by CORS_ORIGINS (plus local Vite defaults).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv

from app.seed.generator import SeedConfig

# Load .env if present so config is available before the store is constructed.
load_dotenv()

_DEFAULT_TIME_START = "2026-08-06T00:00:00.000Z"
_DEFAULT_TIME_END = "2026-08-07T00:00:00.000Z"

# Vite default ports for local frontend development.
_DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


@dataclass(frozen=True)
class Settings:
    seed: SeedConfig = SeedConfig()
    cors_origins: tuple[str, ...] = field(default_factory=lambda: _DEFAULT_CORS_ORIGINS)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw.strip())
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from exc


def _env_optional_int(name: str, default: Optional[int]) -> Optional[int]:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    if raw.strip().lower() in {"none", "null"}:
        return None
    try:
        return int(raw.strip())
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer or 'none', got {raw!r}") from exc


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw.strip())
    except ValueError as exc:
        raise ValueError(f"{name} must be a number, got {raw!r}") from exc


def _env_datetime(name: str, default: str) -> datetime:
    raw = os.getenv(name, default).strip()
    try:
        # Accept trailing Z
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(
            timezone.utc
        )
    except ValueError as exc:
        raise ValueError(
            f"{name} must be an ISO 8601 datetime, got {raw!r}"
        ) from exc


def _load_seed_config() -> SeedConfig:
    config = SeedConfig(
        enabled=_env_bool("SEED_ENABLED", True),
        satellite_count=_env_int("SEED_SATELLITE_COUNT", 3),
        entry_count=_env_int("SEED_ENTRY_COUNT", 3),
        time_start=_env_datetime("SEED_TIME_START", _DEFAULT_TIME_START),
        time_end=_env_datetime("SEED_TIME_END", _DEFAULT_TIME_END),
        altitude_min=_env_float("SEED_ALTITUDE_MIN", 400.0),
        altitude_max=_env_float("SEED_ALTITUDE_MAX", 600.0),
        velocity_min=_env_float("SEED_VELOCITY_MIN", 7.0),
        velocity_max=_env_float("SEED_VELOCITY_MAX", 8.0),
        status_healthy_pct=_env_float("SEED_STATUS_HEALTHY_PCT", 70.0),
        status_warning_pct=_env_float("SEED_STATUS_WARNING_PCT", 20.0),
        status_critical_pct=_env_float("SEED_STATUS_CRITICAL_PCT", 10.0),
        random_seed=_env_optional_int("SEED_RANDOM_SEED", 42),
    )
    config.validate()
    return config


def _load_cors_origins() -> tuple[str, ...]:
    """
    Local Vite origins are always allowed. CORS_ORIGINS adds more
    (comma-separated), typically the production frontend domain.
    """
    raw = os.getenv("CORS_ORIGINS", "").strip()
    extra = tuple(part.strip() for part in raw.split(",") if part.strip())
    merged: list[str] = list(_DEFAULT_CORS_ORIGINS)
    for origin in extra:
        if origin not in merged:
            merged.append(origin)
    return tuple(merged)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(seed=_load_seed_config(), cors_origins=_load_cors_origins())
