# AI-assisted: written with an AI coding assistant.
"""Price adapters, caching, stale handling, no-data paths, units, FX, gross value, SSE.
FIXTURES ARE HAND-WRITTEN from the documented response formats of FRED CSV, data.gov.in and Frankfurter. They are NOT recordings of live responses."""
import asyncio
import json
from datetime import date

from app.providers import prices
from app.providers.prices import PriceService

FRED_WHEAT = "observation_date,PWHEAMTUSDM\n2026-06-01,200.0\n2026-07-01,210.0\n2026-08-01,.\n2026-09-01,231.0\n"
FRED_COTTON = "observation_date,PCOTTINDUSDM\n2026-08-01,95.0\n2026-09-01,100.0\n"
AGM = {"records": [
    {"state": "Karnataka", "market": "A", "commodity": "Onion", "arrival_date": "13/11/2026", "min_price": "1500", "max_price": "2500", "modal_price": "2000"},
    {"state": "Karnataka", "market": "B", "commodity": "Onion", "arrival_date": "13/11/2026", "min_price": "1400", "max_price": "2600", "modal_price": "2200"},
    {"state": "Karnataka", "market": "C", "commodity": "Onion", "arrival_date": "13/11/2026", "min_price": "x", "max_price": "x", "modal_price": "2100"},
    {"state": "Karnataka", "market": "D", "commodity": "Onion", "arrival_date": "bad-date", "modal_price": "9999"},
    {"state": "Karnataka", "market": "E", "commodity": "Onion", "arrival_date": "12/11/2026", "modal_price": "0"},
]}
FX = {"amount": 1.0, "base": "USD", "date": "2026-11-13", "rates": {"EUR": 0.9, "INR": 84.0}}


class FakeHttp:
    """Scripted responses keyed by URL fragment. A value that is an Exception instance is raised."""
    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def _get(self, url, params):
        self.calls.append((url, params))
        for frag, val in self.routes.items():
            if frag in url:
                if isinstance(val, Exception):
                    raise val
                return val() if callable(val) else val
        raise RuntimeError("no route " + url)

    async def text(self, breaker, url, params=None, headers=None):
        return self._get(url, params)

    async def json(self, breaker, url, params=None, headers=None):
        return self._get(url, params)


def make(routes, keys=None, today=date(2026, 11, 14), clock=None):
    return PriceService(FakeHttp(routes), keys or {}, **({"clock": clock} if clock else {}), today=lambda: today)


def run(c):
    return asyncio.run(c)


def test_parse_fred_skips_missing_values_and_rejects_garbage():
    assert prices.parse_fred_csv(FRED_WHEAT) == [("2026-06-01", 200.0), ("2026-07-01", 210.0), ("2026-09-01", 231.0)]
    for bad in ("", "<html>nope</html>", "date,v\n2026-01-01,.\n"):
        try:
            prices.parse_fred_csv(bad); raise AssertionError("accepted " + bad[:10])
        except ValueError:
            pass


def test_parse_agmarknet_median_per_day_and_ignores_bad_rows():
    pts = prices.parse_agmarknet(AGM)
    assert len(pts) == 1 and pts[0]["date"] == "2026-11-13" and pts[0]["value"] == 2100.0 and pts[0]["markets"] == 3 and pts[0]["min"] == 1400.0
    for bad in ({}, {"records": []}, {"records": [{"arrival_date": "x"}]}):
        try:
            prices.parse_agmarknet(bad); raise AssertionError("accepted")
        except ValueError:
            pass


def test_world_series_has_source_unit_currency_asof_and_monthly_badge_never_live():
    s = run(make({"fredgraph": FRED_WHEAT}).series("wheat", "WORLD"))
    assert not s["no_data"] and s["source_id"] == "imf_fred" and s["unit"] == "tonne" and s["currency"] == "USD"
    assert s["as_of"] == "2026-09-01" and s["freshness"]["code"] == "monthly" and "live" not in s["freshness"]["label"]
    assert s["source_url"].endswith("PWHEAMTUSDM") and s["fetched_at"] and s["latest"]["value"] == 231.0
    assert s["stats"]["change_pct"] == 10.0


