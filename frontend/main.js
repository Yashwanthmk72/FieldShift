/* AI-assisted: written with an AI coding assistant (see README, "AI tools used"). */
/* generated from FieldShift v0.4 app.js by the v1.0 module split; edited by hand afterwards */
import { html, setHtml } from "./lib/html.js";
import { $, DEFAULTS, FS, S, ic, write } from "./lib/state.js";
import { loadFields, setActive } from "./lib/storage.js";
import { renderChrome, route } from "./lib/chrome.js";
import { editField } from "./views/fields.js";
import { applyGlow, applyTheme } from "./lib/theme.js";
import { api } from "./lib/api.js";
import "./lib/media.js";
import "./views/studio.js";

document.addEventListener("click", (e) => { const t = e.target.closest("[data-open-crop]"); if (!t) return; e.stopPropagation(); const from = S.view === "rotation" ? "rotation" : S.view === "field" ? "field" : "crops"; FS.openCrop(t.dataset.openCrop, from, t.dataset.stage != null ? +t.dataset.stage : null); });
document.addEventListener("keydown", (e) => { if (e.key !== "Enter") return; const t = e.target.closest?.("[data-open-crop]"); if (t && e.target === t) { const from = S.view === "rotation" ? "rotation" : S.view === "field" ? "field" : "crops"; FS.openCrop(t.dataset.openCrop, from, null); } });
$("fieldPicker").onchange = (e) => setActive(e.target.value);
window.addEventListener("hashchange", route);
Object.assign(FS, { editField, renderChrome });
(async () => {
    setHtml($("brandMark"), ic("sprout", 22)); setHtml($("newFieldBtn"), html`${ic("plus", 16)} New field`); FS.decorate(document);
    applyTheme(S.settings.theme || "system"); applyGlow(S.settings.glow ?? 70);
    try { const remote = await api("/settings"); if (remote && Object.keys(remote).length && (remote._ts || 0) > (S.settings._ts || 0)) { S.settings = { ...DEFAULTS, ...remote }; write("fs-settings", S.settings); applyTheme(S.settings.theme); applyGlow(S.settings.glow); } } catch { /* offline */ }
    await loadFields(); route();
  })();
