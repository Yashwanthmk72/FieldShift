/* AI-assisted: written with an AI coding assistant (see README, "AI tools used"). Overview dashboard cards (v0.8).
   Everything shown comes from the active field's saved analysis or from /api/v1/weather. "Crop suitability" is a rule-based fit of crops
   to the location. It is NOT a measure of field or plant health (no satellite imagery is used). */
import { html, setHtml } from "../lib/html.js";
import { $, S, active, fmtArea, fmtTemp, topCrop } from "../lib/state.js";
import { api } from "../lib/api.js";
import { drawChart } from "../lib/charts.js";
import { BANDS, bandOf, donut, legend, num } from "./common.js";

const PALETTE = ["#2f9e5b", "#9bc53d", "#e8a33b", "#3a8fd0", "#8a6fd0", "#d9534f"];
const isoOf = (d) => `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}`;

/* Upcoming tasks: only items that come from real outputs (management advice, forecast alerts, flagged risks). Nothing invented. */
export function buildTasks(a, weather) {
  const out = [];
  (weather?.alerts || []).forEach((w) => out.push({ t: w.type === "heat" ? "Heat in the forecast" : "Heavy rain in the forecast", s: w.text, p: "high" }));
  (a?.analysis?.management || []).filter((m) => m.priority === "high" || m.priority === "medium").forEach((m) => out.push({ t: m.title, s: "Land management", p: m.priority }));
  const best = topCrop(a);
  (best?.risk_flags || []).forEach((f) => out.push({ t: `${best.crop.name}: ${f}`, s: "Risk flag", p: "medium" }));
  const rank = { high: 0, medium: 1 };
  return out.sort((x, y) => (rank[x.p] ?? 2) - (rank[y.p] ?? 2)).slice(0, 5);
}

export function suitabilityCounts(ranked) {
  const c = [0, 0, 0, 0];
  (ranked || []).forEach((r) => { c[bandOf(r.score)]++; });
  return c;
}

export function cropDistribution(fields) {
  const by = {};
  fields.forEach((f) => { const t = topCrop(f); if (t && f.area_ha) by[t.crop.name] = (by[t.crop.name] || 0) + f.area_ha; });
  return Object.entries(by).sort((x, y) => y[1] - x[1]);
}

function suitabilityCard(an) {
  const counts = suitabilityCounts(an?.ranked), parts = BANDS.map(([label, c], i) => ({ label, c, v: counts[i] }));
  return html`<article class="panel"><div class="panel-kicker">CROP SUITABILITY</div><h3>How well crops fit this location</h3>
    <div class="donutrow">${donut(parts, 128, 18, String(an?.ranked?.length || 0))}${legend(parts)}</div>
    <p class="note">Counts of ${an?.ranked?.length || 0} crops by rule-based score: Excellent 80+, Good 60+, Average 40+, Poor below. This is a fit of crop needs to climate and soil, <strong>not</strong> a measure of field health. ${an?.score_meaning || ""}</p></article>`;
}

function soilCard(an) {
  const so = an?.soil || {};
  return html`<article class="panel"><div class="panel-kicker">SOIL SUMMARY · MODELLED</div><h3>${so.texture || "Soil estimate"}</h3>
    <div class="kv"><div><small>pH</small><b>${num(so.ph, 1)}</b></div><div><small>ORGANIC C</small><b>${num(so.organic_carbon_g_kg, 1)}<small> g/kg</small></b></div><div><small>CLAY</small><b>${num(so.clay_pct, 0)}<small> %</small></b></div><div><small>DEPTH</small><b style="font-size:14px">${so.depth || "—"}</b></div></div>
    <p class="note">ISRIC SoilGrids model, not a lab test. <a href="#soilhealth">Open soil health</a></p></article>`;
}

function wetnessCard(an) {
  return html`<article class="panel"><div class="panel-kicker">NASA POWER · ROOT-ZONE WETNESS</div><h3>Soil moisture, last 14 days</h3><div class="chart" id="dashWet"></div><p class="note" id="dashWetNote"></p></article>`;
}
function paintWetness(an) {
  const el = $("dashWet"); if (!el) return;
  const s = (an?.climate?.series?.root_zone_wetness || []).slice(-14);
  if (s.length < 2) { setHtml(el, html`<p class="note">No root-zone wetness values are available for this field.</p>`); return; }
  drawChart(el, { xs: s.map(([d]) => isoOf(d)), lines: [{ label: "Wetness (0–100 %)", color: "#3a8fd0", values: s.map(([, v]) => +(v * 100).toFixed(0)) }], unit: "%", height: 170, decimals: 0, aria: "Root-zone soil wetness, last 14 days" });
  $("dashWetNote").textContent = "Gridded NASA POWER value for a ~50 km cell, with a lag of a few days. Not a sensor reading in your field.";
}

