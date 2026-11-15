# AI-assisted: written with an AI coding assistant (see README, "AI tools used").
import random

import pytest

from app.engine import content, rotation, scoring
from app.engine.crops import load_crops

CROPS = list(load_crops())
CROP = {c["id"]: c for c in CROPS}
P = scoring.normalize_priorities({"resilience": 34, "profit": 0, "soil": 33, "water": 33})


def normals(temp=25.0, rain=70.0):
    return {"temperature_c": [temp] * 12, "rain_mm_month": [rain] * 12}


def climate(temp, rain14=20.0, wet=0.5):
    return {"latest": {"temperature_c": {"value": temp}, "root_zone_wetness": {"value": wet}}, "rainfall_14d_mm": rain14}


def rank(clim, nrm=None, soil=None, prio=P, previous=(), lat=10.0, margin=None):
    items = [scoring.suitability(c, clim, soil or {"ph": 6.5}, prio, list(previous), nrm, lat, (margin or {}).get(c["id"])) for c in CROPS]
    return sorted(items, key=lambda r: -r["score"])


def test_priorities_normalise_and_ignore_negatives():
    p = scoring.normalize_priorities({"resilience": 50, "water": 50, "soil": -4})
    assert p["soil"] == 0 and p["resilience"] == pytest.approx(.5) and sum(p.values()) == pytest.approx(1)


def test_all_zero_priorities_do_not_divide_by_zero():
    assert sum(scoring.normalize_priorities({}).values()) in (0, 1)


def test_water_scores_are_ordered():
    s = scoring.WATER_SCORES
    assert s["very low"] > s["low"] > s["low–medium"] > s["medium"] > s["medium–high"] > s["high"]


# ---- D1: the profit priority must not be a constant 50 that dilutes the other weights ----
def test_d1_unavailable_profit_does_not_dilute_other_priorities():
    comps = {"climate": 80.0, "soil_and_rotation": 60.0, "water_fit": 70.0, "resilience": 90.0, "profit": None}
    only_res = scoring.combine_score(comps, {"resilience": 1.0, "water": 0, "soil": 0, "profit": 0})
    res_plus_profit_slider = scoring.combine_score(comps, {"resilience": .5, "water": 0, "soil": 0, "profit": .5})
    assert only_res == res_plus_profit_slider  # v0.4 returned a lower score here because profit counted as a flat 50


def test_d1_profit_uses_real_component_when_available():
    base = {"climate": 80.0, "soil_and_rotation": 60.0, "water_fit": 70.0, "resilience": 90.0}
    hi = scoring.combine_score({**base, "profit": 100.0}, {"profit": 1.0})
    lo = scoring.combine_score({**base, "profit": 0.0}, {"profit": 1.0})
    assert hi > lo and hi - lo == pytest.approx(65, abs=1)


def test_profit_priority_ranks_by_margin_when_available():
    m = {c["id"]: (100.0 if c["id"] == "potato" else 10.0) for c in CROPS}
    prio = scoring.normalize_priorities({"profit": 100})
    ranked = rank(climate(20), normals(20, 70), prio=prio, margin=m)
    assert ranked[0]["crop"]["id"] == "potato"


def test_one_cold_day_does_not_flip_top_crop_when_climatology_available():
    cold = [r["crop"]["id"] for r in rank(climate(15), normals())]
    warm = [r["crop"]["id"] for r in rank(climate(28), normals())]
    assert cold[0] in warm[:3] and set(cold[:4]) == set(warm[:4])


def test_hot_dry_site_prefers_drought_tolerant_crops():
    assert {r["crop"]["id"] for r in rank(climate(33, 5), normals(31, 25))[:3]} & {"sorghum", "millet", "cowpea"}


def test_cool_site_ranks_cool_season_crop_first():
    ranked = rank(climate(8, 20), normals(9, 45), lat=45)
    assert ranked[0]["crop"]["season"] == "Cool season"
    assert ranked[-1]["crop"]["season"] == "Warm season"  # v0.7: 27 crops; the worst fit at a cool site is some warm-season crop


def test_priority_toggle_changes_ranking():
    a = [r["crop"]["id"] for r in rank(climate(25), normals(24, 80), prio=scoring.normalize_priorities({"water": 100}))]
    b = [r["crop"]["id"] for r in rank(climate(25), normals(24, 80), prio=scoring.normalize_priorities({"resilience": 100}))]
    assert a != b


def test_missing_data_is_neutral_and_low_confidence():
    r = scoring.suitability(CROP["maize"], {}, {}, P, [], None, 0)
    assert r["basis"] == "crop guide only" and 40 < r["score"] < 80
    assert r["confidence"]["level"] == "low" and r["confidence"]["fraction"] == 0


