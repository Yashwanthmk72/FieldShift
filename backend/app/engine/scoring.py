# AI-assisted: written with an AI coding assistant (see README, "AI tools used").
"""Transparent crop-suitability scoring. Pure functions, no I/O.

A suitability score is a *ranking aid*, NOT a probability of success or yield.
frontend/scoring.js repeats combine_score(); tests/test_parity.py checks they agree.
"""
from __future__ import annotations

import math
from typing import Any

from . import content

CLIMATE_WEIGHT = 0.35
PRIORITY_KEYS = ("resilience", "profit", "soil", "water")
WATER_SCORES = {"very low": 92, "low": 88, "low–medium": 76, "medium": 65, "medium–high": 52, "high": 42}
GDD_BASE_C = 10.0  # generic base temperature (heuristic); crop-specific bases are not yet sourced
SUITABILITY_NOTE = "Suitability score (0-100) ranks crops for planning. It is not a probability of success and not a yield forecast."


def round_half_up(x: float) -> int:
    """Same rounding as JS Math.round for positive numbers (Python round() is banker's rounding)."""
    return int(math.floor(x + 0.5))


def normalize_priorities(p: dict[str, float]) -> dict[str, float]:
    allowed = {k: max(0.0, float(p.get(k, 0) or 0)) for k in PRIORITY_KEYS}
    total = sum(allowed.values()) or 1
    return {k: v / total for k, v in allowed.items()}


def combine_score(components: dict[str, Any], priorities: dict[str, float]) -> int:
    """Fixed climate share + priority-weighted remainder.

    A priority whose component is unavailable (components[k] is None, e.g. 'profit' before any
    price/cost data exists) is excluded and the remaining weights are renormalised, so a
    disabled criterion can never dilute the others (audit defect D1).
    With every usable priority at zero the score is the climate fit alone."""
    weights = {"resilience": ("resilience", priorities.get("resilience", 0)), "water": ("water_fit", priorities.get("water", 0)),
               "soil": ("soil_and_rotation", priorities.get("soil", 0)), "profit": ("profit", priorities.get("profit", 0))}
    num = den = 0.0
    for comp_key, w in weights.values():
        v = components.get(comp_key)
        if v is None or w <= 0:
            continue
        num += w * v
        den += w
    if den <= 0:
        return max(1, min(99, round_half_up(components["climate"])))
    rest = num / den
    return max(1, min(99, round_half_up(CLIMATE_WEIGHT * components["climate"] + (1 - CLIMATE_WEIGHT) * rest)))


def season_fit(crop: dict[str, Any], normals: dict[str, Any], months: list[int]) -> dict[str, Any]:
    """Best sowing month using monthly climatology; also GDD, frost and heat flags for that window."""
    n = max(1, round(content.maturity_days(crop["id"]) / 30))
    lo, hi = crop["temp"]
    rlo, rhi = crop["rain"]
    best: dict[str, Any] | None = None
    for m in months:
        idx = [(m - 1 + i) % 12 for i in range(n)]
        temps = [normals["temperature_c"][i] for i in idx]
        t = sum(temps) / n
        r = sum(normals["rain_mm_month"][i] for i in idx)
        tscore = max(0.0, 100 - max(lo - t, 0, t - hi) * 6)
        rscore = max(0.0, 100 - max(rlo - r, 0, r - rhi) * .12)
        sc = .65 * tscore + .35 * rscore
        if best is None or sc > best["score"]:
            gdd = sum(max(0.0, tt - GDD_BASE_C) * 30.4 for tt in temps)
            best = {"score": sc, "sow_month": m, "temp_c": t, "rain_mm": r, "gdd_base10": round(gdd),
                    "frost_risk": any(tt < 2 for tt in temps), "heat_risk": any(tt > hi + 3 for tt in temps), "months_used": n}
    return best or {"score": 65.0, "sow_month": months[0], "temp_c": 0.0, "rain_mm": 0.0, "gdd_base10": 0, "frost_risk": False, "heat_risk": False, "months_used": n}


def confidence(inputs: dict[str, bool]) -> dict[str, Any]:
    """Confidence from data completeness: fraction of inputs that were measured/modelled rather than defaulted."""
    have = [k for k, v in inputs.items() if v]
    frac = len(have) / len(inputs) if inputs else 0.0
    level = "high" if frac >= .75 else "medium" if frac >= .5 else "low"
    return {"level": level, "fraction": round(frac, 2), "measured": have, "defaulted": [k for k, v in inputs.items() if not v],
            "meaning": "Share of scoring inputs that came from data rather than a neutral default. It says nothing about the chance of a good harvest."}


COMPONENT_LABELS = {"climate": "Climate fit", "soil_and_rotation": "Soil & rotation", "water_fit": "Water use", "resilience": "Resilience", "profit": "Profit"}


