/* AI-assisted: written with an AI coding assistant. Dependency-free SVG charts (line, bars, shaded difference, hover tooltip). */
import { esc, raw, setHtml } from "./html.js";

const NS = 14;
const fmtDate = (s) => { const d = new Date(s + "T00:00:00Z"); return d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "2-digit", timeZone: "UTC" }); };
const niceTicks = (lo, hi, n = 4) => {
  if (!isFinite(lo) || !isFinite(hi)) return [0, 1];
  if (lo === hi) { lo -= 1; hi += 1; }
  const step = Math.pow(10, Math.floor(Math.log10((hi - lo) / n))), err = (hi - lo) / n / step, m = err >= 7.5 ? 10 : err >= 3.5 ? 5 : err >= 1.5 ? 2 : 1, s = m * step;
  const out = []; for (let v = Math.ceil(lo / s) * s; v <= hi + 1e-9; v += s) out.push(+v.toFixed(6)); return out;
};

/* cfg: { xs:[ISO dates], lines:[{label,color,values,dash,width}], bars:{label,values,color}|null, shade:{a,b,up,down}|null, unit, height, decimals } */
export function drawChart(el, cfg) {
  const W = Math.max(280, el.clientWidth || 640), H = cfg.height || 220, L = 44, R = 10, T = 10, B = 24, n = cfg.xs.length, dec = cfg.decimals ?? 1;
  const all = [];
  cfg.lines.forEach((l) => l.values.forEach((v) => v != null && all.push(v)));
  if (cfg.bars) cfg.bars.values.forEach((v) => v != null && all.push(v, 0));
  if (!n || !all.length) { setHtml(el, raw('<p class="note">No values in this range.</p>')); return; }
  let lo = Math.min(...all), hi = Math.max(...all); const pad = (hi - lo || 1) * 0.08; lo = cfg.zero ? Math.min(0, lo) : lo - pad; hi += pad;
  const ticks = niceTicks(lo, hi), y0 = Math.min(lo, ticks[0]), y1 = Math.max(hi, ticks[ticks.length - 1]);
  const X = (i) => L + (n === 1 ? (W - L - R) / 2 : (i / (n - 1)) * (W - L - R)), Y = (v) => T + (1 - (v - y0) / (y1 - y0)) * (H - T - B);
  let g = "";
  ticks.forEach((t) => { g += `<line x1="${L}" x2="${W - R}" y1="${Y(t)}" y2="${Y(t)}" class="ch-grid"/><text x="${L - 6}" y="${Y(t) + 4}" text-anchor="end" class="ch-ax">${esc(+t.toFixed(dec))}</text>`; });
  const step = Math.max(1, Math.ceil(n / Math.max(2, Math.floor((W - L - R) / 90))));
  for (let i = 0; i < n; i += step) g += `<text x="${X(i)}" y="${H - 6}" text-anchor="${i === 0 ? "start" : "middle"}" class="ch-ax">${esc(fmtDate(cfg.xs[i]))}</text>`;
  if (cfg.shade) {
    const { a, b, up, down } = cfg.shade;
    for (let i = 0; i < n - 1; i++) {
      if ([a[i], b[i], a[i + 1], b[i + 1]].some((v) => v == null)) continue;
      const avg = (a[i] - b[i] + a[i + 1] - b[i + 1]) / 2;
      g += `<path d="M${X(i)} ${Y(a[i])} L${X(i + 1)} ${Y(a[i + 1])} L${X(i + 1)} ${Y(b[i + 1])} L${X(i)} ${Y(b[i])}Z" fill="${avg >= 0 ? up : down}" opacity=".28"/>`;
    }
  }
  if (cfg.bars) { const bw = Math.max(1, (W - L - R) / n - 1); cfg.bars.values.forEach((v, i) => { if (v != null && v > 0) g += `<rect x="${X(i) - bw / 2}" y="${Y(v)}" width="${bw}" height="${Y(0) - Y(v)}" fill="${cfg.bars.color}" opacity=".85"/>`; }); }
  cfg.lines.forEach((l) => {
    let d = "", pen = false;
    l.values.forEach((v, i) => { if (v == null) { pen = false; return; } d += `${pen ? "L" : "M"}${X(i).toFixed(1)} ${Y(v).toFixed(1)} `; pen = true; });
    if (d) g += `<path d="${d}" fill="none" stroke="${l.color}" stroke-width="${l.width || 2}" ${l.dash ? `stroke-dasharray="${l.dash}"` : ""} stroke-linejoin="round" stroke-linecap="round"/>`;
    if (n <= 40) l.values.forEach((v, i) => { if (v != null && !l.dash) g += `<circle cx="${X(i)}" cy="${Y(v)}" r="2.6" fill="${l.color}"/>`; });
  });
  const legend = [...cfg.lines.map((l) => [l.label, l.color, l.dash]), ...(cfg.bars ? [[cfg.bars.label, cfg.bars.color]] : []), ...(cfg.shade?.legend ? cfg.shade.legend : [])].map(([t, c, d]) => `<span><i style="background:${d ? "transparent" : c};border-top:${d ? `2px dashed ${c}` : "none"}"></i>${esc(t)}</span>`).join("");
  /* markup below is built only from numbers, our own colours and esc()-escaped labels */
  setHtml(el, raw(`<div class="ch-legend">${legend}</div><div class="ch-wrap"><svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}" role="img" aria-label="${esc(cfg.aria || "Chart")}">${g}<line class="ch-cross" y1="${T}" y2="${H - B}" x1="-10" x2="-10"/></svg><div class="ch-tip" hidden></div></div>`));
  const svg = el.querySelector("svg"), tip = el.querySelector(".ch-tip"), cross = el.querySelector(".ch-cross");
  const move = (ev) => {
    const r = svg.getBoundingClientRect(), px = ((ev.clientX ?? ev.touches?.[0]?.clientX) - r.left) / r.width * W, i = Math.max(0, Math.min(n - 1, Math.round(((px - L) / (W - L - R)) * (n - 1))));
    cross.setAttribute("x1", X(i)); cross.setAttribute("x2", X(i));
    const rows = [...cfg.lines.map((l) => [l.label, l.values[i]]), ...(cfg.bars ? [[cfg.bars.label, cfg.bars.values[i]]] : [])].map(([k, v]) => `<div>${esc(k)}: <b>${v == null ? "no data" : esc(+v.toFixed(dec + 1)) + " " + esc(cfg.unit || "")}</b></div>`).join("");
    setHtml(tip, raw(`<strong>${esc(fmtDate(cfg.xs[i]))}</strong>${rows}`)); tip.hidden = false;
    tip.style.left = Math.min(Math.max(8, X(i) / W * r.width - 60), r.width - 150) + "px";
  };
  const leave = () => { tip.hidden = true; cross.setAttribute("x1", -10); cross.setAttribute("x2", -10); };
  svg.addEventListener("mousemove", move); svg.addEventListener("touchmove", move, { passive: true }); svg.addEventListener("mouseleave", leave); svg.addEventListener("touchend", leave);
}

export function sparkline(values, color = "var(--green-2, #2f8f5b)", w = 120, h = 32) {
  const v = values.filter((x) => x != null); if (v.length < 2) return "";
  const lo = Math.min(...v), hi = Math.max(...v), X = (i) => (i / (v.length - 1)) * (w - 4) + 2, Y = (x) => h - 3 - ((x - lo) / (hi - lo || 1)) * (h - 6);
  return `<svg class="spark" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" aria-hidden="true"><path d="${v.map((x, i) => `${i ? "L" : "M"}${X(i).toFixed(1)} ${Y(x).toFixed(1)}`).join(" ")}" fill="none" stroke="${color}" stroke-width="1.8"/></svg>`;
}
export { fmtDate };
