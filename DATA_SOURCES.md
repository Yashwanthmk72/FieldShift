# Data sources
Machine-readable: `backend/app/data/sources.json` (served at `/api/v1/sources` with live provider status). Licence/terms summaries must be reviewed before commercial use; last review: none (not performed).

| Source | Used for | Type | Status |
|---|---|---|---|
| NASA POWER | 14-day daily weather, monthly climatology | observed / climatology, ~0.5° | parsers tested on fixtures; **live call not verified** |
| ISRIC SoilGrids 2.0 | pH, SOC, clay, sand, silt (0–30 cm) | modelled, 250 m | same |
| Open-Meteo | forecast, ET0, hourly humidity | forecast | same |
| OpenStreetMap Nominatim | place search (1 req/s throttle) | observed | same |
| Wikimedia Commons | crop images, licence shown per file | n/a | same |
| FAO-56 (Allen et al. 1998) | Kc, stage lengths | reference | values fetched 2026-11-14 from fao.org tables 11/12 |

## Crop parameters (`backend/app/data/crops.json`, 11 crops)
Sourced: `kc` 9/11, `stage_fraction` 9/11. Heuristic (no source): `temp`, `rain`, `ph`, `water`, `resilience`, `soil`, `fixer` for all 11, plus `kc`/`stage_fraction` for the 2 flagged crops. The loader rejects a crop with missing provenance, or a "sourced" parameter without a URL. Confidence labels in the data are `sourced`/`heuristic` only; no `high/medium/low` grading has been done.
