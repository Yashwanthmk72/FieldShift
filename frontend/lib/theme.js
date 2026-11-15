/* AI-assisted: written with an AI coding assistant (see README, "AI tools used"). */
/* generated from FieldShift v0.4 app.js by the v1.0 module split; edited by hand afterwards */
import { setHtml } from "./html.js";
import { S, ic, write } from "./state.js";
import { persistSettings } from "./storage.js";
import { renderSettings } from "../views/settings.js";

export function applyTheme(pref) {
    const dark = pref === "dark" || (pref === "system" && matchMedia("(prefers-color-scheme: dark)").matches), r = document.documentElement;
    r.dataset.pref = pref; r.dataset.theme = dark ? "dark" : "light"; write("fs-theme", pref);
    document.querySelector('meta[name="theme-color"]')?.setAttribute("content", dark ? "#06110b" : "#eef6ee");
    document.querySelectorAll("[data-theme-pref]").forEach((b) => { const on = b.dataset.themePref === pref; b.classList.toggle("on", on); b.setAttribute("aria-pressed", on); });
  }
export const applyGlow = (g) => document.documentElement.style.setProperty("--glow-k", String(Math.max(0, Math.min(100, g)) / 100));
matchMedia("(prefers-color-scheme: dark)").addEventListener?.("change", () => { if (S.settings.theme === "system") applyTheme("system"); });
document.querySelectorAll("[data-theme-pref]").forEach((b) => {
    setHtml(b, ic({ light: "sun", dark: "moon", system: "monitor" }[b.dataset.themePref], 16));
    b.onclick = () => { S.settings.theme = b.dataset.themePref; applyTheme(S.settings.theme); persistSettings(); if (S.view === "settings") renderSettings(); };
  });
