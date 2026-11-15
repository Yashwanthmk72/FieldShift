# FieldShift v0.9.0
Decision support for climate-aware crop planning, built for the **NASA Space Apps Challenge 2026**. A planning aid: **not** an agronomic guarantee, yield forecast or financial advice. Rule-based scoring only; no ML model ships.

## Challenge
**Field Shift: Adapting Farms with NASA Data**.

## What it does
- **Field studio**: outline your land on a globe/map; FieldShift pulls NASA POWER climate and ISRIC SoilGrids soil for it.
- **Crop advisor**: ranks **27 crops** with a visible **confidence level** and an **"Illustrative estimate"** badge wherever crop ranges are heuristic.
- **Risks & downsides** on every crop: climate, pest/disease, price volatility, water demand, soil depletion, and what could make the advice wrong.
- **Climate tab**: NASA POWER daily temperature, rainfall and solar radiation against long-term normals, with date-range selector, anomaly shading and auto-refresh.
- **Market prices**: ticker + charts, world view and country selector, currency/unit converter, **Estimated gross value** (revenue, never profit). Every price shows source, as-of date and a cadence badge (daily/monthly). Nothing is real-time; no source means "no data", never an estimate.
- **How accurate is this?** and **Data sources & credits** pages (credits are generated from `backend/app/data/sources.md`).
- Rotation planning, land-management tips, irrigation/pest/finance engines (backend).

## NASA and partner data
NASA **POWER** (daily + climatology) is the NASA data used. Other data: ISRIC SoilGrids, Open-Meteo, IMF commodity prices via FRED, Agmarknet (data.gov.in, optional key), ECB rates via Frankfurter. No NASA logos or branding are used; NASA does not endorse this project. Full list: `backend/app/data/sources.md`.

## AI tools used
AI assistants helped write the code, tests, content and documents (headers in source files say so). Illustrations in the app are drawn by code and carry a visible **"AI-assisted illustration"** mark. Any AI-generated image or video added later must carry a visible watermark. No images of people under 18 are included.

## Run
```
pip install -r requirements.txt
uvicorn backend.main:app          # or: uvicorn app.main:app --app-dir backend
```
Open http://localhost:8000 (the backend serves the frontend). **Check everything works:** `python scripts/smoke.py` (or `python scripts/smoke.py https://your-app.onrender.com`) hits every endpoint and prints PASS/WARN/FAIL; WARN means an upstream data source was unreachable. Tests: `pip install -r requirements-dev.txt && ./run_tests.sh`. Deploy as one Docker service: **DEPLOY.md**.

## Read these
VERIFICATION.md (what was actually run, and what was not) · KNOWN_LIMITATIONS.md · PROGRESS.md · DEMO.md · SUBMISSION.md · DATA_SOURCES.md · SECURITY.md · API.md
