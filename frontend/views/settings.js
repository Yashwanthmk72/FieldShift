/* AI-assisted: written with an AI coding assistant (see README, "AI tools used"). */
/* generated from FieldShift v0.4 app.js by the v1.0 module split; edited by hand afterwards */
import { html, setHtml } from "../lib/html.js";
import { $, DEFAULTS, FS, S, ic, toast, wid } from "../lib/state.js";
import { applyGlow, applyTheme } from "../lib/theme.js";
import { persistSettings } from "../lib/storage.js";
import { renderChrome } from "../lib/chrome.js";

export function renderSettings() {
    const s = S.settings, row = (l, d, ctl) => html`<div class="field-row"><span>${l}<small>${d}</small></span>${ctl}</div>`, sel = (id, opts, v) => html`<select id="${id}" aria-label="${id}">${opts.map(([k, l]) => html`<option value="${k}" ${k == v ? "selected" : ""}>${l}</option>`)}</select>`;
    const segCtl = (id, opts, v) => html`<div class="seg" id="${id}" role="group">${opts.map(([k, l, i]) => html`<button data-v="${k}" class="${k === v ? "on" : ""}" aria-pressed="${k === v}">${i ? ic(i, 16) : ""}${l}</button>`)}</div>`;
    const head = (i, kick, t) => html`<div class="panel-heading"><div><div class="panel-kicker">${kick}</div><h3>${t}</h3></div><span class="set-ic">${ic(i, 20)}</span></div>`;
    const prio = (k, l) => row(l, "Weight in crop scoring (0 = off)", html`<input type="range" min="0" max="100" id="p_${k}" value="${s.priorities[k]}" aria-label="${l}">`);
    setHtml($("settingsBody"), html`<article class="panel">${head("heart", "PROFILE", "About you")}${row("Your name", "Shown in the greeting", html`<input type="text" id="s_name" value="${s.name}" maxlength="40">`)}</article>
    <article class="panel">${head("sun", "APPEARANCE", "Theme & look")}${row("Theme", "Light, dark or follow your device", segCtl("s_theme", [["light", "Light", "sun"], ["dark", "Dark", "moon"], ["system", "System", "monitor"]], s.theme))}${row("Neon glow", "Strength of the green glow on cards and buttons", html`<input type="range" min="0" max="100" id="s_glow" value="${s.glow}" aria-label="Glow strength">`)}${row("Default layout", "For My fields and Crop advisor", segCtl("s_layout", [["grid", "Grid", "gridview"], ["list", "List", "list"]], s.layout))}</article>
    <article class="panel">${head("globe", "DISPLAY", "Units & map")}${row("Area unit", "Hectares or acres", sel("s_area", [["ha", "Hectares"], ["ac", "Acres"]], s.area_unit))}${row("Temperature", "Celsius or Fahrenheit", sel("s_temp", [["C", "°C"], ["F", "°F"]], s.temp_unit))}${row("Default map layer", "Used in Field studio", sel("s_map", [["satellite", "Satellite"], ["streets", "Streets"]], s.map_style))}${row("Place labels", "Town and country names on satellite", sel("s_labels", [["1", "On"], ["0", "Off"]], s.labels ? "1" : "0"))}${row("Start on 3D globe", "Otherwise flat map", sel("s_globe", [["1", "Yes"], ["0", "No"]], s.start_globe ? "1" : "0"))}</article>
    <article class="panel">${head("sliders", "ADVICE", "Defaults for new fields")}${prio("resilience", "Resilience")}${prio("water", "Save water")}${prio("soil", "Soil health")}${row("Rotation length", "Seasons in each plan", sel("s_seasons", [3, 4, 5, 6, 8].map((n) => [n, n + " seasons"]), s.seasons))}</article>
    <article class="panel">${head("layers", "DATA", "Workspace")}${row("Backend", S.online ? "Connected" : "Not reachable — using browser storage", html`<span class="badge ${S.online ? "" : "high"}">${S.online ? "ONLINE" : "OFFLINE"}</span>`)}${row("Workspace ID", wid.slice(0, 18) + "…", html`<button class="button button-light button-compact" id="copyWs">Copy</button>`)}${row("Export fields", "Download as JSON", html`<button class="button button-light button-compact" id="exportBtn" data-ic="download">Export</button>`)}${row("Reset settings", "Back to defaults", html`<button class="button button-light button-compact" id="resetSet">Reset</button>`)}</article>`);
    const bindSeg = (id, fn) => $(id).querySelectorAll("button").forEach((b) => b.onclick = () => { $(id).querySelectorAll("button").forEach((x) => { x.classList.toggle("on", x === b); x.setAttribute("aria-pressed", x === b); }); fn(b.dataset.v); });
    bindSeg("s_theme", (v) => { S.settings.theme = v; applyTheme(v); persistSettings(); });  // live preview
    bindSeg("s_layout", (v) => { S.settings.layout = v; persistSettings(); });
    $("s_glow").oninput = (e) => { S.settings.glow = +e.target.value; applyGlow(S.settings.glow); };
    $("copyWs").onclick = () => { navigator.clipboard?.writeText(wid); toast("Workspace ID copied"); };
    $("exportBtn").onclick = () => { const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([JSON.stringify(S.fields, null, 2)], { type: "application/json" })); a.download = "fieldshift-fields.json"; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000); };
    $("resetSet").onclick = () => { S.settings = { ...DEFAULTS, _ts: Date.now() }; applyTheme("system"); applyGlow(DEFAULTS.glow); persistSettings(); renderSettings(); FS.decorate(document.querySelector(".view.active")); renderChrome(); toast("Settings reset"); };
  }
$("saveSettings").onclick = async () => {
    if (!$("s_name")) return; const g = (id) => $(id).value, seg = (id) => $(id).querySelector("button.on")?.dataset.v;
    S.settings = { ...S.settings, name: g("s_name").trim() || "Farmer", area_unit: g("s_area"), temp_unit: g("s_temp"), map_style: g("s_map"), labels: g("s_labels") === "1", start_globe: g("s_globe") === "1", seasons: +g("s_seasons"), theme: seg("s_theme") || "system", layout: seg("s_layout") || "grid", glow: +g("s_glow"), priorities: Object.fromEntries(["resilience", "water", "soil", "profit"].map((k) => [k, +g("p_" + k)])) };
    await persistSettings(); applyTheme(S.settings.theme); FS.studio?.setBaseLayer(S.settings.map_style); FS.studio?.setLabels(S.settings.labels); renderChrome(); toast("Settings saved");
  };
