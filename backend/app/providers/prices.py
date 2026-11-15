# AI-assisted: written with an AI coding assistant.
"""Market price adapters, freshness rules, caching and an SSE-ready board.

Rules enforced here (and tested):
  * Every price carries its source, as-of date, unit, currency and a freshness badge.
  * Freshness comes from the ADAPTER's declared cadence. Monthly data is never labelled "live". No adapter here is real-time.
  * A crop with no source for a country returns `no_data` with a reason. Nothing is ever estimated or interpolated.
  * If a source fails, the last good series is served and marked stale; if there is none, `no_data`.

Sources actually wired:
  imf_fred   IMF Primary Commodity Prices via FRED CSV (monthly, world benchmark, USD)         - no key
  agmarknet  India daily mandi prices via data.gov.in OGD API (INR per quintal)                - needs DATA_GOV_IN_API_KEY
  frankfurter ECB reference exchange rates via api.frankfurter.dev (daily)                      - no key
NOT built: FAO GIEWS FPMA (no endpoint was verified), World Bank Pink Sheet (xlsx with unstable URL), USDA AMS/NASS, delayed futures (no free key obtained)."""
from __future__ import annotations

import asyncio
import hashlib
import json
import statistics
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable

from . import base

DATA = Path(__file__).resolve().parents[1] / "data"
MAP = json.loads((DATA / "price_map.json").read_text(encoding="utf-8"))
COUNTRIES: dict[str, dict[str, str]] = MAP["countries"]

MASS_KG = {"kg": 1.0, "tonne": 1000.0, "quintal": 100.0, "lb": 0.45359237}
UNIT_LABELS = {"kg": "per kg", "tonne": "per tonne", "quintal": "per quintal (100 kg)", "lb": "per lb"}
STALE_AFTER_DAYS = {"daily": 4, "monthly": 100}  # monthly observations are dated the 1st and published ~1 month after the month ends
TTL_S = {"monthly": 6 * 3600, "daily": 900}
FAIL_TTL_S = 60
FRESHNESS_BASE = {"live": "live", "delayed_15m": "delayed 15 min", "daily": "daily", "monthly": "monthly"}


def freshness(cadence: str, as_of: date, today: date | None = None) -> dict[str, Any]:
    """Badge for a price. Only cadence 'live' may ever say live; monthly data says monthly, and old data is flagged stale."""
    if cadence not in FRESHNESS_BASE:
        raise ValueError(f"unknown cadence {cadence!r}")
    today = today or datetime.now(timezone.utc).date()
    age = (today - as_of).days
    stale = cadence in STALE_AFTER_DAYS and age > STALE_AFTER_DAYS[cadence]
    label = FRESHNESS_BASE[cadence] + (f" · stale ({age} days old)" if stale else "")
    return {"code": cadence, "label": label, "stale": stale, "age_days": age}


def convert_unit(value: float, frm: str, to: str) -> float:
    """Price per `frm` mass unit -> price per `to` mass unit (e.g. USD/tonne -> USD/kg)."""
    return value / MASS_KG[frm] * MASS_KG[to]


# ---------------------------------------------------------------- parsers (pure)
def parse_fred_csv(text: str, scale: float = 1.0) -> list[tuple[str, float]]:
    """FRED graph CSV: header line then 'YYYY-MM-DD,value'. '.' or empty means missing. Raises ValueError when nothing usable."""
    rows = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    if len(rows) < 2 or "," not in rows[0]:
        raise ValueError("not a FRED CSV")
    out = []
    for ln in rows[1:]:
        d, _, v = ln.partition(",")
        try:
            date.fromisoformat(d)
            out.append((d, round(float(v) * scale, 6)))
        except ValueError:
            continue
    if not out:
        raise ValueError("no observations")
    return sorted(out)


