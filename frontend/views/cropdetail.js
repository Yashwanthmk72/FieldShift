/* AI-assisted: written with an AI coding assistant (see README, "AI tools used"). */
/* generated from FieldShift v0.4 app.js by the v1.0 module split; edited by hand afterwards */
import { html, insertHtml, setHtml } from "../lib/html.js";
import { $, FS, MONTHS, S, active, cap, ic, monthName, monthSpan } from "../lib/state.js";
import { askAi, info } from "./assistant.js";
import { priorityState, rescore } from "./crops.js";
import { normalsChart, ring } from "./widgets.js";
import { motion } from "../lib/chrome.js";
import { riskShell, hydrateRisks } from "./risks.js";
import { confBadge } from "./badges.js";

export const rangeGauge = (label, value, unit, lo, hi, scaleLo, scaleHi, ok) => {
    const pos = (v) => Math.max(0, Math.min(100, (v - scaleLo) / (scaleHi - scaleLo) * 100)), has = value != null && !Number.isNaN(value);
    return html`<div class="gauge-row"><div class="lab"><strong>${label}</strong><span>${has ? html`<b>${Number(value).toFixed(value % 1 ? 1 : 0)}${unit}</b> · ` : ""}ideal ${lo}–${hi}${unit}</span></div><div class="gauge" role="img" aria-label="${label}: ${has ? value : "unknown"}, ideal ${lo} to ${hi}"><span class="zone" style="left:${pos(lo)}%;width:${pos(hi) - pos(lo)}%"></span>${has ? html`<span class="mark" style="left:${pos(value)}%"></span>` : ""}</div>${has ? html`<small class="note" style="display:block;margin:6px 0 0">${ok(value)}</small>` : ""}</div>`;
  };
