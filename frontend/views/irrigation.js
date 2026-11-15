/* AI-assisted: written with an AI coding assistant (see README, "AI tools used"). Field "Irrigation" tab: FAO-56 style daily water balance. */
import { html, setHtml } from "../lib/html.js";
import { needField } from "../lib/chrome.js";
import { $, S, topCrop } from "../lib/state.js";
import { post } from "../lib/api.js";
import { drawChart } from "../lib/charts.js";
import { cropOptions, failure, fieldHead, loadCrops, num, provenance, skeleton, todayIso, unavailable } from "./common.js";

const st = { crop: "", sow: "", method: "drip", root: 0.6, dep: 0.5, maxwk: "", sand: "", clay: "", soc: "" };
const val = (id) => { const v = $(id).value.trim(); return v === "" ? null : Number(v); };

function paint(a, d) {
  const w = d.water_holding || {}, ass = d.assumptions || {};
  const days = d.daily || [], xs = days.map((x) => x.date);
  setHtml($("irrResult"), html`
    <article class="panel"><div class="panel-kicker">RESULT · ${d.horizon_days}-DAY FORECAST WINDOW</div>
      <div class="kv"><div><small>IRRIGATION EVENTS</small><b>${d.events.length}</b></div><div><small>STRESS DAYS</small><b>${d.stress_days}</b></div><div><small>TOTAL AVAILABLE WATER</small><b>${d.taw_mm}<small> mm</small></b></div><div><small>REFILL THRESHOLD</small><b>${d.raw_mm}<small> mm</small></b></div></div>
      ${d.method === "rainfed" ? html`<p class="note">Rainfed: no irrigation is scheduled. Days where depletion passes the threshold are counted as stress days.</p>` : ""}
      <h3 style="margin-top:14px">Soil water depletion</h3><div class="chart" id="irrChart"></div>
      <p class="note">Depletion is how much water the root zone has lost below field capacity (0 = full). When it passes the refill threshold the crop is likely to feel stress.</p></article>
    <div class="two"><article class="panel"><div class="panel-kicker">SCHEDULE</div><h3>Suggested irrigation events</h3>
      ${d.events.length ? html`<table class="tbl"><thead><tr><th>Date</th><th>Net (mm)</th><th>Gross (mm)</th></tr></thead><tbody>${d.events.map((e) => html`<tr><td>${e.date}</td><td>${e.net_mm}</td><td>${e.gross_mm}</td></tr>`)}</tbody></table>` : html`<p class="note">No irrigation needed in this window.</p>`}
      ${d.weekly.length ? html`<h3 style="margin-top:14px">Per week</h3><table class="tbl"><thead><tr><th>Week</th><th>Events</th><th>Gross (mm)</th></tr></thead><tbody>${d.weekly.map((x) => html`<tr><td>${x.week}</td><td>${x.events}</td><td>${x.gross_mm}</td></tr>`)}</tbody></table>` : ""}</article>
    <article class="panel"><div class="panel-kicker">ASSUMPTIONS · EDITABLE ABOVE</div><h3>What this is based on</h3>
      <div class="kv"><div><small>ROOT DEPTH</small><b>${ass.root_depth_m}<small> m</small></b></div><div><small>REFILL AT</small><b>${num((ass.depletion_fraction || 0) * 100, 0)}<small> % depleted</small></b></div><div><small>WATER HOLDING</small><b>${w.awc_mm_per_m ?? "—"}<small> mm/m</small></b></div><div><small>EFFICIENCY</small><b>${d.efficiency != null ? num(d.efficiency * 100, 0) + " %" : "—"}</b></div></div>
      <p class="note">${ass.efficiency_note} ${ass.rain_rule || ""}</p>
      <ul class="nodata">${[...d.limitations, ...d.tips].map((t) => html`<li>${t}</li>`)}</ul>${d.days_skipped_missing_data ? html`<p class="note">${d.days_skipped_missing_data} forecast day(s) were skipped because ET₀ or rain was missing.</p>` : ""}${provenance(d.provenance)}</article></div>`);
  drawChart($("irrChart"), { xs, lines: [{ label: "Depletion (mm)", color: "#d9534f", values: days.map((x) => x.depletion_mm) }, { label: "Refill threshold", color: "#555", dash: "5 4", width: 1.5, values: days.map(() => d.raw_mm) }], bars: { label: "Effective rain (mm)", values: days.map((x) => x.eff_rain_mm), color: "#3a8fd0" }, unit: "mm", height: 210, zero: true, aria: "Soil water depletion over the forecast window" });
}

