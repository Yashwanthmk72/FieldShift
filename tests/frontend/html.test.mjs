/* AI-assisted: written with an AI coding assistant (see README, "AI tools used"). */
import test from "node:test";
import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { html, raw, esc, setHtml } from "../../frontend/lib/html.js";

test("interpolations are escaped by default", () => {
  const evil = `<img src=x onerror=alert(1)>"'\``;
  const out = html`<p title="${evil}">${evil}</p>`.toString();
  assert.ok(!out.includes("<img") && !out.includes('onerror=alert(1)>'));
  assert.ok(out.includes("&lt;img") && out.includes("&quot;") && out.includes("&#39;") && out.includes("&#96;"));
});
test("raw() is the only opt-out, and nested html`` is not double-escaped", () => {
  assert.equal(html`${raw("<b>x</b>")}`.toString(), "<b>x</b>");
  assert.equal(html`<ul>${["a", "<i>"].map((v) => html`<li>${v}</li>`)}</ul>`.toString(), "<ul><li>a</li><li>&lt;i&gt;</li></ul>");
  assert.equal(esc(null), "");
});
test("setHtml escapes plain strings", () => {
  const el = { innerHTML: "" };
  setHtml(el, "<script>1</script>"); assert.equal(el.innerHTML, "&lt;script&gt;1&lt;/script&gt;");
});
test("no direct innerHTML assignment outside lib/html.js (defect D5)", () => {
  const bad = [];
  const walk = (d) => readdirSync(d).forEach((f) => { const p = join(d, f); if (statSync(p).isDirectory()) return walk(p); if (!p.endsWith(".js") || p.endsWith(join("lib", "html.js"))) return; if (/\.(innerHTML|outerHTML)\s*=|insertAdjacentHTML/.test(readFileSync(p, "utf8"))) bad.push(p); });
  walk("frontend");
  assert.deepEqual(bad, []);
});
