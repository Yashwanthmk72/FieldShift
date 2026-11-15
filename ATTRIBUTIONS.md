# Attributions

## Photos
FieldShift does not bundle photographs. When online it looks up freely-licensed images on **Wikimedia Commons** at runtime (`/api/crop-info`, `/api/media`) and displays the author and licence on the image or in the "Photo credits" list. Each image links to its Commons file page. When no photo is available, built-in SVG illustrations (original to this project) are shown.

## Data and map services
- NASA POWER (daily + climatology): https://power.larc.nasa.gov/
- ISRIC SoilGrids 2.0: https://rest.isric.org/soilgrids/v2.0/docs
- Esri World Imagery and World Boundaries & Places (labels): © Esri and contributors; check Esri's terms for your use
- OpenStreetMap tiles and Nominatim geocoding: © OpenStreetMap contributors (ODbL); Nominatim usage policy applies (max 1 request/second)
- Terrain tiles: Mapzen / AWS Terrain Tiles
- MapLibre GL JS (BSD-3-Clause), Google Fonts (Figtree, Fraunces, Manrope; OFL)

## Agronomy content
Crop sowing windows, growth stages, pests and tips in `backend/content.py` are general guidance written for this project from widely published extension-style knowledge (FAO crop guides, ECHO, university extension fact sheets). They are not region-specific advice; verify locally.