def suitability(crop: dict[str, Any], climate: dict[str, Any], soil: dict[str, Any], priorities: dict[str, float], previous: list[str],
                normals: dict[str, Any] | None = None, lat: float = 0.0, margin_index: float | None = None) -> dict[str, Any]:
    latest = climate.get("latest", {}) or {}
    temp = (latest.get("temperature_c") or {}).get("value")
    rain = climate.get("rainfall_14d_mm")
    evidence: list[str] = []
    flags: list[str] = []
    recent_score: float | None = None
    if temp is not None:
        lo, hi = crop["temp"]
        recent_score = max(0.0, 100 - max(lo - temp, 0, temp - hi) * 6)
        evidence.append(f"Latest daily temperature {temp:.1f}°C (a single day); crop guide range {lo}–{hi}°C")
    window = content.sow_window(crop["id"], lat)
    best_month: int | None = None
    fit: dict[str, Any] | None = None
    if normals:
        fit = season_fit(crop, normals, window["sow_months"])
        climate_score = fit["score"] if recent_score is None else .85 * fit["score"] + .15 * recent_score
        best_month = fit["sow_month"]
        evidence.append(f"Typical growing-season temperature {fit['temp_c']:.1f}°C and rainfall {fit['rain_mm']:.0f} mm if sown in {content.MONTH_NAMES[fit['sow_month'] - 1]} (NASA POWER climatology)")
        basis = "season climatology"
        if fit["frost_risk"]:
            flags.append("Frost risk: a month in the growing window averages below 2 °C")
        if fit["heat_risk"]:
            flags.append("Heat risk: a month in the growing window averages well above the crop's range")
    elif recent_score is not None:
        climate_score = recent_score
        basis = "recent weather only"
        if rain is not None:
            rain_score = max(0.0, 100 - max(crop["rain"][0] - rain * 26, 0, rain * 26 - crop["rain"][1]) * .12)
            climate_score = .7 * climate_score + .3 * rain_score
            evidence.append(f"NASA POWER 14-day rainfall total {rain:.1f} mm (scaled to a season; rough)")
    else:
        climate_score, basis = 65.0, "crop guide only"
    soil_score = 68.0
    ph = soil.get("ph") or soil.get("phh2o")
    if ph is not None:
        lo, hi = crop["ph"]
        soil_score = max(0.0, 100 - max(lo - float(ph), 0, float(ph) - hi) * 15)
        evidence.append(f"Soil pH {float(ph):.1f}; crop guide range {lo}–{hi}")
    water_score = float(WATER_SCORES.get(crop["water"].lower(), 65))
    wet_obj = latest.get("root_zone_wetness") or {}
    if wet_obj.get("value") is not None:
        wet = wet_obj["value"]
        evidence.append(f"NASA POWER root-zone wetness index {wet:.2f} (unitless relative estimate)")
        if wet < .25 and water_score < 70:
            water_score = max(30.0, water_score - 18)
    rotation_bonus = 12 if crop["fixer"] and any(c in previous for c in ("maize", "wheat", "rice", "sorghum", "millet")) else 0
    if previous and crop["id"] == previous[-1]:
        rotation_bonus -= 22
        evidence.append("Recent repeat crop reduces rotation score")
    soil_rotation_score = max(0.0, min(100.0, soil_score + rotation_bonus))
    components: dict[str, Any] = {"climate": climate_score, "soil_and_rotation": soil_rotation_score, "water_fit": water_score,
                                  "resilience": float(crop["resilience"]), "profit": None if margin_index is None else float(margin_index)}
    score = combine_score(components, priorities)
    label = lambda k: COMPONENT_LABELS[k]  # noqa: E731
    scored = {k: v for k, v in components.items() if v is not None}
    limiting = [{"factor": label(k), "component": k, "value": round(v)} for k, v in sorted(scored.items(), key=lambda kv: kv[1]) if v < 60 and k != "resilience"][:3]
    reasons = [f"{label(k)} {round(v)}/100" for k, v in sorted(scored.items(), key=lambda kv: -kv[1])[:3]]
    conf = confidence({"climatology": bool(normals), "recent_weather": temp is not None, "soil_ph": ph is not None, "soil_wetness": wet_obj.get("value") is not None})
    return {
        "crop": crop, "score": score, "model": "transparent crop-guide scoring (rule-based; no ML model is used)", "basis": basis, "ml_score": None,
        "components": {k: (None if v is None else round(v)) for k, v in components.items()},
        "best_sow_month": best_month, "sow_months": window["sow_months"], "harvest_months": window["harvest_months"],
        "season": ({k: fit[k] for k in ("gdd_base10", "frost_risk", "heat_risk", "months_used")} if fit else None),
        "top_reasons": reasons, "limiting_factors": limiting, "risk_flags": flags, "confidence": conf,
        "score_meaning": SUITABILITY_NOTE,
        "heuristic_params": [k for k, p in crop.get("provenance", {}).items() if p["status"] == "heuristic" and k in ("temp", "rain", "ph", "water", "resilience")],
        "evidence": evidence or ["Live climate observations unavailable; score uses crop guide ranges and the selected priorities."],
        "caveat": "Planning aid only. Confirm with local extension services, seed guidance and soil tests.",
    }
