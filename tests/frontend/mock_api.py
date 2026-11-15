# AI-assisted: written with an AI coding assistant (see README, "AI tools used").
"""STAND-IN server for frontend tests. NOT the real FastAPI app (FastAPI cannot be installed in this sandbox).

It serves frontend/ statics plus the API contract, reusing the real backend modules that are importable without
FastAPI (engine, services, assistant, reports, Database, security) with deterministic hand-written provider fixtures.
Run: python tests/frontend/mock_api.py [port]   (env MOCK_XSS=1 replaces response strings with an XSS probe)."""
from __future__ import annotations

import asyncio
import json
import mimetypes
import os
import sys
import tempfile
import time
import urllib.parse
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app import assistant, reports, services  # noqa: E402
from app.core import security  # noqa: E402
from app.db.repo import Conflict, Database, NotFound, TooLarge, owner_for_guest, owner_for_user  # noqa: E402
from app.engine import content, finance, geo  # noqa: E402
from app.engine.crops import crop_by_id, load_crops  # noqa: E402
from app.providers import parsers  # noqa: E402
from app.providers.base import result  # noqa: E402
from app.providers import prices as prices_mod  # noqa: E402
from app.engine import climate_series, credits as credits_mod, risks as risks_mod  # noqa: E402

XSS = "<img src=x onerror=window.__pwned=1>"
KEEP = {"id", "crop_id", "priority", "category", "kind", "texture_key", "family", "level", "status", "mode", "basis", "type", "date", "generated_at", "time", "state", "season", "water", "stage",
        "method", "fetched_at", "access_token", "token_type", "email", "image_key", "triggered_on", "component", "crop", "sow_months", "harvest_months", "icon", "term"}
SECRET = "k" * 40
today = date.today()
_FRED = lambda sid, base: "observation_date," + sid + "\n" + "\n".join(f"{(date.today().replace(day=1) - timedelta(days=30 * k)).replace(day=1).isoformat()},{base + k * 3}" for k in range(14, 0, -1)) + "\n"
class _FixtureHttp:
    async def text(self, breaker, url, params=None, headers=None): return _FRED(params["id"], 200.0)
    async def json(self, breaker, url, params=None, headers=None): return {"amount": 1.0, "base": "USD", "date": date.today().isoformat(), "rates": {"EUR": 0.9, "INR": 84.0}}
PRICES = prices_mod.PriceService(_FixtureHttp(), {})


def _days(n, start):
    return [(start + timedelta(d)) for d in range(n)]


