# Project Submission form (draft)
Project details are filled in. Review every claim against VERIFICATION.md before submitting.

**Challenge:** Field Shift: Adapting Farms with NASA Data
**Project name:** FieldShift

**Team:** Project Earthwise
**Team members:** Yashwanth M K (Team Owner), Suhas V, Sindu Gowda, Sidhant Saswat, Sohan Malode, Trisha Shashanna
**Local event:** Harohalli, India

**High-level summary (short):** FieldShift helps farmers explore climate-aware crop choices. You outline a field and it uses NASA POWER climate data and SoilGrids soil estimates to rank 27 crops, with a visible confidence level, a risks-and-downsides panel, climate charts against long-term normals, and real published market prices where a source exists.

**Detailed description**
*What it does:* Field outline -> analysis -> ranked crops, rotation and land-management advice; Climate tab (NASA POWER daily vs normals with anomalies); Market page (IMF world benchmark prices monthly, India mandi prices daily when a free key is configured, ECB exchange rates, unit/currency conversion, estimated gross value that is never profit); pages explaining accuracy limits and data credits.
*How it works:* Python FastAPI backend with a rule-based scoring engine (no ML), vanilla JS frontend, provider adapters with timeouts, retries, circuit breakers and caching; per-provider health at /api/health.
*Benefits:* Makes data limits visible (confidence, "illustrative estimate", "no data") instead of hiding them; helps compare options and ask better questions of local extension services.
*Goals:* A transparent starting point for climate-aware planning that points users to local soil tests and expert advice.
*Tools used:* Python, FastAPI, httpx, SQLite, MapLibre GL JS, vanilla JavaScript/SVG charts, Docker. AI assistants helped write code, tests and content; illustrations are marked "AI-assisted".

**NASA data used:** NASA POWER (daily T2M, PRECTOTCORR, ALLSKY_SFC_SW_DWN and long-term monthly climatology, AG community).
**Space-agency partner data:** None.
**Other data:** ISRIC SoilGrids 2.0; Open-Meteo; IMF Primary Commodity Prices via FRED; Agmarknet via data.gov.in (optional); ECB rates via Frankfurter; OpenStreetMap/Esri; Wikimedia Commons.

**Honest limitations to state if asked:** climate is a ~50 km cell and lags days; soil is modelled; all crop ranges are heuristic; nothing is real-time; price adapters and NASA/SoilGrids calls were not run live during development (see VERIFICATION.md).
