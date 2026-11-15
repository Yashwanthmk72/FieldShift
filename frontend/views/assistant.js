/* AI-assisted: written with an AI coding assistant (see README, "AI tools used"). */
/* generated from FieldShift v0.4 app.js by the v1.0 module split; edited by hand afterwards */
import { html, setHtml } from "../lib/html.js";
import { $ } from "../lib/state.js";
import { api } from "../lib/api.js";

export function info(kicker, title, html, foot) { $("infoKicker").textContent = kicker; $("infoTitle").textContent = title; setHtml($("infoBody"), html); setHtml($("infoFoot"), foot || ""); if (!$("infoDialog").open) $("infoDialog").showModal(); }
export async function askAi(a, it) {
    if (!it) return; info("FIELD ASSISTANT", `Why ${it.crop.name}?`, "Thinking through the field conditions…", "Connecting…");
    try { const r = await api("/assistant", { method: "POST", body: JSON.stringify({ crop: it.crop.name, context: { score: it.live ?? it.score, components: it.components, evidence: it.evidence, best_sow_month: it.best_sow_month, location: { lat: a.latitude, lon: a.longitude } } }) }); $("infoBody").textContent = r.answer; $("infoFoot").textContent = r.mode + (r.model ? " · " + r.model : ""); }
    catch { $("infoBody").textContent = it.crop.description; $("infoFoot").textContent = "Local crop guide · backend unavailable"; }
  }
