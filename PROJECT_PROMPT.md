# FieldShift prompt for ChatGPT

Copy this prompt into ChatGPT when you want a second opinion or want help extending the project:

```text
I am building FieldShift, a green, farmer-friendly hackathon project for climate-resilient crop planning. Review the attached repository files before suggesting changes.

The v0.9 app has a responsive dashboard, a map with polygon/rectangle drawing and GeoJSON upload, NASA POWER daily climate data and climatology, ISRIC SoilGrids estimates, ranked crop cards with descriptions and images, rotation suggestions, land-management notes, guest field saving, a FastAPI backend, and a GitHub Pages workflow. Crop ranking is rule-based; no machine-learning model ships. Market-price adapters are connected in code for IMF commodity benchmarks via FRED and optional India mandi prices via Agmarknet/data.gov.in (API key required), with ECB exchange rates via Frankfurter. Price data is published at its source cadence and is not real-time; the live providers and adapters have not been verified in this build. This is a planning prototype, not an agronomic guarantee.

Important limits to preserve: NASA POWER is not an instantaneous field sensor; SoilGrids is a modelled estimate; polygons currently query their centroid; all crop ranges are heuristic; market coverage depends on the provider and configured key, prices are not real-time, and provider behavior has not been verified live in this build. No ML model ships. Do not claim the crop ranking is a trained model.

Please:
1. Explain what is already implemented and identify the highest-impact gaps.
2. Assess connected market-price sources and identify coverage gaps for the region I name: [ENTER REGION].
3. If considering a future ML model, propose how to train and validate crop suitability with public labeled data, including spatial leakage checks; do not imply a model currently ships.
4. Suggest small hackathon improvements that can be finished quickly.
5. Ask only the most important clarifying questions, and do not invent access keys, live data or model results.
```
