# PROJECT_SPEC — Weather-Aware Truck Routing (canonical)

> **This is the single source of truth** for product requirements, business rules, contracts, and decisions.
> Other documents (README, AGENTS.md, code comments) must link here rather than restate rules.
> Labels used below: **[REQ]** = assessment requirement · **[DEC]** = implementation decision · **[LIM]** = known limitation.

---

## 1. Objective and deliverables

**[REQ]** A React + Django web app helping a truck driver compare routes and pick the safest option given weather, cargo load weight, and travel time. The app must:

1. Accept origin, destination, departure date/time, and load weight (lb).
2. Request **three distinct route options** from a routing API, where available.
3. Sample weather along route geometry at configurable intervals of **10, 25, or 50 miles**.
4. Estimate truck arrival time at each checkpoint and use the forecast for that time.
5. Classify checkpoint risk using the thresholds and load rules in §5.
6. Recommend the best eligible route using the ranking in §6.
7. Show route alternatives, checkpoints, ETAs, risk categories and summaries on an interactive map.
8. Show a weather-risk heatmap along the corridor with an interactive **0–48 h forecast slider**.

Third-party routing, geocoding and weather APIs are allowed; no routing engine from scratch.

**[REQ] Deliverables:** GitHub repository, hosted application, 5–10 min Loom walkthrough.
**[REQ] Weights:** 40% routing/weather/risk/recommendation · 35% UI/map/heatmap · 10% code quality · 5% docs/walkthrough. Prioritise correctness and clarity over extras.
**[REQ] Budget:** 16 engineering hours total.

## 2. Technology stack [DEC]

| Layer | Choice |
|---|---|
| Frontend | React 19 + TypeScript, Vite, Tailwind CSS v4, Leaflet + React Leaflet, OSM tiles, Vitest + React Testing Library, ESLint + Prettier |
| Backend | Python 3.12, Django 5.2 LTS, Django REST Framework, httpx, django-cors-headers, pytest + pytest-django, respx (httpx mocking), Ruff |
| Cache | Django `LocMemCache` (configurable). No Redis unless a demonstrated need arises. |
| Infra | No database models, no auth, no Docker, no Redis, no paid infra. SQLite only because Django requires a DB setting. |

Exact versions are pinned in `backend/requirements*.txt` and `frontend/package-lock.json`.

## 3. External providers [DEC]

All providers sit behind interfaces (`apps/routing/providers/base.py`, `apps/weather/providers/base.py`) so business logic never depends on provider JSON.

### 3.1 Routing — Google Routes API (`routes.googleapis.com/directions/v2:computeRoutes`)
- Request: `travelMode: DRIVE`, `routingPreference: TRAFFIC_AWARE` (when departure is in the future), `computeAlternativeRoutes: true`, `departureTime` (RFC 3339 UTC), `polylineEncoding: ENCODED_POLYLINE`, `units: IMPERIAL`. Origin/destination sent as `address` strings or `location.latLng`.
- Field mask (`X-Goog-FieldMask`): `routes.distanceMeters,routes.duration,routes.staticDuration,routes.polyline.encodedPolyline,routes.routeLabels,routes.description,routes.legs.steps.distanceMeters,routes.legs.steps.staticDuration,routes.legs.steps.polyline.encodedPolyline`.
- Key read from `GOOGLE_ROUTES_API_KEY`, sent as `X-Goog-Api-Key` **from the backend only**.
- Normalise into internal `Route` model (§7). **Never fabricate or duplicate** routes; dedupe by identical polyline. If < 3 unique routes, return what exists plus a warning `FEWER_THAN_THREE_ROUTES`.
- Unit tests mock HTTP (respx); no live calls in CI.

