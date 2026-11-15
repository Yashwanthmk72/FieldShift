# AI-assisted: written with an AI coding assistant (see README, "AI tools used").
"""Land-management suggestions from climate + soil summaries. Pure functions."""
from __future__ import annotations

from typing import Any

from . import content

IMAGE_KEYS = {"alkaline": "compost", "rotation": "cover-crop", "texture-clay": "texture", "texture-sand": "mulch"}


def land_management(climate: dict[str, Any], soil: dict[str, Any], top: dict[str, Any] | None) -> list[dict[str, Any]]:
    latest = climate.get("latest", {}) or {}
    rain = climate.get("rainfall_14d_mm")
    wet = (latest.get("root_zone_wetness") or {}).get("value")
    temp = (latest.get("temperature_c") or {}).get("value")
    ph, soc, clay, sand = soil.get("ph"), soil.get("organic_carbon_g_kg"), soil.get("clay_pct"), soil.get("sand_pct")
    items: list[dict[str, Any]] = []

    def add(cat: str, level: str, title: str, detail: str, key: str) -> None:
        tpl = content.MANAGE.get(key, {})
        items.append({"id": f"{cat}-{key}", "category": cat, "priority": level, "title": title, "detail": detail, "image_key": IMAGE_KEYS.get(key, key),
                      "why": tpl.get("why", ""), "steps": tpl.get("steps", []), "when": tpl.get("when", ""), "benefit": tpl.get("benefit", "")})

    if rain is not None and rain > 45:
        add("Water", "high", "Check drainage after recent rain", f"{rain:.0f} mm fell in the last 14 days. Inspect low spots and avoid waterlogging-sensitive crops.", "drainage")
    elif wet is not None and wet < .25:
        add("Water", "high", "Verify moisture before irrigating", "The gridded root-zone estimate is relatively dry. Check soil in the field, then irrigate in short, targeted cycles.", "irrigation")
    else:
        add("Water", "medium", "Balance water with the weather", "Moisture looks moderate. Check a few spots by hand before irrigating; NASA data is regional, not a soil probe.", "irrigation")
    if temp is not None and temp > 33:
        add("Water", "medium", "Heat stress window", f"Recent temperature is {temp:.0f}°C. Irrigate early morning and mulch to cut evaporation.", "heat")
    if ph is not None and ph < 5.5:
        add("Soil", "high", "Soil looks acidic", f"Estimated pH {ph:.1f}. Test locally, then consider liming to roughly pH 6–6.5 if the test agrees.", "lime")
    elif ph is not None and ph > 8:
        add("Soil", "medium", "Soil looks alkaline", f"Estimated pH {ph:.1f}. Add organic matter and favour tolerant crops such as sorghum or chickpea.", "alkaline")
    if soc is not None and soc < 10:
        add("Soil", "high", "Build organic carbon", f"Estimated topsoil carbon is low ({soc:.1f} g/kg). Use compost, residue retention and cover crops.", "compost")
    if clay is not None and clay > 40:
        add("Soil", "medium", "Heavy, clay-rich soil", "Avoid working wet soil, and use raised beds or drainage lines for waterlogging-sensitive crops.", "texture-clay")
    elif (clay is not None and clay < 12) or (sand is not None and sand > 70):
        add("Soil", "medium", "Light, sandy soil", "It drains fast and holds few nutrients. Apply nutrients in small split doses and keep the surface mulched.", "texture-sand")
    add("Soil", "low", "Keep soil covered", "Residue or a cover crop between seasons protects soil and conserves water.", "cover-crop")
    if top:
        add("Crops", "medium", f"Plan for {top['name']}", f"{top['name']} is the top match. Use local seed varieties, check sowing windows with your extension office and scout weekly for pests.", "scouting")
    add("Crops", "low", "Break up crop repeats", "Follow the rotation plan so the same crop family is not grown back to back.", "rotation")
    return items