def parse_agmarknet(raw: dict[str, Any]) -> list[dict[str, Any]]:
    """data.gov.in mandi records -> one point per arrival date: median modal price over reporting markets (INR/quintal)."""
    recs = (raw or {}).get("records")
    if not isinstance(recs, list):
        raise ValueError("no records list")
    by_day: dict[str, dict[str, list[float]]] = {}
    for r in recs:
        if not isinstance(r, dict):
            continue
        try:
            d = datetime.strptime(str(r.get("arrival_date")), "%d/%m/%Y").date().isoformat()
            modal = float(r["modal_price"])
        except (KeyError, TypeError, ValueError):
            continue
        if modal <= 0:
            continue
        day = by_day.setdefault(d, {"modal": [], "min": [], "max": []})
        day["modal"].append(modal)
        for k, f in (("min", "min_price"), ("max", "max_price")):
            try:
                day[k].append(float(r[f]))
            except (KeyError, TypeError, ValueError):
                pass
    pts = [{"date": d, "value": round(statistics.median(v["modal"]), 2), "min": min(v["min"]) if v["min"] else None, "max": max(v["max"]) if v["max"] else None, "markets": len(v["modal"])}
           for d, v in sorted(by_day.items())]
    if not pts:
        raise ValueError("no usable mandi records")
    return pts


def parse_frankfurter(raw: dict[str, Any]) -> dict[str, Any]:
    rates = (raw or {}).get("rates")
    if not isinstance(rates, dict) or not rates or not (raw or {}).get("date"):
        raise ValueError("no rates")
    clean = {k: float(v) for k, v in rates.items() if isinstance(v, (int, float)) and v > 0}
    clean["USD"] = 1.0
    return {"base": "USD", "date": raw["date"], "rates": clean}


def stats(points: list[dict[str, Any]]) -> dict[str, Any]:
    vals = [p["value"] for p in points]
    out: dict[str, Any] = {"n": len(vals), "change_pct": None, "min": min(vals) if vals else None, "max": max(vals) if vals else None, "cv_pct": None}
    if len(vals) >= 2 and vals[-2]:
        out["change_pct"] = round((vals[-1] / vals[-2] - 1) * 100, 1)
    if len(vals) >= 12:
        w = vals[-24:]
        m = statistics.mean(w)
        out["cv_pct"] = round(statistics.pstdev(w) / m * 100, 1) if m else None  # coefficient of variation of up to the last 24 observations
    return out


def no_data(crop: str, country: str, reason: str, tried: list[str] | None = None) -> dict[str, Any]:
    return {"crop": crop, "country": country, "no_data": True, "reason": reason, "sources_tried": tried or [], "points": [], "latest": None, "freshness": None}


# ---------------------------------------------------------------- HTTP seam (tests inject fixtures here)
class Http:
    async def json(self, breaker, url, params=None, headers=None):
        return await base.fetch_json(breaker, url, params, headers)

    async def text(self, breaker, url, params=None, headers=None):
        return await base.fetch_text(breaker, url, params, headers)


