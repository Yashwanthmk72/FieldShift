/* AI-assisted: written with an AI coding assistant (see README, "AI tools used"). */
/* API client. The access token lives in memory only; the refresh token is an httpOnly cookie the page cannot read.
   Signed out = guest mode: requests carry X-Workspace-ID exactly as in v0.4. */
import { wid, FS } from "./state.js";

export const API = (window.FIELDSHIFT_API_BASE || "").replace(/\/$/, "");
const session = { token: null, user: null, listeners: new Set() };
export const getSession = () => ({ user: session.user, signedIn: !!session.token });
export const onSession = (fn) => session.listeners.add(fn);
const emit = () => session.listeners.forEach((f) => f(getSession()));
export function setSession(token, user) { session.token = token || null; session.user = token ? user || session.user : null; emit(); }

async function failure(r) {
  let detail = "";
  try { detail = (await r.json()).detail || ""; } catch { /* not JSON */ }
  const e = new Error(detail || `API ${r.status}`); e.status = r.status; e.detail = detail; return e;
}
const headers = (extra) => ({ "Content-Type": "application/json", ...(session.token ? { Authorization: `Bearer ${session.token}` } : { "X-Workspace-ID": wid }), ...(extra || {}) });

export async function refreshSession() {
  try {
    const r = await fetch(`${API}/api/v1/auth/refresh`, { method: "POST", credentials: "include", headers: { "X-Requested-With": "fieldshift" } });
    if (!r.ok) { setSession(null); return false; }
    const d = await r.json(); setSession(d.access_token, session.user); return true;
  } catch { return false; }
}

async function raw(path, opts, retry = true) {
  const r = await fetch(`${API}/api${path}`, { ...opts, headers: headers(opts.headers) });
  if (r.status === 401 && session.token && retry && await refreshSession()) return raw(path, opts, false);
  if (!r.ok) throw await failure(r);
  return r;
}
export async function api(path, opts = {}) { return (await raw(path, opts)).json(); }
export async function apiBlob(path, opts = {}) { return (await raw(path, opts)).blob(); }
export const post = (path, body) => api(path, { method: "POST", body: JSON.stringify(body) });

export async function authCall(name, body) {
  const r = await fetch(`${API}/api/v1/auth/${name}`, { method: "POST", credentials: "include", headers: { "Content-Type": "application/json", "X-Requested-With": "fieldshift" }, body: JSON.stringify(body || {}) });
  if (!r.ok) throw await failure(r);
  return r.json();
}
export async function register(email, password) { const d = await authCall("register", { email, password }); setSession(d.access_token, d.user); return d.user; }
export async function login(email, password) { const d = await authCall("login", { email, password }); setSession(d.access_token, d.user); return d.user; }
export async function logout() { try { await authCall("logout"); } finally { setSession(null); } }
export async function deleteAccount(password) { await api("/v1/auth/account", { method: "DELETE", body: JSON.stringify({ password }) }); setSession(null); }
export const exportAccount = () => api("/v1/auth/export");
export async function restoreSession() {
  if (!(await refreshSession())) return null;
  try { const u = await api("/v1/auth/me"); session.user = u; emit(); return u; } catch { return null; }
}

FS.api = api;
