/* AI-assisted: written with an AI coding assistant (see README, "AI tools used"). */
/* generated from FieldShift v0.4 app.js by the v1.0 module split; edited by hand afterwards */
import { html, setHtml } from "../lib/html.js";
import { needField, reanalyze } from "../lib/chrome.js";
import { $, FS, HEAVY_N, ic, monthName, seasonName } from "../lib/state.js";

export function renderRotation() {
    const a = needField("rotationBody"); if (!a) return; const lat = a.latitude, plan = a.analysis.rotation; let year = 0, prevSow = 0;
    const monthAt = (s, h, f) => ((s - 1 + Math.round((((h - s) + 12) % 12) * f)) % 12) + 1;
    const cards = plan.map((r, i) => {
      const sow = r.sow_months?.[0] || 6, harv = r.harv_months?.[0] || r.harvest_months?.[0] || (sow + 4 - 1) % 12 + 1; if (i && sow <= prevSow) year++; prevSow = sow;
      const phases = [["sowing", "Sow", 0], ["growing", "Grow", .4], ["flowering", "Bloom", .7], ["harvest", "Harvest", 1]];
      const n = r.fixer ? html`<span class="nitro up">${ic("arrowup", 12)}Adds nitrogen</span>` : HEAVY_N.has(r.id) ? html`<span class="nitro down">${ic("arrowdown", 12)}Uses nitrogen</span>` : "";
      return html`<article class="season lift ${r.fixer ? "legume" : ""}" data-open-crop="${r.id}" data-season="${i}" tabindex="0" role="link" aria-label="${r.crop}, season ${r.season}. Open crop details">${FS.pic("crop", r.id, { cls: "main", family: r.family, alt: r.crop })}<div class="badges"><span class="n">SEASON ${String(r.season).padStart(2, "0")}</span><span>Y${year + 1}</span>${r.fixer ? "<span>LEGUME</span>" : ""}</div>
      <div class="in"><h3>${r.crop}</h3><small><strong>${seasonName(sow, lat)}</strong> · sow ${monthName(sow)} → harvest ${monthName(harv)}<br>${r.reason}</small><div>${n}</div>
      <div class="phases">${phases.map(([k, l, f], pi) => html`<div class="phase" data-open-crop="${r.id}" data-stage="${pi}" title="See ${r.crop} at ${l.toLowerCase()} stage">${FS.pic("season", k, { alt: l, credit: false })}${l}<br>${monthName(monthAt(sow, harv, f))}</div>`)}</div></div></article>`;
    });
    setHtml($("rotationBody"), html`<div class="field-head"><div><div class="eyebrow"><span class="eyebrow-line"></span> CROP ROTATION</div><h1>${plan.length}-season plan for ${a.name}</h1><p>Chosen from each crop's fit with your field, alternating families. Legumes (green outline) add nitrogen. Click a season or a growth stage for photos and timing.</p></div><button class="button button-dark" id="rerun" data-ic="refresh">Regenerate</button></div><div class="timeline">${cards}</div><p class="note">Illustrative sequence built from your field's climate and soil. Confirm sowing windows, disease history, seed access and market fit with local advisers. Change the number of seasons in Settings.</p>`);
    $("rerun").onclick = () => reanalyze();
  }
