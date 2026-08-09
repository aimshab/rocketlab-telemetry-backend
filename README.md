# Satellite Telemetry API

REST API for viewing, filtering, and managing satellite telemetry data.
Built with **Python + FastAPI** and an in-memory SQLite store.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

pip install -r requirements-dev.txt

# Optional: copy .env.example to .env and tune SEED_*
uvicorn app.main:app --reload --port 3000
```

### Startup seed

On boot, `TelemetrySeedGenerator` builds sample entries from `SEED_*` settings
(see `.env.example`). Set `SEED_ENABLED=false` to skip.

| Variable | Default | Description |
|----------|---------|-------------|
| `SEED_ENABLED` | `true` | Whether to seed on startup |
| `SEED_SATELLITE_COUNT` | `3` | Distinct `SAT-NNN` IDs to draw from |
| `SEED_ENTRY_COUNT` | `3` | Number of entries to create |
| `SEED_TIME_START` / `SEED_TIME_END` | `2026-08-06`… / `2026-08-07`… | Timestamp range (ISO 8601) |
| `SEED_ALTITUDE_MIN` / `MAX` | `400` / `600` | Altitude range |
| `SEED_VELOCITY_MIN` / `MAX` | `7.0` / `8.0` | Velocity range |
| `SEED_STATUS_HEALTHY_PCT` | `70` | Share of `healthy` (must sum to 100 with the other two) |
| `SEED_STATUS_WARNING_PCT` | `20` | Share of `warning` |
| `SEED_STATUS_CRITICAL_PCT` | `10` | Share of `critical` |
| `SEED_RANDOM_SEED` | `42` | RNG seed (`none` for non-deterministic) |

API: `http://localhost:3000`  
Interactive docs: `http://localhost:3000/docs`

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/telemetry` | List entries (filters + pagination) |
| `POST` | `/telemetry` | Create a new telemetry entry |
| `GET` | `/telemetry/:id` | Get one entry by ID |
| `DELETE` | `/telemetry/:id` | Delete one entry by ID |
| `GET` | `/health` | Health check |

### Query parameters (`GET /telemetry`)

| Param | Default | Description |
|-------|---------|-------------|
| `satelliteId` | — | Filter by satellite ID |
| `status` | — | Filter by health status |
| `page` | `1` | Page number (1-based, min 1) |
| `limit` | `10` | Page size (1–100) |

Response shape:

```json
{
  "items": [ /* Telemetry[] */ ],
  "page": 1,
  "limit": 10,
  "hasMore": false
}
```

Filtering and pagination share one pass: scanning stops once the page is
filled (with a one-item peek to set `hasMore`). Exact `total` / `pages` are
not returned, since that would require filtering the full dataset.

### Examples

List (page 1, 2 per page):

```bash
curl "http://localhost:3000/telemetry?page=1&limit=2"
```

Filter:

```bash
curl "http://localhost:3000/telemetry?satelliteId=SAT-001&status=critical"
```

Create:

```bash
curl -X POST http://localhost:3000/telemetry ^
  -H "Content-Type: application/json" ^
  -d "{\"satelliteId\":\"SAT-003\",\"timestamp\":\"2026-08-06T12:00:00.000Z\",\"altitude\":500,\"velocity\":7.5,\"status\":\"healthy\"}"
```

Get / delete by ID:

```bash
curl http://localhost:3000/telemetry/<id>
curl -X DELETE http://localhost:3000/telemetry/<id>
```

## Validation (POST)

- `timestamp` — valid ISO 8601 datetime
- `altitude`, `velocity` — positive numbers (`> 0`)
- `satelliteId` — non-empty string
- `status` — one of `critical`, `warning`, `healthy`

Invalid payloads return `422` with field-level error details (FastAPI/Pydantic).

## Tests

```bash
pip install -r requirements-dev.txt
pytest -v
```

## Docker

```bash
docker compose up --build
```

Or without Compose:

```bash
docker build -t satellite-telemetry-api .
docker run --rm -p 3000:3000 satellite-telemetry-api
```

## Architecture

```
app/
  main.py              # FastAPI app, lifespan seed
  config.py            # Startup settings (SEED_*)
  models.py            # Pydantic request/response schemas
  seed/
    generator.py       # TelemetrySeedGenerator + SeedConfig
  store/
    base.py            # TelemetryStore interface
    sqlite_store.py    # In-memory SQLite backend
  filters/             # Chainable filters (Python + SQL clauses)
  routes/telemetry.py  # Endpoint handlers
tests/
  conftest.py          # Shared fixtures
  test_telemetry.py    # Endpoint unit tests
Dockerfile
docker-compose.yml
```

Data persists for the process lifetime and resets on restart. Filters compile
to SQL `WHERE` clauses and pagination uses `LIMIT`/`OFFSET` (`limit+1` for
`hasMore`). Seed entries are generated from `SEED_*` config on startup
(defaults: 3 entries across 3 satellites).