### 3.2 Weather — Open-Meteo Forecast API (`https://api.open-meteo.com/v1/forecast`)
- Request hourly `wind_speed_10m,rain,snowfall`, `wind_speed_unit=mph`, `precipitation_unit=inch`, `timezone=UTC`, `forecast_days` covering departure + 48 h offset + trip duration (max 16). Multiple coordinates batched in one request (comma-separated lat/lon lists).
- **Unit semantics (verified against Open-Meteo docs; re-verify on integration):**
  - `wind_speed_10m`: mean wind speed at 10 m for the hour; with `wind_speed_unit=mph` returned in mph.
  - `rain`: preceding-hour sum (accumulation over the hour ending at the timestamp). With `precipitation_unit=inch` → inches; a 1-hour sum equals in/hr.
  - `snowfall`: preceding-hour sum; cm by default, inches when `precipitation_unit=inch`. Because this is easy to get wrong, the adapter MUST read `hourly_units` from each response and convert explicitly (`cm→in ÷2.54`, `mm→in ÷25.4`, `km/h→mph ÷1.609344`, `m/s→mph ×2.236936`, `kn→mph ×1.150779`). Unknown units ⇒ forecast marked unavailable.
- Timestamp matching: since values are preceding-hour sums, a checkpoint ETA `t` uses the hourly record whose timestamp is `ceil_to_hour(t)` (the hour that contains `t`). ETA exactly on the hour uses that hour's record.
- Cache responses in Django cache keyed by rounded coordinates (3 dp) + date range; TTL `WEATHER_CACHE_TTL_SECONDS`.
- **Missing/expired/out-of-horizon data ⇒ `forecast_available=false`, risk `Unknown`. Never substitute Low.**
- UI must show "Weather data by Open-Meteo.com" attribution.

### 3.3 Map
- React Leaflet, tile URL and attribution from `VITE_MAP_TILE_URL` / `VITE_MAP_ATTRIBUTION` (default OSM, attribution required).
- Risk-coloured route segments, checkpoint markers with detail popups, a corridor weather-intensity overlay (heat layer or risk-coloured circles), legend.
- Map components consume normalised API data only; no backend/provider coupling.

**[LIM] Truck legality:** The assessment provides cargo weight only, not truck dimensions/GVW. Route geometry comes from the routing provider's DRIVE mode; we **do not claim** routes satisfy truck restrictions. The truck-specific safety adjustment is weather/load risk.

## 4. Risk categories [DEC]

Ordinal: `Low=0`, `Moderate=1`, `High=2`, `Severe=3`, `No Travel=4` (used only for worst-of comparison), `Unknown` (no ordinal; excluded from averages, counted separately).

## 5. Exact risk rules [REQ]

Inputs are real numbers. Intervals are half-open as written; "≤" applies only where stated.

### 5.1 Wind (mph)
| Condition | Category |
|---|---|
| w < 25 | Low |
| 25 ≤ w < 35 | Moderate |
| 35 ≤ w < 45 | High |
| 45 ≤ w < 55 | Severe |
| w ≥ 55 | No Travel |

### 5.2 Rain rate (in/hr)
| Condition | Category |
|---|---|
| r < 0.10 | Low |
| 0.10 ≤ r < 0.25 | Moderate |
| 0.25 ≤ r < 0.50 | High |
| 0.50 ≤ r ≤ 1.00 | Severe |
| r > 1.00 | No Travel |

### 5.3 Snowfall rate (in/hr)
| Condition | Category |
|---|---|
| s < 0.5 | Low |
| 0.5 ≤ s < 1.0 | Moderate |
| 1.0 ≤ s < 2.0 | High |
| 2.0 ≤ s ≤ 3.0 | Severe |
| s > 3.0 | No Travel |

**Boundary conventions:** rain 0.25 → High; rain 1.00 → Severe; snow 1.0 → High; snow 2.0 → Severe; snow 3.0 → Severe; wind 55 → No Travel.

### 5.4 Load-dependent wind overrides (load L in lb)
- w ≥ 55 → **No Travel** for every load.
- 45 ≤ w < 55 **and L > 30,000** → **No Travel**.
- 35 ≤ w < 45 **and L > 40,000** → **Severe**.
- Strict: L = 30,000 and L = 40,000 do **not** trigger.

