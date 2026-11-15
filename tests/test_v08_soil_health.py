# AI-assisted: written with an AI coding assistant (see README, "AI tools used").
"""v0.8 soil-health engine (pure functions) and its service wrapper (fake providers; no network)."""
import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))  # share the Fake provider with test_providers_services

from app import services
from app.engine import soil_health as sh
from app.engine.crops import crop_by_id
from app.providers import parsers
from app.providers.base import result, unavailable

from test_providers_services import Fake, layer


def run(c): return asyncio.run(c)


GOOD = {"ph": 6.5, "organic_carbon_g_kg": 25.0, "clay_pct": 25.0, "sand_pct": 40.0, "silt_pct": 35.0, "texture": "Loam"}


def test_acidic_low_carbon_flags_with_level_detail_and_action():
    lims = sh.limitations({"ph": 4.8, "organic_carbon_g_kg": 4.0})
    by = {x["factor"]: x for x in lims}
    assert by["Acidity"]["level"] == "high" and by["Organic carbon"]["level"] == "high"
    assert all(x["detail"] and x["action"] for x in lims)


def test_ph_boundaries():
    assert sh.limitations({"ph": 5.5}) == []          # 5.5 is not acidic
    assert sh.limitations({"ph": 5.49})[0]["level"] == "moderate"
    assert sh.limitations({"ph": 8.0}) == []          # 8.0 is not alkaline
    assert sh.limitations({"ph": 8.01})[0]["factor"] == "Alkalinity"


def test_texture_flags():
    assert sh.limitations({"sand_pct": 80.0})[0]["factor"] == "Texture"
    assert "sandy" in sh.limitations({"sand_pct": 80.0})[0]["detail"].lower()
    assert "clay" in sh.limitations({"clay_pct": 55.0})[0]["detail"].lower()
    assert sh.limitations(GOOD) == []


def test_missing_values_are_never_invented():
    out = sh.assess({})
    assert out["available"] is False and out["limitations"] == [] and out["water_holding"] is None
    assert out["summary"] == ["Not enough soil data to summarise."]
    assert set(out["not_available"]) == {"nitrogen", "phosphorus", "potassium", "salinity"}
    assert "not estimated" in out["disclaimer"]


def test_assess_good_soil_has_water_holding_and_no_limits():
    out = sh.assess(GOOD, 2.0, crop_by_id("maize"))
    assert out["available"] and out["limitations"] == [] and out["water_holding"]["awc_mm_per_m"] > 0
    assert "pedotransfer" in out["water_holding_note"]
    assert out["crop_ph"]["status"] in {"good", "marginal", "poor"}


def test_crop_ph_compat_levels():
    crop = {"ph": [6.0, 7.0]}
    assert sh.crop_ph_compat(crop, {"ph": 6.5})["status"] == "good"
    assert sh.crop_ph_compat(crop, {"ph": 5.5})["status"] == "marginal"   # 0.5 outside
    assert sh.crop_ph_compat(crop, {"ph": 4.5})["status"] == "poor"       # 1.5 outside
    assert sh.crop_ph_compat(crop, {"ph": 8.2})["status"] == "poor"
    assert sh.crop_ph_compat(crop, {})["status"] == "unknown"
    assert sh.crop_ph_compat({}, {"ph": 6})["status"] == "unknown"


@pytest.mark.parametrize("area,cores", [(None, 5), (0.5, 5), (4, 5), (4.1, 6), (8, 7), (20, 10), (40, 15), (500, 15)])
def test_sampling_plan_cores(area, cores):
    plan = sh.sampling_plan(area)
    assert plan["recommended_cores"] == cores and "Zig-zag" in plan["pattern"]


def test_service_uses_provider_soil_and_labels_provenance():
    out = run(services.soil_health_report(Fake(), 12.97, 77.59, "maize", 9.0))
    assert out["available"] and out["soil"]["ph"] is not None
    assert out["provenance"][0]["name"] == "soil" and out["provenance"][0]["ok"] is True
    assert out["sampling"]["recommended_cores"] == 7


def test_service_reports_unavailable_soil_without_estimating():
    fake = Fake(soil=unavailable("ISRIC SoilGrids 2.0", "no soil values at this location"))
    out = run(services.soil_health_report(fake, 0.0, -30.0, None, None))
    assert out["available"] is False and "no soil" in out["error"].lower()
    assert "summary" not in out and out["provenance"][0]["ok"] is False
    assert "nitrogen" in out["not_available"]
