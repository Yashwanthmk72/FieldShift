# Known limitations (v0.9.0)

## v0.9 release-specific gaps
- The layout and Wikimedia lookup changes are in the code, but no v0.9-specific regression run is recorded yet.
- Live Wikimedia fetching, NASA/SoilGrids/market provider calls, a production deployment and real screenshots remain unverified. Screenshots in `docs/screenshots/` use fixture data from the stand-in server and must not be presented as live results.

## v0.8 additions and remaining gaps
- **New screens were verified only against the stand-in server** (`tests/frontend/mock_api.py`, fixture data), not the real FastAPI app and not live providers.
- Soil-health thresholds (pH 5.5/8.0, organic carbon 10 g/kg, sand >70 %, clay >40 %, sampling cores) are general rules of thumb, labelled `heuristic`. The crop pH range used for "crop fit" is itself heuristic for most crops.
- "Upcoming tasks" is built only from forecast alerts, land-management advice and the top crop's risk flags. It is not a calendar and has no due dates.
- "Crop suitability" counts crops by rule-based score. It is not field or plant health and uses no satellite imagery.
- Finance and Irrigation numbers are the user's inputs or labelled assumptions. Saved plans need the backend (no browser-only fallback).
- Still not done from the plan: floating assistant, Data status page, guest-to-account claim, sample mode, NASA GIBS layer, deployment and real screenshots from a live deploy.


## Done in v0.7 versus not done
**Done (code written and tested with mocks/fixtures; see VERIFICATION.md):** 27 crops (was 11); per-crop citation URLs and `sources.md`; visible confidence + "Illustrative estimate" badges; Risks & downsides panel; honest `/api/health` (per-provider, degraded state) and `/readyz`; provider retries/circuit-breaker tests; Market page (IMF/FRED monthly, Agmarknet daily with key, ECB FX, unit/currency conversion, SSE + polling fallback, "Estimated gross value"); Climate tab (NASA POWER daily vs normals, anomaly shading, auto-refresh); Accuracy and Credits pages; single-Docker deploy files; AI-use disclosures and "AI-assisted illustration" marks.
**Not done / unverified:**
- **No provider was called live** (NASA POWER, SoilGrids, FRED, data.gov.in, Frankfurter): the build sandbox had no network. Parsers use hand-written fixtures from documented formats, not recordings. Real responses may differ.
- **The FastAPI app was never started** and real `pytest` never ran (could not be installed). Tests ran under an offline stand-in (`scripts/minipytest.py`) plus Chromium against a stand-in server.
- **All crop temp/rain/pH/water values are still heuristic.** The 16 new crops' Kc/stage values are recalled from FAO-56, not re-verified. Citations say where to verify; they do not mean the values were verified.
- **Not built:** FAO GIEWS FPMA (no endpoint verified), World Bank Pink Sheet (xlsx, unstable URL), USDA AMS/NASS, delayed futures (no key). Nothing is real-time, and no "live" badge can appear.
- Agmarknet commodity names are unverified; the API returns only recent dates so history is short. Country prices exist only for India (with key); other countries show "no data".
- Sugar price is shown for sugarcane as a labelled proxy (raw sugar, not cane).
- Perennials (banana, sugarcane) are excluded from rotation plans. Price-volatility thresholds and pest-pressure/heavy-feeder lists are editorial judgements.
- ECB rates cover ~30 currencies; others stay in original currency.
- Free hosting sleeps and loses SQLite data (DEPLOY.md).
- Illustrations are code-drawn fallbacks, not photos for new crops until Wikimedia lookups succeed.


## Not implemented in v0.6 (deferred to later releases, not silently dropped)
- **Organizations, roles, invitations, sharing; password change/recovery; email verification; session listing.** Only register/login/logout/refresh/me/export/delete exist.
- **Argon2id:** passwords use stdlib **scrypt** (n=2^14, r=8, p=1) because `argon2-cffi` could not be installed. Swap in when installable.
- **SQLAlchemy 2 / Alembic / PostgreSQL / Redis:** the DB layer is SQLite with a small versioned migration runner (up/down tested, including upgrade of a populated v0.4 database). The `postgres` service in docker-compose is a placeholder (profile `future`). Production rate limiting uses a shared SQL counter, which is shared across workers on one DB but is not Redis.
- **Profit-priority scoring in the UI.** It remains disabled unless a costed finance plan supplies margins; passing arbitrary profit weights without margin data is not supported.
- Country/region pickers, metric/imperial toggle beyond ha/ac and °C/°F, currency conversion, `.ics` export, i18n (Hindi/Kannada), PWA/offline sync, tasks/notifications, GIS vertex editing/split/merge/NDVI, React/TypeScript migration.
- ML: the v0.4 trainer was removed (random split leaked spatially; one-day features vs seasonal labels). **No model ships and none is shown in the UI.** A blocked-CV pipeline needs a licensed dataset (GAEZ/EcoCrop).
- Image-based pest diagnosis: not built (no licensed dataset/evaluation).
- Crop count is 27 in v0.7, but the 16 added crops are fully heuristic.

## Scientific-data caveats
- **Heuristic:** all temperature, rainfall and pH ranges, water class, resilience score, soil text and N-fixer flag (66 of the crop parameters) are v0.4 heuristics, labelled `heuristic` in `crops.json` and in API responses (`heuristic_params`).
- **Sourced (FAO-56, fetched 2026-11-14):** Kc mid/end and growth-stage fractions for 9 crops. Cowpea and chickpea stage lengths use a *dry-bean proxy row*; potato and sunflower Kc-ini group values were recalled from memory and are marked heuristic. Kc ini for most crops is the FAO group value, not a per-crop printed value. Where FAO prints a range, the midpoint is used.
- Assumptions in irrigation (root depth 0.6 m, depletion 0.5, efficiencies, 80% effective rain above 2 mm) and finance (±20% yield, ±25% price, ±10% cost) are editable assumptions, not sourced.
- The Smith-period blight rule is cited from memory of the literature and was not re-verified; other pest rules are heuristics. `pests.json` and the assistant knowledge base are v0.4 text, status "unreviewed".
- No yields or costs are bundled; the user must enter them. Market prices are fetched from sources at runtime, never bundled or estimated.
- Licence statements in `sources.json` are summaries to verify before commercial use.

## Security caveats
- Registration returns 409 for an existing email (account enumeration possible).
- CSRF for cookie endpoints uses a custom header + Origin allow-list (the double-submit helper in `core/security.py` is unused).
- Guest mode (`X-Workspace-ID`) is a browser-held random id: it is **not** secure isolation.
- Cache and token-budget for the assistant are per process unless the SQL limiter is used.
