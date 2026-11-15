/* AI-assisted: written with an AI coding assistant (see README, "AI tools used"). */
/* generated from FieldShift v0.4 app.js by the v1.0 module split; edited by hand afterwards */
import { html } from "../lib/html.js";
import { FS, MONTHS, S, cap, fmtArea, fmtTemp, ic, monthName, ringPts, topCrop } from "../lib/state.js";

export const polySvg = (geometry) => {
    if (!geometry) return ""; let pts; try { pts = ringPts(geometry); } catch { return ""; }
    const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]), x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
    const s = Math.max(x1 - x0, y1 - y0) || 1, W = 100, H = 60, k = Math.min(W - 16, H - 12) / s, ox = (W - (x1 - x0) * k) / 2, oy = (H - (y1 - y0) * k) / 2;
    const d = pts.map((p, i) => `${i ? "L" : "M"}${(ox + (p[0] - x0) * k).toFixed(1)} ${(H - oy - (p[1] - y0) * k).toFixed(1)}`).join("") + "Z";
    return html`<svg class="poly" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet" aria-hidden="true"><path d="${d}" fill="rgba(215,255,170,.3)" stroke="#e6ffc0" stroke-width="1.4" stroke-linejoin="round"/></svg>`;
  };
export const ring = (score, extra = "") => html`<span class="ring" style="--p:${score}" ${extra}><b>${score}</b></span>`;
export const metric = (label, value, note, tone = "green", icon = "leaf", thumb = "") => html`<article class="metric-card tone-${tone}"><div class="metric-head"><span class="metric-icon">${ic(icon, 16)}</span><span class="metric-label">${label}</span></div><div class="metric-value">${value}</div><div class="metric-foot">${note}</div>${thumb}</article>`;
export const cropThumb = (c, cls = "", style = "") => FS.pic("crop", c.id, { cls: `round ${cls}`, family: c.family, alt: c.name, credit: false, style });
export function weatherKey(c) {
    const l = c?.latest || {}, t = l.temperature_c?.value, w = l.root_zone_wetness?.value, r = c?.rainfall_14d_mm, sol = l.solar_mj_m2_day?.value;
    if (r != null && r > 45) return "heavy-rain"; if (r != null && r > 15) return "light-rain"; if (w != null && w < .25) return "dry";
    if (t != null && t > 33) return "heat"; if (t != null && t < 12) return "cool"; if (w != null && w > .7 && t > 24) return "humid";
    if (sol != null && sol < 9) return "cloudy"; return "sunny";
  }
export const WEATHER_TXT = { "heavy-rain": ["Heavy rain", "Plenty of recent rain. Watch drainage and waterlogging."], "light-rain": ["Some rain", "Moderate recent rainfall – good for establishment."], dry: ["Dry spell", "The gridded root zone looks dry. Check soil moisture in the field."], heat: ["Hot spell", "High temperatures speed up water loss – mulch and irrigate early."], cool: ["Cool conditions", "Cool weather slows warm-season crops and favours cool-season ones."], humid: ["Warm and humid", "Warm, moist conditions – scout for fungal disease."], sunny: ["Fair and sunny", "Settled weather. Plan irrigation from soil checks, not the sky."], cloudy: ["Overcast", "Lower sunlight this fortnight; growth may be slower."] };
export const SOIL_TXT = { sand: "drains very fast, holds little water", "loamy-sand": "drains fast, low nutrient holding", "sandy-loam": "easy to work, drains well", loam: "balanced – the classic farm soil", "silt-loam": "fertile, holds water well", silt: "smooth, erodes easily when bare", "sandy-clay-loam": "good water and nutrient balance", "clay-loam": "holds water and nutrients, can be heavy", "silty-clay-loam": "fertile but compacts when wet", "sandy-clay": "sticky when wet, hard when dry", "silty-clay": "very slow to drain", clay: "holds water, slow to drain, easy to compact" };
export function conditions(a) {
    const an = a.analysis, c = an.climate || {}, l = c.latest || {}, wk = weatherKey(c), [wt, wd] = WEATHER_TXT[wk], so = an.soil || {}, tk = so.texture_key || "loam", best = topCrop(a);
    const ph = so.ph, phPos = ph != null ? Math.max(0, Math.min(100, (ph - 3.5) / 5 * 100)) : null;
    return html`<section class="cond">
      <article class="panel cond-card">${FS.pic("weather", wk, { alt: wt })}<div class="in"><div class="panel-kicker">WEATHER · LAST 14 DAYS</div><h3>${wt}</h3><p>${l.temperature_c?.value != null ? fmtTemp(l.temperature_c.value) + " · " : ""}${c.rainfall_14d_mm != null ? c.rainfall_14d_mm.toFixed(0) + " mm rain · " : ""}${wd}</p></div></article>
      <article class="panel cond-card">${FS.pic("soil", tk, { alt: so.texture || "Soil" })}<div class="in"><div class="panel-kicker">SOIL · ${so.depth || "topsoil"}</div><h3>${so.texture || "Soil estimate"}</h3><p>${SOIL_TXT[tk] ? cap(SOIL_TXT[tk]) + ". " : ""}${ph != null ? `pH ${ph}` : "pH unavailable"}${so.organic_carbon_g_kg != null ? ` · ${so.organic_carbon_g_kg} g/kg carbon` : ""}</p>${phPos != null ? html`<div class="gauge-ph" title="Soil pH ${ph}"><i style="left:${phPos}%"></i></div>` : ""}</div></article>
      ${best ? html`<article class="panel cond-card lift" data-open-crop="${best.crop.id}" tabindex="0" role="link">${cropThumb(best.crop, "", "height:132px")}<div class="in"><div class="panel-kicker">GROWING OUTLOOK</div><h3>${best.crop.name} · ${best.score}/100</h3><p>${best.best_sow_month ? html`Best climate fit if sown in <strong>${monthName(best.best_sow_month)}</strong>. ` : ""}Tap for photos, timing and advice.</p></div></article>` : ""}</section>`;
  }