def test_cents_per_pound_series_is_scaled_to_dollars_per_lb():
    s = run(make({"fredgraph": FRED_COTTON}).series("cotton", "WORLD"))
    assert s["unit"] == "lb" and s["latest"]["value"] == 1.0
    kg = run(make({"fredgraph": FRED_COTTON}).priced("cotton", "WORLD", "USD", "kg"))
    assert abs(kg["display"]["points"][-1]["value"] - 1.0 / 0.45359237) < 1e-3 and kg["display"]["converted"]


def test_sugar_proxy_is_labelled_as_not_cane():
    s = run(make({"fredgraph": "d,v\n2026-09-01,20\n"}).series("sugarcane", "WORLD"))
    assert "not of sugarcane" in s["proxy_note"]


def test_no_world_source_means_no_data_not_estimate():
    s = run(make({}).series("lentil", "WORLD"))
    assert s["no_data"] and s["points"] == [] and s["latest"] is None and "No price source" in s["reason"]


def test_country_without_source_is_no_data_even_if_world_exists():
    s = run(make({"fredgraph": FRED_WHEAT}).series("wheat", "KE"))
    assert s["no_data"] and "does not estimate" in s["reason"]


def test_unknown_country_is_no_data():
    assert run(make({}).series("wheat", "ZZ"))["no_data"]


def test_india_needs_key_otherwise_no_data_and_makes_no_request():
    svc = make({"data.gov.in": AGM})
    s = run(svc.series("onion", "IN"))
    assert s["no_data"] and "DATA_GOV_IN_API_KEY" in s["reason"] and svc.http.calls == []


def test_india_with_key_returns_daily_series_in_inr_per_quintal():
    svc = make({"data.gov.in": AGM}, {"DATA_GOV_IN_API_KEY": "k"})
    s = run(svc.series("onion", "IN"))
    assert s["currency"] == "INR" and s["unit"] == "quintal" and s["freshness"]["code"] == "daily" and not s["freshness"]["stale"]
    url, params = svc.http.calls[0]
    assert params["filters[commodity]"] == "Onion" and params["api-key"] == "k"
    assert run(svc.priced("onion", "IN", "INR", "tonne"))["display"]["points"][-1]["value"] == 21000.0


def test_old_daily_data_is_flagged_stale():
    old = {"records": [{"market": "A", "arrival_date": "01/10/2026", "modal_price": "100"}]}
    s = run(make({"data.gov.in": old}, {"DATA_GOV_IN_API_KEY": "k"}).series("onion", "IN"))
    assert s["freshness"]["stale"] and "stale" in s["freshness"]["label"]


def test_freshness_labels_and_rules():
    t = date(2026, 11, 14)
    assert prices.freshness("monthly", date(2026, 9, 1), t)["label"] == "monthly"
    assert "stale" in prices.freshness("monthly", date(2026, 6, 1), t)["label"]
    assert prices.freshness("live", t, t)["label"] == "live" and prices.freshness("delayed_15m", t, t)["label"] == "delayed 15 min"
    try:
        prices.freshness("realtime", t, t); raise AssertionError
    except ValueError:
        pass


def test_no_registered_provider_claims_live_or_delayed():
    assert all(p["cadence"] in ("daily", "monthly") for p in make({}).providers())


def test_cache_prevents_second_fetch_within_ttl():
    svc = make({"fredgraph": FRED_WHEAT})
    run(svc.series("wheat")); run(svc.series("wheat"))
    assert len(svc.http.calls) == 1


def test_source_failure_without_cache_is_no_data():
    s = run(make({"fredgraph": RuntimeError("server error 503")}).series("wheat"))
    assert s["no_data"] and "unreachable" in s["reason"]


def test_failure_after_success_serves_stale_last_good_data_and_says_so():
    t = [1000.0]
    state = {"fail": False}
    def src():
        if state["fail"]:
            raise RuntimeError("timeout")
        return FRED_WHEAT
    svc = make({"fredgraph": src}, clock=lambda: t[0])
    ok = run(svc.series("wheat"))
    assert not ok.get("stale_fallback")
    state["fail"] = True
    t[0] += 7 * 3600  # monthly TTL (6 h) expired
    s = run(svc.series("wheat"))
    assert not s["no_data"] and s["stale_fallback"] and s["freshness"]["stale"] and "stale" in s["freshness"]["label"] and "last good" in s["stale_reason"]
    assert s["latest"]["value"] == 231.0