async function run(a) {
  const body = { latitude: a.latitude, longitude: a.longitude, crop_id: $("irCrop").value, sowing_date: $("irSow").value || todayIso(), method: $("irMethod").value,
    sand_pct: val("irSand"), clay_pct: val("irClay"), soc_g_kg: val("irSoc"), root_depth_m: val("irRoot") ?? 0.6, depletion_fraction: val("irDep") ?? 0.5, max_mm_per_week: val("irMax") };
  Object.assign(st, { crop: body.crop_id, sow: body.sowing_date, method: body.method, root: body.root_depth_m, dep: body.depletion_fraction, maxwk: $("irMax").value, sand: $("irSand").value, clay: $("irClay").value, soc: $("irSoc").value });
  setHtml($("irrResult"), skeleton(3));
  try {
    const d = await post("/v1/irrigation", body);
    if (S.view !== "irrigation") return;
    if (!d.available) { setHtml($("irrResult"), html`${unavailable("Irrigation plan unavailable", d.error)}${provenance(d.provenance)}`); return; }
    paint(a, d); window.onresize = () => { if (S.view === "irrigation") paint(a, d); };
  } catch (e) { setHtml($("irrResult"), failure(e.status === 422 ? "Check the values you entered" : "Irrigation plan unavailable", e)); }
}

export async function renderIrrigation() {
  const a = needField("irrigationBody"); if (!a) return;
  setHtml($("irrigationBody"), html`${fieldHead("IRRIGATION · FAO-56 STYLE WATER BALANCE", "Irrigation planner", a)}<div id="irrForm">${skeleton(1)}</div><div id="irrResult"></div>`);
  let crops; try { crops = await loadCrops(); } catch (e) { setHtml($("irrForm"), failure("Crop list unavailable", e)); return; }
  if (S.view !== "irrigation") return;
  const sel = st.crop || topCrop(a)?.crop.id || crops[0].id;
  setHtml($("irrForm"), html`<article class="panel"><div class="panel-kicker">INPUTS</div><h3>Crop, sowing date and method</h3>
    <div class="fgrid">
      <label>Crop<select id="irCrop">${cropOptions(crops, sel)}</select></label>
      <label>Sowing date<input type="date" id="irSow" value="${st.sow || todayIso()}"></label>
      <label>Method<select id="irMethod">${["drip", "sprinkler", "furrow", "rainfed"].map((m) => html`<option value="${m}" ${m === st.method ? "selected" : ""}>${m}</option>`)}</select></label>
      <label>Root depth (m)<input type="number" id="irRoot" min="0.1" max="3" step="0.1" value="${st.root}"></label>
      <label>Refill at depletion (fraction)<input type="number" id="irDep" min="0.1" max="0.9" step="0.05" value="${st.dep}"></label>
      <label>Max water per week (mm, optional)<input type="number" id="irMax" min="1" step="1" value="${st.maxwk}" placeholder="no limit"></label>
      <label>Sand % (optional)<input type="number" id="irSand" min="0" max="100" step="1" value="${st.sand}" placeholder="from SoilGrids"></label>
      <label>Clay % (optional)<input type="number" id="irClay" min="0" max="100" step="1" value="${st.clay}" placeholder="from SoilGrids"></label>
      <label>Organic carbon g/kg (optional)<input type="number" id="irSoc" min="0" step="0.5" value="${st.soc}" placeholder="from SoilGrids"></label>
    </div>
    <p class="note">Leave soil boxes empty to use modelled SoilGrids values for this field. Root depth, refill fraction and efficiencies are <strong>assumptions</strong> you can change.</p>
    <button class="button button-dark" id="irRun">Calculate schedule</button></article>`);
  $("irRun").onclick = () => run(a);
  run(a);
}