# ---------------------------------------------------------------- service
class PriceService:
    def __init__(self, http: Http | None = None, settings: dict[str, str] | None = None, clock: Callable[[], float] = time.time, today: Callable[[], date] | None = None):
        self.http = http or Http()
        self.keys = settings or {}
        self.clock = clock
        self.today = today or (lambda: datetime.now(timezone.utc).date())
        self.cache = base.TTLCache(clock)
        self.last_good: dict[str, dict[str, Any]] = {}
        self.breakers = {n: base.CircuitBreaker(clock=clock) for n in ("imf_fred", "agmarknet", "frankfurter")}
        self.fx_url = self.keys.get("FX_API_URL", "https://api.frankfurter.dev/v1/latest")

    # -- availability
    def providers(self) -> list[dict[str, Any]]:
        return [{"id": "imf_fred", "name": "IMF Primary Commodity Prices (via FRED)", "cadence": "monthly", "scope": "World benchmark, USD", "configured": True, "url": "https://fred.stlouisfed.org/"},
                {"id": "agmarknet", "name": "Agmarknet daily mandi prices (data.gov.in)", "cadence": "daily", "scope": "India, INR per quintal", "configured": bool(self.keys.get("DATA_GOV_IN_API_KEY")),
                 "note": None if self.keys.get("DATA_GOV_IN_API_KEY") else "Not configured: set DATA_GOV_IN_API_KEY (free key from data.gov.in).", "url": "https://data.gov.in/"},
                {"id": "frankfurter", "name": "ECB reference exchange rates (Frankfurter)", "cadence": "daily", "scope": "Currency conversion only", "configured": True, "url": "https://frankfurter.dev/"}]

    def sources_for(self, crop: str, country: str) -> list[str]:
        if country == "WORLD":
            return ["imf_fred"] if crop in MAP["imf_fred"] else []
        if country == "IN":
            return ["agmarknet"] if crop in MAP["agmarknet"] else []
        return []

    # -- fetch with cache + stale fallback
    async def _cached(self, key: str, ttl: int, producer):
        hit = self.cache.get(key)
        if hit is not None:
            return hit
        try:
            res = await producer()
        except Exception as exc:  # never raises to callers
            prev = self.last_good.get(key)
            if prev:
                stale = {**prev, "stale_fallback": True, "stale_reason": f"Source unreachable ({str(exc)[:60]}); showing the last good data fetched {prev['fetched_at']}."}
                stale["freshness"] = {**prev["freshness"], "stale": True, "label": prev["freshness"]["label"].split(" · ")[0] + " · stale (source unreachable)"}
                self.cache.set(key, stale, FAIL_TTL_S)
                return stale
            return self.cache.set(key, {"_failed": str(exc)[:80]}, FAIL_TTL_S)
        self.last_good[key] = res
        return self.cache.set(key, res, ttl)

    def _series(self, crop, country, source_id, source_name, url, series_id, title, unit, currency, cadence, points, fetched_at, extra=None):
        latest = points[-1]
        return {"crop": crop, "country": country, "no_data": False, "source_id": source_id, "source": source_name, "source_url": url, "series_id": series_id, "title": title,
                "unit": unit, "currency": currency, "cadence": cadence, "as_of": latest["date"], "fetched_at": fetched_at, "points": points, "latest": latest,
                "freshness": freshness(cadence, date.fromisoformat(latest["date"]), self.today()), "stats": stats(points), **(extra or {})}

    async def _imf(self, crop: str) -> dict[str, Any]:
        m = MAP["imf_fred"][crop]

        async def go():
            text = await self.http.text(self.breakers["imf_fred"], "https://fred.stlouisfed.org/graph/fredgraph.csv", {"id": m["series"]})
            pts = [{"date": d, "value": v} for d, v in parse_fred_csv(text, m["scale"])]
            return self._series(crop, "WORLD", "imf_fred", "IMF Primary Commodity Prices via FRED", f"https://fred.stlouisfed.org/series/{m['series']}", m["series"], m["title"], m["unit"], "USD", "monthly", pts, base.now_iso(),
                                {"proxy_note": m.get("proxy"), "copyright": "Copyright International Monetary Fund; terms at imf.org/external/terms.htm"})
        return await self._cached(f"imf:{crop}", TTL_S["monthly"], go)

    async def _agmarknet(self, crop: str) -> dict[str, Any]:
        name = MAP["agmarknet"][crop]

        async def go():
            raw = await self.http.json(self.breakers["agmarknet"], "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070",
                                       {"api-key": self.keys["DATA_GOV_IN_API_KEY"], "format": "json", "limit": 1000, "filters[commodity]": name})
            pts = parse_agmarknet(raw)
            return self._series(crop, "IN", "agmarknet", "Agmarknet via data.gov.in (Government of India)", "https://data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi", "9ef84268-d588-465a-a308-a864a43d0070",
                                f"Median of mandi modal prices: {name}", "quintal", "INR", "daily", pts, base.now_iso(),
                                {"note": "Median of market modal prices per arrival date. The API returns only recent dates, so history is short."})
        return await self._cached(f"agm:{crop}", TTL_S["daily"], go)

    async def series(self, crop: str, country: str = "WORLD") -> dict[str, Any]:
        """Real series for (crop, country) or an explicit `no_data` result. Never raises, never estimates."""
        country = country.upper()
        if country not in COUNTRIES:
            return no_data(crop, country, "Unknown country.")
        srcs = self.sources_for(crop, country)
        if not srcs:
            why = ("No price source is wired for this crop at world level." if country == "WORLD" else
                   f"No country-level price source is configured for {COUNTRIES[country]['name']}. FieldShift does not estimate prices.")
            return no_data(crop, country, why)
        if srcs[0] == "agmarknet" and not self.keys.get("DATA_GOV_IN_API_KEY"):
            return no_data(crop, country, "India mandi prices need a free data.gov.in key (DATA_GOV_IN_API_KEY). Not configured on this server.", ["agmarknet"])
        res = await (self._imf(crop) if srcs[0] == "imf_fred" else self._agmarknet(crop))
        if "_failed" in res:
            return no_data(crop, country, f"The price source is unreachable right now ({res['_failed']}). No cached data exists.", srcs)
        return res

    async def board(self, country: str = "WORLD", crops: list[str] | None = None) -> dict[str, Any]:
        from ..engine.crops import load_crops
        ids = crops or [c["id"] for c in load_crops()]
        res = await asyncio.gather(*[self.series(c, country) for c in ids])
        return {"country": country.upper(), "country_name": COUNTRIES.get(country.upper(), {}).get("name", country), "generated_at": base.now_iso(), "crops": {r["crop"]: r for r in res},
                "providers": self.providers()}

    # -- FX
    async def fx(self) -> dict[str, Any]:
        async def go():
            raw = await self.http.json(self.breakers["frankfurter"], self.fx_url, {"base": "USD"})
            fx = parse_frankfurter(raw)
            return {**fx, "source": "ECB reference rates via Frankfurter (api.frankfurter.dev)", "fetched_at": base.now_iso(), "note": "Daily end-of-day reference rates, ~30 currencies. Not a trading quote."}
        res = await self._cached("fx", 6 * 3600, go)
        return {"ok": False, "error": res["_failed"], "rates": {}} if "_failed" in res else {"ok": True, **res}

    def convert(self, value: float, native_currency: str, target: str, fx: dict[str, Any]) -> float | None:
        """Convert via USD. None when either rate is missing (we do not guess)."""
        if native_currency == target:
            return value
        r = (fx or {}).get("rates") or {}
        if native_currency not in r or target not in r:
            return None
        return value / r[native_currency] * r[target]

    async def priced(self, crop: str, country: str, currency: str | None, unit: str | None) -> dict[str, Any]:
        """Series plus converted points in the requested currency/unit. Original values are always kept."""
        s = await self.series(crop, country)
        if s["no_data"]:
            return s
        target_cur = (currency or s["currency"]).upper()
        target_unit = unit or s["unit"]
        if target_unit not in MASS_KG:
            raise ValueError("unit must be one of " + ", ".join(MASS_KG))
        fx = await self.fx() if target_cur != s["currency"] else None
        conv_pts, ok = [], True
        for p in s["points"]:
            v = convert_unit(p["value"], s["unit"], target_unit)
            if fx is not None:
                v = self.convert(v, s["currency"], target_cur, fx)
            if v is None:
                ok = False
                break
            conv_pts.append({"date": p["date"], "value": round(v, 4)})
        out = {**s, "display": {"currency": target_cur if ok else s["currency"], "unit": target_unit if ok else s["unit"], "converted": ok and (target_cur != s["currency"] or target_unit != s["unit"]),
                               "points": conv_pts if ok else s["points"], "unit_label": UNIT_LABELS.get(target_unit if ok else s["unit"])}}
        if fx is not None:
            out["display"]["fx"] = {"source": fx.get("source"), "date": fx.get("date"), "ok": fx.get("ok")}
            if not ok:
                out["display"]["note"] = f"No exchange rate for {target_cur} from the ECB set, so values are shown in {s['currency']} (original)."
        return out

    # -- health
    def status(self) -> list[dict[str, Any]]:
        out = []
        for p in self.providers():
            b = self.breakers[p["id"]]
            out.append({"id": p["id"], "name": p["name"], "configured": p["configured"], "cadence": p["cadence"], "circuit": b.state, "last_success": b.last_success, "last_latency_ms": b.last_latency_ms,
                        "last_error": b.last_error, "consecutive_failures": b.failures})
        return out

    async def probe(self) -> dict[str, dict[str, Any]]:
        """Cheap active check of each configured price provider. Never raises."""
        async def one(pid: str):
            t0 = time.perf_counter()
            try:
                if pid == "imf_fred":
                    await self.http.text(self.breakers["imf_fred"], "https://fred.stlouisfed.org/graph/fredgraph.csv", {"id": "PWHEAMTUSDM"})
                elif pid == "frankfurter":
                    await self.http.json(self.breakers["frankfurter"], self.fx_url, {"base": "USD", "symbols": "EUR"})
                else:
                    if not self.keys.get("DATA_GOV_IN_API_KEY"):
                        return pid, {"state": "not_configured", "detail": "DATA_GOV_IN_API_KEY not set"}
                    await self.http.json(self.breakers["agmarknet"], "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070", {"api-key": self.keys["DATA_GOV_IN_API_KEY"], "format": "json", "limit": 1})
                return pid, {"state": "up", "latency_ms": round((time.perf_counter() - t0) * 1000, 1)}
            except Exception as exc:
                return pid, {"state": "down", "detail": str(exc)[:80], "latency_ms": round((time.perf_counter() - t0) * 1000, 1)}
        return dict(await asyncio.gather(*[one(p["id"]) for p in self.providers()]))


