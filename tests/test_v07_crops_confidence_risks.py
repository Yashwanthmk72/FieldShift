# AI-assisted: written with an AI coding assistant.
import json

from app.engine import confidence, content, rotation, scoring, risks, credits, climate_series
from app.engine.crops import DATA, crop_by_id, load_crops

NORMALS = {"temperature_c": [24, 26, 28, 30, 31, 30, 28, 27, 27, 26, 25, 24], "rain_mm_month": [5, 10, 20, 40, 80, 150, 200, 180, 120, 60, 15, 5], "solar_mj_m2_day": [18, 20, 22, 23, 22, 18, 16, 16, 17, 18, 17, 16]}


def test_crop_list_grew_to_27_and_all_have_content_and_urls():
    cs = load_crops()
    assert len(cs) == 27
    for c in cs:
        assert c["id"] in content.CONTENT and c["id"] in content.SOW and c["id"] in content.MATURITY_DAYS
        assert len(content.CONTENT[c["id"]]["stages"]) == 4
        for k, p in c["provenance"].items():
            if k not in ("resilience",):
                assert p.get("url", "").startswith("https://"), (c["id"], k)


def test_new_crops_are_all_heuristic_nothing_pretends_to_be_sourced():
    old = {"maize", "sorghum", "millet", "soybean", "cowpea", "rice", "groundnut", "chickpea", "wheat", "potato", "sunflower"}
    for c in load_crops():
        if c["id"] not in old:
            assert all(p["status"] == "heuristic" for p in c["provenance"].values()), c["id"]


def test_every_crop_has_a_valid_sowing_window_and_perennials_are_flagged():
    for c in load_crops():
        w = content.sow_window(c["id"], 12.9)
        assert w["sow_months"] and w["harvest_months"]
    assert crop_by_id("banana").get("perennial") and crop_by_id("sugarcane").get("perennial")


def test_rotation_never_picks_perennials():
    cs = list(load_crops())
    scores = {c["id"]: (99 if c.get("perennial") else 50) for c in cs}
    plan = rotation.build_rotation(cs, scores, {"resilience": .25, "soil": .25, "water": .25, "profit": .25}, [], 6, 12.9)
    assert plan and all(not crop_by_id(p["id"]).get("perennial") for p in plan)


def test_all_crops_score_without_error_and_fixers_flagged_legume():
    for c in load_crops():
        r = scoring.suitability(c, {}, {}, {"resilience": .34, "soil": .33, "water": .33, "profit": 0}, [], NORMALS, 12.9)
        assert 0 <= r["score"] <= 100
    assert crop_by_id("lentil")["fixer"] and crop_by_id("pigeonpea")["fixer"] and not crop_by_id("tomato")["fixer"]


def test_confidence_is_capped_at_medium_while_ranges_are_heuristic():
    base = scoring.confidence({"a": True, "b": True, "c": True, "d": True})
    assert base["level"] == "high"
    out = confidence.assess(base, crop_by_id("wheat"), 4)
    assert out["level"] == "medium" and out["illustrative"] is True and out["label"] == "Medium confidence" and out["reasons"]


def test_confidence_low_when_inputs_missing_and_can_reach_high_only_with_sourced_ranges():
    low = confidence.assess(scoring.confidence({"a": False, "b": False}), crop_by_id("maize"), None)
    assert low["level"] == "low" and low["defaulted"]
    c = json.loads(json.dumps(crop_by_id("maize")))
    for k in ("temp", "rain", "ph", "water", "resilience"):
        c["provenance"][k]["status"] = "sourced"
    hi = confidence.assess(scoring.confidence({"a": True, "b": True, "c": True, "d": True}), c, 4)
    assert hi["level"] == "high" and hi["illustrative"] is False


def test_few_soil_samples_cap_confidence():
    out = confidence.assess(scoring.confidence({"a": True, "b": True, "c": True, "d": True}), crop_by_id("wheat"), 1)
    assert out["level"] != "high" and any("fewer than 2" in r for r in out["reasons"])


def test_risks_cover_required_categories_and_never_estimate_price_volatility():
    r = risks.build(crop_by_id("tomato"), NORMALS, {"ph": 5.0}, 12.9, 3)
    keys = [i["key"] for i in r["items"]]
    assert {"climate", "pest", "price", "water", "soil"} <= set(keys)
    price = next(i for i in r["items"] if i["key"] == "price")
    assert price["level"] == "unknown" and "not low" in price["text"]
    assert any(i["key"] == "ph" for i in r["items"])
    assert len(r["could_be_wrong"]) >= 5 and any("heuristic" in w for w in r["could_be_wrong"])


def test_risks_without_climate_data_say_unknown_not_low():
    r = risks.build(crop_by_id("wheat"), None, {}, 40.0)
    assert next(i for i in r["items"] if i["key"] == "climate")["level"] == "unknown"


def test_legume_soil_risk_is_low_and_heavy_feeder_is_high():
    assert next(i for i in risks.build(crop_by_id("lentil"), NORMALS, {}, 12.9)["items"] if i["key"] == "soil")["level"] == "low"
    assert next(i for i in risks.build(crop_by_id("maize"), NORMALS, {}, 12.9)["items"] if i["key"] == "soil")["level"] == "high"


def test_credits_parse_sources_md_and_cover_required_providers():
    c = credits.load()
    names = " ".join(s["name"] for s in c["sections"])
    for need in ("NASA POWER", "SoilGrids", "IMF", "Agmarknet", "Frankfurter", "AI tools"):
        assert need in names, need
    assert all(s["group"] for s in c["sections"])
    assert any("not integrated" in s["group"].lower() for s in c["sections"])


def test_climate_series_anomaly_and_lag():
    from datetime import date
    dates = [f"2026-10-{d:02d}" for d in range(1, 31)]
    daily = {"dates": dates, "temperature_c": [30.0] * 30, "rain_mm": [0.0] * 30, "solar_mj_m2": [None] * 30}
    out = climate_series.build(daily, NORMALS, date(2026, 11, 3))
    assert out["lag_days"] == 4 and out["latest_data_date"] == "2026-10-30"
    assert out["temperature_c"]["anomaly"][0] is not None and out["rain_mm"]["normal"][0] > 0
    assert out["rain_cumulative"]["actual"][-1] == 0 and out["summary"]["rain_vs_normal_pct"] == -100
    assert out["solar_mj_m2"]["anomaly"][0] is None  # missing values stay missing, never filled in


def test_climate_series_without_normals_has_no_anomaly():
    out = climate_series.build({"dates": ["2026-10-01"], "temperature_c": [20.0], "rain_mm": [1.0], "solar_mj_m2": [15.0]}, None)
    assert out["temperature_c"]["anomaly"] is None and out["normals_available"] is False


def test_climate_range_clamp():
    from datetime import date, timedelta
    t = date(2026, 11, 14)
    s, e = climate_series.clamp_range(None, None, t)
    assert e == t - timedelta(days=2) and (e - s).days == 179
    for bad in ((date(2026, 5, 1), date(2026, 4, 1)), (date(2020, 1, 1), date(2026, 1, 1))):
        try:
            climate_series.clamp_range(*bad, today=t)
            raise AssertionError("should reject")
        except ValueError:
            pass
