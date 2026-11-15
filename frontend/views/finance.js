/* AI-assisted: written with an AI coding assistant (see README, "AI tools used"). Field "Finance" tab.
   Every number is the user's own input or a labelled assumption. FieldShift never supplies prices, yields or costs. */
import { html, setHtml } from "../lib/html.js";
import { needField } from "../lib/chrome.js";
import { $, S, toast, topCrop } from "../lib/state.js";
import { api, apiBlob, post } from "../lib/api.js";
import { cropOptions, failure, fieldHead, loadCrops, num, saveBlob, skeleton, tag } from "./common.js";

const COSTS = [["seed", "Seed"], ["fertilizer", "Fertiliser"], ["soil_prep", "Soil preparation"], ["irrigation", "Irrigation"], ["labour", "Labour"], ["pesticide", "Pesticide"], ["machinery", "Machinery"], ["transport", "Transport"], ["other", "Other"]];
const st = { crop: "", area: "", yield: "", price: "", cur: "USD", costs: {}, r: { yield: 20, price: 25, cost: 10 }, notes: "" };
let last = null, lastFor = null;

const n = (id) => { const v = $(id).value.trim(); return v === "" || Number.isNaN(Number(v)) ? null : Number(v); };
const money = (v, cur) => v == null ? "—" : `${cur} ${Math.round(v).toLocaleString()}`;

function collect(a) {
  const costs = {}, prov = {};
  COSTS.forEach(([k]) => { costs[k] = n("fc_" + k); if (costs[k] != null) prov[k] = "user-entered"; });
  const y = n("fYield"), p = n("fPrice");
  if (y != null) prov.yield_t_ha = "user-entered";
  if (p != null) prov.price_per_t = "user-entered";
  prov.ranges = "assumption";
  const r = { yield: (n("rYield") ?? 20) / 100, price: (n("rPrice") ?? 25) / 100, cost: (n("rCost") ?? 10) / 100 };
  const cur = ($("fCur").value.trim().toUpperCase() || "USD").slice(0, 3);
  Object.assign(st, { crop: $("fCrop").value, area: $("fArea").value, yield: $("fYield").value, price: $("fPrice").value, cur, costs: Object.fromEntries(COSTS.map(([k]) => [k, $("fc_" + k).value])), r: { yield: r.yield * 100, price: r.price * 100, cost: r.cost * 100 }, notes: $("fNotes").value });
  const farm = a.id != null && !String(a.id).startsWith("L") ? Number(a.id) : null;
  return { crop_id: st.crop, farm_id: farm, area_ha: n("fArea") ?? a.area_ha ?? 1, yield_t_ha: y, price_per_t: p, costs, ranges: r, currency: cur, provenance: prov, notes: st.notes.slice(0, 500) };
}