export function climateMetrics(a) {
    const c = a.analysis.climate || {}, l = c.latest || {}, t = l.temperature_c?.value, w = l.root_zone_wetness?.value;
    return html`<section class="metrics-grid">${metric("AIR TEMPERATURE", t != null ? fmtTemp(t) : "—", t != null ? "Daily · " + l.temperature_c.date : "Not available", "amber", "thermo")}${metric("RAINFALL · 14 DAYS", c.rainfall_14d_mm != null ? html`${c.rainfall_14d_mm.toFixed(1)}<small> mm</small>` : "—", "NASA POWER", "aqua", "rain")}${metric("ROOT-ZONE MOISTURE", w != null ? html`${w.toFixed(2)}<small> / 1</small>` : "—", "Gridded estimate", "green", "droplet")}${metric("FIELD AREA", fmtArea(a.area_ha), `${a.latitude.toFixed(3)}°, ${a.longitude.toFixed(3)}°`, "lime", "pin")}</section>`;
  }
export function normalsChart(nm, shade = []) {
    if (!nm) return html`<p class="note">Long-term climate averages are not available for this field.</p>`;
    const W = 360, H = 124, pl = 6, pr = 6, pt = 10, pb = 18, iw = W - pl - pr, ih = H - pt - pb, bw = iw / 12, maxR = Math.max(...nm.rain_mm_month, 1), t0 = Math.min(...nm.temperature_c) - 2, t1 = Math.max(...nm.temperature_c) + 2;
    const ty = (t) => pt + ih - ih * (t - t0) / (t1 - t0 || 1);
    const bars = nm.rain_mm_month.map((r, i) => html`<rect x="${pl + i * bw + bw * .18}" y="${pt + ih - ih * r / maxR}" width="${bw * .64}" height="${ih * r / maxR}" rx="3" fill="var(--aqua)" opacity=".55"/>`);
    const sh = shade.map((m) => html`<rect x="${pl + (m - 1) * bw}" y="${pt}" width="${bw}" height="${ih}" fill="var(--amber)" opacity=".2"/>`);
    const pts = nm.temperature_c.map((t, i) => [pl + i * bw + bw / 2, ty(t)]);
    const line = html`<path d="${pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join("")}" fill="none" stroke="var(--amber)" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>${pts.map((p) => html`<circle cx="${p[0].toFixed(1)}" cy="${p[1].toFixed(1)}" r="2.6" fill="var(--amber)"/>`)}`;
    const lab = MONTHS.map((m, i) => html`<text x="${pl + i * bw + bw / 2}" y="${H - 4}" text-anchor="middle">${m[0]}</text>`);
    return html`<svg class="spark" viewBox="0 0 ${W} ${H}" role="img" aria-label="Typical monthly temperature and rainfall">${sh}${bars}${line}${lab}</svg><div class="legend"><span style="--c:var(--amber)">Temperature (${S.settings.temp_unit === "F" ? "°F" : "°C"}): ${fmtTemp(Math.min(...nm.temperature_c))} – ${fmtTemp(Math.max(...nm.temperature_c))}</span><span style="--c:var(--aqua)">Rain: up to ${Math.round(maxR)} mm/month</span>${shade.length ? html`<span style="--c:rgba(240,160,32,.4)">Growing season</span>` : ""}</div>`;
  }
export const heroSvg = () => html`<svg viewBox="0 0 520 260" preserveAspectRatio="xMidYMax slice" aria-hidden="true"><defs><linearGradient id="hs" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffe9b0"/><stop offset="1" stop-color="#d9f3e0"/></linearGradient><linearGradient id="hh" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#52b97c"/><stop offset="1" stop-color="#1f7a4b"/></linearGradient></defs><rect width="520" height="260" fill="url(#hs)" opacity=".7"/><circle cx="380" cy="70" r="46" fill="#ffb84d" opacity=".95"/><circle cx="380" cy="70" r="76" fill="#ffd27a" opacity=".3"/><path d="M0 170 Q130 118 260 160 T520 140 V260 H0Z" fill="url(#hh)"/><path d="M0 214 Q150 170 300 206 T520 190 V260 H0Z" fill="#17653d"/>${Array.from({ length: 9 }, (_, i) => html`<path d="M${-20 + i * 70} 260 L${150 + i * 34} 196" stroke="#c8f169" stroke-opacity=".4" stroke-width="3"/>`)}<g fill="#fff" opacity=".9"><ellipse cx="120" cy="60" rx="36" ry="13"/><ellipse cx="100" cy="52" rx="20" ry="14"/><ellipse cx="138" cy="48" rx="22" ry="16"/></g></svg>`;
