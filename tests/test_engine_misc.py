# AI-assisted: written with an AI coding assistant (see README, "AI tools used").
import math
from datetime import date, timedelta

import pytest

from app.engine import finance, geo, irrigation, pest_risk, soil, units
from app.engine.crops import crop_by_id


# ---------- units ----------
def test_unit_conversions_round_trip_and_known_values():
    assert units.ha_to_acre(1) == pytest.approx(2.47105, abs=1e-4)
    assert units.acre_to_ha(units.ha_to_acre(7.3)) == pytest.approx(7.3)
    assert units.c_to_f(100) == pytest.approx(212) and units.f_to_c(-40) == pytest.approx(-40)
    assert units.mm_to_in(25.4) == pytest.approx(1) and units.kg_to_lb(1) == pytest.approx(2.20462, abs=1e-4)
    assert units.bushel_kg("maize") == pytest.approx(25.4012, abs=1e-3)  # 56 lb
    assert units.t_per_ha_to_bu_per_acre(10, "maize") == pytest.approx(10000 / 25.4012 / 2.47105, rel=1e-4)
    with pytest.raises(ValueError):
        units.bushel_kg("cowpea")
    assert units.convert_currency(100, 0.5) == 50
    with pytest.raises(ValueError):
        units.convert_currency(1, 0)


# ---------- finance: golden numbers computed by hand ----------
COSTS = {"seed": 100, "fertilizer": 200, "soil_prep": 50, "irrigation": 0, "labour": 150, "pesticide": 50, "machinery": 100, "transport": 25, "other": 25}  # total 700; variable 525


def test_finance_golden_numbers():
    r = finance.evaluate(4.0, 300.0, COSTS, area_ha=2)
    assert r["revenue_per_ha"] == 1200.0
    assert r["cost_total_per_ha"] == 700.0 and r["cost_variable_per_ha"] == 525.0
    assert r["gross_margin_per_ha"] == 675.0 and r["net_profit_per_ha"] == 500.0
    assert r["break_even_price_per_t"] == 175.0
    assert r["break_even_yield_t_ha"] == pytest.approx(700 / 300)
    assert r["roi"] == pytest.approx(500 / 700)
    assert r["payback_seasons"] == pytest.approx(1.4)
    assert r["net_profit_total"] == 1000.0 and r["partial"] == []


def test_finance_is_partial_not_guessed_when_inputs_missing():
    costs = {**COSTS, "machinery": None, "other": None}
    r = finance.evaluate(4.0, 300.0, costs)
    assert r["net_profit_per_ha"] is None and r["roi"] is None and r["break_even_price_per_t"] is None
    assert r["gross_margin_per_ha"] == 675.0  # variable categories are all present
    assert any("machinery" in p and "other" in p for p in r["partial"])
    r2 = finance.evaluate(None, 300.0, COSTS)
    assert r2["revenue_per_ha"] is None and r2["net_profit_per_ha"] is None and any("yield" in p for p in r2["partial"])


def test_scenarios_golden_numbers():
    s = finance.scenarios(4, 300, 700, {"yield": .2, "price": .25, "cost": .1})
    assert s["base"] == 500
    assert s["best"] == pytest.approx(4 * 1.2 * 300 * 1.25 - 700 * .9)  # 1800 - 630 = 1170
    assert s["worst"] == pytest.approx(4 * .8 * 300 * .75 - 700 * 1.1)  # 720 - 770 = -50
    assert s["ranges_label"].startswith("ASSUMPTION")


def test_percentile_interpolates():
    assert finance.percentile([1, 2, 3, 4, 5], .5) == 3 and finance.percentile([0, 10], .25) == 2.5


def test_monte_carlo_is_reproducible_and_ordered():
    a, b = finance.monte_carlo(4, 300, 700), finance.monte_carlo(4, 300, 700)
    assert a == b and a["runs"] == 2000 and a["seed"] == 42
    assert a["p10"] < a["p50"] < a["p90"]
    assert a["p10"] < 500 < a["p90"] and abs(a["p50"] - 500) < 60
    loss = finance.monte_carlo(2, 300, 900)  # base case loses money
    assert loss["prob_loss"] > .9 and "not a forecast" in loss["label"]


def test_margin_indices_need_two_distinct_margins_and_flag_neutral_fill():
    ids = ["a", "b", "c"]
    assert finance.margin_indices({"a": 100.0}, ids) == {} and finance.margin_indices({"a": 5.0, "b": 5.0}, ids) == {}
    out = finance.margin_indices({"a": 100.0, "b": 300.0}, ids)
    assert out["a"]["index"] == 0 and out["b"]["index"] == 100
    assert out["c"]["index"] == 50 and "neutral" in out["c"]["basis"]