def test_fx_conversion_and_missing_rate_is_not_guessed():
    svc = make({"fredgraph": FRED_WHEAT, "frankfurter": FX})
    inr = run(svc.priced("wheat", "WORLD", "INR", "quintal"))
    assert inr["display"]["currency"] == "INR" and abs(inr["display"]["points"][-1]["value"] - 231.0 / 1000 * 100 * 84.0) < 1e-3
    assert inr["display"]["fx"]["date"] == "2026-11-13" and "ECB" in inr["display"]["fx"]["source"]
    ngn = run(svc.priced("wheat", "WORLD", "NGN", None))
    assert ngn["display"]["currency"] == "USD" and not ngn["display"]["converted"] and "No exchange rate" in ngn["display"]["note"]


def test_fx_unreachable_keeps_original_currency():
    svc = make({"fredgraph": FRED_WHEAT, "frankfurter": RuntimeError("down")})
    d = run(svc.priced("wheat", "WORLD", "EUR", None))["display"]
    assert d["currency"] == "USD" and "No exchange rate" in d["note"]


def test_bad_unit_rejected():
    try:
        run(make({"fredgraph": FRED_WHEAT}).priced("wheat", "WORLD", None, "bushel")); raise AssertionError
    except ValueError:
        pass


def test_board_has_entry_for_every_crop_and_marks_no_data():
    b = run(make({"fredgraph": FRED_WHEAT}).board("WORLD"))
    assert len(b["crops"]) == 27 and b["crops"]["wheat"]["no_data"] is False and b["crops"]["lentil"]["no_data"] is True
    assert any(p["id"] == "agmarknet" and not p["configured"] for p in b["providers"])


def test_gross_value_requires_user_yield_and_real_price_and_is_labelled_not_profit():
    s = run(make({"fredgraph": FRED_WHEAT}).series("wheat"))
    conv = lambda v, a, b: v if a == b else None
    g = prices.gross_value(s, 2.0, 3.0, "USD", conv)
    assert g["available"] and g["gross_per_ha"] == 693.0 and g["gross_total"] == 1386.0 and "NOT profit" in g["label"] and len(g["assumptions"]) == 3
    assert not prices.gross_value(s, 0, 3.0, "USD", conv)["available"]
    assert not prices.gross_value(s, 1, 0, "USD", conv)["available"]
    nd = prices.gross_value(prices.no_data("lentil", "WORLD", "none"), 1, 1, "USD", conv)
    assert nd["available"] is False and "gross_total" not in nd
    assert prices.gross_value(s, 1, 1, "INR", conv)["currency"] == "USD"  # no FX -> original currency, with a note


def test_provider_status_and_probe_report_down_and_not_configured():
    svc = make({"fredgraph": RuntimeError("503"), "frankfurter": FX})
    p = run(svc.probe())
    assert p["imf_fred"]["state"] == "down" and p["frankfurter"]["state"] == "up" and p["agmarknet"]["state"] == "not_configured"


def test_sse_sends_snapshot_then_ticks_and_only_resends_on_change():
    state = {"csv": FRED_WHEAT}
    svc = make({"fredgraph": lambda: state["csv"]})
    async def collect():
        out = []
        async def nosleep(_):
            if len(out) == 2:
                svc.cache.items.clear(); state["csv"] = FRED_WHEAT + "2026-10-01,240.0\n"
        async for frame in prices.stream(svc, "WORLD", 1, max_events=3, sleep=nosleep):
            out.append(frame)
        return out
    frames = run(collect())
    assert frames[0].startswith("event: prices") and frames[1].startswith("event: tick") and frames[2].startswith("event: prices")
    payload = json.loads(frames[2].split("data: ", 1)[1])
    assert payload["crops"]["wheat"]["latest"]["value"] == 240.0 and frames[0].endswith("\n\n")
