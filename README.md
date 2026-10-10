# StormRoute Dispatch — Weather-Aware Truck Routing

Compare up to three driving routes and recommend the safest one based on forecast weather along the route, cargo load weight, and travel time.

> **Canonical specification:** [`docs/PROJECT_SPEC.md`](docs/PROJECT_SPEC.md) — all requirements, risk thresholds, ranking rules, API contract and decisions live there. AI agents: see [`AGENTS.md`](AGENTS.md).

**Status:** Stage 2 complete (orchestration backend). End-to-end route analysis (`POST /api/v1/route-analysis/`) is implemented and verified with Google Routes, Open-Meteo, distance checkpoints, risk evaluation, and lexicographic ranking. Frontend UI shell is connected; interactive map visualization will be finalized in Stage 3. Not deployed.

## Stack
- **Frontend:** React 19 + TypeScript, Vite, Tailwind CSS v4, React Leaflet (OSM tiles), Vitest + RTL, ESLint + Prettier
- **Backend:** Python 3.12, Django 5.2 + DRF, httpx, pytest + pytest-django + respx, Ruff
- **Providers:** Google Routes API (routing), Open-Meteo (weather)

## Quickstart

```powershell
# 1. Environment (backend secrets stay in the repo-root .env, never committed)
copy .env.example .env          # then set GOOGLE_ROUTES_API_KEY and DJANGO_DEBUG=true for local dev

# 2. Backend (Python 3.12; `uv venv --python 3.12 backend/.venv` also works)
cd backend
py -3.12 -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\python manage.py runserver 8000     # http://localhost:8000/api/health/

# 3. Frontend (new terminal)
cd frontend
npm ci
npm run dev                                        # http://localhost:5173
```
macOS/Linux: use `.venv/bin/...` or the [`Makefile`](Makefile) (`make setup`, `make backend`, `make frontend`).

## Environment variables
| Variable | Scope | Purpose |
|---|---|---|
| `DJANGO_SECRET_KEY` | backend **secret** | Required when `DJANGO_DEBUG=false` |
| `GOOGLE_ROUTES_API_KEY` | backend **secret** | Google Routes API key (never `VITE_`-prefixed) |
| `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS` | backend config | Comma-separated lists |
| `OPEN_METEO_BASE_URL`, `WEATHER_CACHE_TTL_SECONDS`, `PROVIDER_TIMEOUT_SECONDS` | backend config | Provider settings |
| `VITE_API_BASE_URL`, `VITE_MAP_TILE_URL`, `VITE_MAP_ATTRIBUTION` | frontend **public** | Put in `frontend/.env.local`; bundled into JS |

## Tests & checks
```powershell
cd backend;  .venv\Scripts\ruff check . ; .venv\Scripts\ruff format --check . ; .venv\Scripts\python manage.py check ; .venv\Scripts\pytest
cd frontend; npm run typecheck ; npm run lint ; npm run format:check ; npm test ; npm run build
```
Unit tests never call real providers (HTTP is mocked with respx). CI: [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

## Repository structure
```
backend/
  config/            settings, urls, wsgi/asgi
  apps/api/          versioned views, serializers, structured errors
  apps/routing/      provider interface, Google Routes adapter, polyline, checkpoints, ETA
  apps/weather/      provider interface, Open-Meteo adapter, units, forecast-hour matching, cache
  apps/risk/         pure risk classification, metrics, lexicographic recommendation
  tests/
frontend/
  src/api/           typed client + response models
  src/components/    form, map, legend, route cards, checkpoint details, slider, status
  src/test/
docs/PROJECT_SPEC.md canonical spec
```

## Deployment (planned, see spec §15)
Frontend → Vercel (`frontend/`), backend → Render (`gunicorn config.wsgi`, health check `/api/health/`).
