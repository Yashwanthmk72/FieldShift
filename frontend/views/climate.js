/* AI-assisted: written with an AI coding assistant. Field "Climate" tab: NASA POWER daily data vs long-term normals with anomaly shading. */
import { html, setHtml } from "../lib/html.js";
import { needField } from "../lib/chrome.js";
import { $, S } from "../lib/state.js";
import { api } from "../lib/api.js";
import { drawChart } from "../lib/charts.js";

const st = { days: 180, start: "", end: "", timer: null, fetched: 0, data: null, key: "" };
const REFRESH_MS = 30 * 60 * 1000;
const iso = (d) => d.toISOString().slice(0, 10);
const num = (v, d = 1) => v == null ? "—" : (v > 0 && d ? "+" : "") + v.toFixed(d);

function query(a) {
  let s = st.start, e = st.end;
  if (!s || !e) { const end = new Date(Date.now() - 2 * 864e5), start = new Date(end.getTime() - (st.days - 1) * 864e5); s = iso(start); e = iso(end); }
  return { s, e, q: `/v1/climate/series?lat=${a.latitude}&lon=${a.longitude}&start=${s}&end=${e}` };
}
function paint(d) {
  const s = d.summary || {}, n = d.normals_available;
  setHtml($("climStats"), html`<div class="kv"><div><small>LATEST DATA</small><b style="font-size:15px">${d.latest_data_date || "—"}</b></div><div><small>DATA LAG</small><b>${d.lag_days ?? "—"}<small> days</small></b></div><div><small>MEAN TEMP VS NORMAL</small><b>${n ? num(s.temp_anomaly_mean_c) : "—"}<small> °C</small></b></div><div><small>RAIN VS NORMAL</small><b>${n && s.rain_vs_normal_pct != null ? (s.rain_vs_normal_pct > 0 ? "+" : "") + s.rain_vs_normal_pct : "—"}<small> %</small></b></div></div>${n ? "" : html`<p class="note"><strong>Climate normals are unavailable right now</strong>, so anomalies and shading are hidden. Daily values are still real NASA POWER data.</p>`}`);
  const xs = d.dates, warm = "#e5733a", cool = "#3a8fd0";
  drawChart($("chTemp"), { xs, lines: [{ label: "Daily mean temperature", color: "#d9534f", values: d.temperature_c.values }, ...(n ? [{ label: "Normal", color: "#555", dash: "5 4", width: 1.5, values: d.temperature_c.normal }] : [])], shade: n ? { a: d.temperature_c.values, b: d.temperature_c.normal, up: warm, down: cool, legend: [["Warmer than normal", warm], ["Cooler than normal", cool]] } : null, unit: "°C", height: 230, aria: "Daily temperature versus normal" });
  drawChart($("chRain"), { xs, lines: [], bars: { label: "Daily rainfall (mm)", values: d.rain_mm.values, color: "#3a8fd0" }, unit: "mm", height: 170, zero: true, aria: "Daily rainfall" });
  if (d.rain_cumulative) drawChart($("chCum"), { xs, lines: [{ label: "Cumulative rain", color: "#2d8fd0", values: d.rain_cumulative.actual }, { label: "Cumulative normal", color: "#555", dash: "5 4", width: 1.5, values: d.rain_cumulative.normal }], shade: { a: d.rain_cumulative.actual, b: d.rain_cumulative.normal, up: "#3a8fd0", down: "#e5b73a", legend: [["Wetter than normal", "#3a8fd0"], ["Drier than normal", "#e5b73a"]] }, unit: "mm", height: 200, zero: true, aria: "Cumulative rainfall versus normal" });
  else setHtml($("chCum"), html`<p class="note">Cumulative comparison needs climate normals.</p>`);
  drawChart($("chSol"), { xs, lines: [{ label: "Solar radiation", color: "#e0a21a", values: d.solar_mj_m2.values }, ...(n && d.solar_mj_m2.normal ? [{ label: "Normal", color: "#555", dash: "5 4", width: 1.5, values: d.solar_mj_m2.normal }] : [])], shade: n && d.solar_mj_m2.normal ? { a: d.solar_mj_m2.values, b: d.solar_mj_m2.normal, up: "#e0a21a", down: "#7a8aa0", legend: [["Sunnier than normal", "#e0a21a"], ["Duller than normal", "#7a8aa0"]] } : null, unit: "MJ/m²/day", height: 200, aria: "Solar radiation versus normal" });
  $("climChecked").textContent = `Last checked ${new Date(st.fetched).toLocaleTimeString()} · refreshes every 30 min while this tab is open`;
}
async function load(a, force) {
  const { s, e, q } = query(a); st.key = q;
  if (!force && st.data && st.data.__q === q && Date.now() - st.fetched < REFRESH_MS) return paint(st.data);
  $("climChecked").textContent = "Loading NASA POWER data…";
  try { const d = await api(q); d.__q = q; st.data = d; st.fetched = Date.now(); if (S.view === "climate") paint(d); }
  catch (err) { setHtml($("climStats"), html`<div class="empty"><h3>Climate data unavailable</h3><p>${err.detail || "The backend or NASA POWER could not be reached."} Try again in a few minutes. No values are estimated.</p></div>`); }
}
export function renderClimate() {
  clearInterval(st.timer);
  const a = needField("climateBody"); if (!a) return;
  setHtml($("climateBody"), html`<div class="field-head"><div><div class="eyebrow"><span class="eyebrow-line"></span> CLIMATE · NASA POWER</div><h1>Weather vs normal</h1><p>${a.name} · ${a.latitude.toFixed(3)}°, ${a.longitude.toFixed(3)}°</p></div></div>
    <article class="panel"><div class="mk-controls"><div class="seg" role="group" aria-label="Date range">${[30, 90, 180, 365].map((d) => html`<button data-days="${d}" class="${!st.start && st.days === d ? "on" : ""}">${d} days</button>`)}</div><label>From<input type="date" id="climFrom" value="${st.start}"></label><label>To<input type="date" id="climTo" value="${st.end}"></label><button class="button button-light" id="climApply">Apply</button><button class="button button-light" id="climRefresh">Refresh</button></div>
    <p class="note" id="climChecked"></p><div id="climStats"></div></article>
    <article class="panel"><div class="panel-kicker">TEMPERATURE</div><h3>Daily mean temperature</h3><div class="chart" id="chTemp"></div></article>
    <div class="two"><article class="panel"><div class="panel-kicker">RAINFALL</div><h3>Daily rainfall</h3><div class="chart" id="chRain"></div></article><article class="panel"><div class="panel-kicker">RAINFALL</div><h3>Cumulative vs normal</h3><div class="chart" id="chCum"></div></article></div>
    <article class="panel"><div class="panel-kicker">SUNSHINE</div><h3>Solar radiation</h3><div class="chart" id="chSol"></div></article>
    <article class="panel"><div class="panel-kicker">READ THIS FIRST</div><h3>What these charts can and cannot tell you</h3><ul class="nodata"><li>NASA POWER daily data <strong>lags real time by a few days</strong>. The newest days may be missing or revised.</li><li>Each value describes one <strong>~50 km (0.5°) grid cell</strong>, not your field. Rain in particular can differ a lot over short distances.</li><li>The dashed “normal” is NASA POWER’s long-term monthly climatology, smoothed between months. Shading shows whether a day was above or below it.</li><li>This is observed history, not a forecast.</li></ul></article>`);
  document.querySelectorAll("[data-days]").forEach((b) => b.onclick = () => { st.days = +b.dataset.days; st.start = st.end = ""; renderClimate(); });
  $("climApply").onclick = () => { st.start = $("climFrom").value; st.end = $("climTo").value; if (!st.start || !st.end) { st.start = st.end = ""; } load(a, true); };
  $("climRefresh").onclick = () => load(a, true);
  load(a, false);
  st.timer = setInterval(() => { if (S.view !== "climate") return clearInterval(st.timer); if (document.visibilityState === "visible") load(a, true); }, REFRESH_MS);
  window.onresize = () => { if (S.view === "climate" && st.data) paint(st.data); };
}
