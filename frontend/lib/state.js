/* AI-assisted: written with an AI coding assistant (see README, "AI tools used"). */
/* generated from FieldShift v0.4 app.js by the v1.0 module split; edited by hand afterwards */
import { html, insertHtml, esc } from "./html.js";
import { icon } from "./icons.js";

export const FS = (window.FS = window.FS || {});
export const ic = icon;
export const $ = (id) => document.getElementById(id);
FS.$ = $;
FS.esc = esc;
export const read = (k, d) => { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } };
export const write = (k, v) => { try { localStorage.setItem(k, typeof v === "string" ? v : JSON.stringify(v)); } catch { /* storage unavailable */ } };
export const wid = (() => { try { return localStorage.getItem("fs-workspace") || (() => { const id = crypto.randomUUID(); localStorage.setItem("fs-workspace", id); return id; })(); } catch { return crypto.randomUUID(); } })();
export const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export const DEFAULTS = { name: "Farmer", area_unit: "ha", temp_unit: "C", seasons: 4, map_style: "satellite", start_globe: true, labels: true, theme: "system", layout: "grid", glow: 70, priorities: { resilience: 34, profit: 0, soil: 33, water: 33 }, _ts: 0 };
export const S = FS.S = { settings: { ...DEFAULTS, ...read("fs-settings", {}) }, fields: [], activeId: (() => { try { return localStorage.getItem("fs-active"); } catch { return null; } })(), online: false, view: "overview", arg: "", compare: false, focusStage: null, cropFrom: "crops",
    draft: { pts: [], drawing: false, geometry: null, area: 0, analysis: null, saved: null } };
export const ACTIVE_VIEWS = ["field", "weather", "climate", "crops", "irrigation", "soilhealth", "pests", "finance", "rotation", "management"];
export const TAB_LABELS = { field: "Overview", weather: "Weather", climate: "Climate", crops: "Crop advisor", irrigation: "Irrigation", soilhealth: "Soil health", pests: "Pests & disease", finance: "Finance", rotation: "Crop rotation", management: "Land management" };
export const PRIOS = [
    ["resilience", "Resilience", "heart", "Handles heat, drought and shocks."],
    ["water", "Save water", "droplet", "Prefers crops that need less water."],
    ["soil", "Soil health", "layers", "Rewards good pH fit and nitrogen-fixing rotations."],
  ];
/* The old "Yield & value" slider stays hidden: FieldShift has no real yield data. Prices live on the Market page as an "Estimated gross value" (never profit). */
export const YIELD_DATA_AVAILABLE = false;
export const HEAVY_N = new Set(["maize", "wheat", "rice", "potato", "sorghum", "sunflower"]);
export function toast(m) { const n = $("toast"); n.textContent = m; n.classList.add("show"); clearTimeout(toast.t); toast.t = setTimeout(() => n.classList.remove("show"), 3400); }
FS.toast = toast;
export const fmtArea = (ha) => ha == null ? "—" : S.settings.area_unit === "ac" ? `${(ha * 2.47105).toFixed(1)} ac` : `${Number(ha).toFixed(ha < 10 ? 2 : 1)} ha`;
export const fmtTemp = (c) => c == null ? "—" : S.settings.temp_unit === "F" ? `${(c * 9 / 5 + 32).toFixed(0)}°F` : `${c.toFixed(1)}°C`;
FS.fmtArea = fmtArea;
FS.fmtTemp = fmtTemp;
export const active = () => S.fields.find((f) => String(f.id) === String(S.activeId)) || null;
FS.active = active;
FS.currentLat = () => active()?.latitude ?? 0;
export const normP = (p) => { const t = Object.values(p).reduce((a, b) => a + b, 0) || 1; return Object.fromEntries(Object.entries(p).map(([k, v]) => [k, v / t])); };
export function areaHa(pts) { let a = 0; pts.forEach((p, i) => { const q = pts[(i + 1) % pts.length]; a += ((q[0] - p[0]) * Math.PI / 180) * (2 + Math.sin(p[1] * Math.PI / 180) + Math.sin(q[1] * Math.PI / 180)); }); return Math.abs(a * 6378137 ** 2 / 2) / 10000; }
export const centroid = (pts) => ({ lat: pts.reduce((s, p) => s + p[1], 0) / pts.length, lon: pts.reduce((s, p) => s + p[0], 0) / pts.length });
export const polyGeo = (pts) => ({ type: "Polygon", coordinates: [[...pts, pts[0]]] });
export const ringPts = (g) => { const c = (g.type === "MultiPolygon" ? g.coordinates[0] : g.coordinates)[0]; return c.slice(0, -1).map(([x, y]) => [x, y]); };
export const bounds = (pts) => pts.reduce((b, p) => b.extend(p), new maplibregl.LngLatBounds(pts[0], pts[0]));
Object.assign(FS, { areaHa, centroid, polyGeo, ringPts, bounds });
export const topCrop = (f) => f?.analysis?.ranked?.[0];
export const monthName = (m) => MONTHS[(m - 1 + 12) % 12];
export const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);
FS.decorate = (root = document) => root.querySelectorAll("[data-ic]:not([data-dec])").forEach((el) => {
    el.dataset.dec = "1"; const svg = ic(el.dataset.ic, el.classList.contains("nav-item") ? 20 : 16);
    insertHtml(el, "afterbegin", el.classList.contains("nav-item") ? html`<span class="ico">${svg}</span>` : svg);
  });
export function seasonName(m, lat) {
    if (Math.abs(lat) < 23.5) return "Rainy-season window";
    const i = [[12, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]].findIndex((a) => a.includes(m));
    return ["Winter", "Spring", "Summer", "Autumn"][(i + (lat >= 0 ? 0 : 2)) % 4];
  }
export const monthSpan = (ms) => !ms?.length ? "—" : ms.length > 1 ? `${monthName(ms[0])}–${monthName(ms[ms.length - 1])}` : monthName(ms[0]);