# ---------------------------------------------------------------- estimated gross value (NOT profit)
def gross_value(series: dict[str, Any], area_ha: float, yield_t_ha: float, display_currency: str, fx_convert: Callable[[float, str, str], float | None]) -> dict[str, Any]:
    """area x yield (BOTH entered by the user) x latest real price. Excludes every cost. Refuses to run on `no_data`."""
    if series.get("no_data"):
        return {"available": False, "reason": series.get("reason", "no price data")}
    if not (area_ha > 0 and yield_t_ha > 0):
        return {"available": False, "reason": "Enter an area and an expected yield (t/ha). FieldShift does not bundle yields."}
    price_t = convert_unit(series["latest"]["value"], series["unit"], "tonne")
    cur = series["currency"]
    conv = fx_convert(price_t, cur, display_currency)
    note = None
    if conv is None:
        conv, display_currency, note = price_t, cur, f"No exchange rate available; shown in {cur}."
    per_ha = yield_t_ha * conv
    return {"available": True, "label": "Estimated gross value (revenue before any costs; NOT profit)", "price_per_tonne": round(conv, 2), "currency": display_currency, "price_as_of": series["as_of"], "price_source": series["source"],
            "freshness": series["freshness"], "yield_t_ha": yield_t_ha, "area_ha": area_ha, "gross_per_ha": round(per_ha, 2), "gross_total": round(per_ha * area_ha, 2), "note": note,
            "assumptions": ["Yield and area are entered by you; FieldShift has no yield data.", "Uses the latest published price shown, which may be a national or export benchmark, not your local farm-gate price.",
                            "Excludes seed, fertiliser, labour, water, transport, losses, taxes and storage. This is not profit and not a forecast."]}


