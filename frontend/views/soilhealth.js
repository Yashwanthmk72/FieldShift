/* AI-assisted: written with an AI coding assistant (see README, "AI tools used"). Field "Soil health" tab: modelled soil limits, actions, sampling plan. */
import { html, setHtml } from "../lib/html.js";
import { needField } from "../lib/chrome.js";
import { $, S, fmtArea, topCrop } from "../lib/state.js";
import { api } from "../lib/api.js";
import { cropOptions, failure, fieldHead, level, loadCrops, num, provenance, skeleton, unavailable } from "./common.js";

const st = { crop: "" };
const STATUS = { good: "Good fit", marginal: "Marginal", poor: "Poor fit", unknown: "Unknown" };

function paint(a, d, crops) {
  const so = d.soil || {}, w = d.water_holding, cp = d.crop_ph, sp = d.sampling;
  setHtml($("shBody"), html`
    <article class="panel"><div class="panel-kicker">MODELLED TOPSOIL · ${so.depth || "0–30 cm"}</div><h3>${so.texture || "Soil estimate"}</h3>
      <div class="kv"><div><small>pH</small><b>${num(so.ph, 1)}</b></div><div><small>ORGANIC CARBON</small><b>${num(so.organic_carbon_g_kg, 1)}<small> g/kg</small></b></div><div><small>CLAY</small><b>${num(so.clay_pct, 0)}<small> %</small></b></div><div><small>SAND</small><b>${num(so.sand_pct, 0)}<small> %</small></b></div></div>
      <ul class="nodata">${d.summary.map((t) => html`<li>${t}</li>`)}</ul>
      <p class="note"><strong>${d.disclaimer}</strong></p></article>
    <div class="two"><article class="panel"><div class="panel-kicker">LIMITATIONS AND WHAT TO DO</div><h3>${d.limitations.length ? "Things to watch" : "No limitation flags"}</h3>
      ${d.limitations.length ? d.limitations.map((l) => html`<div class="lim"><div class="lim-h"><b>${l.factor}</b> ${level(l.level)}</div><p>${l.detail}</p><p class="note"><strong>Next step:</strong> ${l.action}</p></div>`) : html`<p class="note">The modelled pH, organic carbon and texture do not trigger any of the simple rules used here. That is not proof the soil is fine; the dataset cannot see nutrients or salinity.</p>`}
      <p class="note">Basis: ${d.basis}.</p></article>
    <div class="stack"><article class="panel"><div class="panel-kicker">WATER HOLDING</div><h3>${w ? html`${w.awc_mm_per_m} mm of available water per metre` : "Not available"}</h3><p class="note">${d.water_holding_note || "Needs sand, clay and organic carbon values for this point."}</p></article>
    <article class="panel"><div class="panel-kicker">CROP FIT · pH ONLY</div><label class="inl">Crop<select id="shCrop">${cropOptions(crops, st.crop)}</select></label>
      ${cp ? html`<h3>${STATUS[cp.status]}</h3><p class="note">${cp.detail}</p><p class="note">The crop pH range is a heuristic guide value for most crops (see Accuracy page).</p>` : ""}</article></div></div>
    <div class="two"><article class="panel"><div class="panel-kicker">SOIL SAMPLING PLAN</div><h3>About ${sp.recommended_cores} cores for ${fmtArea(a.area_ha)}</h3><p>${sp.pattern}</p><p class="note">${sp.note}</p></article>
    <article class="panel"><div class="panel-kicker">NOT AVAILABLE FROM THIS DATA</div><h3>Nitrogen, phosphorus, potassium, salinity</h3><div class="chips">${d.not_available.map((n) => html`<span class="chip">${n}</span>`)}</div><p class="note">No global dataset provides these, so FieldShift shows nothing for them rather than guessing. Only a laboratory soil test can.</p>${provenance(d.provenance)}</article></div>`);
  $("shCrop").onchange = (e) => { st.crop = e.target.value; load(a, crops); };
}

async function load(a, crops) {
  setHtml($("shBody"), skeleton(3));
  const q = `/v1/soil-health?lat=${a.latitude}&lon=${a.longitude}${st.crop ? "&crop_id=" + encodeURIComponent(st.crop) : ""}${a.area_ha ? "&area_ha=" + a.area_ha : ""}`;
  try {
    const d = await api(q);
    if (S.view !== "soilhealth") return;
    if (!d.available) { setHtml($("shBody"), html`${unavailable("Soil data unavailable", d.error)}${html`<article class="panel"><div class="panel-kicker">SAMPLING PLAN</div><h3>About ${d.sampling.recommended_cores} cores</h3><p>${d.sampling.pattern}</p></article>`}${provenance(d.provenance)}`); return; }
    paint(a, d, crops);
  } catch (e) { if (S.view === "soilhealth") setHtml($("shBody"), failure("Soil health unavailable", e)); }
}

export async function renderSoilHealth() {
  const a = needField("soilhealthBody"); if (!a) return;
  setHtml($("soilhealthBody"), html`${fieldHead("SOIL HEALTH · ISRIC SOILGRIDS (MODELLED)", "Soil health", a)}<div id="shBody">${skeleton(3)}</div>`);
  let crops; try { crops = await loadCrops(); } catch (e) { setHtml($("shBody"), failure("Crop list unavailable", e)); return; }
  if (!st.crop) st.crop = topCrop(a)?.crop.id || crops[0].id;
  load(a, crops);
}