function paintResult(d, cur) {
  const r = d.result, sc = d.scenarios, mc = d.monte_carlo;
  setHtml($("finResult"), html`
    <article class="panel"><div class="panel-kicker">RESULT · PER HECTARE</div>
      <div class="kv"><div><small>REVENUE ${tag("user")}</small><b>${money(r.revenue_per_ha, cur)}</b></div><div><small>TOTAL COST ${tag("user")}</small><b>${money(r.cost_total_per_ha, cur)}</b></div><div><small>GROSS MARGIN</small><b>${money(r.gross_margin_per_ha, cur)}</b></div><div><small>NET PROFIT</small><b>${money(r.net_profit_per_ha, cur)}</b></div>
      <div><small>BREAK-EVEN PRICE (per t)</small><b>${money(r.break_even_price_per_t, cur)}</b></div><div><small>BREAK-EVEN YIELD (t/ha)</small><b>${num(r.break_even_yield_t_ha, 2)}</b></div><div><small>RETURN ON COST</small><b>${r.roi != null ? num(r.roi * 100, 0) + " %" : "—"}</b></div><div><small>NET PROFIT, WHOLE FIELD</small><b>${money(r.net_profit_total, cur)}</b></div></div>
      ${r.partial.length ? html`<ul class="nodata">${r.partial.map((p) => html`<li>${p}</li>`)}</ul>` : ""}
      <p class="note"><strong>${d.disclaimer}</strong> Revenue, cost, yield and price are your own inputs; FieldShift does not supply them.</p></article>
    ${sc ? html`<div class="two"><article class="panel"><div class="panel-kicker">SCENARIOS ${tag("assumption")}</div><h3>Best, base, worst (net profit per ha)</h3>
      <div class="kv"><div><small>BEST</small><b>${money(sc.best, cur)}</b></div><div><small>BASE</small><b>${money(sc.base, cur)}</b></div><div><small>WORST</small><b>${money(sc.worst, cur)}</b></div></div>
      <p class="note">Ranges used: yield ±${num(sc.ranges.yield * 100, 0)} %, price ±${num(sc.ranges.price * 100, 0)} %, cost ±${num(sc.ranges.cost * 100, 0)} %. ${sc.ranges_label}.</p></article>
      <article class="panel"><div class="panel-kicker">SIMULATION ${tag("assumption")}</div><h3>Likely spread of net profit</h3>
      <div class="kv"><div><small>P10</small><b>${money(mc.p10, cur)}</b></div><div><small>MEDIAN</small><b>${money(mc.p50, cur)}</b></div><div><small>P90</small><b>${money(mc.p90, cur)}</b></div><div><small>CHANCE OF A LOSS</small><b>${num(mc.prob_loss * 100, 0)}<small> %</small></b></div></div>
      <p class="note">${mc.label} ${mc.runs} runs.</p></article></div>` : html`<p class="note">Enter yield, price and every cost category to see scenarios and the simulation.</p>`}`);
}

async function loadPlans(a, crops) {
  let plans = [];
  try { plans = await api("/v1/finance/plans"); } catch { setHtml($("finPlans"), html`<p class="note">Saved plans could not be loaded.</p>`); return; }
  const names = Object.fromEntries(crops.map((c) => [c.id, c.name]));
  setHtml($("finPlans"), plans.length ? html`<table class="tbl"><thead><tr><th>Crop</th><th>Area (ha)</th><th>Yield</th><th>Price</th><th></th></tr></thead><tbody>${plans.map((p) => html`<tr><td>${names[p.crop_id] || p.crop_id}</td><td>${p.area_ha}</td><td>${p.yield_t_ha ?? "—"}</td><td>${p.price_per_t != null ? p.currency + " " + p.price_per_t : "—"}</td><td><button class="button button-light button-compact" data-load="${p.id}">Load</button> <button class="button button-light button-compact" data-del="${p.id}">Delete</button></td></tr>`)}</tbody></table>` : html`<p class="note">No saved plans yet.</p>`);
  document.querySelectorAll("[data-load]").forEach((b) => b.onclick = () => {
    const p = plans.find((x) => String(x.id) === b.dataset.load); if (!p) return;
    Object.assign(st, { crop: p.crop_id, area: String(p.area_ha ?? ""), yield: p.yield_t_ha ?? "", price: p.price_per_t ?? "", cur: p.currency || "USD", costs: Object.fromEntries(COSTS.map(([k]) => [k, p.costs?.[k] ?? ""])), r: p.ranges ? { yield: p.ranges.yield * 100, price: p.ranges.price * 100, cost: p.ranges.cost * 100 } : st.r, notes: p.notes || "" });
    renderFinance();
  });
  document.querySelectorAll("[data-del]").forEach((b) => b.onclick = async () => { try { await api(`/v1/finance/plans/${b.dataset.del}`, { method: "DELETE" }); toast("Plan deleted"); loadPlans(a, crops); } catch { toast("Could not delete the plan"); } });
}

