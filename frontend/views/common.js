/* AI-assisted: written with an AI coding assistant (see README, "AI tools used"). Shared helpers for the v0.8 screens.
   All dynamic text goes through the escaping html`` helper. Raw SVG below is built only from numbers and our own colours. */
import { html, raw, esc } from "../lib/html.js";
import { api } from "../lib/api.js";

export const num = (v, d = 1) => (v == null || Number.isNaN(+v) ? "—" : (+v).toFixed(d));
export const todayIso = () => new Date().toISOString().slice(0, 10);

export const skeleton = (rows = 3) => html`<div class="skel-wrap" aria-busy="true" aria-label="Loading">${Array.from({ length: rows }, () => html`<div class="skel"></div>`)}</div>`;
export const failure = (title, e) => html`<div class="empty"><h3>${title}</h3><p>${e?.detail || e?.message || "The backend or an upstream data source could not be reached."} Nothing is estimated in its place.</p></div>`;
export const unavailable = (title, why) => html`<div class="empty"><h3>${title}</h3><p>${why || "No data available for this location."} Nothing is estimated in its place.</p></div>`;

export const fieldHead = (kicker, title, a, sub = "") => html`<div class="field-head"><div><div class="eyebrow"><span class="eyebrow-line"></span> ${kicker}</div><h1>${title}</h1><p>${a.name} · ${a.latitude.toFixed(3)}°, ${a.longitude.toFixed(3)}°${sub ? " · " + sub : ""}</p></div></div>`;

/* Where did this come from? One line per provider result: name, kind (observed/forecast/modelled), whether it worked, when. */
export const provenance = (list) => !list?.length ? "" : html`<p class="note prov">${list.map((p) => html`<span class="prov-i ${p.ok ? "ok" : "bad"}" title="${p.coverage || ""}">${p.ok ? "●" : "○"} ${p.source || p.name}${p.kind ? " · " + p.kind : ""}${p.ok ? "" : " · unavailable"}${p.fetched_at ? " · " + String(p.fetched_at).slice(0, 16).replace("T", " ") + " UTC" : ""}</span>`)}</p>`;

export const level = (l) => html`<span class="lvl lvl-${String(l).replace(/[^a-z]/g, "")}">${String(l || "unknown").toUpperCase()}</span>`;
export const tag = (t) => html`<span class="tag tag-${t}">${t === "user" ? "your input" : t}</span>`;

/* Donut from [{v, c}] where v is a count/number and c one of our own colours. Returns Raw html. */
export function donut(parts, size = 128, thick = 18, centre = "") {
  const tot = parts.reduce((s, p) => s + p.v, 0);
  const r = (size - thick) / 2, C = 2 * Math.PI * r;
  let off = 0, segs = "";
  if (tot > 0) parts.forEach((p) => { if (p.v <= 0) return; const len = p.v / tot * C; segs += `<circle r="${r}" cx="${size / 2}" cy="${size / 2}" fill="none" stroke="${p.c}" stroke-width="${thick}" stroke-dasharray="${len.toFixed(2)} ${(C - len).toFixed(2)}" stroke-dashoffset="${(-off).toFixed(2)}" transform="rotate(-90 ${size / 2} ${size / 2})"/>`; off += len; });
  return raw(`<svg class="donut-svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" role="img" aria-label="Donut chart"><circle r="${r}" cx="${size / 2}" cy="${size / 2}" fill="none" stroke="var(--line)" stroke-width="${thick}"/>${segs}<text x="50%" y="50%" text-anchor="middle" dominant-baseline="central" class="donut-c">${esc(centre)}</text></svg>`);
}
export const legend = (parts) => html`<ul class="lg">${parts.map((p) => html`<li><i style="background:${p.c}"></i>${p.label}<b>${p.v}</b></li>`)}</ul>`;

let cropsCache = null;
export async function loadCrops() { if (!cropsCache) cropsCache = await api("/v1/crops"); return cropsCache; }
export const cropOptions = (crops, sel) => crops.map((c) => html`<option value="${c.id}" ${c.id === sel ? "selected" : ""}>${c.name}</option>`);
export const bandOf = (s) => (s >= 80 ? 0 : s >= 60 ? 1 : s >= 40 ? 2 : 3);
export const BANDS = [["Excellent", "#2f9e5b"], ["Good", "#9bc53d"], ["Average", "#e8a33b"], ["Poor", "#d9534f"]];

/* Download a blob from an authenticated endpoint (exports need the guest/Bearer header, so a plain link will not work). */
export function saveBlob(blob, name) {
  const u = URL.createObjectURL(blob), a = document.createElement("a");
  a.href = u; a.download = name; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(u), 2000);
}
