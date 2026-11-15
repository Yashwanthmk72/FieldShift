# VERIFICATION — v0.9.0 release-preparation note (2026-11-15)
The v0.9 layout and Wikimedia lookup changes are listed in `CHANGELOG.md`. v0.9 regression checks were run directly in Windows PowerShell because Bash (`/bin/bash`) is unavailable, so `run_tests.sh` itself could not start. Results: `python -m pytest -q tests --ignore=tests/frontend` — 171 passed; `node --test tests/frontend/html.test.mjs` — 4 passed; `node --check` — all 35 frontend JavaScript files passed; `python -m pytest -q tests/frontend/test_browser.py` — 6 passed against the stand-in API. The HTML guard was made path-separator portable for Windows, and the mobile browser check exposed a narrow-screen overflow fixed by allowing the panel heading to wrap. These checks do not cover live providers, the production FastAPI app's HTTP layer, Docker, dependency audit or deployment; those remain unverified.

This supplied directory has no `.git` metadata, so commit history, working-tree changes and release tags cannot be verified or created here.

# VERIFICATION — v0.8.0 addendum (Phase 0 + 1, 2026-11-15 build session)
**Phase 0 result: could NOT be done.** The sandbox blocks outbound network (`curl` to NASA POWER and Frankfurter: proxy 403) and `pip` cannot fetch packages (`fastapi`, `httpx` still missing). So: uvicorn was never started, real provider responses were never compared with the parser fixtures, `scripts/smoke.py` was not run against a live server. **Do this first on a machine with network access** (see README "Run").
**Executed here:** baseline before changes: minipytest 155 passed; node html test 4 passed; Chromium 4 passed. After changes final `./run_tests.sh` exit code 0: real pytest 171 passed (tests that do not import FastAPI; the HTTP layer is still unrun), minipytest 171 passed, node html test 4 passed, Chromium 6 passed (4 old + 2 new; one old v0.7 test was flaky under load and was hardened to wait for text instead of the element).
**New tests:** `tests/test_v08_soil_health.py` (16: thresholds and boundaries, missing data never invented, sampling-core table, service with fake providers incl. unavailable soil) and two Chromium tests in `tests/frontend/test_browser.py` (all five new screens plus dashboard cards render with real content and no console errors; XSS probe in server strings does not execute; no horizontal scroll at 390 px on every new screen).
**Still unverified:** everything in the v0.7 addendum below, plus the new `/api/v1/soil-health` route under real FastAPI (the service function and the stand-in route are tested; the FastAPI decorator and `Query` validation are not).

# VERIFICATION — v0.7.0 addendum (2026-11-15 build session)
**Environment:** Python 3.12.3, Node 22, Playwright + Chromium. `pip install` failed (no network): `fastapi`, `httpx`, `pydantic`, `pytest` are NOT installed. `uvicorn` was never started.
**Executed:** offline stand-in test runner (155 passed); node html tests (4 passed); Chromium tests against `tests/frontend/mock_api.py` (4 passed); `compileall` of backend/tests/scripts; static import check of `routes_market.py` names.
**Web lookups (search tool) used to confirm sources:** FRED series ids PWHEAMTUSDM, PMAIZMTUSDM, PSOYBUSDM, PRICENPQUSDM, PCOTTINDUSDM, PSUGAISAUSDM exist (IMF series on FRED); data.gov.in mandi resource id and field names; Frankfurter `/v1/latest?base=USD` response shape. The CSV/JSON adapters themselves were not called.
**NOT executed / unverified:** FastAPI routes (`routes_market.py`, health, SSE `StreamingResponse`, Pydantic request models) never ran; real pytest; any live call to NASA POWER, SoilGrids, FRED, data.gov.in or Frankfurter; Docker build; render/fly deploy; CI. Crop parameter values are unverified heuristics.
**Bugs found while testing (fixed):** direct `innerHTML` use in new chart code violated the repo's XSS rule (caught by `html.test.mjs`); a wrong test expectation (data lag 4 vs 5 days). Three old assertions changed because the feature changed (27 crops, "high" confidence capped at medium).

# VERIFICATION — FieldShift v0.6.0 (Verified Core)

Evidence categories: **Verified** (executed here), **Mocked** (logic run against controlled responses), **Unverified** (code exists, not executed), **Not implemented**.

## Environment (2026-11-14)
Python 3.13.18, pytest 9.1.1, Node v22.23.4, Playwright (Python) + Chromium preinstalled. **Package installs were blocked**, so `fastapi`, `httpx`, `sqlalchemy`, `alembic`, `respx`, `argon2-cffi`, `pytest-cov`/`coverage` and `pip-audit` were NOT installed.

## Baseline (v0.4 as received)
`pytest -q` → collection error: `ModuleNotFoundError: No module named 'httpx'`. The original 21 tests cannot run against the real stack in this environment (a previous audit only ran them with stubbed FastAPI/httpx/pydantic). The v0.4 server was never started.

## Final results — `./run_tests.sh` (exit code 0)
| Step | Result | Category |
|---|---|---|
| `pytest -q tests --ignore=tests/frontend` | **107 passed**, 0 failed, 0 skipped | Verified (engine, DB, security primitives); provider/HTTP and services use fakes → **Mocked** |
| `node --check` on every `frontend/**/*.js` | no syntax errors | Verified |
| `node --test tests/frontend/html.test.mjs` | 4 passed (escape helper, no raw `innerHTML`) | Verified |
| `pytest tests/frontend/test_browser.py` (Chromium) | 3 passed: app loads with no console errors, profit control inert, XSS probe does not execute, mobile has no horizontal scroll | Verified against a **stand-in server** (`tests/frontend/mock_api.py`), not the real FastAPI app |
| Client/server scoring parity | 200 random inputs + .5 rounding edge, Python vs the real `frontend/lib/scoring.js` run in Node: identical | Verified |

Runner integrity: adding a deliberately failing test made `./run_tests.sh` exit 1; the test was then removed.
XSS test integrity: temporarily disabling escaping in `lib/html.js` made the XSS browser test fail; escaping was restored.

Bugs found by the tests while building (fixed in code, not by editing tests): log redaction leaked `sk-…` keys; Nominatim parser crashed on non-dict rows. Four test expectations of mine were wrong (hand-calculation errors) and were corrected after checking the engine was right.

## NOT verified (do these on a machine with network access)
1. **The FastAPI app was never started.** `backend/app/main.py`, `backend/app/api/*.py` (auth, fields, finance, analysis, assistant routes, CORS, security-header middleware, cookies) are *implemented but unverified*. Run: `pip install -r requirements-dev.txt && uvicorn app.main:app --app-dir backend` then `curl localhost:8000/api/health`.
2. No real provider (NASA POWER, SoilGrids, Open-Meteo, Nominatim, Wikimedia) was called; their parsers were tested on hand-written fixtures shaped like the documented responses. Real response shapes may differ.
3. HTTP-level authorization matrix, CSRF header check, CORS and rate-limit-through-HTTP were not run. Ownership isolation **is** verified at the repository layer (user A vs user B, guest vs user).
4. Coverage: **not measured** (no coverage tool). No percentage is claimed.
5. Docker image, docker-compose, GitHub Actions: written, **not run**. `pip-audit`: not run. Lighthouse/axe: not run.
6. Real map tiles/MapLibre CDN were blocked in the browser tests, so Field Studio drawing was not exercised.
