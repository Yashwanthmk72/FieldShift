/* AI-assisted: written with an AI coding assistant (see README, "AI tools used"). */
/* generated from FieldShift v0.4 app.js by the v1.0 module split; edited by hand afterwards */
import { FS, S, active, read, toast, write } from "./state.js";
import { api } from "./api.js";
import { refreshAll, renderChrome, setStatus } from "./chrome.js";

export const isLocal = (id) => String(id).startsWith("L");
export const localFields = () => read("fs-fields-local", []);
export const setLocalFields = (arr) => write("fs-fields-local", arr);
export const body = (f) => ({ name: f.name, geometry: f.geometry, latitude: f.latitude, longitude: f.longitude, area_ha: f.area_ha, soil: f.soil || {}, priorities: f.priorities || {}, notes: f.notes || "", previous_crops: f.previous_crops || [], analysis: f.analysis || null, done_actions: f.done_actions || [] });
export async function persist(f) {
    const update = f.id && !isLocal(f.id);
    try { const r = await api(update ? `/farms/${f.id}` : "/farms", { method: update ? "PUT" : "POST", body: JSON.stringify(body(f)) }); S.online = true; return { ...f, ...r, id: r.id, updated_at: new Date().toISOString() }; }
    catch (e) {
      if (e.status && e.status >= 400 && e.status < 500 && e.status !== 404) { toast(e.status === 409 ? "Workspace field limit reached" : "Could not save to the server"); }
      S.online = e.status ? S.online : false;
      const saved = { ...f, id: f.id || "L" + Date.now(), updated_at: new Date().toISOString() };
      setLocalFields([saved, ...localFields().filter((x) => String(x.id) !== String(saved.id))]); return saved;
    }
  }
export async function syncLocal() { // push browser-only fields to the server once it is reachable again
    if (!S.online) return;
    for (const f of localFields()) { try { const r = await api("/farms", { method: "POST", body: JSON.stringify(body(f)) }); setLocalFields(localFields().filter((x) => x.id !== f.id)); S.fields = S.fields.map((x) => x.id === f.id ? { ...f, ...r, id: r.id } : x); if (String(S.activeId) === String(f.id)) S.activeId = r.id; } catch { break; } }
  }
export async function loadFields() {
    let server = [];
    try { server = await api("/farms"); S.online = true; } catch { S.online = false; }
    const byId = new Map([...localFields(), ...server].map((f) => [String(f.id), f]));
    S.fields = [...byId.values()].sort((a, b) => String(b.updated_at || "").localeCompare(String(a.updated_at || "")));
    if (!active()) S.activeId = S.fields[0]?.id ?? null;
    setStatus(); syncLocal().then(() => { if (localFields().length === 0 && S.online) renderChrome(); });
  }
export async function saveField(f, quiet) { const saved = await persist(f); S.fields = [saved, ...S.fields.filter((x) => String(x.id) !== String(saved.id))]; setActive(saved.id, true); if (!quiet) toast(S.online ? "Field saved" : "Saved in this browser — start the backend for shared storage"); return saved; }
export let quietT;
export function saveQuiet(f) { clearTimeout(quietT); quietT = setTimeout(async () => { const saved = await persist(f); S.fields = S.fields.map((x) => String(x.id) === String(f.id) ? { ...x, id: saved.id, updated_at: saved.updated_at } : x); if (String(S.activeId) === String(f.id)) { S.activeId = saved.id; write("fs-active", String(saved.id)); } }, 600); }
export async function removeField(id) {
    if (!isLocal(id)) { try { await api(`/farms/${id}`, { method: "DELETE" }); } catch (e) { if (e.status !== 404) return toast("Couldn't delete on the server. Check the connection and try again."); } }
    setLocalFields(localFields().filter((x) => String(x.id) !== String(id)));
    S.fields = S.fields.filter((f) => String(f.id) !== String(id)); if (!active()) S.activeId = S.fields[0]?.id ?? null; refreshAll(); toast("Field deleted");
  }
export function setActive(id, silent) { S.activeId = id; write("fs-active", id == null ? "" : String(id)); if (!silent) refreshAll(); else renderChrome(); }
export async function analyzeField(f) {
    const a = await api("/analyze", { method: "POST", body: JSON.stringify({ geometry: f.geometry, priorities: f.priorities && Object.keys(f.priorities).length ? f.priorities : S.settings.priorities, previous_crops: f.previous_crops || [], seasons: S.settings.seasons }) });
    return { ...f, analysis: a, area_ha: a.area_ha };
  }
FS.persist = persist;
FS.saveField = saveField;
FS.setActive = setActive;
FS.analyzeField = analyzeField;
FS.refreshAll = () => refreshAll();
FS.setStatus = () => setStatus();
export async function persistSettings() { S.settings._ts = Date.now(); write("fs-settings", S.settings); try { await api("/settings", { method: "PUT", body: JSON.stringify({ data: S.settings }) }); } catch { /* offline: browser copy is kept */ } }
