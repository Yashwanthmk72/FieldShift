# Architecture (v0.6.0)
```
backend/app/
  main.py        app factory, middleware (request id, size limit, security headers), routers
  config.py      env settings, fail-fast validation
  api/           FastAPI routers + Pydantic schemas (thin; unverified here)
  services.py    providers -> engine orchestration (framework-free, tested with fake providers)
  engine/        PURE functions: scoring, crops loader, rotation, geo, soil, finance, irrigation, pest_risk, units, content
  providers/     base (cache, breaker, retrying fetch), parsers (pure), clients, media
  core/          security, ratelimit, logging, errors
  db/            migrations.py (versioned up/down), repo.py (owner-filtered queries)
  assistant.py   BM25 retrieval, prompt hygiene, JSON validation, templated fallback
  data/          crops.json, sources.json, pests.json, kb/*.md
frontend/        ES modules: main.js, lib/ (state, api, html, scoring, storage...), views/*.js
tests/           pytest (backend), node tests, Chromium tests against a stand-in server
```
Compatibility: all v0.4 `/api/*` routes remain; new contracts live under `/api/v1`. `uvicorn backend.main:app` still works via a shim. Ownership: `owner` string on every row (`u:<id>` accounts, `g:<uuid>` guests). The v0.4 database upgrades in place (migration 2 maps `workspace_id` → `g:<uuid>`).