# ---------------------------------------------------------------- Server-Sent Events
def digest(board: dict[str, Any]) -> str:
    key = [(c, (r.get("latest") or {}).get("date"), (r.get("latest") or {}).get("value"), bool((r.get("freshness") or {}).get("stale")), r.get("no_data")) for c, r in sorted(board["crops"].items())]
    return hashlib.sha1(json.dumps(key, default=str).encode()).hexdigest()[:12]


def sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str, separators=(',', ':'))}\n\n"


async def stream(svc: PriceService, country: str, interval_s: float = 60.0, max_events: int | None = None, sleep=asyncio.sleep):
    """Yield an SSE frame for the first snapshot, then only when the cached data changes (plus keep-alives). `max_events` is for tests."""
    last, n = None, 0
    while True:
        board = await svc.board(country)
        d = digest(board)
        if d != last:
            last = d
            yield sse("prices", {"digest": d, **slim(board)})
        else:
            yield sse("tick", {"checked_at": base.now_iso(), "digest": d})
        n += 1
        if max_events is not None and n >= max_events:
            return
        await sleep(interval_s)


def slim(board: dict[str, Any], keep: int = 36) -> dict[str, Any]:
    """Board without the heavy `points` arrays beyond the last `keep` observations (keeps SSE frames small)."""
    crops = {}
    for c, r in board["crops"].items():
        r2 = dict(r)
        if r2.get("points"):
            r2["points"] = r2["points"][-keep:]
        crops[c] = r2
    return {**board, "crops": crops}
