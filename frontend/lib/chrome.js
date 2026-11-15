/* AI-assisted: written with an AI coding assistant (see README, "AI tools used"). */
/* generated from FieldShift v0.4 app.js by the v1.0 module split; edited by hand afterwards */
import { html, setHtml } from "./html.js";
import { $, ACTIVE_VIEWS, FS, S, TAB_LABELS, active, cap, toast } from "./state.js";
import { renderOverview } from "../views/overview.js";
import { renderFields } from "../views/fields.js";
import { renderField } from "../views/field.js";
import { renderCrops } from "../views/crops.js";
import { renderRotation } from "../views/rotation.js";
import { renderManagement } from "../views/management.js";
import { renderSettings } from "../views/settings.js";
import { renderCropDetail } from "../views/cropdetail.js";
import { renderClimate } from "../views/climate.js";
import { renderWeather } from "../views/weather.js";
import { renderIrrigation } from "../views/irrigation.js";
import { renderSoilHealth } from "../views/soilhealth.js";
import { renderPests } from "../views/pests.js";
import { renderFinance } from "../views/finance.js";
import { renderMarket, stopMarket } from "../views/market.js";
import { renderAccuracy, renderCredits } from "../views/about.js";
import { analyzeField, saveField } from "./storage.js";

export function setStatus() { $("statusDot").style.background = S.online ? "var(--neon)" : "var(--amber)"; $("statusText").textContent = S.online ? "Backend connected" : "Offline · browser only"; }
export function renderChrome() {
    $("fieldCount").textContent = S.fields.length; const a = active();
    $("activeLabel").textContent = a ? `ACTIVE · ${a.name.toUpperCase().slice(0, 18)}` : "ACTIVE FIELD";
    setHtml($("fieldPicker"), S.fields.length ? S.fields.map((f) => html`<option value="${f.id}" ${String(f.id) === String(S.activeId) ? "selected" : ""}>${f.name}</option>`) : "<option>No fields yet</option>");
    const navView = S.view === "crop" ? "crops" : S.view;
    document.querySelectorAll(".nav-item[data-view]").forEach((n) => { n.classList.toggle("active", n.dataset.view === navView); if (n.dataset.view === navView) n.setAttribute("aria-current", "page"); else n.removeAttribute("aria-current"); });
    const crumbs = { overview: "Overview", studio: "Field studio", fields: "My fields", settings: "Settings", market: "Market prices", accuracy: "How accurate is this?", credits: "Data sources & credits", crop: `Crop advisor / ${S.arg ? cap(S.arg) : "Crop"}` };
    $("pageCrumb").textContent = ACTIVE_VIEWS.includes(S.view) ? `${a?.name || "Field"} · ${TAB_LABELS[S.view]}` : crumbs[S.view];
  }
export function route() {
    const [name, arg = ""] = (location.hash.slice(1) || "overview").split("/");
    S.view = document.getElementById("v-" + name) ? name : "overview"; S.arg = arg;
    document.querySelectorAll(".view").forEach((s) => { const on = s.id === "v-" + S.view; s.classList.toggle("active", on); });
    if (S.view !== "market") stopMarket();
    renderViews(); renderChrome(); window.scrollTo(0, 0);
    if (S.view === "studio") FS.studio?.shown();
  }
export function refreshAll() { renderViews(); renderChrome(); FS.studio?.drawSaved(); }
export function motion() {
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) return; let i = 0;
    document.querySelectorAll(".view.active .hero,.view.active .view-head,.view.active .field-head,.view.active .tabs,.view.active .metric-card,.view.active .panel,.view.active .crop-card,.view.active .season,.view.active .mg-card,.view.active .field-card,.view.active .empty,.view.active .detail-hero,.view.active .detail-card,.view.active .cond-card").forEach((n) => { n.classList.remove("rise"); n.style.setProperty("--d", Math.min(i++, 14) * 60 + "ms"); void n.offsetWidth; n.classList.add("rise"); });
  }
export function renderViews() {
    ({ overview: renderOverview, fields: renderFields, field: renderField, crops: renderCrops, rotation: renderRotation, management: renderManagement, settings: renderSettings, crop: renderCropDetail, climate: renderClimate, weather: renderWeather, irrigation: renderIrrigation, soilhealth: renderSoilHealth, pests: renderPests, finance: renderFinance, market: renderMarket, accuracy: renderAccuracy, credits: renderCredits }[S.view] || (() => {}))();
    const root = document.querySelector(".view.active"); if (root) { FS.decorate(root); FS.hydrateKnown(root); FS.hydrate(root); }
    motion();
  }
export const tabs = () => html`<div class="tabs" role="tablist">${ACTIVE_VIEWS.map((v) => html`<a href="#${v}" class="${v === S.view ? "on" : ""}" role="tab">${TAB_LABELS[v]}</a>`)}</div>`;
export function needField(target, withTabs = true) {
    const a = active(); if (!a) { setHtml($(target), html`<div class="empty"><h3>No field selected</h3><p>Outline your land in the Field studio and save it with a name.</p><a class="button button-dark" href="#studio">Open Field studio</a></div>`); if (withTabs) setHtml($("tabs-" + S.view), ""); return null; }
    if (withTabs) setHtml($("tabs-" + S.view), tabs());
    if (!a.analysis) { setHtml($(target), html`<div class="empty"><h3>${a.name} hasn't been analyzed yet</h3><p>Run the analysis to load climate, soil, crops, rotation and management advice.</p><button class="button button-dark" id="runAn" data-ic="zap">Analyze now</button></div>`); $("runAn").onclick = () => reanalyze(); return null; }
    return a;
  }
export async function reanalyze(patch = {}) {
    const a = active(); if (!a) return; toast("Analyzing field…");
    try { const f = await analyzeField({ ...a, ...patch }); await saveField(f, true); refreshAll(); toast("Analysis updated"); } catch { toast("Analysis needs the backend. Run: uvicorn backend.main:app"); }
  }
