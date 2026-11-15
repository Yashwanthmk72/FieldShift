# AI-assisted: written with an AI coding assistant (see README, "AI tools used").
"""Soil-health summary from MODELLED topsoil values (SoilGrids). Pure functions, no I/O.

Never invents values: anything missing is reported as missing. N, P, K and salinity are not available globally and are never estimated.
Thresholds are general agronomic rules of thumb (status: heuristic), not site-specific recommendations."""
from __future__ import annotations

from typing import Any

from . import soil as soil_eng

UNAVAILABLE = ["nitrogen", "phosphorus", "potassium", "salinity"]
DISCLAIMER = ("Modelled global soil data (SoilGrids, ~250 m) cannot replace a laboratory soil test. "
              "Nitrogen, phosphorus, potassium and salinity are not provided by this dataset and are not estimated.")
BASIS = "heuristic: general rules of thumb, not verified for your site"
SAMPLE_PATTERN = ("Zig-zag/W pattern across uniform zones; 15-20 cm depth; mix the cores for each zone; "
                  "avoid headlands, fence lines, manure heaps and recent fertiliser bands.")


def _lim(factor: str, level: str, detail: str, action: str) -> dict[str, str]:
    return {"factor": factor, "level": level, "detail": detail, "action": action}


def limitations(soil: dict[str, Any]) -> list[dict[str, str]]:
    """Acidity, alkalinity, low organic carbon, and sand/clay texture, each with a level, detail and action."""
    out: list[dict[str, str]] = []
    ph, soc = soil.get("ph"), soil.get("organic_carbon_g_kg")
    clay, sand = soil.get("clay_pct"), soil.get("sand_pct")
    if ph is not None:
        if ph < 5.5:
            out.append(_lim("Acidity", "high" if ph < 5.0 else "moderate",
                            f"pH {ph:.1f} is acidic; aluminium toxicity and low phosphorus availability are possible.",
                            "Get a lab test, then consider liming to the crop's target pH and adding organic matter."))
        elif ph > 8.0:
            out.append(_lim("Alkalinity", "moderate",
                            f"pH {ph:.1f} is alkaline; iron, zinc and phosphorus can be less available.",
                            "Test for micronutrients; organic matter and acidifying fertilisers can help."))
    if soc is not None and soc < 10:
        out.append(_lim("Organic carbon", "high" if soc < 5 else "moderate",
                        f"{soc:.1f} g/kg organic carbon is low; weaker structure, water retention and nutrient supply.",
                        "Add compost or manure, keep residues, use cover crops or legumes in the rotation."))
    if (sand is not None and sand > 70) or (clay is not None and clay < 12):
        out.append(_lim("Texture", "moderate", "Light, sandy soil: drains fast and holds little water or nutrients.",
                        "Irrigate lighter and more often, split fertiliser doses, add organic matter."))
    if clay is not None and clay > 40:
        out.append(_lim("Texture", "moderate", "Heavy clay: waterlogging and compaction risk; slow to warm up.",
                        "Use raised beds or drainage, avoid working the soil when wet, add organic matter."))
    return out


def good_points(soil: dict[str, Any]) -> list[str]:
    out: list[str] = []
    ph, soc = soil.get("ph"), soil.get("organic_carbon_g_kg")
    if ph is not None and 5.5 <= ph <= 8.0:
        out.append(f"pH {ph:.1f} is in a workable range for many crops.")
    if soc is not None and soc >= 20:
        out.append(f"Organic carbon {soc:.1f} g/kg is relatively high.")
    return out


def crop_ph_compat(crop: dict[str, Any], soil: dict[str, Any]) -> dict[str, Any]:
    """Compare modelled pH with the crop's guide range. status: good | marginal | poor | unknown. The guide range itself is heuristic for most crops."""
    ph = soil.get("ph")
    rng = crop.get("ph")
    if ph is None or not rng:
        return {"status": "unknown", "detail": "No pH estimate or no crop pH range available."}
    lo, hi = float(rng[0]), float(rng[1])
    if lo <= ph <= hi:
        return {"status": "good", "detail": f"pH {ph:.1f} is within the {lo:g}-{hi:g} guide range."}
    gap = lo - ph if ph < lo else ph - hi
    return {"status": "poor" if gap > 1 else "marginal", "detail": f"pH {ph:.1f} is {gap:.1f} unit(s) outside the {lo:g}-{hi:g} guide range."}


def sampling_plan(area_ha: float | None) -> dict[str, Any]:
    """About 5 cores for fields up to 4 ha, +1 core per extra 4 ha, capped at 15. Unknown area -> 5."""
    if not area_ha or area_ha <= 4:
        n = 5
    else:
        n = min(15, 5 + int(area_ha // 4))
    return {"recommended_cores": n, "pattern": SAMPLE_PATTERN, "basis": "heuristic",
            "note": "Send the mixed sample to a local laboratory. Extension services can say which tests matter locally."}


def assess(soil: dict[str, Any], area_ha: float | None = None, crop: dict[str, Any] | None = None) -> dict[str, Any]:
    """Full soil-health summary. `soil` uses the keys of services.soil_summary_from_layers (ph, organic_carbon_g_kg, clay_pct, sand_pct, silt_pct, texture)."""
    soil = soil or {}
    lims = limitations(soil)
    good = good_points(soil)
    have = [k for k in ("ph", "organic_carbon_g_kg", "clay_pct", "sand_pct", "silt_pct") if soil.get(k) is not None]
    awc = None
    if None not in (soil.get("sand_pct"), soil.get("clay_pct"), soil.get("organic_carbon_g_kg")):
        awc = soil_eng.water_holding(soil["sand_pct"], soil["clay_pct"], soil["organic_carbon_g_kg"])
    actions: list[str] = []
    for lim in lims:
        if lim["action"] not in actions:
            actions.append(lim["action"])
    summary = good + [lim["detail"] for lim in lims]
    return {
        "available": bool(have),
        "summary": summary or (["No limitation flags from the modelled values."] if have else ["Not enough soil data to summarise."]),
        "limitations": lims,
        "actions": actions,
        "water_holding": awc,
        "water_holding_note": "Plant-available water from a pedotransfer estimate (Saxton & Rawls 2006) on modelled inputs; indicative only." if awc else None,
        "crop_ph": crop_ph_compat(crop, soil) if crop else None,
        "sampling": sampling_plan(area_ha),
        "data_available": have,
        "not_available": UNAVAILABLE,
        "basis": BASIS,
        "disclaimer": DISCLAIMER,
    }
