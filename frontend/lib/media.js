/* AI-assisted: written with an AI coding assistant (see README, "AI tools used"). */
/* Pictures for FieldShift.
 * 1) Every picture slot starts as a generated SVG illustration (works offline, themed, never broken).
 * 2) FS.hydrate() then asks the backend for a real, freely-licensed Wikimedia Commons photo and fades it in
 *    with author + licence credit. URLs always come from the live lookup – nothing is hard-coded or invented. */
import { html, raw, esc, safeUrl } from "./html.js";
import { FS } from "./state.js";
import { P as iconPaths } from "./icons.js";

  let uid = 0;
  const rnd = (seed) => () => { seed |= 0; seed = (seed + 0x6D2B79F5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  const hash = (s) => [...String(s)].reduce((a, c) => (a * 31 + c.charCodeAt(0)) | 0, 7);
  const wrap = (inner, defs = "") => `<svg class="art" viewBox="0 0 400 240" preserveAspectRatio="xMidYMid slice" role="img" aria-hidden="true" xmlns="http://www.w3.org/2000/svg"><defs>${defs}</defs>${inner}</svg>`;
  const grad = (id, stops, dir = "x1=0 y1=0 x2=0 y2=1") => `<linearGradient id="${id}" ${dir}>${stops.map(([o, c]) => `<stop offset="${o}" stop-color="${c}"/>`).join("")}</linearGradient>`;
  const cloud = (x, y, s, c = "#fff", o = 0.95) => `<g transform="translate(${x} ${y}) scale(${s})" fill="${c}" opacity="${o}"><ellipse cx="0" cy="0" rx="40" ry="17"/><ellipse cx="-22" cy="-9" rx="22" ry="17"/><ellipse cx="14" cy="-15" rx="26" ry="21"/></g>`;
  const hills = (c1, c2) => `<path d="M0 190 Q90 150 190 182 T400 168 V240 H0Z" fill="${c1}"/><path d="M0 214 Q110 184 220 210 T400 202 V240 H0Z" fill="${c2}"/>`;

  /* ----- weather ----- */
  const WEATHER = {
    "heavy-rain": { sky: ["#3b4d5c", "#7f97a6"], ground: ["#2f5a43", "#234a38"], clouds: "#56697a", rain: 46 },
    "light-rain": { sky: ["#7f9fb0", "#c5d6dd"], ground: ["#4d8f64", "#3b7a54"], clouds: "#9fb4bf", rain: 16 },
    dry: { sky: ["#f7c473", "#fde6b3"], ground: ["#c59a5a", "#a97f45"], sun: 1, cracks: 1 },
    heat: { sky: ["#ff9f43", "#ffd89a"], ground: ["#b98b4c", "#9c7339"], sun: 1.3, waves: 1 },
    cool: { sky: ["#a9c5d6", "#e3eef2"], ground: ["#5f9b78", "#4a8663"], mist: 1 },
    humid: { sky: ["#8ec9c1", "#d7eee8"], ground: ["#2f8f5b", "#237a4b"], clouds: "#ffffff", mist: 1 },
    sunny: { sky: ["#6fc1f2", "#d6f0ff"], ground: ["#5fae5f", "#4a9a4d"], sun: 1 },
    cloudy: { sky: ["#9fb2bf", "#dbe5ea"], ground: ["#5c9a6c", "#4a8759"], clouds: "#f4f8fa" },
  };
  function weather(key) {
    const w = WEATHER[key] || WEATHER.sunny, id = "w" + ++uid, r = rnd(hash(key));
    let s = `<rect width="400" height="240" fill="url(#${id})"/>`;
    if (w.sun) s += `<circle cx="318" cy="64" r="${70 * w.sun}" fill="#fff3b0" opacity=".28"/><circle cx="318" cy="64" r="${34 * w.sun}" fill="#ffd25e"/>`;
    if (w.clouds) s += cloud(110, 62, 1.6, w.clouds) + cloud(270, 48, 1.2, w.clouds, .9) + cloud(220, 96, 1.1, w.clouds, .85);
    if (w.mist) s += `<ellipse cx="200" cy="176" rx="260" ry="26" fill="#fff" opacity=".45"/><ellipse cx="90" cy="150" rx="150" ry="14" fill="#fff" opacity=".3"/>`;
    s += hills(w.ground[0], w.ground[1]);
    if (w.cracks) for (let i = 0; i < 9; i++) { const x = 20 + r() * 360, y = 206 + r() * 28; s += `<path d="M${x} ${y} l${8 + r() * 14} ${4 + r() * 6} l${-4 - r() * 8} ${6 + r() * 5}" stroke="#6f4f22" stroke-width="1.6" fill="none" opacity=".6"/>`; }
    if (w.waves) for (let i = 0; i < 4; i++) s += `<path d="M${40 + i * 90} 176 q8 -14 0 -26 t0 -26" stroke="#fff" stroke-width="2.4" fill="none" opacity=".5" stroke-linecap="round"/>`;
    if (w.rain) for (let i = 0; i < w.rain; i++) { const x = r() * 400, y = 70 + r() * 150; s += `<path d="M${x} ${y} l-5 15" stroke="#e8f3fa" stroke-width="2" opacity=".75" stroke-linecap="round"/>`; }
    return wrap(s, grad(id, [[0, w.sky[0]], [1, w.sky[1]]]));
  }

  /* ----- soil cross-sections ----- */
  const SOIL = {
    sand: ["#e8d19b", "#b99a55", 2, 90], "loamy-sand": ["#dcbf84", "#a98a4c", 2.4, 90], "sandy-loam": ["#c9a56b", "#8c6a3a", 2.6, 80], loam: ["#7a5636", "#4d3220", 3, 70],
    "silt-loam": ["#8c6a47", "#5b4129", 2, 80], silt: ["#a68a64", "#76603f", 1.6, 90], "sandy-clay-loam": ["#a9693f", "#6f4326", 3, 60], "clay-loam": ["#9b5a35", "#5e3320", 3, 50],
    "silty-clay-loam": ["#955b3a", "#5a3522", 2, 60], "sandy-clay": ["#b4623a", "#72391f", 3, 50], "silty-clay": ["#8f5333", "#573019", 2, 60], clay: ["#a24f2f", "#5e2a18", 2, 40],
    peat: ["#3d2d22", "#1f1611", 2.6, 60], acidic: ["#b9803f", "#7a4f1f", 3, 50], organic: ["#4a3324", "#241812", 3, 80],
  };
  function soil(key) {
    const [c1, c2, size, n] = SOIL[key] || SOIL.loam, id = "s" + ++uid, r = rnd(hash(key));
    let s = `<rect width="400" height="240" fill="url(#${id})"/><path d="M0 46 Q60 30 120 44 T260 42 T400 40 V0 H0Z" fill="#86c46b"/>`;
    for (let i = 0; i < 20; i++) s += `<path d="M${10 + i * 20} 44 l${-3 + r() * 6} ${-14 - r() * 10}" stroke="#4f9d4e" stroke-width="2.4" stroke-linecap="round"/>`;
    for (let b = 0; b < 3; b++) s += `<path d="M0 ${96 + b * 52} Q100 ${88 + b * 52 + r() * 14} 200 ${100 + b * 52} T400 ${96 + b * 52}" stroke="#0002" stroke-width="2" fill="none"/>`;
    for (let i = 0; i < n * 4; i++) { const x = r() * 400, y = 58 + r() * 182, rad = size * (.4 + r()), light = r() > .55; s += key.includes("clay") && r() > .6 ? `<rect x="${x}" y="${y}" width="${rad * 4}" height="${rad * 1.2}" rx="1" fill="${c2}" opacity=".35"/>` : `<circle cx="${x}" cy="${y}" r="${rad}" fill="${light ? "#fff" : c2}" opacity="${light ? .28 : .5}"/>`; }
    if (key === "organic" || key === "peat") for (let i = 0; i < 16; i++) s += `<path d="M${r() * 400} ${70 + r() * 160} q8 -6 16 0" stroke="#7aa05a" stroke-width="2" fill="none" opacity=".7"/>`;
    return wrap(s, grad(id, [[0, c1], [1, c2]]));
  }

  /* ----- season / growth-stage scenes ----- */
  function season(key) {
    const id = "n" + ++uid, r = rnd(hash(key));
    const cfg = { sowing: ["#bfe3f5", "#eaf6ee", "#7b5a3a", 0], growing: ["#9ad4f2", "#e9f7e2", "#6b4c2f", 1], flowering: ["#8fd0f4", "#fff4d2", "#6b4c2f", 2], harvest: ["#f6c477", "#ffe8b8", "#7b5a30", 3], fallow: ["#b6d4e3", "#eaf0ea", "#6e5a3c", 4] }[key] || ["#bfe3f5", "#eaf6ee", "#7b5a3a", 0];
    let s = `<rect width="400" height="240" fill="url(#${id})"/>`;
    s += cfg[3] === 3 ? `<circle cx="320" cy="60" r="30" fill="#ffb347"/>` : `<circle cx="324" cy="58" r="26" fill="#ffe27a"/>`;
    s += cloud(90, 56, 1, "#fff", .9);
    s += `<path d="M0 150 Q100 128 200 148 T400 140 V240 H0Z" fill="${cfg[3] === 3 ? "#d9a441" : "#79b36a"}"/><rect y="170" width="400" height="70" fill="${cfg[2]}"/>`;
    for (let row = 0; row < 3; row++) for (let i = 0; i < 14; i++) {
      const x = 20 + i * 28 + (row % 2) * 12, y = 186 + row * 20, h = [0, 14, 30, 34, 4][cfg[3]] + r() * 4;
      if (cfg[3] === 0) { s += `<ellipse cx="${x}" cy="${y}" rx="4" ry="2.4" fill="#d7b46a"/>`; continue; }
      if (cfg[3] === 4) { s += `<path d="M${x} ${y} l-2 -${h}M${x + 4} ${y} l2 -${h - 2}" stroke="#b79d62" stroke-width="2"/>`; continue; }
      const col = cfg[3] === 3 ? "#e0a93a" : "#3e9a4f";
      s += `<path d="M${x} ${y} V${y - h}" stroke="${col}" stroke-width="3" stroke-linecap="round"/>`;
      if (cfg[3] >= 1) s += `<ellipse cx="${x - 6}" cy="${y - h * .55}" rx="7" ry="3" fill="${col}" transform="rotate(-25 ${x - 6} ${y - h * .55})"/><ellipse cx="${x + 6}" cy="${y - h * .7}" rx="7" ry="3" fill="${col}" transform="rotate(25 ${x + 6} ${y - h * .7})"/>`;
      if (cfg[3] === 2) s += `<circle cx="${x}" cy="${y - h - 2}" r="4.5" fill="#fff"/><circle cx="${x}" cy="${y - h - 2}" r="2" fill="#f5a524"/>`;
      if (cfg[3] === 3) s += `<ellipse cx="${x}" cy="${y - h - 4}" rx="4" ry="8" fill="#f2c14e"/>`;
    }
    return wrap(s, grad(id, [[0, cfg[0]], [1, cfg[1]]]));
  }

  /* ----- land-management tiles ----- */
  const MANAGE = { drainage: ["droplet", "#3aa1b5", "#bfeaf0"], irrigation: ["droplet", "#2d8fd0", "#cfeaf9"], heat: ["sun", "#f59f2c", "#ffe7b8"], lime: ["flask", "#8a7a5a", "#efe7d2"], compost: ["leaf", "#5b8a3a", "#dff0c8"], texture: ["layers", "#9a6a43", "#f0dcc4"], mulch: ["layers", "#7a8a3a", "#e8efc6"], "cover-crop": ["sprout", "#2f8f5b", "#d4f1de"], residue: ["sprout", "#a08a3a", "#f3ead0"], scouting: ["search", "#4a7f5a", "#dcefe2"] };
  function manage(key) {
    const [ic, c1, c2] = MANAGE[key] || MANAGE.scouting, id = "m" + ++uid, r = rnd(hash(key));
    let s = `<rect width="400" height="240" fill="url(#${id})"/>`;
    for (let i = 0; i < 7; i++) s += `<circle cx="${r() * 400}" cy="${r() * 240}" r="${12 + r() * 40}" fill="#fff" opacity=".12"/>`;
    s += `<g transform="translate(140 60) scale(5)" fill="none" stroke="#fff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" opacity=".92">${iconPaths[ic]}</g>`;
    return wrap(s, grad(id, [[0, c2], [1, c1]], "x1=0 y1=0 x2=1 y2=1"));
  }

  /* ----- crops (when no photo yet) ----- */
  const CROPTONE = { Grass: ["#e8d58a", "#4f9a55"], Legume: ["#b9dd8a", "#2f8f5b"], Tuber: ["#d9c19a", "#5d8f4a"], Oilseed: ["#ffd45e", "#3e8f4a"], Vegetable: ["#ffc9b8", "#3f9150"], Fruit: ["#fff0a8", "#4aa361"], "Fibre & sugar": ["#e6efc0", "#4f9a55"] };
  function crop(family, id2 = "") {
    const [a, b] = CROPTONE[family] || CROPTONE.Grass, id = "c" + ++uid, r = rnd(hash(id2 + family));
    let s = `<rect width="400" height="240" fill="url(#${id})"/><circle cx="330" cy="54" r="26" fill="#fff" opacity=".35"/><path d="M0 196 Q120 170 230 192 T400 184 V240 H0Z" fill="#2c5f3d" opacity=".55"/>`;
    const stalk = (x, h) => {
      let g = `<path d="M${x} 214 V${214 - h}" stroke="#2c6a42" stroke-width="4" stroke-linecap="round"/>`;
      if (family === "Grass") g += `<ellipse cx="${x}" cy="${214 - h - 14}" rx="7" ry="20" fill="#d9a936"/>` + [1, 2, 3].map((k) => `<path d="M${x} ${214 - k * h / 4} q-24 -10 -34 -26 M${x} ${214 - k * h / 4} q24 -10 34 -26" stroke="#3a8a50" stroke-width="5" fill="none" stroke-linecap="round"/>`).join("");
      else if (family === "Legume") g += [1, 2, 3].map((k) => `<ellipse cx="${x + 12}" cy="${214 - k * h / 4}" rx="16" ry="6" fill="#4aa361" transform="rotate(-20 ${x + 12} ${214 - k * h / 4})"/><ellipse cx="${x - 12}" cy="${214 - k * h / 4 - 8}" rx="16" ry="6" fill="#3d9456" transform="rotate(20 ${x - 12} ${214 - k * h / 4 - 8})"/>`).join("") + `<path d="M${x + 6} ${214 - h * .55} q18 12 8 34" stroke="#7bbf4d" stroke-width="7" fill="none" stroke-linecap="round"/>`;
      else if (family === "Tuber") g += `<ellipse cx="${x}" cy="${214 - h}" rx="28" ry="14" fill="#3f9150"/><ellipse cx="${x - 10}" cy="218" rx="14" ry="9" fill="#b88a55"/><ellipse cx="${x + 12}" cy="222" rx="11" ry="8" fill="#c79a63"/>`;
      else if (family === "Vegetable") g += `<circle cx="${x}" cy="${214 - h - 10}" r="22" fill="#d8452f"/><circle cx="${x - 7}" cy="${214 - h - 17}" r="6" fill="#fff" opacity=".25"/>` + [0, 1].map((k) => `<ellipse cx="${x + (k ? 20 : -20)}" cy="${214 - h * .5}" rx="18" ry="7" fill="#3f9150" transform="rotate(${k ? -20 : 20} ${x} ${214 - h * .5})"/>`).join("");
      else if (family === "Fruit") g += `<ellipse cx="${x}" cy="${214 - h - 8}" rx="30" ry="20" fill="#f0c63a" transform="rotate(-18 ${x} ${214 - h - 8})"/><path d="M${x} 214 q-30 -30 -34 -62 M${x} 214 q30 -30 34 -62" stroke="#3a8a50" stroke-width="7" fill="none" stroke-linecap="round"/>`;
      else if (family === "Fibre & sugar") g += `<path d="M${x} 214 V${214 - h - 20}" stroke="#9bb04a" stroke-width="9" stroke-linecap="round"/>` + [1, 2, 3].map((k) => `<path d="M${x} ${214 - k * h / 4} q-30 -8 -42 -30 M${x} ${214 - k * h / 4} q30 -8 42 -30" stroke="#3a8a50" stroke-width="5" fill="none" stroke-linecap="round"/>`).join("") + `<circle cx="${x}" cy="${214 - h - 26}" r="9" fill="#fff" opacity=".85"/>`;
      else g += `<circle cx="${x}" cy="${214 - h - 18}" r="26" fill="#f5b81c"/><circle cx="${x}" cy="${214 - h - 18}" r="13" fill="#6b4423"/>` + [0, 1].map((k) => `<ellipse cx="${x + (k ? 18 : -18)}" cy="${214 - h * .5}" rx="18" ry="7" fill="#3f9150" transform="rotate(${k ? -20 : 20} ${x} ${214 - h * .5})"/>`).join("");
      return g;
    };
    s += stalk(150, 100 + r() * 12) + stalk(230, 112 + r() * 12) + stalk(310, 92 + r() * 12);
    return wrap(s, grad(id, [[0, a], [1, "#f5fbef"]]));
  }

    /* Every generated illustration carries a visible mark (NASA Space Apps AI rules). These are drawn by code written with an AI assistant. */
  const markAi = (svg) => svg.replace(/<\/svg>\s*$/, '<text x="392" y="232" text-anchor="end" font-size="9" font-family="sans-serif" fill="#fff" stroke="#000" stroke-opacity=".35" stroke-width=".4" opacity=".9">AI-assisted illustration</text></svg>');
FS.illus = (kind, key, extra) => raw(markAi((kind === "weather" ? weather(key) : kind === "soil" ? soil(key) : kind === "season" ? season(key) : kind === "manage" ? manage(key) : kind === "crop" ? crop(extra || "Grass", key) : weather("sunny"))));

  /* ----- photo loading with attribution ----- */
  /* v0.9: a failed lookup is never cached (it used to stick for the whole session, so one slow
   * Wikimedia answer left every picture as an illustration). Lookups are queued, at most 4 at a time,
   * and retried once, so opening the crop list no longer fires dozens of requests at once. */
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  let running = 0; const queue = [];
  const limited = (fn) => new Promise((resolve) => { queue.push({ fn, resolve }); pump(); });
  function pump() {
    while (running < 4 && queue.length) {
      const { fn, resolve } = queue.shift(); running++;
      fn().then(resolve, () => resolve(null)).finally(() => { running--; pump(); });
    }
  }
  const withRetry = async (get) => { for (let i = 0; i < 2; i++) { try { const r = await get(); if (r) return r; } catch { /* retry */ } if (i === 0) await wait(900); } return null; };
  const mediaCache = new Map();
  FS.media = (kind, key) => {
    const k = kind + ":" + key;
    if (!mediaCache.has(k)) mediaCache.set(k, limited(() => withRetry(() => FS.api(`/media?kind=${encodeURIComponent(kind)}&key=${encodeURIComponent(key)}`).then((r) => (r.images || [])[0] || null))).then((r) => { if (!r) mediaCache.delete(k); return r; }));
    return mediaCache.get(k);
  };
  const cropCache = new Map();
  FS.cropInfo = (id, light = true) => {
    const lat = FS.currentLat ? FS.currentLat() : 0, full = `${id}:${Math.round(lat)}:full`, lite = `${id}:${Math.round(lat)}:lite`;
    if (cropCache.has(full)) return cropCache.get(full);
    if (light && cropCache.has(lite)) return cropCache.get(lite);
    const key = light ? lite : full;
    const p = limited(() => withRetry(() => FS.api(`/crop-info/${id}?lat=${lat.toFixed(2)}${light ? "&light=true" : ""}`).then((i) => (i && (i.image_url || !light) ? i : null)))).then((i) => { if (!i) cropCache.delete(key); return i; });
    cropCache.set(key, p);
    return p;
  };

  /* A picture slot. kind: crop | weather | soil | season | manage. */
  FS.pic = (kind, key, { cls = "", alt = "", family = "", credit = true, style = "", img = null } = {}) =>
    html`<div class="pic ${cls}" ${style ? raw(`style="${String(style).replace(/[^a-zA-Z0-9:;. %-]/g, "")}"`) : ""} data-pic="${kind}:${key}" data-credit="${credit ? 1 : 0}" data-alt="${alt}"${img ? raw(` data-done="1" data-img="${esc(JSON.stringify(img))}"`) : ""}>${FS.illus(kind, key, family)}</div>`;

  function attach(el, img) {
    if (!img || !img.url || !el.isConnected) return;
    const tag = new Image();
    tag.alt = el.dataset.alt || "";
    /* no loading="lazy": a detached Image never starts loading with it. Slots are only hydrated when rendered, so eager is right. */
    tag.decoding = "async";
    tag.referrerPolicy = "no-referrer";
    tag.onload = () => {
      el.appendChild(tag);
      requestAnimationFrame(() => tag.classList.add("in"));
      if (el.dataset.credit === "1" && img.page) {
        const a = document.createElement("a");
        a.className = "credit";
        a.href = safeUrl(img.page); a.target = "_blank"; a.rel = "noreferrer noopener";
        a.textContent = `${img.author ? img.author.slice(0, 28) + " · " : ""}${img.license || "Wikimedia Commons"}`;
        a.title = "Photo from Wikimedia Commons – open file page";
        a.addEventListener("click", (e) => e.stopPropagation());
        el.appendChild(a);
      }
    };
    tag.onerror = () => tag.remove();
    tag.src = safeUrl(img.url);
  }

  FS.hydrate = (root = document) => {
    root.querySelectorAll("[data-pic]:not([data-done])").forEach((el) => {
      el.dataset.done = "1";
      const [kind, key] = el.dataset.pic.split(":");
      if (kind === "crop") FS.cropInfo(key, true).then((i) => i && i.image_url && attach(el, { url: i.image_url, page: i.image_attribution_url, license: i.image_license, author: i.image_author }));
      else FS.media(kind, key).then((img) => attach(el, img));
    });
  };
  /* Attach a known image object (e.g. growth-stage photos already returned by the API). */
  FS.picWith = (kind, key, img, opts = {}) => FS.pic(kind, key, { ...opts, img: img || null });
  FS.hydrateKnown = (root = document) => root.querySelectorAll("[data-img]:not([data-attached])").forEach((el) => { el.dataset.attached = "1"; try { attach(el, JSON.parse(el.dataset.img)); } catch { /* ignore */ } });
