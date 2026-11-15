# AI-assisted: written with an AI coding assistant (see README, "AI tools used").
"""Soil helpers. Pure functions."""
from __future__ import annotations

from typing import Any


def usda_texture(sand: float, silt: float, clay: float) -> str:
    """USDA soil texture class from percentages (normalised to 100)."""
    total = (sand + silt + clay) or 1
    sand, silt, clay = sand / total * 100, silt / total * 100, clay / total * 100
    if silt + 1.5 * clay < 15:
        return "Sand"
    if silt + 1.5 * clay >= 15 and silt + 2 * clay < 30:
        return "Loamy sand"
    if (7 <= clay < 20 and sand > 52 and silt + 2 * clay >= 30) or (clay < 7 and silt < 50 and silt + 2 * clay >= 30):
        return "Sandy loam"
    if 7 <= clay < 27 and 28 <= silt < 50 and sand <= 52:
        return "Loam"
    if (silt >= 50 and 12 <= clay < 27) or (50 <= silt < 80 and clay < 12):
        return "Silt loam"
    if silt >= 80 and clay < 12:
        return "Silt"
    if 20 <= clay < 35 and silt < 28 and sand > 45:
        return "Sandy clay loam"
    if 27 <= clay < 40 and 20 < sand <= 45:
        return "Clay loam"
    if 27 <= clay < 40 and sand <= 20:
        return "Silty clay loam"
    if clay >= 35 and sand > 45:
        return "Sandy clay"
    if clay >= 40 and silt >= 40:
        return "Silty clay"
    if clay >= 40:
        return "Clay"
    return "Loam"


def organic_matter_pct(soc_g_kg: float) -> float:
    """Soil organic matter (%) from SOC (g/kg) using the conventional van Bemmelen factor 1.724."""
    return soc_g_kg / 10 * 1.724


def water_holding(sand_pct: float, clay_pct: float, soc_g_kg: float) -> dict[str, float]:
    """Plant-available water capacity from sand, clay and organic matter.

    Method: Saxton & Rawls (2006), Soil Sci. Soc. Am. J. 70:1569-1578, eqs. for theta_1500 (wilting point)
    and theta_33 (field capacity). Returns volumetric fractions and mm of water per metre of soil.
    A pedotransfer estimate from modelled inputs: indicative only; real values need local measurement."""
    s, c, om = sand_pct / 100, clay_pct / 100, organic_matter_pct(soc_g_kg)
    t1500t = -0.024 * s + 0.487 * c + 0.006 * om + 0.005 * s * om - 0.013 * c * om + 0.068 * s * c + 0.031
    wp = t1500t + (0.14 * t1500t - 0.02)
    t33t = -0.251 * s + 0.195 * c + 0.011 * om + 0.006 * s * om - 0.027 * c * om + 0.452 * s * c + 0.299
    fc = t33t + (1.283 * t33t ** 2 - 0.374 * t33t - 0.015)
    awc = max(0.0, fc - wp)
    return {"wilting_point": round(wp, 3), "field_capacity": round(fc, 3), "awc_fraction": round(awc, 3), "awc_mm_per_m": round(awc * 1000, 1)}


def limitations(soil: dict[str, Any]) -> list[dict[str, str]]:
    """Soil limitation flags from modelled values. Nothing is reported for N/P/K or salinity (no global data)."""
    out: list[dict[str, str]] = []
    ph, soc, clay, sand = soil.get("ph"), soil.get("organic_carbon_g_kg"), soil.get("clay_pct"), soil.get("sand_pct")
    if ph is not None and ph < 5.5:
        out.append({"id": "acidic", "level": "high", "text": f"Acidic (pH {ph:.1f}). Aluminium toxicity and phosphorus lock-up are possible; confirm with a lab test before liming."})
    if ph is not None and ph > 8.0:
        out.append({"id": "alkaline", "level": "medium", "text": f"Alkaline (pH {ph:.1f}). Iron, zinc and phosphorus availability may be limited."})
    if soc is not None and soc < 10:
        out.append({"id": "low_soc", "level": "high", "text": f"Low organic carbon ({soc:.1f} g/kg in the modelled topsoil)."})
    if clay is not None and clay > 40:
        out.append({"id": "heavy", "level": "medium", "text": "Heavy clay: slow drainage and compaction risk when worked wet."})
    if (clay is not None and clay < 12) or (sand is not None and sand > 70):
        out.append({"id": "light", "level": "medium", "text": "Light, sandy soil: drains fast and holds few nutrients."})
    return out


UNAVAILABLE_NOTE = "No global data for nitrogen, phosphorus, potassium or salinity. Get a laboratory soil test."
BANNER = "Modelled soil data cannot replace a laboratory test."
