/* AI-assisted: written with an AI coding assistant (see README, "AI tools used"). */
/* Field studio: MapLibre globe, drawing, place labels and "where am I" readout.
   Drawing / selection / analysis flow is unchanged from v0.3; v0.4 adds labels, a place chip, coordinate entry and a scale bar. */
import { html, raw, setHtml, insertHtml } from "../lib/html.js";
import { FS, $, S, toast, fmtArea, fmtTemp, areaHa, centroid, polyGeo, ringPts, bounds, ic } from "../lib/state.js";
import { api } from "../lib/api.js";

  let map = null, markers = [], spinning = false, terrain = false, labelsOn = S.settings.labels !== false;
  const SAT = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";
  const LABELS = "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}";

  function spin() { if (!spinning || !map || map.getZoom() > 3.5 || S.draft.drawing || S.view !== "studio") return; const c = map.getCenter(); map.easeTo({ center: [c.lng - 25, c.lat], duration: 12000, easing: (t) => t }); }
  const stopSpin = () => { spinning = false; };

  function initMap() {
    if (map) return;
    if (!window.maplibregl) { setHtml($("map"), html`<p style="padding:24px;color:#fff">Map library could not load. Check your connection.</p>`); return; }
    map = new maplibregl.Map({ container: "map", center: [20, 18], zoom: 1.5, maxPitch: 75, attributionControl: { compact: true }, style: { version: 8, projection: { type: "globe" },
      sources: {
        sat: { type: "raster", tiles: [SAT], tileSize: 256, maxzoom: 19, attribution: "Imagery © Esri, Maxar, Earthstar Geographics" },
        osm: { type: "raster", tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"], tileSize: 256, maxzoom: 19, attribution: "© OpenStreetMap contributors" },
        labels: { type: "raster", tiles: [LABELS], tileSize: 256, maxzoom: 19, attribution: "Labels © Esri" },
        dem: { type: "raster-dem", tiles: ["https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"], encoding: "terrarium", tileSize: 256, maxzoom: 14, attribution: "Terrain: Mapzen / AWS" } },
      layers: [{ id: "sat", type: "raster", source: "sat" }, { id: "osm", type: "raster", source: "osm", layout: { visibility: "none" } }, { id: "labels", type: "raster", source: "labels" }] } });
    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "bottom-right");
    map.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");
    map.on("load", () => {
      const empty = { type: "geojson", data: { type: "FeatureCollection", features: [] } };
      ["fields", "draft", "samples"].forEach((id) => map.addSource(id, empty));
      map.addLayer({ id: "fields-fill", type: "fill", source: "fields", paint: { "fill-color": "#7bd389", "fill-opacity": 0.22 } });
      map.addLayer({ id: "fields-line", type: "line", source: "fields", paint: { "line-color": "#d5eca9", "line-width": 2 } });
      map.addLayer({ id: "draft-fill", type: "fill", source: "draft", filter: ["==", ["geometry-type"], "Polygon"], paint: { "fill-color": "#ffd166", "fill-opacity": 0.28 } });
      map.addLayer({ id: "draft-line", type: "line", source: "draft", filter: ["!=", ["geometry-type"], "Point"], paint: { "line-color": "#ffd166", "line-width": 2.5 } });
      map.addLayer({ id: "draft-pts", type: "circle", source: "draft", filter: ["==", ["geometry-type"], "Point"], paint: { "circle-radius": 5, "circle-color": "#fff", "circle-stroke-color": "#e09f1f", "circle-stroke-width": 2 } });
      map.addLayer({ id: "samples", type: "circle", source: "samples", paint: { "circle-radius": 6, "circle-color": "#3ee0a0", "circle-stroke-color": "#06281a", "circle-stroke-width": 2 } });
      setBaseLayer(S.settings.map_style); setLabels(labelsOn);
      if (!S.settings.start_globe) { $("globeBtn").classList.remove("on"); $("globeBtn").setAttribute("aria-pressed", "false"); map.setProjection({ type: "mercator" }); }
      drawSaved();
      const a = FS.active(); if (a?.geometry) flyToField(a); else if (S.settings.start_globe) { spinning = true; setTimeout(spin, 600); }
      updatePlace();
    });
    ["mousedown", "touchstart", "wheel"].forEach((ev) => map.on(ev, stopSpin));
    map.on("moveend", () => { if (spinning) spin(); schedulePlace(); });
    map.on("move", paintCoords);
    map.on("click", (e) => { if (!S.draft.drawing) return; S.draft.pts.push([+e.lngLat.lng.toFixed(6), +e.lngLat.lat.toFixed(6)]); drawDraft(); });
  }
  function studioShown() { initMap(); setTimeout(() => map && map.resize(), 60); }

  /* ----- base layer + labels ----- */
  function setBaseLayer(style) {
    if (!map || !map.getLayer("sat")) return;
    map.setLayoutProperty("sat", "visibility", style === "streets" ? "none" : "visible"); map.setLayoutProperty("osm", "visibility", style === "streets" ? "visible" : "none");
    document.querySelectorAll("[data-style]").forEach((b) => b.classList.toggle("on", b.dataset.style === style)); applyLabelVisibility();
  }
  function applyLabelVisibility() { // OSM tiles already carry names, so the extra label layer is only for satellite imagery
    if (!map || !map.getLayer("labels")) return; const streets = document.querySelector('[data-style="streets"]')?.classList.contains("on");
    map.setLayoutProperty("labels", "visibility", labelsOn && !streets ? "visible" : "none");
  }
  function setLabels(on) { labelsOn = !!on; const b = $("labelsBtn"); b.classList.toggle("on", labelsOn); b.setAttribute("aria-pressed", String(labelsOn)); applyLabelVisibility(); }

  /* ----- "where am I": reverse geocode the map centre (town · state · country), debounced and cached ----- */
  const placeCache = new Map(); let placeTimer = null, lastReq = 0, placeCtl = null;
  const flag = (cc) => cc && cc.length === 2 ? String.fromCodePoint(...[...cc.toUpperCase()].map((c) => 127397 + c.charCodeAt(0))) : "";
  const nomZoom = (z) => z < 4 ? 3 : z < 6 ? 5 : z < 8 ? 8 : z < 11 ? 10 : z < 14 ? 12 : 14;
  function paintCoords() {
    if (!map) return; const c = map.getCenter(), z = map.getZoom();
    $("placeSub").textContent = `${Math.abs(c.lat).toFixed(3)}°${c.lat >= 0 ? "N" : "S"}  ${Math.abs(c.lng).toFixed(3)}°${c.lng >= 0 ? "E" : "W"} · zoom ${z.toFixed(1)}`;
  }
  const schedulePlace = () => { clearTimeout(placeTimer); placeTimer = setTimeout(updatePlace, 900); };
  async function updatePlace() {
    if (!map) return; paintCoords(); const c = map.getCenter(), z = map.getZoom(), nz = nomZoom(z), key = `${nz}:${c.lat.toFixed(2)}:${c.lng.toFixed(2)}`;
    if (placeCache.has(key)) return showPlace(placeCache.get(key));
    const wait = Math.max(0, 1100 - (Date.now() - lastReq)); // Nominatim usage policy: max 1 request per second
    await new Promise((r) => setTimeout(r, wait)); if (map.getCenter().lat.toFixed(2) !== c.lat.toFixed(2)) return; // moved again – skip stale lookup
    placeCtl?.abort(); placeCtl = new AbortController(); lastReq = Date.now();
    try {
      const r = await fetch(`https://nominatim.openstreetmap.org/reverse?format=jsonv2&zoom=${nz}&accept-language=en&lat=${c.lat}&lon=${c.lng}`, { signal: placeCtl.signal });
      const j = await r.json(); const ad = j.address || {};
      const town = ad.city || ad.town || ad.village || ad.hamlet || ad.suburb || ad.municipality || "";
      const region = ad.state_district || ad.county || "", state = ad.state || ad.region || "";
      const parts = [town, nz >= 8 ? region : "", state, ad.country].filter((p, i, a) => p && a.indexOf(p) === i);
      const out = j.error ? { text: "Open ocean / unmapped area" } : { text: parts.join(" · ") || j.display_name || "Unknown place", cc: ad.country_code };
      placeCache.set(key, out); showPlace(out);
    } catch (e) { if (e.name !== "AbortError") $("placeMain").textContent = "Place name unavailable – labels on the map still show names"; }
  }
  function showPlace(p) { $("placeMain").textContent = `${flag(p.cc)} ${p.text}`.trim(); }

  /* ----- drawing (unchanged logic) ----- */
  function drawDraft() {
    const p = S.draft.pts, d = S.draft, fs = [];
    if (p.length >= 3 && d.geometry) fs.push({ type: "Feature", geometry: d.geometry, properties: {} });
    if (p.length >= 2) fs.push({ type: "Feature", geometry: { type: "LineString", coordinates: d.geometry ? [...p, p[0]] : p }, properties: {} });
    p.forEach((c) => fs.push({ type: "Feature", geometry: { type: "Point", coordinates: c }, properties: {} }));
    map.getSource("draft").setData({ type: "FeatureCollection", features: fs });
    $("finishBtn").disabled = !d.drawing || p.length < 3; $("undoBtn").disabled = !d.drawing || !p.length;
    $("areaReadout").textContent = d.geometry ? `Selected · ${fmtArea(d.area)} · ${p.length} corners` : p.length ? `Drawing… ${p.length} corner${p.length > 1 ? "s" : ""}${p.length >= 3 ? " · ≈ " + fmtArea(areaHa(p)) : ""}` : "No area selected yet";
    $("analyzeBtn").disabled = !d.geometry;
  }
  function startDraw() { if (!map) return; clearDraft(true); S.draft.drawing = true; map.getCanvas().style.cursor = "crosshair"; map.doubleClickZoom.disable(); $("drawHint").textContent = "Click the map to add corners (at least 3), then press Finish. Undo removes the last corner."; drawDraft(); }
  function finishDraw() {
    const d = S.draft; if (d.pts.length < 3) return; d.drawing = false; d.geometry = polyGeo(d.pts); d.area = areaHa(d.pts); map.getCanvas().style.cursor = ""; map.doubleClickZoom.enable();
    $("drawHint").textContent = "Area selected. Name it and press Analyze. Use Clear to start over."; drawDraft();
  }
  function clearDraft(keepMode) {
    S.draft = { pts: [], drawing: false, geometry: null, area: 0, analysis: null, saved: null }; $("analysisBox").hidden = true;
    if (map?.getSource("draft")) { map.getSource("samples").setData({ type: "FeatureCollection", features: [] }); drawDraft(); map.getCanvas().style.cursor = ""; map.doubleClickZoom.enable(); }
    if (!keepMode) $("drawHint").textContent = "Press “Start drawing”, then click the map to place each corner of your field.";
  }
  function useGeometry(g, name) {
    const pts = ringPts(g); clearDraft(true); S.draft.pts = pts; S.draft.geometry = polyGeo(pts); S.draft.area = areaHa(pts); if (name && !$("fieldName").value) $("fieldName").value = name; drawDraft(); map.fitBounds(bounds(pts), { padding: 70, maxZoom: 18 });
  }
  async function analyzeDraft() {
    const d = S.draft; if (!d.geometry) return; const btn = $("analyzeBtn"); btn.disabled = true; btn.classList.add("busy"); btn.lastChild.textContent = " Analyzing…";
    try {
      const a = await api("/analyze", { method: "POST", body: JSON.stringify({ geometry: d.geometry, priorities: S.settings.priorities, seasons: S.settings.seasons }) });
      d.analysis = a; map.getSource("samples").setData({ type: "FeatureCollection", features: a.samples.map((s) => ({ type: "Feature", geometry: { type: "Point", coordinates: [s.lon, s.lat] }, properties: {} })) }); renderAnalysisBox(); S.online = true; FS.setStatus();
    } catch { toast("Analysis needs the backend. Start it with: uvicorn backend.main:app"); S.online = false; FS.setStatus(); }
    btn.disabled = false; btn.classList.remove("busy"); btn.lastChild.textContent = " Analyze this area";
  }
  function renderAnalysisBox() {
    const a = S.draft.analysis, c = a.climate?.latest || {}, t = c.temperature_c?.value, box = $("analysisBox"); box.hidden = false;
    setHtml(box, html`<div class="panel-kicker">ANALYSIS · COVERED AREA</div><h3>${fmtArea(a.area_ha)} analyzed</h3><div class="kv"><div><small>TEMPERATURE</small><b>${t != null ? fmtTemp(t) : "—"}</b></div><div><small>RAIN · 14D</small><b>${a.climate?.rainfall_14d_mm ?? "—"}<small> mm</small></b></div><div><small>SOIL</small><b style="font-size:15px">${a.soil.texture || "—"}</b></div><div><small>SOIL pH</small><b>${a.soil.ph ?? "—"}</b></div></div><div class="panel-kicker" style="margin-top:6px">TOP CROPS</div>${a.ranked.slice(0, 3).map((r) => html`<div class="mini-crop"><span class="grow">${FS.pic("crop", r.crop.id, { family: r.crop.family, credit: false })}<span>${r.crop.name}</span></span><strong>${r.score}/100</strong></div>`)}<p class="note">Green dots on the map show where soil was sampled (${a.soil.samples_with_data}/${a.coverage.soil_sample_points} with data). ${a.coverage.note}</p><button class="button button-dark wide" id="saveDraft" data-ic="save">Save field${$("fieldName").value.trim() ? " “" + $("fieldName").value.trim() + "”" : ""}</button>`);
    $("saveDraft").onclick = saveDraft; FS.decorate(box); FS.hydrate(box);
  }
  async function saveDraft() {
    const d = S.draft, name = $("fieldName").value.trim(); if (!name) { $("fieldName").focus(); return toast("Give your field a name first"); }
    const c = centroid(d.pts), f = await FS.saveField({ name, geometry: d.geometry, latitude: d.analysis.centroid?.lat ?? c.lat, longitude: d.analysis.centroid?.lon ?? c.lon, area_ha: d.analysis.area_ha, priorities: S.settings.priorities, previous_crops: [], analysis: d.analysis, notes: "", done_actions: [] });
    insertHtml($("analysisBox"), "beforeend", html`<div class="row"><a class="button button-light button-compact" href="#field">Open field overview</a></div>`); $("saveDraft").disabled = true; $("saveDraft").textContent = "✓ Saved"; clearDraftKeepMap(); drawSaved(); return f;
  }
  function clearDraftKeepMap() { S.draft = { pts: [], drawing: false, geometry: null, area: 0, analysis: null }; map.getSource("draft").setData({ type: "FeatureCollection", features: [] }); $("analyzeBtn").disabled = true; $("areaReadout").textContent = "Saved. Draw another area to add more fields."; $("fieldName").value = ""; }
  function drawSaved() {
    if (!map?.getSource("fields")) return; markers.forEach((m) => m.remove()); markers = [];
    const feats = S.fields.filter((f) => f.geometry).map((f) => ({ type: "Feature", geometry: f.geometry, properties: { id: f.id } }));
    map.getSource("fields").setData({ type: "FeatureCollection", features: feats });
    S.fields.filter((f) => f.geometry).forEach((f) => { const el = document.createElement("button"); el.className = "fs-label"; el.textContent = f.name; el.onclick = () => { FS.setActive(f.id, true); location.hash = "#field"; }; markers.push(new maplibregl.Marker({ element: el }).setLngLat([f.longitude, f.latitude]).addTo(map)); });
  }
  function flyToField(f) { if (!map || !f.geometry) return; stopSpin(); map.fitBounds(bounds(ringPts(f.geometry)), { padding: 90, maxZoom: 17, duration: 3200, pitch: 0 }); }

  /* ----- search / locate / coordinates / upload ----- */
  async function searchPlace() {
    const q = $("placeSearch").value.trim(); if (!q || !map) return;
    try { const hits = await (await fetch(`https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&accept-language=en&q=${encodeURIComponent(q)}`)).json(); if (!hits.length) throw Error(); const h = hits[0]; stopSpin(); map.flyTo({ center: [+h.lon, +h.lat], zoom: 15, duration: 3600, essential: true }); if (!$("fieldName").value) $("fieldName").placeholder = h.name || q; }
    catch { toast("Place not found. Try a nearby town or landmark."); }
  }
  function goCoords() {
    const m = $("coordInput").value.match(/(-?\d+(?:\.\d+)?)\s*[,;\s]\s*(-?\d+(?:\.\d+)?)/); if (!m || !map) return toast("Enter coordinates like 12.97, 77.59");
    const lat = +m[1], lon = +m[2]; if (Math.abs(lat) > 90 || Math.abs(lon) > 180) return toast("Latitude must be −90…90 and longitude −180…180");
    stopSpin(); map.flyTo({ center: [lon, lat], zoom: 15, duration: 3000, essential: true });
  }
  $("searchBtn").onclick = searchPlace; $("placeSearch").onkeydown = (e) => { if (e.key === "Enter") searchPlace(); };
  $("coordBtn").onclick = goCoords; $("coordInput").onkeydown = (e) => { if (e.key === "Enter") goCoords(); };
  $("locateBtn").onclick = () => navigator.geolocation ? navigator.geolocation.getCurrentPosition((p) => { stopSpin(); map?.flyTo({ center: [p.coords.longitude, p.coords.latitude], zoom: 16, duration: 3400 }); }, () => toast("Allow location access or search for your farm")) : toast("Location is not available in this browser");
  $("uploadGeo").onclick = () => $("geoFile").click();
  $("geoFile").onchange = async (e) => { const file = e.target.files[0]; if (!file) return; try { const j = JSON.parse(await file.text()); const g = j.type === "FeatureCollection" ? j.features[0]?.geometry : j.type === "Feature" ? j.geometry : j; if (!g || !/Polygon/.test(g.type)) throw Error("Choose a Polygon GeoJSON boundary."); useGeometry(g, file.name.replace(/\.(geo)?json$/i, "")); finishDraw(); toast("Boundary imported"); } catch (err) { toast(err.message || "Could not read that file"); } e.target.value = ""; };
  $("drawBtn").onclick = startDraw; $("finishBtn").onclick = finishDraw; $("clearBtn").onclick = () => clearDraft(false);
  $("undoBtn").onclick = () => { S.draft.pts.pop(); drawDraft(); }; $("analyzeBtn").onclick = analyzeDraft;
  document.addEventListener("keydown", (e) => { if (S.view === "studio" && S.draft.drawing && e.key === "Enter" && !["INPUT", "BUTTON", "SELECT"].includes(document.activeElement.tagName)) finishDraw(); });
  document.querySelectorAll("[data-style]").forEach((b) => b.onclick = () => setBaseLayer(b.dataset.style));
  $("labelsBtn").onclick = () => { setLabels(!labelsOn); S.settings.labels = labelsOn; try { localStorage.setItem("fs-settings", JSON.stringify(S.settings)); } catch { /* storage unavailable */ } };
  $("globeBtn").onclick = () => { if (!map) return; const on = !$("globeBtn").classList.contains("on"); $("globeBtn").classList.toggle("on", on); $("globeBtn").setAttribute("aria-pressed", String(on)); if (!terrain) map.setProjection({ type: on ? "globe" : "mercator" }); };
  $("terrainBtn").onclick = () => { if (!map) return; terrain = !terrain; $("terrainBtn").classList.toggle("on", terrain); $("terrainBtn").setAttribute("aria-pressed", String(terrain)); if (terrain) { map.setProjection({ type: "mercator" }); map.setTerrain({ source: "dem", exaggeration: 1.5 }); map.easeTo({ pitch: 62, duration: 1200 }); } else { map.setTerrain(null); map.easeTo({ pitch: 0, duration: 800 }); map.setProjection({ type: $("globeBtn").classList.contains("on") ? "globe" : "mercator" }); } };
  $("worldBtn").onclick = () => { if (!map) return; map.flyTo({ center: [20, 18], zoom: 1.5, pitch: 0, duration: 3500 }); setTimeout(() => { spinning = true; }, 3600); };

  FS.decorate(document);
  FS.studio = { shown: studioShown, drawSaved, flyToField, setBaseLayer, setLabels };
  if (S.view === "studio") studioShown();
