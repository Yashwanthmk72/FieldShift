# Changelog

## 0.9.0
- Layout: consistent vertical spacing for view bodies, cards, grids, panels and key-value tiles; improved topbar spacing, two-column stretch and single-column mobile layout.
- Photos: Wikimedia lookups use a descriptive User-Agent (`FIELDSHIFT_CONTACT`), at most four concurrent requests, plain-search fallback, short failure cache and tolerant circuit breaker. Failed browser lookups are not cached for the session; queued requests retry once.
- Version strings updated to 0.9.
- Verification status: live Wikimedia fetching, full v0.9 regression checks, container build and deployment remain pending; see `VERIFICATION.md` and `PROGRESS.md`.

## 0.8.0 (Phase 0 + Phase 1 of the NASA-readiness plan)
- Added field screens for existing Weather, Irrigation, Soil health, Pests & disease and Finance engines; added Overview dashboard cards and the `GET /api/v1/soil-health` endpoint.
- Added shared view helpers, skeleton/empty/error states and print styles.
- Added 16 engine/service tests and 2 Chromium tests.
- Scoring, crop data and providers were not changed in this release.

## 0.7.0
- Added 27 crops, citations and `sources.md`, confidence and illustrative badges, Risks & downsides, per-provider health, the Market page, Climate tab, Accuracy and Credits pages, single-Docker deploy files and AI-use disclosures.
- See `KNOWN_LIMITATIONS.md` for unverified integrations and heuristic data.

## 0.6.0 — Verified Core (2026-11-14)
- Split `main.py` into `backend/app/` packages; separated pure engines from I/O and kept v0.4 routes.
- Fixed profit-priority handling, trusted-proxy processing, per-user rate limits, request-size caps and server-recomputed assistant facts.
- Removed the unsound ML trainer; documented rule-based scoring only.
- Added `crops.json` with per-parameter provenance and validation, plus FAO-56 Kc and stage fractions.
- Added escape-by-default HTML helpers and frontend ES modules.
- Added account and repository primitives, migrations, resilient providers, finance/irrigation/soil-water/pest-risk engines, grounded assistant, CSV/PDF export, Docker, Compose and CI configuration.
- See `KNOWN_LIMITATIONS.md` for deferred and unverified work.
