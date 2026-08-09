# Satellite Telemetry — Project Overview

Two complementary apps (both on their `main` branches):

| Project | Repository | Role |
|---------|------------|------|
| **Backend** | [aimshab/rocketlab-telemetry-backend](https://github.com/aimshab/rocketlab-telemetry-backend) | FastAPI REST API + in-memory SQLite |
| **Frontend** | [aimshab/rocketlab-telemetry-frontend](https://github.com/aimshab/rocketlab-telemetry-frontend) | React dashboard; mock API or live backend via config |

Together they support viewing, filtering, creating, and deleting satellite telemetry
(Satellite ID, Timestamp, Altitude, Velocity, Health Status).

For full setup notes, API details, architecture, and examples, see each repository’s
`README.md` on `main`:

- [Backend README](https://github.com/aimshab/rocketlab-telemetry-backend/blob/main/README.md)
- [Frontend README](https://github.com/aimshab/rocketlab-telemetry-frontend/blob/main/README.md)

### Live deployments

| App | URL |
|-----|-----|
| **Web app** | https://rocketlab-telemetry-frontend.vercel.app/ |
| **Backend API** | https://rocketlab-telemetry-backend.vercel.app/ |

---

## Main approach

### Backend

Repo: [rocketlab-telemetry-backend](https://github.com/aimshab/rocketlab-telemetry-backend) (`main`)

- **FastAPI + Pydantic** for routing and request/response validation.
- **In-memory SQLite** (`mode=memory&cache=shared`) as the only store — data lives for the
  process lifetime and resets on restart.
- **Store interface** (`TelemetryStore`) with a SQLite implementation; each operation opens
  its own connection and closes it when done (plus a keep-alive connection so the shared
  in-memory DB is not wiped).
- **Filters** compile to SQL `WHERE` clauses; list pagination uses `LIMIT` / `OFFSET` and
  fetches `limit + 1` rows to set `hasMore` without a full `COUNT`.
- **Configurable seeding** via `TelemetrySeedGenerator` and `SEED_*` env vars (satellite
  count, entry count, time/altitude/velocity ranges, status mix).

### Frontend

Repo: [rocketlab-telemetry-frontend](https://github.com/aimshab/rocketlab-telemetry-frontend) (`main`)

- **React 18 + TypeScript + Vite**, plain CSS, Vitest + React Testing Library.
- **Configurable API target** — by configuration only (`VITE_API_MODE`), the app can either
  use a built-in **mock API** (no backend required) or **connect to the real telemetry
  service** (the backend repo). No code changes are needed to switch; an API facade
  (`telemetryApi.ts`) re-exports the active client with the same function signatures.
- **Simulate backend outage** — in the header (dev only), a toggle forces API calls to fail
  client-side so error/retry UI can be exercised. Shown only when `import.meta.env.DEV` is
  true; hidden in production builds.
- **Dev proxy** in Vite forwards `/telemetry` and `/health` to the backend so the browser
  avoids CORS (backend does not send CORS headers).
- **Server-side filtering** (satellite ID / status); **client-side sorting** on the loaded
  page set. The real client walks `hasMore` pages to aggregate results for the table.
- State lives in a single `useTelemetry` hook (`useState` / `useMemo`), not Redux.

---

## Main assumptions

1. **Ephemeral storage** — backend data is in-memory only; restart clears everything.
2. **Pagination is always on** — `GET /telemetry` defaults to `page=1`, `limit=10`; there is
   no “return all rows” API. Response includes `items`, `page`, `limit`, `hasMore` (no total
   count / page count).
3. **Status is an enum on the API** — `critical` | `warning` | `healthy` (invalid → `422`).
4. **Validation** — ISO 8601 timestamps; altitude and velocity must be `> 0`; non-empty
   `satelliteId`.
5. **Frontend ↔ backend contract** — same CRUD paths; real mode expects backend on port
   **3000** (or `VITE_API_PROXY_TARGET` / `VITE_API_BASE_URL`).
6. **CORS** — in local real mode, the UI talks to Vite (port **5173**) and the proxy reaches
   the API; production direct calls need CORS or a same-origin setup.
7. **Mock mode** — frontend can run fully without the backend (`VITE_API_MODE=mock`).

---

## How to run

### Backend

```bash
git clone https://github.com/aimshab/rocketlab-telemetry-backend.git
cd rocketlab-telemetry-backend
git checkout main

python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements-dev.txt

# Optional: copy .env.example → .env and tune SEED_*
uvicorn app.main:app --reload --port 3000
```

- API: http://localhost:3000  
- Docs: http://localhost:3000/docs  

Docker (from the cloned backend repo):

```bash
docker compose up --build
```

### Frontend

Requires Node.js 18+.

```bash
git clone https://github.com/aimshab/rocketlab-telemetry-frontend.git
cd rocketlab-telemetry-frontend
git checkout main

npm install

# Real API (default) — start the backend on :3000 first
npm run dev

# Or mock API (no backend)
# PowerShell:  $env:VITE_API_MODE="mock"; npm run dev
# bash/zsh:    VITE_API_MODE=mock npm run dev
```

UI: http://localhost:5173 (typical Vite URL).

---

## How to test

### Backend

From the [backend](https://github.com/aimshab/rocketlab-telemetry-backend) repo (`main`):

```bash
pip install -r requirements-dev.txt
pytest -v
```

Covers endpoints, filters, seed generator, store concurrency, and config.

### Frontend

From the [frontend](https://github.com/aimshab/rocketlab-telemetry-frontend) repo (`main`):

```bash
npm run test          # once
npm run test:watch    # watch mode
npm run lint
npm run build         # type-check + production build
```

Tests stub `fetch` / use the mock client — no running backend or network required.
Coverage includes API clients (pagination, filters, errors), `useTelemetry`, form timestamp
helpers, components, and an App-level flow (load → filter → add → delete → simulated outage).

---

## Quick end-to-end (real mode)

1. Clone and start the [backend](https://github.com/aimshab/rocketlab-telemetry-backend) on port 3000 (`main`).  
2. Clone and start the [frontend](https://github.com/aimshab/rocketlab-telemetry-frontend) with default `VITE_API_MODE` (real) (`main`).  
3. Open the Vite URL; table should load seeded telemetry via the proxy.  
4. Filter, sort, add, and delete entries against the live API.

For UI-only work, use `VITE_API_MODE=mock` and skip the backend.
