# API (v0.9.0) — OpenAPI is served at `/docs` once the app runs (live server not verified here)
Legacy (unchanged paths): `GET /api/health, /api/crops, /api/climate, /api/soil`, `POST /api/recommendations, /api/rotation, /api/analyze, /api/assistant`, `GET/POST/PUT/DELETE /api/farms[/id]`, `GET/PUT /api/settings`, `GET /api/crop-info/{id}, /api/media`.
New: `/healthz`, `/readyz`, `GET /api/v1/{crops,sources,weather,pests,geocode}`, `POST /api/v1/{analysis,recommendations,irrigation,assistant}`, `/api/v1/fields`, `/api/v1/finance/{evaluate,plans,export.csv,export.pdf}`, `/api/v1/auth/{register,login,refresh,logout,me,export}`, `DELETE /api/v1/auth/account`.
Identity: `Authorization: Bearer <access token>` or, for guest demo mode, `X-Workspace-ID: <uuid>`. A bad bearer token is 401 (never downgraded to guest).
Every provider-backed response carries `provenance[]` = `{name, ok, source, kind (observed|climatology|forecast|modelled), fetched_at, coverage, error}`. Recommendation items add `score_meaning`, `confidence`, `top_reasons`, `limiting_factors`, `risk_flags`, `heuristic_params`, and `components.profit` (null when unavailable).

## v0.7 additions (never run against a live FastAPI server)
`GET /api/health` (per-provider status, `degraded`), `GET /readyz` · `GET /api/v1/market/{meta,board,series,fx,stream}` · `POST /api/v1/market/gross-value` · `GET /api/v1/climate/series?lat&lon&start&end` · `GET /api/v1/credits` · `POST /api/v1/risks`

## v0.8 addition (never run against a live FastAPI server)
`GET /api/v1/soil-health?lat&lon[&crop_id][&area_ha]` -> `{available, summary, limitations[{factor,level,detail,action}], actions, water_holding, crop_ph, sampling, not_available, disclaimer, provenance}`; when soil data is unavailable: `{available:false, error, sampling, not_available, provenance}`.

## v0.9 additions
No API changes are recorded for v0.9; this release updates layout and media lookup behavior.