def test_compare_orders_by_risk_adjusted_margin_none_last():
    rows = [{"crop": "x", "risk_adjusted_margin_per_ha": None}, {"crop": "y", "risk_adjusted_margin_per_ha": 10}, {"crop": "z", "risk_adjusted_margin_per_ha": 99}]
    assert [r["crop"] for r in finance.compare(rows)] == ["z", "y", "x"]


def test_csv_export_neutralises_formula_injection_but_keeps_negatives():
    out = finance.to_csv([{"crop": "=HYPERLINK(\"x\")", "net_profit_per_ha": -50.0, "provenance": "user-entered"}])
    assert "'=HYPERLINK" in out and '"-50"' in out


# ---------- irrigation ----------
def test_extraterrestrial_radiation_matches_fao56_worked_example():
    assert irrigation.extraterrestrial_radiation_mm(-20, 246) / 0.408 == pytest.approx(32.2, abs=0.1)  # FAO-56 Example 8, 3 September, 20 deg S


def test_hargreaves_increases_with_temperature_range_and_is_nonnegative():
    a = irrigation.hargreaves_et0(15, 25, 20, 180)
    assert a > irrigation.hargreaves_et0(15, 20, 20, 180) > 0
    assert irrigation.hargreaves_et0(10, 10, 20, 180) == 0


def test_kc_curve_is_piecewise_and_hits_the_stage_values():
    maize = crop_by_id("maize")
    assert irrigation.kc_at(maize, 0, 125)[0] == maize["kc"]["ini"]
    assert irrigation.kc_at(maize, 62, 125)[1] == "mid-season" and irrigation.kc_at(maize, 62, 125)[0] == maize["kc"]["mid"]
    assert irrigation.kc_at(maize, 125, 125)[0] == pytest.approx(maize["kc"]["end"], abs=1e-6)
    f = maize["stage_fraction"]; mid_dev = round(125 * (f["ini"] + f["dev"] / 2))
    assert maize["kc"]["ini"] < irrigation.kc_at(maize, mid_dev, 125)[0] < maize["kc"]["mid"]


def test_effective_rain_rule():
    assert irrigation.effective_rain(2) == 0 and irrigation.effective_rain(10) == pytest.approx(8)


def days(n, et0=5.0, rain=0.0, start=date(2026, 6, 1)):
    return [{"date": start + timedelta(d), "et0": et0, "rain": rain} for d in range(n)]


def test_schedule_irrigates_when_depletion_reaches_raw_and_refills_to_capacity():
    maize = crop_by_id("maize")
    sow = date(2026, 4, 1)  # 61 days after sowing on 1 June = 49 % of a 125-day season -> mid-season, Kc 1.2
    r = irrigation.schedule(maize, days(14), sow, 125, awc_mm_per_m=150, method="drip", root_depth_m=0.6, depletion_fraction=0.5)
    assert r["taw_mm"] == 90 and r["raw_mm"] == 45
    first = r["events"][0]
    assert first["date"] == "2026-06-08" and first["net_mm"] == pytest.approx(48, abs=0.5)  # 8 d x 6 mm ETc = 48 mm >= 45 mm RAW
    assert first["gross_mm"] == pytest.approx(first["net_mm"] / 0.9, abs=0.1)
    assert all(row["depletion_mm"] <= 90 for row in r["daily"]) and r["stress_days"] == 0


def test_rainfed_reports_stress_and_schedules_no_irrigation():
    r = irrigation.schedule(crop_by_id("maize"), days(14), date(2026, 5, 1), 125, 150, method="rainfed")
    assert r["events"] == [] and r["stress_days"] > 0 and r["efficiency"] is None


def test_rain_resets_depletion_and_weekly_cap_is_respected():
    wet = irrigation.schedule(crop_by_id("maize"), days(10, rain=15), date(2026, 5, 1), 125, 150, "sprinkler")
    assert wet["events"] == []  # 12 mm effective rain/day > 6 mm ETc/day
    capped = irrigation.schedule(crop_by_id("maize"), days(14), date(2026, 5, 1), 125, 150, "drip", max_mm_per_week=20)
    assert all(w["gross_mm"] <= 20.01 for w in capped["weekly"])


def test_schedule_rejects_unknown_method_and_states_assumptions():
    with pytest.raises(ValueError):
        irrigation.schedule(crop_by_id("maize"), days(3), date(2026, 5, 1), 125, 150, "flood")
    r = irrigation.schedule(crop_by_id("maize"), days(3), date(2026, 5, 1), 125, 150)
    assert "80 %" in r["assumptions"]["rain_rule"] and r["limitations"]


def test_season_water_need_integrates_kc():
    m = crop_by_id("maize")
    flat = irrigation.season_water_need(m, [4.0], 125)
    assert 0.3 * 4 * 125 < flat < 1.2 * 4 * 125
    with pytest.raises(ValueError):
        irrigation.season_water_need(m, [], 125)


