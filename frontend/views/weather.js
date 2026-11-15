/* AI-assisted: written with an AI coding assistant (see README, "AI tools used"). Field "Weather" tab: model forecast, alerts, rain vs normal. */
import { html, setHtml } from "../lib/html.js";
import { needField } from "../lib/chrome.js";
import { $, S, fmtTemp } from "../lib/state.js";
import { api } from "../lib/api.js";
import { drawChart } from "../lib/charts.js";
import { failure, fieldHead, num, provenance, skeleton, unavailable } from "./common.js";

const todayIso = () => new Date().toISOString().slice(0, 10);

function paint(d) {
  const cur = d.current || {}, days = d.days || [], rvn = d.rainfall_vs_normal;
  const t = todayIso(), past = days.filter((x) => x.date < t).length;
  setHtml($("wxBody"), html`
    <article class="panel"><div class="panel-kicker">NOW · MODEL ESTIMATE</div>
      <div class="kv"><div><small>TEMPERATURE</small><b>${cur.temperature_2m != null ? fmtTemp(cur.temperature_2m) : "—"}</b></div><div><small>HUMIDITY</small><b>${num(cur.relative_humidity_2m, 0)}<small> %</small></b></div><div><small>PRECIPITATION</small><b>${num(cur.precipitation, 1)}<small> mm</small></b></div><div><small>HORIZON</small><b>${d.horizon_days}<small> days</small></b></div></div>
      ${d.alerts?.length ? html`<div class="alerts">${d.alerts.map((a) => html`<div class="alert alert-${a.type}"><b>${a.type === "heat" ? "Heat" : "Heavy rain"}</b> ${a.text}</div>`)}</div>` : html`<p class="note">No heat (≥ 35 °C) or heavy-rain (≥ 50 mm) days in this forecast window.</p>`}
      ${rvn ? html`<p class="note"><strong>Rain outlook:</strong> ${rvn.forecast_mm} mm forecast over the next ${rvn.days} days against about ${rvn.normal_mm_for_same_days} mm normal for the same period (NASA POWER long-term average). ${rvn.note}</p>` : ""}
    </article>
    <div class="two"><article class="panel"><div class="panel-kicker">TEMPERATURE</div><h3>Daily maximum and minimum</h3><div class="chart" id="wxTemp"></div></article>
    <article class="panel"><div class="panel-kicker">RAINFALL AND WATER DEMAND</div><h3>Daily rain and reference ET₀</h3><div class="chart" id="wxRain"></div></article></div>
    <article class="panel"><div class="panel-kicker">HOW TO READ THIS</div><h3>Forecast, not observation</h3><ul class="nodata"><li>These values come from a <strong>weather model</strong> (kind: forecast). They are not measurements at your field, and skill falls with lead time.</li><li>The first ${past} day(s) shown are the recent past as modelled; the rest are forecast. Observed NASA POWER history is on the <a href="#climate">Climate</a> tab.</li><li>Nothing here is real-time.</li></ul>${provenance(d.provenance)}</article>`);
  const xs = days.map((x) => x.date);
  drawChart($("wxTemp"), { xs, lines: [{ label: "Max", color: "#e5733a", values: days.map((x) => x.tmax) }, { label: "Min", color: "#3a8fd0", values: days.map((x) => x.tmin) }], unit: "°C", height: 200, aria: "Daily maximum and minimum temperature" });
  drawChart($("wxRain"), { xs, lines: [{ label: "ET₀ (mm)", color: "#e0a21a", values: days.map((x) => x.et0), dash: "5 4", width: 1.6 }], bars: { label: "Rain (mm)", values: days.map((x) => x.rain), color: "#3a8fd0" }, unit: "mm", height: 200, zero: true, aria: "Daily rain and reference evapotranspiration" });
}

export async function renderWeather() {
  const a = needField("weatherBody"); if (!a) return;
  setHtml($("weatherBody"), html`${fieldHead("WEATHER · OPEN-METEO MODEL", "Weather outlook", a)}<div id="wxBody">${skeleton(3)}</div>`);
  try {
    const d = await api(`/v1/weather?lat=${a.latitude}&lon=${a.longitude}`);
    if (S.view !== "weather") return;
    if (!d.available) { setHtml($("wxBody"), html`${unavailable("Forecast unavailable", d.error)}${provenance(d.provenance)}`); return; }
    paint(d);
    window.onresize = () => { if (S.view === "weather") paint(d); };
  } catch (e) { if (S.view === "weather") setHtml($("wxBody"), failure("Forecast unavailable", e)); }
}
