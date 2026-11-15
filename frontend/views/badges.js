/* AI-assisted: written with an AI coding assistant. Confidence, "illustrative estimate" and freshness badges. */
import { html } from "../lib/html.js";

export function confInfo(item) {
  const c = item?.confidence || {}, illus = c.illustrative ?? (item?.heuristic_params || []).some((k) => ["temp", "rain", "ph"].includes(k));
  let level = c.level || "low"; if (illus && level === "high") level = "medium"; /* heuristic ranges cap confidence at medium */
  return { level, illus, label: { low: "Low confidence", medium: "Medium confidence", high: "High confidence" }[level], reasons: c.reasons || [] };
}
export const confBadge = (item) => {
  const i = confInfo(item);
  return html`<span class="badges"><span class="conf conf-${i.level}" title="${i.reasons.join(" ") || "How much we trust the inputs behind this ranking. It is not the chance of a good harvest."}">${i.label}</span>${i.illus ? html`<span class="badge-illus" title="Temperature, rainfall and pH ranges for this crop are heuristic estimates, not verified against a source.">Illustrative estimate</span>` : ""}</span>`;
};
export const freshBadge = (f) => !f ? "" : html`<span class="fresh fresh-${f.code}${f.stale ? " fresh-stale" : ""}" title="Data cadence of the source. Nothing here is real-time.">${f.label}</span>`;