### 5.5 Checkpoint overall risk
Classify wind (with overrides), rain, snow separately; overall = worst. If any measurement is missing ⇒ overall `Unknown` (do not compute a partial best-case). Every High/Severe/No Travel result carries a human-readable reason, e.g. `"Wind 47.0 mph with 35,000 lb load > 30,000 lb → No Travel"`.

## 6. Recommendation rules

**[REQ] Lexicographic ranking** (no weighted score):
1. Fewest Severe miles.
2. Fewest High miles.
3. Lowest average risk.
4. Shortest travel time.

**[DEC] Average risk** = distance-weighted mean of ordinal (Low 0 … Severe 3) over intervals with known risk. Unknown intervals excluded from the mean and reported as `unknown_miles`.

**[DEC] Interval allocation (midpoint rule):** checkpoints at distances `d_0=0 < d_1 < … < d_n = total`. Checkpoint *i* represents `[ (d_{i-1}+d_i)/2 , (d_i+d_{i+1})/2 ]`, with the first starting at 0 and the last ending at `total`. Represented distances therefore sum exactly to the route distance (tolerance: ≤ 0.01 mi floating error).

**[DEC] Safety eligibility:**
- Any checkpoint with **No Travel** ⇒ route **ineligible**; shown as unsafe with reason.
- If all routes ineligible ⇒ status `NO_SAFE_ROUTE`; nothing recommended.
- Routes with any Unknown interval may still be ranked but are flagged `weather_incomplete`; the UI must not claim they are verified safe. **[DEC]** Ties broken by fewer `unknown_miles` before travel time is **not** applied (keeps assessment order); incompleteness is shown as a warning.
- Recommendation response includes the basis (the metric values compared and which criterion decided).

Recommendation status values: `RECOMMENDED`, `NO_SAFE_ROUTE`, `NO_ROUTES`.

## 7. Checkpoint geometry and ETA [REQ/DEC]

- Decode polylines (Google encoded polyline, precision 5). Distances via haversine (earth radius 3958.7613 mi).
- **Never select by vertex index.** Checkpoints placed at cumulative distance 0, N, 2N, … and the destination, where N ∈ {10,25,50}, with linear interpolation between vertices.
- ETA: build a cumulative (distance, duration) profile from step `distanceMeters`/`staticDuration` when present; interpolate the checkpoint's time within it. Fallback: `eta = departure + total_duration × (d / total_distance)` (distance-proportional). Step durations are scaled so their sum equals the route `duration` (traffic-aware).
- Each checkpoint includes: `lat`, `lon`, `distance_miles`, `interval_start_miles`, `interval_end_miles`, `represented_miles`, `eta` (ISO-8601 UTC), `weather {wind_mph, rain_in_per_hr, snow_in_per_hr, forecast_time}`, `forecast_available`, `risk {wind, rain, snow, overall}`, `reasons[]`.

## 8. Forecast slider [DEC]

- Slider value `forecast_offset_hours ∈ [0,48]` (integer) means **shifted-departure scenario**: departure' = departure + offset; all ETAs recomputed and weather re-sampled.
- Updates checkpoints, intervals, eligibility, heat overlay, metrics and recommendation consistently.
- UI labels "Departure shifted +X h (scenario)".
- Debounce slider (≈400 ms) and rely on backend weather cache; route geometry is not re-requested when only offset changes (backend caches route responses by request key).
- Beyond the forecast horizon ⇒ Unknown, never Low.

## 9. API contract [DEC]

Base: `/api/`. Errors: `{"error": {"code": str, "message": str, "details"?: object}}`.

### `GET /api/health/` → 200
```json
{"status": "ok", "service": "truck-routing-api", "version": "v1", "providers": {"routing_configured": true, "weather_base_url": "https://api.open-meteo.com/v1/forecast"}}
```
(Reports only whether the key is configured — never the key.)

