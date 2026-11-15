# FieldShift data sources and credits

Every dataset FieldShift shows is listed here. This file is the single source for the in-app "Data sources & credits" page. "Status" says what was and was not tested live. Licence lines are summaries: verify them before any commercial use.

## NASA POWER
- Group: Climate & soil
- Used for: Recent daily weather (temperature, rainfall, solar radiation), long-term monthly climate normals, the climate charts and the season-fit score.
- Provider: NASA Langley Research Center (LaRC) POWER Project, funded through the NASA Earth Science / Applied Science Program.
- URL: https://power.larc.nasa.gov/
- Resolution: about 0.5 degree grid cell (roughly 50 km). Daily values lag real time by a few days.
- Credit: These data were obtained from the NASA Langley Research Center POWER Project (wording recalled from the POWER documentation; check power.larc.nasa.gov for the current citation text).
- Status: Parser tested on hand-written fixtures. Live calls were not made during development of v0.7 (no network in the build sandbox).
FieldShift uses NASA data only through the public POWER API. NASA does not endorse FieldShift, and no NASA logos are used.

## ISRIC SoilGrids 2.0
- Group: Climate & soil
- Used for: Modelled topsoil pH, organic carbon, clay, sand and silt (0 to 30 cm weighted).
- Provider: ISRIC - World Soil Information.
- URL: https://soilgrids.org
- API: https://rest.isric.org/soilgrids/v2.0/docs
- Resolution: 250 m, machine-learning model output, not measurements. Gaps over water, ice and some built-up areas.
- Credit: Poggio et al. (2021), SoilGrids 2.0: producing soil information for the globe with quantified spatial uncertainty, SOIL 7, 217-240.
- Licence: CC BY 4.0 (summary; verify at soilgrids.org).
- Status: Parser tested on fixtures only; not called live in v0.7 development.

## Open-Meteo
- Group: Climate & soil
- Used for: Short-range forecast, evapotranspiration and pest-weather rules (not for the climate charts).
- URL: https://open-meteo.com/
- Licence: Open-Meteo data is offered under CC BY 4.0 (summary; verify). Attribution required.
- Status: Parser tested on fixtures only.

## FAO Irrigation and Drainage Paper 56 (Allen et al., 1998)
- Group: Crop science
- Used for: Crop coefficients (Kc) and growth-stage lengths. Verified for 9 original crops; the 16 crops added in v0.7 use values recalled from this paper and are marked heuristic.
- URL: https://www.fao.org/4/x0490e/x0490e0b.htm
- Status: Verified for 9 crops on 2026-11-14 (earlier release); NOT re-verified for the new crops.

## FAO EcoCrop
- Group: Crop science
- Used for: Reference only. Temperature, rainfall and pH ranges in crops.json are heuristic estimates; each carries this URL as the place to verify them. No EcoCrop value was copied.
- URL: https://ecocrop.apps.fao.org/ecocrop/srv/en/home
- Status: Not queried. All ranges remain heuristic until someone checks them.

## IMF Primary Commodity Prices (via FRED)
- Group: Prices & currency
- Used for: World benchmark prices on the Market page: wheat, maize, soybean, rice (Thailand), cotton and sugar (as a proxy for sugarcane, clearly labelled).
- Cadence: monthly (observation dated the 1st of the month; published about a month later). Never shown as live.
- Unit: US dollars per metric ton, or US cents per pound for cotton and sugar (converted for display).
- Provider: International Monetary Fund, distributed by the Federal Reserve Bank of St. Louis (FRED).
- URL: https://fred.stlouisfed.org/series/PWHEAMTUSDM
- Credit: Copyright International Monetary Fund. Terms at imf.org/external/terms.htm.
- Status: Series ids confirmed on FRED pages on 2026-11-14. The CSV adapter was tested on fixtures only, not called live in v0.7 development.

## Agmarknet daily mandi prices (data.gov.in)
- Group: Prices & currency
- Used for: India country view: daily wholesale (mandi) modal prices in INR per quintal.
- Cadence: daily. The API returns recent dates only, so history is short.
- Provider: Government of India, Open Government Data Platform, Agmarknet dataset (resource 9ef84268-d588-465a-a308-a864a43d0070).
- URL: https://data.gov.in/
- Licence: Government Open Data License - India (summary; verify).
- Status: Needs a free key (DATA_GOV_IN_API_KEY). Adapter tested on fixtures only; commodity names are unverified and may need adjusting.

## ECB reference exchange rates (via Frankfurter)
- Group: Prices & currency
- Used for: Currency conversion on the Market page. About 30 currencies; others show "no exchange rate" and stay in the original currency.
- Cadence: daily end-of-day reference rates; not a trading quote.
- URL: https://frankfurter.dev/
- Status: Adapter tested on fixtures only.

## OpenStreetMap, Nominatim and Esri World Imagery
- Group: Maps & media
- Used for: Map tiles, place search and satellite imagery in the Field studio.
- Credit: (c) OpenStreetMap contributors (ODbL); imagery (c) Esri and its data providers.
- URL: https://www.openstreetmap.org/copyright

## MapLibre GL JS
- Group: Maps & media
- Used for: Interactive globe and map rendering (BSD-3-Clause).
- URL: https://maplibre.org/

## Wikimedia Commons
- Group: Maps & media
- Used for: Crop photos, with author and licence shown on each image.
- URL: https://commons.wikimedia.org/

## FAO GIEWS FPMA (not integrated)
- Group: Not integrated
- Why: FPMA offers country food prices, but no machine-readable endpoint was verified, so no adapter was built. The Market page links to it instead.
- URL: https://fpma.fao.org/giews/fpmat4/#/dashboard/home

## World Bank Commodity Price Data - Pink Sheet (not integrated)
- Group: Not integrated
- Why: Published as an Excel file at a URL that changes. The IMF series on FRED covers the same commodities as clean CSV.

## USDA AMS and NASS (not integrated)
- Group: Not integrated
- Why: Needs an API key and report-specific parsing. Not built.

## Delayed futures (not integrated)
- Group: Not integrated
- Why: No free key was obtained, so no futures prices are shown. Nothing on the Market page is real-time.

## AI tools used
- Group: Project
- Used for: AI assistants helped write the code, tests, content and documents in this project. Generated illustrations carry a visible "AI-assisted illustration" mark. No NASA logos or branding are used. No images of people under 18 are included.
