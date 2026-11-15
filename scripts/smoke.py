#!/usr/bin/env python3
# AI-assisted: written with an AI coding assistant (see README, "AI tools used").
"""Smoke test for a RUNNING FieldShift server. Uses only the standard library.
Usage: python scripts/smoke.py [base_url]     (default http://127.0.0.1:8000)
Hits every endpoint, prints PASS/FAIL/WARN and exits non-zero on any FAIL. WARN = an upstream data source was unreachable (not a code bug)."""
import json, sys, urllib.error, urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")
LAT, LON = 12.97, 77.59
res = []

def call(method, path, body=None):
    req = urllib.request.Request(BASE + path, method=method, data=json.dumps(body).encode() if body is not None else None, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as e:
        return 0, str(e)

def check(name, method, path, body=None, test=None, upstream=False):
    code, text = call(method, path, body)
    try:
        data = json.loads(text)
    except Exception:
        data = text
    try:
        ok = code == 200 and (test is None or bool(test(data)))
    except Exception:  # unexpected response shape counts as a failure
        ok = False
    status = "PASS" if ok else ("WARN" if upstream and code in (0, 502, 503) else "FAIL")
    res.append(status)
    print(f"{status:4} {name:34} {method} {path.split('?')[0]} -> {code}" + ("" if ok else f"  {str(text)[:160]}"))
    return data if ok else None

check("readyz", "GET", "/readyz", test=lambda d: d["status"] == "ready")
check("health honest + per provider", "GET", "/api/health", test=lambda d: d["status"] in ("ok", "degraded") and {"nasa_power", "soilgrids", "imf_fred"} <= {p["id"] for p in d["providers"]})
crops = check("27 crops", "GET", "/api/v1/crops", test=lambda d: len(d) == 27)
check("crop info", "GET", "/api/v1/crops/tomato", test=lambda d: bool(d))
check("market meta", "GET", "/api/v1/market/meta", test=lambda d: len(d["crops"]) == 27)
check("market board", "GET", "/api/v1/market/board?country=WORLD", test=lambda d: len(d["crops"]) == 27, upstream=True)
check("market series wheat (FRED)", "GET", "/api/v1/market/series?crop=wheat&country=WORLD", test=lambda d: d["no_data"] or d["freshness"]["code"] == "monthly", upstream=True)
check("market series India (key?)", "GET", "/api/v1/market/series?crop=onion&country=IN", test=lambda d: "no_data" in d)
check("fx rates", "GET", "/api/v1/market/fx", test=lambda d: "ok" in d, upstream=True)
check("gross value", "POST", "/api/v1/market/gross-value", {"crop_id": "wheat", "country": "WORLD", "area_ha": 2, "yield_t_ha": 3, "currency": "USD"}, test=lambda d: "available" in d, upstream=True)
check("climate series (NASA POWER)", "GET", f"/api/v1/climate/series?lat={LAT}&lon={LON}", test=lambda d: d["n_days"] > 0, upstream=True)
check("risks", "POST", "/api/v1/risks", {"crop_id": "tomato", "latitude": LAT, "longitude": LON}, test=lambda d: len(d["items"]) >= 5, upstream=True)
check("credits", "GET", "/api/v1/credits", test=lambda d: len(d["sections"]) >= 10)
check("recommendations (NASA+SoilGrids)", "POST", "/api/v1/recommendations", {"latitude": LAT, "longitude": LON}, test=lambda d: len(d["ranked"]) == 27 and "confidence" in d["ranked"][0], upstream=True)
check("frontend served", "GET", "/", test=lambda d: "FieldShift" in str(d))
print(f"\n{res.count('PASS')} passed, {res.count('WARN')} warnings (upstream unreachable), {res.count('FAIL')} failed")
sys.exit(1 if "FAIL" in res else 0)
