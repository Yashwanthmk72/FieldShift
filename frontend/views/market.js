/* AI-assisted: written with an AI coding assistant. Market page: price board, ticker, charts, converter, estimated gross value. */
import { html, setHtml, safeUrl } from "../lib/html.js";
import { $, FS, S, active, fmtArea, ic } from "../lib/state.js";
import { API, api, post } from "../lib/api.js";
import { drawChart, sparkline } from "../lib/charts.js";
import { freshBadge } from "./badges.js";

const MASS = { kg: 1, tonne: 1000, quintal: 100, lb: 0.45359237 };
const UL = { kg: "kg", tonne: "tonne", quintal: "quintal", lb: "lb" };
const st = { meta: null, board: null, fx: null, country: "WORLD", cur: "native", unit: "native", es: null, poll: null, sel: null, checked: null };

export function convert(v, sCur, sUnit, dCur, dUnit, fx) {
  let x = v / MASS[sUnit] * MASS[dUnit];
  if (sCur !== dCur) { const r = fx?.rates; if (!r || !r[sCur] || !r[dCur]) return null; x = x / r[sCur] * r[dCur]; }
  return x;
}
const target = (s) => ({ cur: st.cur === "native" ? s.currency : st.cur, unit: st.unit === "native" ? s.unit : st.unit });
const money = (v, cur) => v == null ? "—" : `${cur} ${v >= 100 ? v.toLocaleString(undefined, { maximumFractionDigits: 0 }) : v.toFixed(v >= 1 ? 2 : 3)}`;
function shown(s) {
  const t = target(s), pts = s.points.map((p) => ({ date: p.date, value: convert(p.value, s.currency, s.unit, t.cur, t.unit, st.fx) }));
  if (pts.some((p) => p.value == null)) return { ok: false, cur: s.currency, unit: s.unit, pts: s.points, note: `No ECB exchange rate for ${t.cur}; showing the original ${s.currency}.` };
  return { ok: true, cur: t.cur, unit: t.unit, pts, note: t.cur !== s.currency || t.unit !== s.unit ? `Converted from ${s.currency}/${s.unit}${t.cur !== s.currency && st.fx?.date ? ` using ECB rates dated ${st.fx.date}` : ""}.` : "" };
}

function stop() { st.es?.close(); st.es = null; clearInterval(st.poll); st.poll = null; }
function live() {
  stop();
  const url = `${API}/api/v1/market/stream?country=${st.country}&interval=60`;
  try {
    st.es = new EventSource(url);
    st.es.addEventListener("prices", (e) => { if (S.view !== "market") return stop(); st.board = JSON.parse(e.data); st.checked = new Date(); paint(); });
    st.es.addEventListener("tick", () => { st.checked = new Date(); stamp(); });
    st.es.onerror = () => { st.es?.close(); st.es = null; if (!st.poll) st.poll = setInterval(refetch, 60000); };
  } catch { st.poll = setInterval(refetch, 60000); }
}
async function refetch() { if (S.view !== "market") return stop(); try { st.board = await api(`/v1/market/board?country=${st.country}`); st.checked = new Date(); paint(); } catch { /* keep last */ } }
const stamp = () => { const e = $("mkChecked"); if (e && st.checked) e.textContent = `Checked ${st.checked.toLocaleTimeString()}`; };

