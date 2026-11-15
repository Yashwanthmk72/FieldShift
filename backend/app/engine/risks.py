# AI-assisted: written with an AI coding assistant.
"""'Risks & downsides' for one crop at one location. Pure function; no I/O.

Levels are qualitative ('low' | 'moderate' | 'high' | 'unknown'). Where a level comes from the crop guide or editorial judgement rather
than a measurement, `basis` says so. Price volatility is never estimated here: it needs a real price series (see the Market page)."""
from __future__ import annotations

from typing import Any

from . import content, scoring

# Editorial, unverified groupings used only for plain-language flags (see `basis` on each risk).
HEAVY_FEEDERS = {"maize", "wheat", "rice", "potato", "sorghum", "sunflower", "cotton", "sugarcane", "banana", "tomato", "cassava", "mustard", "onion"}
HIGH_PEST_PRESSURE = {"tomato", "chili", "cotton", "potato", "banana", "sugarcane", "rice", "okra"}
EDITORIAL = "FieldShift editorial judgement from general guidance; not verified against a source."


def _risk(key: str, title: str, level: str, text: str, basis: str) -> dict[str, str]:
    return {"key": key, "title": title, "level": level, "text": text, "basis": basis}


def build(crop: dict[str, Any], normals: dict[str, Any] | None, soil: dict[str, Any] | None, lat: float, soil_samples: int | None = None) -> dict[str, Any]:
    soil = soil or {}
    cid = crop["id"]
    window = content.sow_window(cid, lat)
    items: list[dict[str, str]] = []

    # climate
    if normals:
        fit = scoring.season_fit(crop, normals, window["sow_months"])
        lo, hi = crop["temp"]
        rlo, rhi = crop["rain"]
        problems = []
        if fit["frost_risk"]:
            problems.append("a month in the growing window averages below 2 °C (frost risk)")
        if fit["heat_risk"]:
            problems.append("a month averages well above the crop's range (heat stress)")
        if fit["temp_c"] < lo - 3 or fit["temp_c"] > hi + 3:
            problems.append(f"average growing-season temperature {fit['temp_c']:.1f} °C is far outside the guide range {lo}–{hi} °C")
        if fit["rain_mm"] < rlo * 0.75:
            problems.append(f"expected rainfall {fit['rain_mm']:.0f} mm is well below the guide minimum {rlo} mm (irrigation likely needed)")
        elif fit["rain_mm"] > rhi * 1.25:
            problems.append(f"expected rainfall {fit['rain_mm']:.0f} mm is well above the guide maximum {rhi} mm (waterlogging and disease risk)")
        level = "high" if len(problems) >= 2 or fit["frost_risk"] else "moderate" if problems else "low"
        text = ("; ".join(problems).capitalize() + ".") if problems else f"Typical growing-season temperature {fit['temp_c']:.1f} °C and rainfall {fit['rain_mm']:.0f} mm sit within or near the crop guide ranges. Individual years can still be hotter, drier or wetter."
        items.append(_risk("climate", "Climate risk", level, text, "NASA POWER long-term monthly averages vs the crop guide ranges (heuristic). Averages hide bad years."))
    else:
        items.append(_risk("climate", "Climate risk", "unknown", "Climate normals were unavailable, so seasonal climate risk was not assessed.", "No NASA POWER climatology for this location right now."))

    # pest / disease
    pests = (content.CONTENT.get(cid) or {}).get("pests", [])
    level = "high" if cid in HIGH_PEST_PRESSURE else "moderate"
    items.append(_risk("pest", "Pest & disease risk", level, ("Commonly reported: " + ", ".join(pests) + ". ") + "Pressure depends on local weather, variety and neighbours' fields; scout weekly and ask your extension office.", EDITORIAL))

    # price volatility (never estimated here)
    items.append(_risk("price", "Price volatility", "unknown", "Not assessed here. Open the Market page for the real price history of this crop where a source exists; where none exists, volatility is unknown, not low.", "Requires a real price series; none is bundled."))

    # water demand
    w = crop["water"].lower()
    level = "high" if w in ("high", "medium–high") else "moderate" if w in ("medium", "low–medium") else "low"
    text = f"Crop guide water class: {crop['water']}."
    if normals:
        fit = scoring.season_fit(crop, normals, window["sow_months"])
        gap = crop["rain"][0] - fit["rain_mm"]
        text += f" Expected rainfall in the growing window is about {fit['rain_mm']:.0f} mm against a guide minimum of {crop['rain'][0]} mm" + (f", a possible shortfall of ~{gap:.0f} mm without irrigation." if gap > 0 else ".")
        if gap > 0 and level == "low":
            level = "moderate"
        if gap > crop["rain"][0] * 0.25:
            level = "high"
    items.append(_risk("water", "Water demand", level, text, "Crop guide water class and range (heuristic) vs NASA POWER climatology."))

    # soil depletion
    if crop["fixer"]:
        items.append(_risk("soil", "Soil depletion", "low", "A nitrogen-fixing legume: it usually adds nitrogen for the next crop but still removes phosphorus and other nutrients.", EDITORIAL))
    else:
        level = "high" if cid in HEAVY_FEEDERS else "moderate"
        nut = (content.CONTENT.get(cid) or {}).get("nutrients", "")
        items.append(_risk("soil", "Soil depletion", level, (nut + " " if nut else "") + "Follow with a legume or add organic matter to rebuild fertility.", EDITORIAL))
    ph = soil.get("ph")
    if ph is not None:
        lo, hi = crop["ph"]
        if float(ph) < lo - 0.3 or float(ph) > hi + 0.3:
            items.append(_risk("ph", "Soil pH mismatch", "moderate", f"Modelled topsoil pH {float(ph):.1f} is outside the guide range {lo}–{hi}. Confirm with a lab test before acting.", "SoilGrids (modelled, 250 m) vs crop guide range (heuristic)."))

    wrong = ["The crop guide ranges for this crop are heuristic unless marked 'sourced'; they may be off for your variety." if any((crop["provenance"].get(k) or {}).get("status") != "sourced" for k in ("temp", "rain", "ph")) else "Crop ranges are sourced, but still describe an average variety.",
             "Climate comes from a ~50 km grid cell and monthly averages; your microclimate and this year's weather can differ a lot.",
             "Soil values are modelled estimates at 250 m, not measurements of your field.",
             "The score ignores pests, diseases, seed availability, labour, irrigation access, markets and prices.",
             "Nothing here is a yield forecast or a guarantee. A local soil test and extension advice should come first."]
    if soil_samples is not None and soil_samples < 2:
        wrong.insert(2, "Soil was sampled at fewer than 2 points inside your boundary.")
    return {"crop_id": cid, "items": items, "could_be_wrong": wrong,
            "disclaimer": "Qualitative planning flags, not forecasts. Levels marked editorial are judgement calls and are not verified."}
