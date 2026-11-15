/* AI-assisted: written with an AI coding assistant (see README, "AI tools used"). */
/* generated from FieldShift v0.4 app.js by the v1.0 module split; edited by hand afterwards */
import { html, setHtml } from "../lib/html.js";
import { $, FS, S, fmtArea, ic, read, topCrop, write } from "../lib/state.js";
import { cropThumb, polySvg } from "./widgets.js";
import { removeField, saveField, setActive } from "../lib/storage.js";
import { refreshAll } from "../lib/chrome.js";

export function sortedFields() {
    const q = (S.fq || "").toLowerCase(), by = S.fsort || "recent";
    const list = S.fields.filter((f) => !q || f.name.toLowerCase().includes(q));
    const cmp = { recent: (a, b) => String(b.updated_at || "").localeCompare(String(a.updated_at || "")), name: (a, b) => a.name.localeCompare(b.name), area: (a, b) => (b.area_ha || 0) - (a.area_ha || 0), score: (a, b) => (topCrop(b)?.score || 0) - (topCrop(a)?.score || 0) }[by];
    return list.sort(cmp);
  }
export const layoutOf = (page) => read("fs-layout-" + page, S.settings.layout || "grid");
export const layoutSeg = (page) => html`<div class="seg" role="group" aria-label="Layout">${[["grid", "gridview", "Grid"], ["list", "list", "List"]].map(([k, i, l]) => html`<button data-layout="${k}" data-page="${page}" class="${layoutOf(page) === k ? "on" : ""}" aria-pressed="${layoutOf(page) === k}" aria-label="${l} layout">${ic(i, 16)}<span>${l}</span></button>`)}</div>`;
export function bindLayout(root, rerender) { root.querySelectorAll("[data-layout]").forEach((b) => b.onclick = () => { write("fs-layout-" + b.dataset.page, JSON.stringify(b.dataset.layout)); rerender(); }); }
export function renderFields() {
    setHtml($("fieldsHead"), html`<div class="view-head"><div><div class="eyebrow"><span class="eyebrow-line"></span> SAVED LAND</div><h1>My fields</h1><p>Open a field to see its overview, crop advice, rotation and land management.</p></div><a class="button button-dark" href="#studio" data-ic="plus">Add field</a></div>
      <div class="toolbar"><label class="grow">${ic("search", 16)}<input id="fq" type="search" placeholder="Search fields…" value="${S.fq || ""}" aria-label="Search fields"></label><select id="fsort" aria-label="Sort fields">${[["recent", "Recently updated"], ["name", "Name A–Z"], ["area", "Largest area"], ["score", "Top crop score"]].map(([k, l]) => html`<option value="${k}" ${(S.fsort || "recent") === k ? "selected" : ""}>${l}</option>`)}</select>${layoutSeg("fields")}</div>`);
    $("fq").oninput = (e) => { S.fq = e.target.value; drawFields(); }; $("fsort").onchange = (e) => { S.fsort = e.target.value; drawFields(); };
    bindLayout($("fieldsHead"), renderViewsFields); drawFields();
  }
export const renderViewsFields = () => { renderFields(); const r = document.querySelector(".view.active"); FS.decorate(r); FS.hydrate(r); };
export function drawFields() {
    const list = sortedFields(), listMode = layoutOf("fields") === "list";
    if (!S.fields.length) { setHtml($("fieldsBody"), html`<div class="empty"><h3>No saved fields yet</h3><p>Create one in the Field studio.</p><a class="button button-dark" href="#studio">Open Field studio</a></div>`); return; }
    if (!list.length) { setHtml($("fieldsBody"), html`<div class="empty"><h3>No fields match “${S.fq}”</h3></div>`); return; }
    const act = (f) => html`<div class="card-actions"><button class="button button-dark button-compact" data-open="${f.id}">Open</button><button class="button button-light button-compact" data-rename="${f.id}" aria-label="Rename ${f.name}">${ic("pencil", 14)}</button><button class="button button-light button-compact danger" data-del="${f.id}" aria-label="Delete ${f.name}">${ic("trash", 14)}</button></div>`;
    $("fieldsBody").className = "field-grid" + (listMode ? " is-list" : "");
    setHtml($("fieldsBody"), list.map((f) => { const b = topCrop(f), on = String(f.id) === String(S.activeId);
      return listMode
        ? html`<article class="field-row-card lift ${on ? "is-active" : ""}" data-open="${f.id}" tabindex="0" role="link" aria-label="Open ${f.name}"><div class="field-art">${polySvg(f.geometry)}</div><div><div class="top">${b ? cropThumb(b.crop) : ""}<div><h3>${f.name}</h3><p>${fmtArea(f.area_ha)} · ${f.latitude.toFixed(2)}°, ${f.longitude.toFixed(2)}°</p></div></div></div><div class="meta-col"><p>${b ? html`Top match: <strong>${b.crop.name}</strong> (${b.score}/100)` : "Not analyzed yet"}</p>${f.notes ? html`<p>${f.notes}</p>` : ""}</div>${act(f)}</article>`
        : html`<article class="field-card lift ${on ? "is-active" : ""}" data-open="${f.id}" tabindex="0" role="link" aria-label="Open ${f.name}"><div class="field-art">${polySvg(f.geometry)}<span class="tag">${on ? "ACTIVE" : "FIELD"}</span>${b ? cropThumb(b.crop, "crop-thumb") : ""}</div><div class="in"><h3>${f.name}</h3><p>${fmtArea(f.area_ha)} · ${f.latitude.toFixed(2)}°, ${f.longitude.toFixed(2)}°</p><p style="margin-top:6px">${b ? html`Top match: <strong>${b.crop.name}</strong> (${b.score}/100)` : "Not analyzed yet"}</p>${f.notes ? html`<p style="margin-top:6px">${f.notes}</p>` : ""}${act(f)}</div></article>`; }));
    const root = $("fieldsBody");
    root.querySelectorAll("[data-open]").forEach((n) => { const go = (e) => { e.stopPropagation(); setActive(n.dataset.open, true); location.hash = "#field"; }; n.onclick = go; n.onkeydown = (e) => { if (e.key === "Enter" && e.target === n) go(e); }; });
    root.querySelectorAll("[data-rename]").forEach((n) => n.onclick = (e) => { e.stopPropagation(); editField(n.dataset.rename); });
    root.querySelectorAll("[data-del]").forEach((n) => n.onclick = (e) => { e.stopPropagation(); if (confirm("Delete this field?")) removeField(n.dataset.del); });
    FS.decorate(root); FS.hydrate(root);
  }
export function editField(id) {
    const f = S.fields.find((x) => String(x.id) === String(id)); if (!f) return; const form = $("fieldForm"); form.name.value = f.name; form.notes.value = f.notes || ""; $("fieldDialog").showModal();
    form.onsubmit = async (e) => { if (e.submitter?.value !== "ok") return; await saveField({ ...f, name: form.name.value.trim() || f.name, notes: form.notes.value.trim() }, false); refreshAll(); };
  }