class FakeProviders:
    """Hand-written fixtures shaped like the real provider JSON, run through the real parsers."""
    def __init__(self):
        raw = {"properties": {"parameter": {
            "T2M": {d.strftime("%Y%m%d"): 24 + (i % 4) for i, d in enumerate(_days(14, today - timedelta(17)))},
            "PRECTOTCORR": {d.strftime("%Y%m%d"): 0.4 * (i % 3) for i, d in enumerate(_days(14, today - timedelta(17)))},
            "GWETROOT": {d.strftime("%Y%m%d"): 0.45 for d in _days(14, today - timedelta(17))},
            "ALLSKY_SFC_SW_DWN": {d.strftime("%Y%m%d"): 18.0 for d in _days(14, today - timedelta(17))}}}}
        T = [22, 25, 28, 31, 33, 29, 27, 26, 26, 25, 23, 21]
        R = [0.1, 0.1, 0.2, 0.5, 0.9, 3.5, 5.0, 4.5, 4.0, 1.8, 0.5, 0.1]
        clim = {"properties": {"parameter": {"T2M": dict(zip(parsers.MONTHS, T)), "PRECTOTCORR": dict(zip(parsers.MONTHS, R))}}}
        layer = lambda name, v: {"name": name, "depths": [{"label": l, "values": {"mean": v}} for l in ("0-5cm", "5-15cm", "15-30cm")]}  # noqa: E731
        soil = {"properties": {"layers": [layer("phh2o", 68), layer("soc", 150), layer("clay", 250), layer("sand", 450), layer("silt", 300)]}}
        start = today - timedelta(3)
        ds = _days(19, start)
        hours = []
        for i, d in enumerate(ds):
            for h in range(24):
                hours.append((f"{d.isoformat()}T{h:02d}:00", 18 + 8 * (h in range(11, 17)) + (i % 3), 95 if (i % 5 in (2, 3) and h < 14) else 55))
        fc = {"daily": {"time": [d.isoformat() for d in ds], "temperature_2m_max": [31 + (i % 6) for i in range(19)], "temperature_2m_min": [19 + (i % 3) for i in range(19)],
                        "precipitation_sum": [0, 0, 2, 12, 0, 0, 55 if i == 8 else 1, 0, 0, 0, 6, 0, 0, 0, 1, 0, 0, 0, 0][:19] if (i := 0) is not None else [], "et0_fao_evapotranspiration": [4.5 + (i % 3) * .4 for i in range(19)]},
              "hourly": {"time": [h[0] for h in hours], "temperature_2m": [h[1] for h in hours], "relative_humidity_2m": [h[2] for h in hours]},
              "current": {"temperature_2m": 27.1, "relative_humidity_2m": 61, "precipitation": 0.0}, "timezone": "Asia/Kolkata"}
        fc["daily"]["precipitation_sum"] = [0, 0, 2, 12, 0, 0, 0, 0, 55, 0, 0, 6, 0, 0, 1, 0, 0, 0, 0]
        self.d = parsers.parse_power_daily(raw); self.c = parsers.parse_power_climatology(clim); self.s = parsers.parse_soilgrids(soil); self.f = parsers.parse_open_meteo(fc)

    async def nasa_daily(self, lat, lon): return result("NASA POWER daily", self.d, "Global ~0.5° grid (fixture)", 3600, kind="observed")
    async def nasa_climatology(self, lat, lon): return result("NASA POWER climatology", self.c, "Global ~0.5° grid (fixture)", 86400, kind="climatology")
    async def soil(self, lat, lon): return result("ISRIC SoilGrids 2.0", dict(self.s), "Global 250 m modelled (fixture)", 86400, kind="modelled")
    async def forecast(self, lat, lon): return result("Open-Meteo forecast", self.f, "Model forecast up to 16 days (fixture)", 1800, kind="forecast")
    async def geocode(self, q): return result("OpenStreetMap Nominatim", [{"name": "Hyderabad, Telangana, India", "lat": 17.385, "lon": 78.4867, "country_code": "in"}], "fixture", 100)
    def status(self): return [{"provider": n, "state": "closed", "last_success": None, "last_error": None, "consecutive_failures": 0} for n in ("nasa_power", "soilgrids", "open_meteo", "nominatim")]


PROV = FakeProviders()
DB = Database(os.path.join(tempfile.mkdtemp(), "mock.db"))
KB = assistant.BM25(assistant.load_kb())
RUN = lambda coro: asyncio.run(coro)  # noqa: E731


