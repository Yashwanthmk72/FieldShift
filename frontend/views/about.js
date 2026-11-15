/* AI-assisted: written with an AI coding assistant. "How accurate is this?" and "Data sources & credits" pages. */
import { html, setHtml, safeUrl } from "../lib/html.js";
import { $ } from "../lib/state.js";
import { api } from "../lib/api.js";

const head = (k, t, p) => html`<div class="view-head"><div><div class="eyebrow"><span class="eyebrow-line"></span> ${k}</div><h1>${t}</h1><p>${p}</p></div></div>`;

export function renderAccuracy() {
  setHtml($("accuracyBody"), html`${head("ABOUT", "How accurate is this?", "FieldShift is a planning aid. Here is exactly what limits it.")}
  <div class="two"><div class="stack">
  <article class="panel"><div class="panel-kicker">DATA RESOLUTION</div><h3>Coarse climate, modelled soil</h3><ul class="nodata"><li><strong>NASA POWER climate is about 50 km (0.5°) per grid cell.</strong> Your field gets the value of the whole cell. Hills, coasts and valleys can make your real weather quite different.</li><li><strong>SoilGrids is a 250 m model, not a measurement.</strong> It is sampled at up to 4 points in your boundary and can be wrong, especially for pH and texture.</li><li>Daily weather lags real time by a few days and is observed history, not a forecast.</li></ul></article>
  <article class="panel"><div class="panel-kicker">CROP PARAMETERS</div><h3>Many values are unverified</h3><ul class="nodata"><li>Temperature, rainfall and pH ranges for <strong>all 27 crops are heuristic estimates</strong>. They are labelled “Illustrative estimate” in the app. Each lists where to verify it (FAO EcoCrop).</li><li>Only crop coefficients and growth-stage lengths for 9 original crops were checked against FAO-56. The 16 crops added later use recalled values and are still heuristic.</li><li>Sowing windows, pests and tips are general guidance, not local advice.</li></ul></article></div>
  <div class="stack">
  <article class="panel"><div class="panel-kicker">WHAT A SCORE MEANS</div><h3>No yield guarantee</h3><ul class="nodata"><li>A score is a rule-based suitability signal. <strong>It is not a probability of a good harvest and not a yield forecast.</strong> No machine-learning model is used.</li><li>The <strong>confidence level</strong> shows how much we trust the inputs (data completeness and whether crop values are verified). It is capped at “Medium” while ranges are heuristic.</li><li>Pests, diseases, seed supply, labour, irrigation access, markets and prices are not in the score.</li><li>Market prices are published benchmarks (world, or India mandi), not your local farm-gate price, and are never real-time. “Estimated gross value” is revenue before costs, <strong>never profit</strong>.</li></ul></article>
  <article class="panel"><div class="panel-kicker">WHAT TO DO</div><h3>Check locally before you act</h3><ul class="nodata"><li>Get a <strong>local soil test</strong> before changing fertiliser or lime.</li><li>Ask your <strong>agricultural extension office</strong> about varieties, sowing dates and pests.</li><li>Treat FieldShift as a way to compare options and ask better questions.</li></ul><p class="note">Full sources: <a href="#credits">Data sources &amp; credits</a>.</p></article></div></div>`);
}

export async function renderCredits() {
  setHtml($("creditsBody"), html`${head("ABOUT", "Data sources & credits", "Every dataset used, with what it is for, its limits and what was actually tested.")}<p class="note">Loading…</p>`);
  let d; try { d = await api("/v1/credits"); } catch { setHtml($("creditsBody"), html`${head("ABOUT", "Data sources & credits", "")}<div class="empty"><h3>Credits need the backend</h3><p>They are generated from <code>backend/app/data/sources.md</code>.</p></div>`); return; }
  const groups = [...new Set(d.sections.map((s) => s.group || "Other"))];
  setHtml($("creditsBody"), html`${head("ABOUT", "Data sources & credits", d.intro || "")}${groups.map((g) => html`<h3 class="grp">${g}</h3><div class="src-grid">${d.sections.filter((s) => (s.group || "Other") === g).map((s) => html`<article class="panel"><h4>${s.name}</h4>${s.text ? html`<p class="note" style="margin-top:0">${s.text}</p>` : ""}<dl>${Object.entries(s.fields).filter(([k]) => k !== "URL" && k !== "API").map(([k, v]) => html`<dt>${k}</dt><dd>${v}</dd>`)}</dl>${Object.entries(s.urls).map(([k, v]) => html`<a href="${safeUrl(v)}" target="_blank" rel="noreferrer noopener">${k === "URL" ? "Website" : k}</a> `)}</article>`)}</div>`)}`);
}
