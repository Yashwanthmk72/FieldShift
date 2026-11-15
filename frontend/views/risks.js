/* AI-assisted: written with an AI coding assistant. "Risks & downsides" panel for a crop. */
import { html, setHtml } from "../lib/html.js";
import { api, post } from "../lib/api.js";

const LV = { low: "Low", moderate: "Moderate", high: "High", unknown: "Not assessed" };
const row = (r) => html`<li class="risk lvl-${r.level}"><div class="risk-top"><strong>${r.title}</strong><span class="lvl">${LV[r.level] || r.level}</span></div><p>${r.text}</p><small>Basis: ${r.basis}</small></li>`;
const FALLBACK_WRONG = ["Crop ranges may be heuristic estimates, not verified values.", "Climate is one ~50 km NASA POWER grid cell; soil is modelled at 250 m.", "Pests, diseases, seed supply, labour, irrigation, markets and prices are not in the score.", "This is not a yield forecast or guarantee. Get a local soil test and extension advice first."];

export const riskShell = (c) => html`<article class="detail-card" id="risksCard" data-crop="${c.id}"><div class="panel-kicker">RISKS &amp; DOWNSIDES</div><h3>What could go wrong with ${c.name.toLowerCase()}</h3><div id="risksBody"><p class="note">Loading risk checks…</p></div></article>`;

export async function hydrateRisks(c, field) {
  const body = document.getElementById("risksBody"); if (!body) return;
  let data = null;
  if (field) { try { data = await post("/v1/risks", { crop_id: c.id, latitude: field.latitude, longitude: field.longitude }); } catch { data = null; } }
  if (!document.getElementById("risksBody")) return;
  const items = data?.items || [];
  const wrong = data?.could_be_wrong || FALLBACK_WRONG;
  setHtml(body, html`${data ? html`<ul class="risks">${items.map(row)}</ul>` : html`<p class="note">${field ? "Risk checks need the backend and live climate data; showing the general limits only." : "Select and analyze a field to see climate, water and soil risks for it."}</p>`}<div id="priceRisk"></div><details class="wrong" open><summary>What could make this advice wrong</summary><ul>${wrong.map((w) => html`<li>${w}</li>`)}</ul></details><p class="note">${data?.disclaimer || "Qualitative planning flags, not forecasts."} See <a href="#accuracy">How accurate is this?</a></p>`);
  priceRow(c);
}

async function priceRow(c) {
  const el = document.getElementById("priceRisk"); if (!el) return;
  let s = null; try { s = await api(`/v1/market/series?crop=${encodeURIComponent(c.id)}&country=WORLD`); } catch { /* offline */ }
  if (!document.getElementById("priceRisk")) return;
  let r;
  if (!s || s.no_data) r = { title: "Price volatility", level: "unknown", text: s ? "No real price series exists for this crop in FieldShift, so volatility is unknown (not low)." : "Price data needs the backend.", basis: "Market page sources" };
  else {
    const cv = s.stats?.cv_pct, lvl = cv == null ? "unknown" : cv > 25 ? "high" : cv > 12 ? "moderate" : "low";
    r = { title: "Price volatility", level: lvl, text: cv == null ? "Not enough history to measure volatility." : `World benchmark price varied by about ${cv}% (coefficient of variation over up to the last 24 monthly values). Local farm-gate prices can move differently.`, basis: `${s.source}, ${s.freshness.label}; thresholds are an editorial judgement.` };
  }
  setHtml(el, html`<ul class="risks">${row(r)}</ul>`);
}