def poison(v, key=None):
    if isinstance(v, dict):
        return {k: poison(x, k) for k, x in v.items()}
    if isinstance(v, list):
        return [poison(x, key) for x in v]
    if isinstance(v, str) and key not in KEEP:
        return XSS
    return v


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *a): pass

    def _send(self, code, body, ctype="application/json", headers=None):
        data = body if isinstance(body, bytes) else (json.dumps(poison(body) if os.environ.get("MOCK_XSS") else body)).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(data))); self.send_header("Cache-Control", "no-store")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers(); self.wfile.write(data)

    def _json(self): 
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}") if n else {}

    def who(self):
        h = self.headers.get("Authorization", "")
        if h.lower().startswith("bearer "):
            p = security.verify_token(h[7:], SECRET)
            if not p or not DB.user_by_id(int(p["sub"])): raise PermissionError("Invalid or expired token")
            return owner_for_user(int(p["sub"])), int(p["sub"])
        ws = self.headers.get("X-Workspace-ID")
        if ws:
            try: return owner_for_guest(ws), None
            except ValueError: raise PermissionError("A valid guest workspace ID is required")
        raise PermissionError("Sign in or provide a guest workspace ID")

    def do_GET(self): self.route("GET")
    def do_POST(self): self.route("POST")
    def do_PUT(self): self.route("PUT")
    def do_DELETE(self): self.route("DELETE")

    def route(self, m):
        u = urllib.parse.urlparse(self.path); path, q = u.path, {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        try:
            if path.startswith("/api") or path in ("/healthz", "/readyz"):
                return self.api(m, path, q)
            return self.static(path)
        except PermissionError as e:
            self._send(401, {"detail": str(e)})
        except NotFound as e:
            self._send(404, {"detail": str(e)})
        except Conflict as e:
            self._send(409, {"detail": str(e)})
        except TooLarge as e:
            self._send(413, {"detail": str(e)})
        except geo.GeometryError as e:
            self._send(422, {"detail": str(e)})
        except Exception as e:  # pragma: no cover
            import traceback; traceback.print_exc()
            self._send(500, {"detail": f"mock error {type(e).__name__}"})

    def static(self, path):
        base = Path(os.environ.get("FRONTEND_DIR") or ROOT / "frontend").resolve()
        f = (base / (path.lstrip("/") or "index.html")).resolve()
        if f.is_dir(): f = f / "index.html"
        if not str(f).startswith(str(base)) or not f.exists():
            return self._send(404, b"not found", "text/plain")
        ct = mimetypes.guess_type(str(f))[0] or "application/octet-stream"
        if f.suffix == ".js": ct = "text/javascript"
        self._send(200, f.read_bytes(), ct)

    def v07(self, m, p, q):
        """v0.7 endpoints. Prices come from hand-written fixtures through the REAL PriceService; nothing here is live data."""
        if p == "/api/market/stream": return self._send(404, {"detail": "mock: no SSE (frontend must fall back to polling)"})
        if p == "/api/market/meta": return self._send(200, {"countries": [{"code": k, **v} for k, v in prices_mod.COUNTRIES.items()], "providers": PRICES.providers(), "units": list(prices_mod.UNIT_LABELS), "currencies": ["USD", "EUR", "INR"],
                                                            "crops": [{"id": c["id"], "name": c["name"]} for c in load_crops()], "freshness_note": "fixture", "links": {"fao_fpma": "https://fpma.fao.org/giews/fpmat4/#/dashboard/home"}})
        if p == "/api/market/board": return self._send(200, prices_mod.slim(RUN(PRICES.board(q.get("country", "WORLD")))))
        if p == "/api/market/fx": return self._send(200, RUN(PRICES.fx()))
        if p == "/api/market/series": return self._send(200, RUN(PRICES.priced(q["crop"], q.get("country", "WORLD"), q.get("currency"), q.get("unit"))))
        if p == "/api/market/gross-value":
            b = self._json(); sr = RUN(PRICES.series(b["crop_id"], b.get("country", "WORLD")))
            return self._send(200, prices_mod.gross_value(sr, b["area_ha"], b["yield_t_ha"], b.get("currency", "USD"), lambda v, a, c: v if a == c else None))
        if p == "/api/credits": return self._send(200, credits_mod.load())
        if p == "/api/risks":
            b = self._json(); res = RUN(PROV.nasa_climatology(b["latitude"], b["longitude"]))
            return self._send(200, risks_mod.build(crop_by_id(b["crop_id"]), res["data"], {"ph": 6.4}, b["latitude"], 3))
        if p == "/api/climate/series":
            n = 60; end = date.today() - timedelta(days=3); ds = [(end - timedelta(days=n - 1 - i)).isoformat() for i in range(n)]
            daily = {"dates": ds, "temperature_c": [24 + (i % 7) * .6 for i in range(n)], "rain_mm": [0 if i % 5 else 6.0 for i in range(n)], "solar_mj_m2": [18 + (i % 4) for i in range(n)]}
            norm = RUN(PROV.nasa_climatology(float(q["lat"]), float(q["lon"])))["data"]; norm = {**norm, "solar_mj_m2_day": [18.0] * 12}
            return self._send(200, {**climate_series.build(daily, norm), "range": {"start": ds[0], "end": ds[-1]}, "source": "NASA POWER daily (fixture)", "fetched_at": "fixture", "coverage": "fixture", "units": {}, "location": {}})
        return self._send(404, {"detail": "mock: no route " + p})

    def api(self, m, path, q):
        p = path.replace("/api/v1/", "/api/", 1) if path.startswith("/api/v1/") else path
        v1 = path.startswith("/api/v1/")
        crops = list(load_crops())
        if p.startswith("/api/market/") or p in ("/api/climate/series", "/api/credits", "/api/risks"): return self.v07(m, p, q)
        if p in ("/api/health", "/healthz", "/readyz"): return self._send(200, {"status": "ok", "service": "FieldShift mock", "version": "1.0.0"})
        if p == "/api/crops": return self._send(200, crops)
        # ---- auth ----
        if v1 and p.startswith("/api/auth/"):
            return self.auth(m, p[len("/api/auth/"):])
        if p == "/api/sources":
            return self._send(200, {"sources": json.loads((ROOT / "backend/app/data/sources.json").read_text()), "status": PROV.status()})
        if p == "/api/farms" or p == "/api/fields":
            owner, _ = self.who()
            if m == "GET": return self._send(200, DB.list_farms(owner))
            body = self._json(); fid = DB.create_farm(owner, body["name"], body); return self._send(200, {"id": fid, **body, "saved": True})
        if p.startswith("/api/farms/") or p.startswith("/api/fields/"):
            owner, _ = self.who(); fid = int(p.rsplit("/", 1)[1])
            if m == "GET": return self._send(200, DB.get_farm(owner, fid))
            if m == "PUT": body = self._json(); DB.update_farm(owner, fid, body["name"], body); return self._send(200, {"id": fid, **body, "saved": True})
            if m == "DELETE": DB.delete_farm(owner, fid); return self._send(200, {"deleted": True})
        if p == "/api/settings":
            owner, _ = self.who()
            if m == "PUT": DB.put_settings(owner, self._json()["data"]); return self._send(200, self._json() if False else {})
            return self._send(200, DB.get_settings(owner))
        if p == "/api/analyze" or p == "/api/analysis":
            b = self._json(); return self._send(200, RUN(services.analyze(PROV, b["geometry"], b.get("priorities", {}), b.get("previous_crops", []), b.get("seasons", 4), b.get("margins") or {})))
        if p == "/api/recommendations":
            b = self._json(); return self._send(200, RUN(services.recommend(PROV, b["latitude"], b["longitude"], b.get("soil", {}), b.get("priorities", {}), b.get("previous_crops", []), b.get("margins") or {})))
        if p.startswith("/api/crop-info/") or (v1 and p.startswith("/api/crops/")):
            cid = p.rsplit("/", 1)[1]; c = crop_by_id(cid)
            if not c: return self._send(404, {"detail": "Crop not found"})
            extra = content.crop_extra(cid, float(q.get("lat", 0)))
            for s in extra["stages"]: s["image"] = None
            return self._send(200, {**c, **extra, "image_url": None, "image_attribution_url": None, "image_license": None, "image_author": None, "image_source": "Image unavailable; crop details remain available.", "gallery": [],
                                    "heuristic_parameters": [k for k, pr in c["provenance"].items() if pr["status"] == "heuristic"]})
        if p == "/api/media": return self._send(200, {"kind": q.get("kind"), "key": q.get("key"), "images": []})
        if p == "/api/weather": return self._send(200, RUN(services.weather(PROV, float(q["lat"]), float(q["lon"]))))
        if p == "/api/pests":
            out = RUN(services.pest_outlook(PROV, float(q["lat"]), float(q["lon"]), q["crop_id"]))
            out["known_issues"] = json.loads((ROOT / "backend/app/data/pests.json").read_text()).get(q["crop_id"], {}); return self._send(200, out)
        if p == "/api/irrigation":
            b = self._json()
            return self._send(200, RUN(services.irrigation_plan(PROV, b["latitude"], b["longitude"], b["crop_id"], date.fromisoformat(b["sowing_date"]), b.get("method", "drip"), b.get("sand_pct"), b.get("clay_pct"), b.get("soc_g_kg"), b.get("root_depth_m", .6), b.get("depletion_fraction", .5), b.get("max_mm_per_week"))))
        if p == "/api/soil-health": return self._send(200, RUN(services.soil_health_report(PROV, float(q["lat"]), float(q["lon"]), q.get("crop_id"), float(q["area_ha"]) if q.get("area_ha") else None)))
        if p == "/api/geocode": return self._send(200, {"results": RUN(PROV.geocode(q.get("q", "")))["data"], "source": "OpenStreetMap Nominatim", "attribution": "© OpenStreetMap contributors"})
        if p == "/api/finance/evaluate":
            b = self._json(); costs = {k: (b.get("costs") or {}).get(k) for k in finance.COST_CATEGORIES}
            now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            return self._send(200, services.finance_report(b["crop_id"], b.get("area_ha", 1.0), b.get("yield_t_ha"), b.get("price_per_t"), costs, b.get("ranges"), {k: {"type": t, "recorded_at": now} for k, t in (b.get("provenance") or {}).items()}))
        if p == "/api/finance/plans":
            owner, _ = self.who()
            if m == "GET": return self._send(200, DB.list_plans(owner, int(q["farm_id"]) if q.get("farm_id") else None))
            b = self._json(); now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            data = {k: v for k, v in b.items() if k not in ("crop_id", "farm_id")}; data["provenance"] = {k: {"type": t, "recorded_at": now} for k, t in (b.get("provenance") or {}).items()}
            pid = DB.save_plan(owner, b["crop_id"], data, b.get("farm_id"), int(q["plan_id"]) if q.get("plan_id") else None); return self._send(200, {"id": pid, "saved": True})
        if p.startswith("/api/finance/plans/") and m == "DELETE":
            owner, _ = self.who(); DB.delete_plan(owner, int(p.rsplit("/", 1)[1])); return self._send(200, {"deleted": True})
        if p in ("/api/finance/export.csv", "/api/finance/export.pdf"):
            owner, _ = self.who(); plans = DB.list_plans(owner)
            for pl in plans: pl["provenance"] = {k: (x["type"] if isinstance(x, dict) else x) for k, x in pl.get("provenance", {}).items()}
            names = {c["id"]: c["name"] for c in crops}
            if p.endswith(".csv"): return self._send(200, finance.to_csv(reports.plan_rows(plans, names)).encode(), "text/csv", {"Content-Disposition": 'attachment; filename="fieldshift-finance.csv"'})
            return self._send(200, reports.pdf_report(plans, names), "application/pdf")
        if p == "/api/assistant":
            b = self._json(); crop = next((c for c in crops if c["id"] == b["crop"].lower() or c["name"].lower() == b["crop"].lower()), None)
            if not crop: return self._send(200, {"answer": "I couldn't match that crop.", "mode": "automatic explanation", "evidence": [], "uncertainty": "", "follow_ups": []})
            if b.get("latitude") is None: return self._send(200, {"answer": crop["description"], "mode": "automatic explanation", "evidence": [], "uncertainty": "No site data supplied.", "follow_ups": []})
            res = RUN(services.recommend(PROV, b["latitude"], b["longitude"], {}, {"resilience": .34, "soil": .33, "water": .33}, []))
            item = next(r for r in res["ranked"] if r["crop"]["id"] == crop["id"])
            return self._send(200, RUN(assistant.answer(b.get("question", ""), assistant.facts_from_result(item), KB, None)))
        self._send(404, {"detail": f"mock: no route {m} {path}"})

    def auth(self, m, name):
        if name == "register":
            b = self._json(); email = b["email"].strip().lower(); probs = security.password_problems(b["password"], email)
            if not security.valid_email(email): return self._send(422, {"detail": "Enter a valid email address"})
            if probs: return self._send(422, {"detail": " ".join(probs)})
            uid = DB.create_user(email, security.hash_password(b["password"])); return self.issue(uid, {"user": {"id": uid, "email": email}}, 201)
        if name == "login":
            b = self._json(); u = DB.user_by_email(b["email"].strip().lower())
            if not u or not security.verify_password(b["password"], u["password_hash"]): return self._send(401, {"detail": "Incorrect email or password"})
            return self.issue(u["id"], {"user": {"id": u["id"], "email": u["email"]}})
        if name in ("refresh", "logout"):
            if self.headers.get("X-Requested-With") != "fieldshift": return self._send(403, {"detail": "Missing request header"})
            ck = {k.strip(): v for k, v in (c.split("=", 1) for c in self.headers.get("Cookie", "").split(";") if "=" in c)}; tok = ck.get("fs_refresh")
            if name == "logout":
                if tok: DB.revoke_family(security.hash_refresh(tok))
                return self._send(200, {"ok": True}, headers={"Set-Cookie": "fs_refresh=; Path=/api/v1/auth; Max-Age=0; HttpOnly"})
            got = DB.rotate_refresh(security.hash_refresh(tok)) if tok else None
            if not got: return self._send(401, {"detail": "Session expired"})
            return self.issue(got[0], {}, 200, got[1])
        owner, uid = self.who()
        if uid is None: return self._send(401, {"detail": "An account is required"})
        if name == "me": return self._send(200, DB.user_by_id(uid))
        if name == "export": return self._send(200, DB.export_user(uid))
        if name == "account" and m == "DELETE":
            b = self._json(); u = DB.user_by_email(DB.user_by_id(uid)["email"])
            if not security.verify_password(b["password"], u["password_hash"]): return self._send(403, {"detail": "Password is incorrect"})
            DB.delete_user(uid); return self._send(200, {"deleted": True})
        self._send(404, {"detail": "no such auth route"})

    def issue(self, uid, extra, code=200, family=None):
        import uuid
        access = security.sign_token({"sub": str(uid), "typ": "access"}, SECRET, 900); t, th = security.new_refresh_token()
        DB.store_refresh(th, uid, family or uuid.uuid4().hex, time.time() + 86400)
        self._send(code, {"access_token": access, "token_type": "bearer", "expires_in": 900, **extra}, headers={"Set-Cookie": f"fs_refresh={t}; Path=/api/v1/auth; HttpOnly; SameSite=Lax; Max-Age=86400"})


def serve(port=0):
    srv = ThreadingHTTPServer(("127.0.0.1", port), H); return srv


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    print(f"mock API + frontend on http://127.0.0.1:{port}", flush=True)
    serve(port).serve_forever()
