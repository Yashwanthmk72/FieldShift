/* AI-assisted: written with an AI coding assistant (see README, "AI tools used"). */
// Escape-by-default tagged template (audit defect D5). Interpolated values are escaped unless wrapped in raw().
const ESC = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;", "`": "&#96;" };
export const esc = (v) => String(v ?? "").replace(/[&<>"'`]/g, (c) => ESC[c]);
class Raw { constructor(s) { this.s = String(s); } toString() { return this.s; } }
export const raw = (s) => new Raw(s);
const part = (v) => (v instanceof Raw ? v.s : Array.isArray(v) ? v.map(part).join("") : esc(v));
export function html(strings, ...vals) {
  let out = strings[0];
  vals.forEach((v, i) => { out += part(v) + strings[i + 1]; });
  return new Raw(out);
}
export const setHtml = (el, value) => { el.innerHTML = part(value); };
export const insertHtml = (el, pos, value) => el.insertAdjacentHTML(pos, part(value));
// Only http(s)/relative URLs from the server are ever put into href/src (blocks javascript: and data: URLs).
export const safeUrl = (u) => { try { const x = new URL(String(u ?? ""), location.href); return x.protocol === "https:" || x.protocol === "http:" ? x.href : "#"; } catch { return "#"; } };