# ---------- soil ----------
def test_texture_examples():
    assert soil.usda_texture(90, 5, 5) == "Sand" and soil.usda_texture(40, 40, 20) == "Loam" and soil.usda_texture(20, 20, 60) == "Clay"
    assert soil.usda_texture(10, 80, 10) == "Silt" and soil.usda_texture(65, 20, 15) == "Sandy loam"


def test_water_holding_is_plausible_and_ordered_by_texture():
    sand = soil.water_holding(90, 5, 8)["awc_mm_per_m"]
    loam = soil.water_holding(40, 20, 15)["awc_mm_per_m"]
    silty = soil.water_holding(15, 20, 15)["awc_mm_per_m"]
    assert 40 < sand < 110 and 100 < loam < 200 and silty > sand
    w = soil.water_holding(40, 20, 15)
    assert w["field_capacity"] > w["wilting_point"] > 0


def test_soil_limitations_never_invent_npk():
    items = soil.limitations({"ph": 5.0, "organic_carbon_g_kg": 5, "clay_pct": 50})
    assert {i["id"] for i in items} == {"acidic", "low_soc", "heavy"}
    assert "No global data" in soil.UNAVAILABLE_NOTE and "laboratory" in soil.BANNER


# ---------- pest risk ----------
def wet_day(d, tmin=12, tmean=18, rh=12):
    return {"date": d, "tmin": tmin, "tmean": tmean, "rh_hours_ge90": rh}


def test_smith_period_needs_two_consecutive_qualifying_days():
    one = pest_risk.evaluate([wet_day("d1"), wet_day("d2", rh=5), wet_day("d3")], "potato")
    smith = next(x for x in one if x["id"] == "smith_period")
    assert smith["level"] == "low"
    two = pest_risk.evaluate([wet_day("d1"), wet_day("d2")], "potato")
    assert next(x for x in two if x["id"] == "smith_period")["level"] == "elevated"
    cold = pest_risk.evaluate([wet_day("d1", tmin=9), wet_day("d2", tmin=9)], "potato")
    assert next(x for x in cold if x["id"] == "smith_period")["level"] == "low"


def test_rules_only_apply_to_listed_crops_and_state_source_and_no_diagnosis():
    res = pest_risk.evaluate([wet_day("d1")], "wheat")
    assert "smith_period" not in {r["id"] for r in res}
    for r in pest_risk.evaluate([wet_day(f"d{i}") for i in range(4)], "potato"):
        assert r["source"] and r["rule"] and "not a diagnosis" in r["advice"] and "local label" in r["advice"]
    assert {r["basis"] for r in pest_risk.evaluate([], "potato")} >= {"literature", "heuristic"}


def test_daily_aggregation_from_hourly_requires_nearly_complete_days():
    hours = [{"time": f"2026-06-01T{h:02d}:00", "t": 15 + h / 10, "rh": 95 if h < 12 else 60} for h in range(24)] + [{"time": "2026-06-02T00:00", "t": 10, "rh": 99}]
    out = pest_risk.daily_from_hourly(hours)
    assert len(out) == 1 and out[0]["rh_hours_ge90"] == 12 and out[0]["tmin"] == 15.0


# ---------- geometry ----------
SQUARE = [[0, 0], [0.001, 0], [0.001, 0.001], [0, 0.001], [0, 0]]


def test_area_inside_and_sampling():
    assert geo.ring_area_ha(SQUARE) == pytest.approx(1.24, abs=0.06)
    assert geo.inside((0.0005, 0.0005), SQUARE) and not geo.inside((0.002, 0.0005), SQUARE)
    centre, pts = geo.sample_points(SQUARE)
    assert 1 <= len(pts) <= 4 and all(geo.inside((p["lon"], p["lat"]), SQUARE) for p in pts)


def test_concave_shape_samples_stay_inside():
    ell = [[0, 0], [10, 0], [10, 1], [1, 1], [1, 10], [0, 10], [0, 0]]
    centre, pts = geo.sample_points(ell)
    assert geo.inside((centre["lon"], centre["lat"]), ell) and all(geo.inside((p["lon"], p["lat"]), ell) for p in pts)


def test_ring_validation_rejects_bad_geometry():
    with pytest.raises(geo.GeometryError):
        geo._ring({"type": "Point", "coordinates": [0, 0]})
    with pytest.raises(geo.GeometryError):
        geo._ring({"type": "Polygon", "coordinates": [[[0, 0], [1, 1]]]})
    with pytest.raises(geo.GeometryError):
        geo._ring({"type": "Polygon", "coordinates": [[["a", 0], [1, 1], [2, 2], [0, 0]]]})