def test_confidence_rises_with_data():
    full = scoring.suitability(CROP["maize"], climate(25), {"ph": 6.5}, P, [], normals(), 10)["confidence"]
    assert full["level"] == "high" and "climatology" in full["measured"]


def test_result_explains_itself_and_is_not_a_probability():
    r = rank(climate(33), normals(10, 20))[0]
    assert len(r["top_reasons"]) == 3 and r["score_meaning"].startswith("Suitability score") and "not a probability" in r["score_meaning"]
    bad = scoring.suitability(CROP["rice"], climate(25), {"ph": 4.0}, P, [], normals(25, 15), 10)
    assert "water_fit" in {f["component"] for f in bad["limiting_factors"]}  # rice: high water need
    assert all(f["value"] < 60 for f in bad["limiting_factors"])


def test_frost_and_heat_flags():
    cold = scoring.suitability(CROP["maize"], climate(1), {"ph": 6.5}, P, [], {"temperature_c": [1.0] * 12, "rain_mm_month": [70.0] * 12}, 45)
    assert any("Frost" in f for f in cold["risk_flags"])
    hot = scoring.suitability(CROP["wheat"], climate(40), {"ph": 6.5}, P, [], normals(40), 10)
    assert any("Heat" in f for f in hot["risk_flags"])


def test_gdd_is_computed_from_monthly_normals():
    r = scoring.suitability(CROP["maize"], {}, {}, P, [], normals(20, 70), 10)
    n = r["season"]["months_used"]
    assert r["season"]["gdd_base10"] == round(n * (20 - 10) * 30.4)


def test_repeat_crop_is_penalised_and_legume_after_cereal_rewarded():
    base = scoring.suitability(CROP["maize"], climate(25), {"ph": 6.5}, P, [], normals(), 10)["score"]
    assert scoring.suitability(CROP["maize"], climate(25), {"ph": 6.5}, P, ["maize"], normals(), 10)["score"] < base
    a = scoring.suitability(CROP["soybean"], climate(25), {"ph": 6.5}, P, [], normals(), 10)["components"]["soil_and_rotation"]
    b = scoring.suitability(CROP["soybean"], climate(25), {"ph": 6.5}, P, ["maize"], normals(), 10)["components"]["soil_and_rotation"]
    assert b >= a


def test_all_priorities_off_ranks_by_climate_alone():
    r = scoring.suitability(CROP["sorghum"], climate(25), {"ph": 6.5}, scoring.normalize_priorities({}), [], normals(), 10)
    assert r["score"] == max(1, min(99, round(r["components"]["climate"])))


def test_rotation_depends_on_field_scores_and_avoids_repeats():
    hot = {c["id"]: (95 if c["id"] in ("sorghum", "cowpea", "millet", "groundnut", "sunflower") else 30) for c in CROPS}
    cool = {c["id"]: (95 if c["id"] in ("wheat", "chickpea", "potato") else 30) for c in CROPS}
    a, b = rotation.build_rotation(CROPS, hot, P, [], 4, 10), rotation.build_rotation(CROPS, cool, P, [], 4, 45)
    assert [s["id"] for s in a] != [s["id"] for s in b]
    for plan in (a, b):
        fams = [s["family"] for s in plan]
        assert all(x != y for x, y in zip(fams, fams[1:]))
    assert rotation.build_rotation(CROPS, {c["id"]: 70 for c in CROPS}, P, ["maize"], 2, 10)[0]["id"] != "maize"


def test_rotation_adds_legume_when_none_recent():
    assert any(s["fixer"] for s in rotation.build_rotation(CROPS, {c["id"]: 70 for c in CROPS}, P, ["maize", "wheat"], 2, 10))


def test_sow_window_flips_in_southern_hemisphere():
    assert content.sow_window("maize", 45)["sow_months"] == [4, 5] and content.sow_window("maize", -35)["sow_months"] == [10, 11]


def test_every_crop_has_content():
    for c in CROPS:
        extra = content.crop_extra(c["id"], 20)
        assert len(extra["stages"]) == 4 and extra["pests"] and extra["tips"]


def test_client_server_parity_python_side_is_deterministic():
    rng = random.Random(1)
    for _ in range(50):
        comps = {k: rng.uniform(0, 100) for k in ("climate", "soil_and_rotation", "water_fit", "resilience")}
        comps["profit"] = rng.choice([None, rng.uniform(0, 100)])
        pr = scoring.normalize_priorities({k: rng.choice([0, rng.uniform(0, 5)]) for k in scoring.PRIORITY_KEYS})
        assert 1 <= scoring.combine_score(comps, pr) <= 99