function ticker() {
  const items = Object.values(st.board.crops).filter((r) => !r.no_data && r.latest);
  if (!items.length) return html`<div class="ticker empty-t">No crop has a price source for ${st.board.country_name}. See the list below.</div>`;
  return html`<div class="ticker" role="list" aria-label="Latest prices">${items.map((r) => { const d = shown(r), last = d.pts[d.pts.length - 1].value, ch = r.stats?.change_pct; return html`<a class="tick" href="#mk-${r.crop}" role="listitem"><b>${FS.cropName?.(r.crop) || r.crop}</b><span>${money(last, d.cur)}<small>/${UL[d.unit]}</small></span>${ch == null ? "" : html`<em class="${ch >= 0 ? "up" : "dn"}">${ch >= 0 ? "▲" : "▼"} ${Math.abs(ch)}%</em>`}${freshBadge(r.freshness)}</a>`; })}</div>`;
}
function card(r) {
  const d = shown(r), last = d.pts[d.pts.length - 1];
  return html`<article class="panel mk-card" id="mk-${r.crop}"><div class="panel-heading"><div><div class="panel-kicker">${r.country === "IN" ? "INDIA · MANDI" : "WORLD BENCHMARK"}</div><h3>${FS.cropName?.(r.crop) || r.crop}</h3></div>${freshBadge(r.freshness)}</div>
    <div class="mk-price">${money(last.value, d.cur)}<small> ${UL[d.unit] ? "per " + UL[d.unit] : ""}</small></div>
    <div class="mk-chart" data-chart="${r.crop}"></div>
    <p class="note">As of <strong>${r.as_of}</strong> · ${r.source} · <a href="${safeUrl(r.source_url)}" target="_blank" rel="noreferrer noopener">${r.series_id}</a><br>${r.title}${r.proxy_note ? html`<br><strong>Note:</strong> ${r.proxy_note}` : ""}${d.note ? html`<br>${d.note}` : ""}${r.stale_reason ? html`<br><strong>Stale:</strong> ${r.stale_reason}` : ""}${r.note ? html`<br>${r.note}` : ""}</p></article>`;
}
function paint() {
  const root = $("marketBody"); if (!root || !st.board) return;
  const rows = Object.values(st.board.crops), has = rows.filter((r) => !r.no_data), none = rows.filter((r) => r.no_data);
  const keyed = st.board.providers.filter((p) => !p.configured);
  setHtml($("mkTicker"), ticker());
  setHtml($("mkCards"), html`${has.length ? has.map(card) : html`<div class="empty"><h3>No prices for ${st.board.country_name}</h3><p>${none[0]?.reason || "No source is configured."} FieldShift never estimates a price.</p></div>`}`);
  setHtml($("mkNone"), html`${none.length ? html`<details class="panel"><summary><strong>${none.length} crops with no data</strong> for ${st.board.country_name}</summary><ul class="nodata">${none.map((r) => html`<li><b>${FS.cropName?.(r.crop) || r.crop}</b> — ${r.reason}</li>`)}</ul></details>` : ""}${keyed.map((p) => html`<p class="note">${p.name}: ${p.note}</p>`)}`);
  has.forEach((r) => { const el = document.querySelector(`[data-chart="${r.crop}"]`); if (!el) return; const d = shown(r); drawChart(el, { xs: d.pts.map((p) => p.date), lines: [{ label: `${d.cur}/${d.unit}`, color: "#2f8f5b", values: d.pts.map((p) => p.value) }], unit: `${d.cur}/${d.unit}`, height: 150, decimals: d.pts[0].value < 10 ? 3 : 1, aria: `${r.crop} price history` }); });
  setHtml($("gvCrop"), has.map((r) => html`<option value="${r.crop}">${FS.cropName?.(r.crop) || r.crop}</option>`));
  stamp();
}
export async function renderMarket() {
  stop();
  setHtml($("marketHead"), html`<div class="view-head"><div><div class="eyebrow"><span class="eyebrow-line"></span> MARKET</div><h1>Market prices</h1><p>Real published prices only. <strong>Nothing here is real-time</strong>: every price shows its source, as-of date and cadence (daily or monthly). Where no source exists we say “no data” instead of guessing.</p></div><span class="note" id="mkChecked"></span></div>`);
  setHtml($("marketBody"), html`<p class="note">Loading prices…</p>`);
  try { [st.meta, st.fx] = await Promise.all([api("/v1/market/meta"), api("/v1/market/fx").catch(() => null)]); st.board = await api(`/v1/market/board?country=${st.country}`); } catch {
    setHtml($("marketBody"), html`<div class="empty"><h3>Market prices need the backend</h3><p>Start the server (<code>uvicorn backend.main:app</code>) to load price sources.</p></div>`); return; }
  FS.cropName = (id) => st.meta.crops.find((c) => c.id === id)?.name || id;
  const m = st.meta, a = active();
  setHtml($("marketBody"), html`<div class="mk-controls panel"><label>Country<select id="mkCountry">${m.countries.map((c) => html`<option value="${c.code}" ${c.code === st.country ? "selected" : ""}>${c.name}</option>`)}</select></label>
    <label>Currency<select id="mkCur"><option value="native">Original</option>${m.currencies.map((c) => html`<option ${c === st.cur ? "selected" : ""}>${c}</option>`)}</select></label>
    <label>Unit<select id="mkUnit"><option value="native">Original</option>${m.units.map((u) => html`<option value="${u}" ${u === st.unit ? "selected" : ""}>${UL[u] || u}</option>`)}</select></label>
    <p class="note" style="margin:0;flex:1 1 220px">${st.fx?.ok ? `Exchange rates: ${st.fx.source}, ${st.fx.date}. Daily reference rates, not trading quotes.` : "Exchange rates unavailable: values stay in their original currency."}</p></div>
    <div id="mkTicker"></div><div class="mk-grid" id="mkCards"></div><div id="mkNone"></div>
    <article class="panel" id="gvPanel"><div class="panel-kicker">ESTIMATED GROSS VALUE</div><h3>Revenue estimate, not profit</h3><p class="note" style="margin-top:0">Area × your expected yield × the latest published price. You enter the yield: FieldShift has no yield data. Costs are not included, and this is not a forecast.</p>
      <div class="mk-controls"><label>Crop<select id="gvCrop"></select></label><label>Area (ha)<input id="gvArea" type="number" min="0" step="any" value="${a?.area_ha ? a.area_ha.toFixed(2) : ""}" placeholder="e.g. 2"></label><label>Expected yield (t/ha)<input id="gvYield" type="number" min="0" step="any" placeholder="you enter this"></label><button class="button button-dark" id="gvGo">Calculate</button></div><div id="gvOut" aria-live="polite"></div></article>
    <article class="panel"><div class="panel-kicker">SOURCES</div><h3>Where these prices come from</h3><ul class="nodata">${m.providers.map((p) => html`<li><b>${p.name}</b> — ${p.scope}, ${p.cadence}${p.configured ? "" : " (not configured on this server)"}</li>`)}</ul><p class="note">Country food prices: <a href="${safeUrl(m.links.fao_fpma)}" target="_blank" rel="noreferrer noopener">FAO GIEWS FPMA</a> (not integrated). Details and credits: <a href="#credits">Data sources &amp; credits</a>.</p></article>`);
  FS.decorate($("marketBody")); paint(); live();
  $("mkCountry").onchange = async (e) => { st.country = e.target.value; st.board = await api(`/v1/market/board?country=${st.country}`); paint(); live(); };
  $("mkCur").onchange = (e) => { st.cur = e.target.value; paint(); }; $("mkUnit").onchange = (e) => { st.unit = e.target.value; paint(); };
  $("gvGo").onclick = async () => {
    const out = $("gvOut"), area = +$("gvArea").value, y = +$("gvYield").value;
    if (!(area > 0) || !(y > 0)) { setHtml(out, html`<p class="note">Enter an area and an expected yield first.</p>`); return; }
    try { const r = await post("/v1/market/gross-value", { crop_id: $("gvCrop").value, country: st.country, area_ha: area, yield_t_ha: y, currency: st.cur === "native" ? "USD" : st.cur });
      setHtml(out, r.available ? html`<div class="kv"><div><small>GROSS PER HA</small><b>${money(r.gross_per_ha, r.currency)}</b></div><div><small>GROSS TOTAL (${fmtArea(r.area_ha)})</small><b>${money(r.gross_total, r.currency)}</b></div><div><small>PRICE USED</small><b>${money(r.price_per_tonne, r.currency)}<small>/tonne</small></b></div></div><p class="note"><strong>${r.label}.</strong> Price as of ${r.price_as_of}, ${r.price_source} (${r.freshness.label}). ${r.note || ""}</p><ul class="nodata">${r.assumptions.map((x) => html`<li>${x}</li>`)}</ul>` : html`<p class="note">${r.reason}</p>`);
    } catch (e) { setHtml(out, html`<p class="note">Could not calculate: ${e.detail || "backend unavailable"}.</p>`); }
  };
}
export const stopMarket = stop;