### `POST /api/v1/route-analysis/`
Request:
```json
{
  "origin": "Chicago, IL",
  "destination": "Denver, CO",
  "departure_time": "2026-10-11T08:00:00-05:00",
  "load_weight_lbs": 35000,
  "checkpoint_interval_miles": 25,
  "forecast_offset_hours": 0
}
```
Validation: origin/destination non-empty ≤ 200 chars and not equal; `departure_time` ISO-8601 **with UTC offset** (naive rejected); `load_weight_lbs` number, 0 < L ≤ 200,000; interval ∈ {10,25,50}; offset integer 0–48.

Response 200:
```json
{
  "request": { "...echoed normalised request; departure_time in UTC..." },
  "effective_departure_time": "ISO UTC",
  "routes": [{
    "id": "route-0", "label": "DEFAULT_ROUTE", "description": "I-80 W",
    "distance_miles": 1003.2, "duration_seconds": 52000,
    "polyline": [[lat, lon], "..."],
    "checkpoints": ["…§7"],
    "segments": [{"start_miles": 0, "end_miles": 12.5, "risk": "Low", "coordinates": [[lat,lon], "..."]}],
    "metrics": {"severe_miles": 0, "high_miles": 0, "moderate_miles": 0, "low_miles": 0, "unknown_miles": 0, "average_risk": 0.0, "duration_seconds": 0},
    "eligible": true, "weather_incomplete": false, "unsafe_reasons": []
  }],
  "recommendation": {"status": "RECOMMENDED", "route_id": "route-0", "deciding_criterion": "severe_miles", "explanation": "…"},
  "warnings": [{"code": "FEWER_THAN_THREE_ROUTES", "message": "…"}],
  "attribution": {"routing": "Google Routes API", "weather": "Open-Meteo.com"}
}
```

Error codes: `VALIDATION_ERROR` (400), `ROUTING_NOT_CONFIGURED` (503), `NO_ROUTES_FOUND` (404/200 with NO_ROUTES), `UPSTREAM_ERROR` (502), `UPSTREAM_RATE_LIMITED` (429), `UPSTREAM_TIMEOUT` (504), `NOT_IMPLEMENTED` (501, stage-1 placeholder). Forecast gaps are per-checkpoint (`forecast_available=false`) plus warning `FORECAST_INCOMPLETE`, not a request failure.

Credentials never appear in responses or logs (httpx logging of headers disabled; errors sanitised).

## 10. Architecture [DEC]

```
frontend (Vite/React) ──HTTPS JSON──> backend (Django/DRF)
                                        ├─ apps/api       views, serializers, error mapping
                                        ├─ apps/routing   provider iface, Google adapter, polyline, checkpoints, ETA
                                        ├─ apps/weather   provider iface, Open-Meteo adapter, units, time match, cache
                                        └─ apps/risk      pure classification, metrics, recommendation
```
`apps/risk` is pure Python (no Django/HTTP). Orchestration lives in `apps/api/services.py`.

