/* AI-assisted: written with an AI coding assistant (see README, "AI tools used"). Field "Pests & disease" tab: weather-based favourable-conditions indicators. */
import { html, setHtml } from "../lib/html.js";
import { needField } from "../lib/chrome.js";
import { $, S, topCrop } from "../lib/state.js";
import { api } from "../lib/api.js";
import { cropOptions, failure, fieldHead, level, loadCrops, provenance, skeleton, unavailable } from "./common.js";

const st = { crop: "" };

function paint(a, d, crops) {
  const k = d.known_issues || {};
  setHtml($("pestBody"), html`
    <article class="panel"><div class="panel-kicker">CROP</div><label class="inl">Crop<select id="pestCrop">${cropOptions(crops, st.crop)}</select></label>
      <p class="note"><strong>These are indicators of favourable conditions, not diagnoses.</strong> They check recent and forecast temperature and humidity (${d.days_evaluated} days) against published-style weather rules. A "low" level does not mean the pest is absent.</p></article>
    <div class="two"><article class="panel"><div class="panel-kicker">WEATHER-BASED INDICATORS</div><h3>Conditions that favour disease</h3>
      ${d.risks.length ? d.risks.map((r) => html`<div class="lim"><div class="lim-h"><b>${r.name}</b> ${level(r.level)}</div><p class="note">${r.rule}</p>${r.triggered_on.length ? html`<p>Conditions met on: ${r.triggered_on.join(", ")}</p>` : html`<p class="note">Conditions not met in this window.</p>`}<p class="note">Source: ${r.source} · basis: ${r.basis}</p></div>`) : html`<p class="note">FieldShift has no weather rule for this crop yet, so it shows no indicator. Scout regularly and ask local extension about what is common near you.</p>`}
      <p class="note">${d.note}</p>${provenance(d.provenance)}</article>
    <article class="panel"><div class="panel-kicker">COMMONLY REPORTED PROBLEMS</div><h3>${k.issues?.length ? "Worth knowing about" : "No list for this crop"}</h3>
      ${k.issues?.length ? html`<div class="chips">${k.issues.map((i) => html`<span class="chip">${i}</span>`)}</div>` : ""}
      ${k.source ? html`<p class="note">${k.note}</p><p class="note"><strong>Status: ${k.status}.</strong> ${k.source}.</p><p class="note">Verify with: ${(k.verify_with || []).join("; ")}.</p>` : ""}</article></div>`);
  $("pestCrop").onchange = (e) => { st.crop = e.target.value; load(a, crops); };
}

async function load(a, crops) {
  setHtml($("pestBody"), skeleton(3));
  try {
    const d = await api(`/v1/pests?crop_id=${encodeURIComponent(st.crop)}&lat=${a.latitude}&lon=${a.longitude}`);
    if (S.view !== "pests") return;
    if (!d.available) { setHtml($("pestBody"), html`<article class="panel"><label class="inl">Crop<select id="pestCrop">${cropOptions(crops, st.crop)}</select></label></article>${unavailable("Pest indicators unavailable", d.error)}${provenance(d.provenance)}`); $("pestCrop").onchange = (e) => { st.crop = e.target.value; load(a, crops); }; return; }
    paint(a, d, crops);
  } catch (e) { if (S.view === "pests") setHtml($("pestBody"), failure("Pest indicators unavailable", e)); }
}

export async function renderPests() {
  const a = needField("pestsBody"); if (!a) return;
  setHtml($("pestsBody"), html`${fieldHead("PESTS & DISEASE · WEATHER INDICATORS", "Pests and disease conditions", a)}<div id="pestBody">${skeleton(3)}</div>`);
  let crops; try { crops = await loadCrops(); } catch (e) { setHtml($("pestBody"), failure("Crop list unavailable", e)); return; }
  if (!st.crop) st.crop = topCrop(a)?.crop.id || crops[0].id;
  load(a, crops);
}
