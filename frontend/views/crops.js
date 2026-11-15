/* AI-assisted: written with an AI coding assistant (see README, "AI tools used"). */
/* generated from FieldShift v0.4 app.js by the v1.0 module split; edited by hand afterwards */
import { html, setHtml } from "../lib/html.js";
import { confBadge } from "./badges.js";
import { combineScore, normalizePriorities } from "../lib/scoring.js";
import { $, FS, PRIOS, S, ic, monthName, normP } from "../lib/state.js";
import { ring } from "./widgets.js";
import { needField } from "../lib/chrome.js";
import { bindLayout, layoutOf, layoutSeg } from "./fields.js";
import { saveQuiet } from "../lib/storage.js";
import { askAi } from "./assistant.js";

export const priorityState = (a) => ({ resilience: 0, water: 0, soil: 0, profit: 0, ...(a.priorities && Object.keys(a.priorities).length ? a.priorities : S.settings.priorities) });
export function rescore(ranked, P) {
    // Same formula as the server (lib/scoring.js is parity-tested against backend/app/engine/scoring.py). ML blending was removed: no model is shipped.
    const n = normalizePriorities(P);
    return ranked.map((r) => ({ ...r, live: combineScore(r.components, n) })).sort((x, y) => y.live - x.live);
  }
export const cropCard = (r, i, delta) => { const c = r.crop; return html`<button class="crop-card lift ${i === 0 ? "top" : ""}" data-crop="${c.id}" aria-label="${c.name}, score ${r.live}. Open details"><div class="crop-art">${FS.pic("crop", c.id, { family: c.family, alt: c.name })}<span class="crop-rank">${String(i + 1).padStart(2, "0")}${i === 0 ? " · TOP MATCH" : ""}</span>${delta ? html`<span class="delta ${delta > 0 ? "up" : "down"}">${ic(delta > 0 ? "arrowup" : "arrowdown", 12)}${Math.abs(delta)}</span>` : ""}${ring(r.live)}</div><div class="crop-info"><div class="crop-name-row"><span class="crop-name">${c.name}</span><span class="crop-family">${c.family}</span></div><p class="crop-description">${c.description}</p>${confBadge(r)}<div class="crop-tags"><span class="crop-tag">${ic("droplet", 13)}${c.water}</span><span class="crop-tag">${ic("heart", 13)}${c.resilience}%</span>${r.best_sow_month ? html`<span class="crop-tag amber">${ic("calendar", 13)}Sow ${monthName(r.best_sow_month)}</span>` : ""}</div></div></button>`; };
export function renderCrops() {
    const a = needField("cropsBody"); if (!a) return; const P = priorityState(a);
    const profitOk = !!a.analysis?.profit_available; if (!profitOk) P.profit = 0; // D1: no real economics yet, so the control is inert and cannot dilute other weights
    setHtml($("cropsBody"), html`<div class="field-head"><div><div class="eyebrow"><span class="eyebrow-line"></span> CROP ADVISOR</div><h1>What could grow on ${a.name}?</h1><p>Ranked by climate, soil, water and your priorities. Click a crop for photos, timing and advice.</p></div><button class="button button-light" id="askAi" data-ic="sparkle">Ask FieldShift AI</button></div>
    <section class="prio-panel"><div style="display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;align-items:center"><div><div class="panel-kicker">PRIORITIES</div><strong id="prioSummary"></strong></div><div class="row" style="margin:0"><button class="chip ${S.compare ? "on" : ""}" id="cmpBtn" aria-pressed="${S.compare}">${ic("arrowup", 14)}Show rank change</button><button class="chip" id="condOnly">Conditions only</button><button class="chip" id="prioReset">Reset to my defaults</button></div></div>
      <div class="prio-grid">${PRIOS.map(([k, l, i, d]) => html`<div class="prio-row ${P[k] > 0 ? "on" : "off"}" data-row="${k}"><div class="prio-top">${ic(i, 18)}<strong>${l}</strong><button class="switch" role="switch" aria-checked="${P[k] > 0}" aria-label="${l}" data-sw="${k}" ${k === "profit" && !profitOk ? "disabled" : ""}></button></div><small>${k === "profit" && !profitOk ? "Unavailable: needs a costed finance plan (not part of this release)." : d}</small><input type="range" min="0" max="100" value="${P[k]}" ${P[k] > 0 && (k !== "profit" || profitOk) ? "" : "disabled"} data-rg="${k}" aria-label="${l} weight"></div>`)}</div></section>
    <div class="toolbar" style="justify-content:space-between"><span class="note" id="resCount" style="margin:0"></span>${layoutSeg("crops")}</div><div id="cropResults"></div>`);
    const draw = () => {
      const base = rescore(a.analysis.ranked, { ...S.settings.priorities, ...(profitOk ? {} : { profit: 0 }) }).map((r) => r.crop.id), list = rescore(a.analysis.ranked, P), on = PRIOS.filter(([k]) => P[k] > 0).map(([, l]) => l);
      $("prioSummary").textContent = on.length ? `Best match with ${on.join(", ")}: ${list[0].crop.name} (${list[0].live}/100)` : `Conditions only – ranked by climate fit: ${list[0].crop.name} (${list[0].live}/100)`;
      $("resCount").textContent = `${list.length} crops ranked`;
      const el = $("cropResults"); el.className = "crop-list" + (layoutOf("crops") === "list" ? " is-list" : "");
      setHtml(el, list.map((r, i) => cropCard(r, i, S.compare ? base.indexOf(r.crop.id) - i : 0)));
      el.querySelectorAll("[data-crop]").forEach((c) => c.onclick = () => { S.cropFrom = "crops"; S.focusStage = null; location.hash = "#crop/" + c.dataset.crop; });
      FS.decorate(el); FS.hydrate(el);
    };
    const saveP = () => { a.priorities = { ...P }; saveQuiet({ ...a, priorities: { ...P } }); };
    $("cropsBody").querySelectorAll("[data-sw]").forEach((b) => b.onclick = () => { const k = b.dataset.sw, row = b.closest(".prio-row"), rg = row.querySelector("input"); if (P[k] > 0) { S.lastP = { ...(S.lastP || {}), [k]: P[k] }; P[k] = 0; } else P[k] = S.lastP?.[k] || 34; b.setAttribute("aria-checked", P[k] > 0); row.classList.toggle("on", P[k] > 0); row.classList.toggle("off", P[k] === 0); rg.disabled = P[k] === 0; rg.value = P[k]; saveP(); draw(); });
    $("cropsBody").querySelectorAll("[data-rg]").forEach((r) => r.oninput = () => { P[r.dataset.rg] = +r.value; saveP(); draw(); });
    const syncUi = () => $("cropsBody").querySelectorAll(".prio-row").forEach((row) => { const k = row.dataset.row, on = P[k] > 0; row.classList.toggle("on", on); row.classList.toggle("off", !on); row.querySelector(".switch").setAttribute("aria-checked", on); const rg = row.querySelector("input"); rg.disabled = !on; rg.value = P[k]; });
    $("condOnly").onclick = () => { PRIOS.forEach(([k]) => { if (P[k] > 0) (S.lastP ||= {})[k] = P[k]; P[k] = 0; }); syncUi(); saveP(); draw(); };
    $("prioReset").onclick = () => { Object.assign(P, { resilience: 0, water: 0, soil: 0, profit: 0 }, S.settings.priorities); syncUi(); saveP(); draw(); };
    $("cmpBtn").onclick = () => { S.compare = !S.compare; $("cmpBtn").classList.toggle("on", S.compare); $("cmpBtn").setAttribute("aria-pressed", S.compare); draw(); };
    bindLayout($("cropsBody"), () => { renderCrops(); const r = document.querySelector(".view.active"); FS.decorate(r); FS.hydrate(r); });
    $("askAi").onclick = () => askAi(a, rescore(a.analysis.ranked, P)[0]);
    draw();
  }