## 11. Security [REQ/DEC]
- `GOOGLE_ROUTES_API_KEY` backend-only; never prefixed `VITE_`; never in fixtures, logs, screenshots, CI.
- `.env*` gitignored (except `.env.example` placeholders).
- Production: `DEBUG=false`, `SECRET_KEY` required, `ALLOWED_HOSTS`/`CORS_ALLOWED_ORIGINS` from env, `SECURE_PROXY_SSL_HEADER`, secure cookies, HSTS.
- Input validation on all fields; request-size limits by Django defaults.
- **Environment variables:** backend-secret: `DJANGO_SECRET_KEY`, `GOOGLE_ROUTES_API_KEY`. Backend config: `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `OPEN_METEO_BASE_URL`, `WEATHER_CACHE_TTL_SECONDS`, `PROVIDER_TIMEOUT_SECONDS`. Frontend-public: `VITE_API_BASE_URL`, `VITE_MAP_TILE_URL`, `VITE_MAP_ATTRIBUTION`.

## 12. Functional acceptance criteria
1. Form validates and submits all six inputs; invalid input shows field errors.
2. Up to three distinct real routes shown; notice when fewer.
3. Checkpoints spaced by cumulative distance at selected interval; represented miles reconcile to route distance ±0.01 mi.
4. Each checkpoint shows ETA, wind/rain/snow in assessment units, per-condition and overall risk, reason.
5. Risk classification matches §5 exactly at all boundaries including load overrides.
6. Recommendation follows §6 order; No Travel routes never recommended; NO_SAFE_ROUTE shown when applicable.
7. Map shows risk-coloured routes, markers, popups, legend (incl. Unknown), corridor overlay, attributions.
8. Slider 0–48 h re-evaluates everything consistently, labelled as shifted departure; no Low fabrication beyond horizon.
9. Loading, empty, error, and unavailable-forecast states visible.
10. No secrets in repo or browser bundle.

## 13. Test plan
- **Backend (pytest):** settings check; health; request validation; risk boundaries (every threshold + overrides + strict load); worst-of; ranking order per criterion; No Travel ineligible; all-unsafe; checkpoint spacing/interpolation; interval reconciliation; ETA profile & fallback; polyline decode; Google normalisation + errors (mocked); Open-Meteo unit normalisation & time matching (mocked).
- **Frontend (Vitest/RTL):** app shell renders empty state; form validation; legend; API client error handling; later: route cards & recommendation display.
- **CI:** GitHub Actions — ruff, `manage.py check`, pytest; `tsc`, eslint, vitest, vite build.

## 14. Demo (Loom 5–10 min)
Problem & stack → enter trip → three routes & recommendation basis → checkpoint popups → slider scenario changing risk → unsafe/No Travel case → code tour of risk engine & tests → limitations.

## 15. Deployment plan
- Frontend: Vercel (root `frontend/`, build `npm run build`, output `dist`, env `VITE_API_BASE_URL`).
- Backend: Render web service (root `backend/`, build `pip install -r requirements.txt`, start `gunicorn config.wsgi`, health `/api/health/`, env vars per §11).
- Not deployed during initialization.

## 16. Limitations [LIM]
- No truck-dimension/restriction routing (see §3.3).
- Open-Meteo forecasts are model output at ~1–11 km grid; hourly granularity.
- Free Open-Meteo is for non-commercial use; rate limits apply.
- Google Routes may return fewer than 3 alternatives (no fabrication).
- Traffic-aware durations are estimates; ETA errors grow with trip length.
- In-memory cache is per-process.

## 17. Milestones
1. **Init (done in stage 1):** spec, scaffolds, risk engine, geometry utils, provider skeletons, health endpoint, contract, UI shell, CI.
2. Google Routes adapter live integration + route normalisation.
3. Open-Meteo adapter + unit/time matching + caching.
4. Orchestration service → `/api/v1/route-analysis/` full response.
5. Map: routes, segments, markers, popups, legend, overlay.
6. Route cards, recommendation basis, slider wiring.
7. Polish, deploy, README, Loom.

## 18. Decision log
- 2026-10-10: Midpoint interval allocation; Unknown excluded from average; No Travel ⇒ ineligible; slider = shifted departure; Open-Meteo hour matching uses ceil-to-hour due to preceding-hour sums.
- 2026-10-10: No Travel intervals are excluded from `average_risk` (ordinal mapping defined only Low–Severe) and reported as `no_travel_miles`; such routes are ineligible regardless. Metrics object therefore also includes `no_travel_miles`.
- 2026-10-10: Initial corridor overlay = translucent risk-coloured circles per checkpoint (no extra dependency); may switch to `leaflet.heat` in milestone 5.
- 2026-10-10: Stage-1 `/api/v1/route-analysis/` validates input, returns 503 if the key is missing, otherwise 501 `NOT_IMPLEMENTED` — no fake analyses.