function distCard(fields) {
  const d = cropDistribution(fields), parts = d.map(([label, v], i) => ({ label, v: +v.toFixed(1), c: PALETTE[i % PALETTE.length] }));
  return html`<article class="panel"><div class="panel-kicker">YOUR FIELDS</div><h3>Top-pick crop by area</h3>
    ${parts.length ? html`<div class="donutrow">${donut(parts, 128, 18, fmtArea(parts.reduce((s, p) => s + p.v, 0)))}${legend(parts)}</div><p class="note">Area of each saved field, grouped by its highest-scoring crop. Not what is actually planted.</p>` : html`<p class="note">Analyze at least one saved field with an area to see this.</p>`}</article>`;
}

function weatherCard() { return html`<article class="panel"><div class="panel-kicker">WEATHER TODAY · MODEL</div><div id="dashWx"><div class="skel-wrap"><div class="skel"></div></div></div></article>`; }
function tasksCard() { return html`<article class="panel"><div class="panel-kicker">NEXT STEPS</div><h3>Upcoming tasks</h3><div id="dashTasks"></div><p class="note">Built from your forecast alerts, land-management advice and flagged risks only.</p></article>`; }

const powerCard = () => html`<article class="panel"><div class="panel-kicker">POWERED BY NASA POWER</div><h3>The NASA data behind this page</h3>
  <ul class="nodata"><li><strong>Parameters:</strong> air temperature at 2 m, corrected precipitation, root-zone soil wetness, and all-sky solar radiation.</li><li><strong>Resolution:</strong> a ~50 km (0.5°) grid cell, not your field.</li><li><strong>Latency:</strong> daily values lag real time by a few days; long-term normals come from NASA POWER climatology.</li><li>Soil comes from ISRIC SoilGrids and the forecast from Open-Meteo. See <a href="#credits">Data sources &amp; credits</a>. NASA does not endorse FieldShift.</li></ul></article>`;

export function dashboardHtml(a) {
  const an = a?.analysis;
  if (!an) return html`<div class="panel"><p class="note">Analyze the active field to see its dashboard.</p></div>`;
  return html`<div class="dash-head"><div class="panel-kicker">DASHBOARD · ${a.name}</div></div>
    <div class="dash-grid">${suitabilityCard(an)}${weatherCard()}${soilCard(an)}${tasksCard()}${wetnessCard(an)}${distCard(S.fields)}</div>${powerCard()}`;
}

export async function hydrateDashboard() {
  const a = active(); if (!a?.analysis) return;
  paintWetness(a.analysis);
  let w = null;
  try {
    const d = await api(`/v1/weather?lat=${a.latitude}&lon=${a.longitude}`);
    if (S.view !== "overview") return;
    if (d.available) {
      w = d; const c = d.current || {}, t = new Date().toISOString().slice(0, 10), today = (d.days || []).find((x) => x.date === t) || {};
      setHtml($("dashWx"), html`<h3>${c.temperature_2m != null ? fmtTemp(c.temperature_2m) : "—"}</h3><div class="kv"><div><small>HIGH / LOW TODAY</small><b style="font-size:15px">${today.tmax != null ? fmtTemp(today.tmax) : "—"} / ${today.tmin != null ? fmtTemp(today.tmin) : "—"}</b></div><div><small>RAIN TODAY</small><b>${num(today.rain, 1)}<small> mm</small></b></div></div><p class="note">Open-Meteo model (forecast), not a measurement. <a href="#weather">Full outlook</a></p>`);
    } else setHtml($("dashWx"), html`<p class="note">Forecast unavailable right now. ${d.error || ""} No values are estimated.</p>`);
  } catch { if ($("dashWx")) setHtml($("dashWx"), html`<p class="note">Forecast unavailable: the backend could not be reached.</p>`); }
  const T = buildTasks(a, w);
  if ($("dashTasks")) setHtml($("dashTasks"), T.length ? T.map((t) => html`<div class="mini-crop"><span>${t.t}<small class="sub">${String(t.s).slice(0, 110)}</small></span><span class="badge ${t.p}">${t.p.toUpperCase()}</span></div>`) : html`<p class="note">Nothing urgent from the data we have.</p>`);
}
