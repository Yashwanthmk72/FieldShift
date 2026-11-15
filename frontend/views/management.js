/* AI-assisted: written with an AI coding assistant (see README, "AI tools used"). */
/* generated from FieldShift v0.4 app.js by the v1.0 module split; edited by hand afterwards */
import { html, setHtml } from "../lib/html.js";
import { needField } from "../lib/chrome.js";
import { $, FS, ic } from "../lib/state.js";
import { saveQuiet } from "../lib/storage.js";

export const CAT_ICON = { Water: "droplet", Soil: "layers", Crops: "sprout" };
export function renderManagement() {
    const a = needField("managementBody"); if (!a) return; const order = { high: 0, medium: 1, low: 2 }, groups = {}, done = new Set(a.done_actions || []), items = a.analysis.management;
    [...items].sort((x, y) => order[x.priority] - order[y.priority]).forEach((m) => (groups[m.category] ||= []).push(m));
    const total = items.length, nDone = items.filter((m) => done.has(m.id)).length;
    setHtml($("managementBody"), html`<div class="field-head"><div><div class="eyebrow"><span class="eyebrow-line"></span> LAND MANAGEMENT</div><h1>This week on ${a.name}</h1><p>Rule-based advice from recent weather and modelled soil. Always verify in the field.</p></div><div style="min-width:220px"><strong id="mgProg">${nDone} of ${total} done</strong><div class="bar"><i id="mgBar" style="width:${total ? nDone / total * 100 : 0}%"></i></div></div></div>${Object.entries(groups).map(([g, list]) => html`<div class="cat-head"><span class="cat-dot ${g}">${ic(CAT_ICON[g] || "leaf", 15)}</span>${g.toUpperCase()}</div><div class="mg">${list.map((m) => html`<article class="mg-card ${done.has(m.id) ? "done" : ""}" data-mg="${m.id}">${FS.pic("manage", m.image_key || "scouting", { alt: m.title })}<div class="badges"><span class="badge ${m.priority}">${m.priority.toUpperCase()}</span></div><div class="in"><h4>${m.title}</h4><p>${m.detail}</p>${m.why ? html`<p><strong>Why it matters:</strong> ${m.why}</p>` : ""}${m.steps?.length ? html`<ol>${m.steps.map((s) => html`<li>${s}</li>`)}</ol>` : ""}<div class="meta">${m.when ? html`<span>${ic("calendar", 13)}${m.when}</span>` : ""}${m.benefit ? html`<span>${ic("check", 13)}${m.benefit}</span>` : ""}</div><button class="button ${done.has(m.id) ? "button-light" : "button-dark"} button-compact donebtn" data-mgdone="${m.id}" aria-pressed="${done.has(m.id)}">${done.has(m.id) ? "Done ✓ (undo)" : "Mark as done"}</button></div></article>`)}</div>`)}`);
    $("managementBody").querySelectorAll("[data-mgdone]").forEach((b) => b.onclick = () => {
      const id = b.dataset.mgdone, s = new Set(a.done_actions || []); s.has(id) ? s.delete(id) : s.add(id); a.done_actions = [...s];
      const on = s.has(id); b.setAttribute("aria-pressed", on); b.textContent = on ? "Done ✓ (undo)" : "Mark as done"; b.classList.toggle("button-light", on); b.classList.toggle("button-dark", !on); b.closest(".mg-card").classList.toggle("done", on);
      const n = items.filter((m) => s.has(m.id)).length; $("mgProg").textContent = `${n} of ${total} done`; $("mgBar").style.width = (total ? n / total * 100 : 0) + "%"; saveQuiet({ ...a, done_actions: a.done_actions });
    });
  }