export async function renderFinance() {
  const a = needField("financeBody"); if (!a) return;
  if (lastFor !== a.id) { last = null; lastFor = a.id; } /* never show one field's result on another */
  setHtml($("financeBody"), html`${fieldHead("FINANCE · YOUR NUMBERS", "Profit and risk planner", a)}${skeleton(2)}`);
  let crops; try { crops = await loadCrops(); } catch (e) { setHtml($("financeBody"), failure("Crop list unavailable", e)); return; }
  if (S.view !== "finance") return;
  const sel = st.crop || topCrop(a)?.crop.id || crops[0].id, area = st.area !== "" ? st.area : (a.area_ha ?? "");
  setHtml($("financeBody"), html`${fieldHead("FINANCE · YOUR NUMBERS", "Profit and risk planner", a)}
    <article class="panel"><div class="panel-kicker">INPUTS · ALL ${tag("user")} OR ${tag("assumption")}</div><h3>Enter your own yield, price and costs</h3>
      <p class="note">FieldShift does not bundle prices, yields or costs. Reference prices, where a real source exists, are on the <a href="#market">Market</a> page (gross value only, never profit). Leave a box empty if you do not know it: that part is then reported as missing, not guessed.</p>
      <div class="fgrid">
        <label>Crop<select id="fCrop">${cropOptions(crops, sel)}</select></label>
        <label>Area (ha)<input type="number" id="fArea" min="0.01" step="0.1" value="${area}"></label>
        <label>Currency (3 letters)<input type="text" id="fCur" maxlength="3" value="${st.cur}"></label>
        <label>Yield (t/ha)<input type="number" id="fYield" min="0" step="0.1" value="${st.yield}"></label>
        <label>Price (${st.cur} per tonne)<input type="number" id="fPrice" min="0" step="1" value="${st.price}"></label>
      </div>
      <h3 style="margin-top:14px">Costs per hectare (${st.cur})</h3>
      <div class="fgrid">${COSTS.map(([k, l]) => html`<label>${l}<input type="number" id="fc_${k}" min="0" step="1" value="${st.costs[k] ?? ""}"></label>`)}</div>
      <h3 style="margin-top:14px">Uncertainty ranges ${tag("assumption")}</h3>
      <div class="fgrid"><label>Yield ± %<input type="number" id="rYield" min="0" max="90" value="${st.r.yield}"></label><label>Price ± %<input type="number" id="rPrice" min="0" max="90" value="${st.r.price}"></label><label>Cost ± %<input type="number" id="rCost" min="0" max="90" value="${st.r.cost}"></label></div>
      <label class="inl" style="display:block">Notes (optional)<input type="text" class="text-input" id="fNotes" maxlength="500" value="${st.notes}"></label>
      <div class="row"><button class="button button-dark" id="fCalc">Calculate</button> <button class="button button-light" id="fSave">Save plan</button></div></article>
    <div id="finResult"></div>
    <article class="panel"><div class="panel-heading"><div><div class="panel-kicker">SAVED PLANS</div><h3>Your plans</h3></div><div class="row"><button class="button button-light button-compact" id="fCsv">Export CSV</button> <button class="button button-light button-compact" id="fPdf">Export PDF</button></div></div><div id="finPlans">${skeleton(1)}</div></article>`);
  $("fCalc").onclick = async () => {
    const body = collect(a); setHtml($("finResult"), skeleton(2));
    try { const d = await post("/v1/finance/evaluate", body); last = d; paintResult(d, body.currency); } catch (e) { setHtml($("finResult"), failure(e.status === 422 ? "Check the values you entered" : "Calculation unavailable", e)); }
  };
  $("fSave").onclick = async () => { try { await post("/v1/finance/plans", collect(a)); toast("Plan saved"); loadPlans(a, crops); } catch (e) { toast(e.status === 422 ? "Check the values you entered" : "Could not save the plan"); } };
  $("fCsv").onclick = async () => { try { saveBlob(await apiBlob("/v1/finance/export.csv"), "fieldshift-finance.csv"); } catch { toast("Export failed"); } };
  $("fPdf").onclick = async () => { try { saveBlob(await apiBlob("/v1/finance/export.pdf"), "fieldshift-finance.pdf"); } catch { toast("Export failed"); } };
  if (last) paintResult(last, st.cur);
  loadPlans(a, crops);
}