export async function renderCropDetail() {
    const id = S.arg, a = active(), ranked = a?.analysis?.ranked, item = ranked?.find((r) => r.crop.id === id), view = $("cropDetail");
    const back = S.cropFrom === "rotation" ? ["#rotation", "Back to rotation"] : S.cropFrom === "field" ? ["#field", "Back to field"] : ["#crops", "Back to crop advisor"];
    if (!id) { setHtml(view, html`<div class="empty"><h3>No crop selected</h3><a class="button button-dark" href="#crops">Open Crop advisor</a></div>`); return; }
    const draw = (info) => {
      const c = info || item?.crop; if (!c) { setHtml(view, html`<a class="button button-light back" href="${back[0]}" data-ic="back">${back[1]}</a><div class="empty"><h3>Crop details unavailable</h3><p>Start the backend or analyze a field to load crop information.</p></div>`); FS.decorate(view); return; }
      const lat = a?.latitude ?? 0, nm = a?.analysis?.normals, soilPh = a?.analysis?.soil?.ph;
      const live = item ? rescore(ranked, priorityState(a), a.analysis.weights).find((r) => r.crop.id === id) : null, score = live?.live ?? item?.score;
      const sow = item?.sow_months || info?.window?.sow_months || [], harv = item?.harvest_months || info?.window?.harvest_months || [], bestM = item?.best_sow_month || sow[0];
      const days = info?.days_to_maturity, nMonths = days ? Math.max(1, Math.round((days[0] + days[1]) / 60)) : 4, growMonths = bestM ? Array.from({ length: nMonths }, (_, i) => ((bestM - 1 + i) % 12) + 1) : [];
      const nowM = new Date().getMonth() + 1;
      const ribbon = MONTHS.map((m, i) => { const mm = i + 1, cls = sow.includes(mm) ? "sow" : harv.includes(mm) ? "harvest" : growMonths.includes(mm) ? "grow" : ""; return html`<div class="rcell ${cls} ${mm === bestM ? "best" : ""} ${mm === nowM ? "today" : ""}" title="${m}${cls ? " – " + cls : ""}">${m[0]}<i></i></div>`; });
      let seasonT = null, seasonR = null; if (nm && bestM) { seasonT = growMonths.reduce((s, m) => s + nm.temperature_c[m - 1], 0) / growMonths.length; seasonR = growMonths.reduce((s, m) => s + nm.rain_mm_month[m - 1], 0); }
      const recs = []; const warn = (t) => recs.push({ t, warn: 1 }), good = (t) => recs.push({ t });
      if (bestM) good(html`Best climate fit at your field: sow in <strong>${monthName(bestM)}</strong> (typical window ${monthSpan(sow)}), harvest around ${monthSpan(harv)}.`);
      if (soilPh != null) { if (soilPh < c.ph[0]) warn(`Soil pH ${soilPh} is below ${c.name}'s ideal ${c.ph[0]}–${c.ph[1]}. Test locally and consider liming.`); else if (soilPh > c.ph[1]) warn(`Soil pH ${soilPh} is above the ideal ${c.ph[0]}–${c.ph[1]}. Add organic matter and check nutrient availability.`); else good(`Soil pH ${soilPh} sits inside the ideal ${c.ph[0]}–${c.ph[1]} range.`); }
      if (seasonT != null) { if (seasonT < c.temp[0] || seasonT > c.temp[1]) warn(`Typical growing-season temperature (${seasonT.toFixed(1)}°C) is outside the ${c.temp[0]}–${c.temp[1]}°C guide. Choose a suited variety and timing.`); }
      if (seasonR != null) { if (seasonR < c.rain[0]) warn(`Expected season rainfall (~${Math.round(seasonR)} mm) is below the ~${c.rain[0]} mm this crop needs – plan supplemental irrigation.`); else if (seasonR > c.rain[1]) warn(`Expected season rainfall (~${Math.round(seasonR)} mm) is above ${c.rain[1]} mm – ensure good drainage.`); }
      const prev = a?.previous_crops || []; if (prev.length && c.good_previous && !c.good_previous.some((p) => prev.map((x) => cap(x)).includes(p)) && prev[prev.length - 1] === id) warn(`You grew ${c.name} last season – repeating it raises disease risk. Rotate first.`);
      (c.tips || []).slice(0, 4).forEach((t) => good(t));
      const photos = [c.image_url && { l: "Hero", ...{ url: c.image_url, page: c.image_attribution_url, a: c.image_author, lic: c.image_license } }, ...(c.stages || []).filter((s) => s.image).map((s) => ({ l: s.name, url: s.image.url, page: s.image.page, a: s.image.author, lic: s.image.license }))].filter(Boolean);
      const focus = S.focusStage;
      setHtml(view, html`<a class="button button-light back" href="${back[0]}" data-ic="back">${back[1]}</a>
      <section class="detail-hero">${info?.image_url ? FS.picWith("crop", c.id, { url: info.image_url, page: info.image_attribution_url, author: info.image_author, license: info.image_license }, { cls: "show-credit", family: c.family, alt: c.name }) : FS.pic("crop", c.id, { cls: "show-credit", family: c.family, alt: c.name })}<div class="copy"><div><div class="eyebrow"><span class="eyebrow-line"></span> CROP FIELD GUIDE${a ? " · " + a.name.toUpperCase() : ""}</div><h1>${c.name}</h1><p>${c.description}</p><div class="pills"><span class="pill">${ic("calendar", 14)}${c.season}</span><span class="pill">${ic("droplet", 14)}${c.water} water</span>${days ? html`<span class="pill">${ic("refresh", 14)}${days[0]}–${days[1]} days</span>` : ""}<span class="pill">${c.family}${c.fixer ? " · fixes nitrogen" : ""}</span><span class="pill">${ic("heart", 14)}${c.resilience}% resilience</span></div></div>${score != null ? html`<div style="text-align:center">${ring(score)}<div class="pill" style="margin-top:8px">FIT</div></div>` : ""}</div></section>
      <div class="two"><div class="stack">
        <article class="detail-card"><div class="panel-kicker">WHEN TO GROW</div><h3>Best time for ${a ? "your field" : "your latitude"}</h3><div class="ribbon" role="img" aria-label="Sowing and harvest months">${ribbon}</div><div class="legend"><span style="--c:var(--amber)">Sow ${monthSpan(sow)}</span><span style="--c:var(--green-2)">Growing</span><span style="--c:var(--lime)">Harvest ${monthSpan(harv)}</span></div><p class="note">${info?.window?.note || ""} ${bestM && item ? `Highlighted month is the best climate fit using long-term averages.` : ""}</p>${nm ? html`<div style="margin-top:8px"><strong style="font-size:13px">Typical temperature &amp; rainfall at your field</strong>${normalsChart(nm, growMonths)}</div>` : ""}</article>
        <article class="detail-card"><div class="panel-kicker">GROWTH STAGES</div><h3>What ${c.name.toLowerCase()} looks like through the season</h3>${(c.stages || []).length ? html`<div class="stage-grid">${c.stages.map((s, i) => html`<div class="stage ${focus === i ? "focus" : ""}" id="stage-${i}">${FS.picWith("season", ["sowing", "growing", "flowering", "harvest"][i] || "growing", s.image, { alt: `${c.name} – ${s.name}` })}<div class="txt"><small>${s.when}</small><h4>${s.name}</h4><p>${s.text}</p></div></div>`)}</div>` : html`<p class="note">Stage details load from the backend.</p>`}</article>
        <article class="detail-card"><div class="panel-kicker">RECOMMENDATIONS</div><h3>What to do</h3><ul class="recs">${recs.map((r) => html`<li class="${r.warn ? "warn" : ""}">${ic(r.warn ? "info" : "check", 18)}<span>${r.t}</span></li>`)}</ul>${item ? html`<details style="margin-top:12px"><summary style="cursor:pointer;font-weight:700">Why this score</summary><ul class="recs">${item.evidence.map((e) => html`<li>${ic("info", 18)}<span>${e}</span></li>`)}</ul><p class="note">${item.caveat}</p></details>` : ""}</article>
      </div><div class="stack">
        ${riskShell(c)}
        ${a && (seasonT != null || soilPh != null) ? html`<article class="detail-card"><div class="panel-kicker">FIT WITH YOUR FIELD</div><h3>Your conditions vs ${c.name}</h3>${rangeGauge("Growing-season temperature", seasonT, "°C", c.temp[0], c.temp[1], c.temp[0] - 12, c.temp[1] + 12, (v) => v < c.temp[0] ? "A little cool for this crop." : v > c.temp[1] ? "A little hot for this crop." : "Comfortably inside the ideal range.")}${rangeGauge("Season rainfall", seasonR, " mm", c.rain[0], c.rain[1], Math.max(0, c.rain[0] - 400), c.rain[1] + 500, (v) => v < c.rain[0] ? "Drier than ideal – irrigation likely." : v > c.rain[1] ? "Wetter than ideal – check drainage." : "Within the ideal rainfall band.")}${rangeGauge("Soil pH", soilPh, "", c.ph[0], c.ph[1], 3.5, 9, (v) => v < c.ph[0] ? "Acidic for this crop." : v > c.ph[1] ? "Alkaline for this crop." : "In the sweet spot.")}</article>` : ""}
        <article class="detail-card"><div class="panel-kicker">GENERAL INFORMATION</div><h3>About ${c.name}</h3><p class="note" style="margin-top:0"><strong>Soil:</strong> ${c.soil}<br><strong>Uses:</strong> ${c.uses}${info?.nutrients ? html`<br><strong>Nutrients:</strong> ${info.nutrients}` : ""}</p>${info?.pests?.length ? html`<div class="panel-kicker" style="margin-top:12px">WATCH FOR</div><div class="taglist">${info.pests.map((p) => html`<span class="tl pest">${p}</span>`)}</div>` : ""}${info?.good_previous?.length ? html`<div class="panel-kicker" style="margin-top:12px">GOOD AFTER</div><div class="taglist">${info.good_previous.map((p) => html`<span class="tl">${p}</span>`)}</div><div class="panel-kicker">GOOD BEFORE</div><div class="taglist">${(info.good_next || []).map((p) => html`<span class="tl">${p}</span>`)}</div>` : ""}${info?.guidance_note ? html`<p class="note">${info.guidance_note}</p>` : ""}<div class="row">${a ? html`<button class="button button-dark" id="askCrop" data-ic="sparkle">Ask FieldShift AI</button>` : ""}</div></article>
        ${photos.length ? html`<article class="detail-card"><div class="panel-kicker">PHOTO CREDITS</div><div class="credits">${photos.map((p) => html`<a href="${p.page || "#"}" target="_blank" rel="noreferrer noopener">${p.l}: ${p.a || "Wikimedia Commons"} · ${p.lic || ""}</a>`)}</div></article>` : ""}
      </div></div>`);
      FS.decorate(view); FS.hydrateKnown(view); FS.hydrate(view);
      if (item) { const h = view.querySelector(".detail-hero h1, .detail-hero h2"); if (h) insertHtml(h, "afterend", confBadge(item)); }
      hydrateRisks(c, a);
      $("askCrop")?.addEventListener("click", () => askAi(a, item || { crop: c, score: score ?? 0, components: {}, evidence: [] }));
      if (focus != null) { const el = $("stage-" + focus); if (el) setTimeout(() => el.scrollIntoView({ behavior: "smooth", block: "center" }), 250); }
    };
    draw(item ? { ...item.crop, ...(await Promise.resolve(null) || {}) } : null); // instant paint from analysis data
    const full = await FS.cropInfo(id, false);
    if (S.view === "crop" && S.arg === id) { draw(full ? { ...(item?.crop || {}), ...full } : item?.crop); motion(); }
  }
FS.openCrop = (id, from, stage) => { S.cropFrom = from || "crops"; S.focusStage = stage ?? null; location.hash = "#crop/" + id; };
