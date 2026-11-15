# AI-assisted: written with an AI coding assistant (see README, "AI tools used").
"""Orchestration: providers -> pure engine -> API-shaped dicts. Framework-free so it can be tested with fake providers."""
from __future__ import annotations

import asyncio
from datetime import date, datetime
from typing import Any

from .engine import confidence as conf_engine, content, finance, geo, irrigation, management, pest_risk, rotation, scoring, soil, soil_health
from .engine.crops import crop_by_id, load_crops

SOURCES_NOTE = "NASA POWER observations are near real time, not instantaneous. SoilGrids values are modelled global estimates. Field summaries sample points inside the boundary; they are indicative."
DEGRADED_CLIMATE = {"latest": {}, "rainfall_14d_mm": None, "series": {}}


def _data(res: dict[str, Any] | BaseException | None) -> Any:
    return res["data"] if isinstance(res, dict) and res.get("ok") else None


def _prov(res: Any, name: str) -> dict[str, Any]:
    if isinstance(res, dict):
        return {"name": name, "ok": res.get("ok", False), "source": res.get("source"), "kind": res.get("kind"), "fetched_at": res.get("fetched_at"), "coverage": res.get("coverage"), "error": res.get("error")}
    return {"name": name, "ok": False, "source": name, "kind": None, "fetched_at": None, "coverage": "", "error": f"{name} unavailable"}


def profit_components(margins: dict[str, float] | None) -> dict[str, Any]:
    ids = [c["id"] for c in load_crops()]
    return finance.margin_indices(margins or {}, ids)


async def recommend(p, lat: float, lon: float, soil_in: dict[str, Any], priorities: dict[str, float], previous: list[str], margins: dict[str, float] | None = None) -> dict[str, Any]:
    clim_r, soil_r, norm_r = await asyncio.gather(p.nasa_daily(lat, lon), p.soil(lat, lon), p.nasa_climatology(lat, lon), return_exceptions=True)
    climate = _data(clim_r) or DEGRADED_CLIMATE
    normals = _data(norm_r)
    soil_values = dict(_data(soil_r) or {})
    soil_values.update(soil_in)
    prio = scoring.normalize_priorities(priorities)
    pc = profit_components(margins)
    ranked = [scoring.suitability(c, climate, soil_values, prio, previous, normals, lat, pc.get(c["id"], {}).get("index")) for c in load_crops()]
    ranked.sort(key=lambda r: r["score"], reverse=True)
    for r in ranked:
        r["confidence"] = conf_engine.assess(r["confidence"], r["crop"], None)
        r["profit_basis"] = pc.get(r["crop"]["id"], {}).get("basis", "profit priority unavailable: no costed crops")
    return {"generated_at": date.today().isoformat(), "ranked": ranked, "climate": climate, "profit_available": bool(pc), "priorities": prio,
            "provenance": [_prov(clim_r, "recent weather"), _prov(norm_r, "climate normals"), _prov(soil_r, "soil")],
            "soil": {"values": soil_values, "note": "Modelled; " + soil.BANNER}, "data_quality": SOURCES_NOTE,
            "sources": ["NASA POWER Daily API", "NASA POWER climatology", "ISRIC SoilGrids 2.0", "FieldShift crop requirement guide"], "score_meaning": scoring.SUITABILITY_NOTE,
            "inputs": {"latitude": lat, "longitude": lon, "priorities": prio, "soil": soil_values}}


def soil_summary_from_layers(layers: list[dict[str, float]]) -> dict[str, Any]:
    def mean(k: str):
        v = [x[k] for x in layers if k in x]
        return sum(v) / len(v) if v else None
    ph, soc, clay, sand, silt = (mean(k) for k in ("phh2o", "soc", "clay", "sand", "silt"))
    pct = lambda v: v / 10 if v is not None else None  # noqa: E731
    clay_p, sand_p, silt_p = pct(clay), pct(sand), pct(silt)
    texture = soil.usda_texture(sand_p, silt_p, clay_p) if None not in (clay_p, sand_p, silt_p) else None
    out = {"ph": round(ph, 2) if ph is not None else None, "organic_carbon_g_kg": round(soc / 10, 1) if soc is not None else None,
           "clay_pct": round(clay_p, 1) if clay_p is not None else None, "sand_pct": round(sand_p, 1) if sand_p is not None else None, "silt_pct": round(silt_p, 1) if silt_p is not None else None,
           "texture": texture, "texture_key": texture.lower().replace(" ", "-") if texture else None, "depth": "0–30 cm weighted", "samples_with_data": len(layers)}
    if None not in (out["sand_pct"], out["clay_pct"], out["organic_carbon_g_kg"]):
        out["water_holding"] = soil.water_holding(out["sand_pct"], out["clay_pct"], out["organic_carbon_g_kg"])
    out["limitations"] = soil.limitations(out)
    out["npk"] = soil.UNAVAILABLE_NOTE
    out["banner"] = soil.BANNER
    return out


async def analyze(p, geometry: dict[str, Any], priorities: dict[str, float], previous: list[str], seasons: int, margins: dict[str, float] | None = None) -> dict[str, Any]:
    ring = geo._ring(geometry)
    area_ha = geo.ring_area_ha(ring)
    centre, points = geo.sample_points(ring)
    results = await asyncio.gather(p.nasa_daily(centre["lat"], centre["lon"]), p.nasa_climatology(centre["lat"], centre["lon"]), *[p.soil(pt["lat"], pt["lon"]) for pt in points], return_exceptions=True)
    climate = _data(results[0]) or {**DEGRADED_CLIMATE, "error": "NASA POWER is temporarily unavailable; scores use crop guides."}
    normals = _data(results[1])
    layers = [d for d in (_data(r) for r in results[2:]) if d]
    soil_sum = soil_summary_from_layers(layers)
    soil_values = {"ph": soil_sum["ph"]} if soil_sum["ph"] is not None else {}
    prio = scoring.normalize_priorities(priorities)
    pc = profit_components(margins)
    crops = list(load_crops())
    ranked = [scoring.suitability(c, climate, soil_values, prio, previous, normals, centre["lat"], pc.get(c["id"], {}).get("index")) for c in crops]
    ranked.sort(key=lambda r: r["score"], reverse=True)
    for r in ranked:
        r["confidence"] = conf_engine.assess(r["confidence"], r["crop"], soil_sum.get("samples_with_data"))
    scores = {r["crop"]["id"]: r["score"] for r in ranked}
    return {"generated_at": date.today().isoformat(), "area_ha": round(area_ha, 2), "centroid": centre, "samples": points,
            "coverage": {"boundary_corners": len(ring) - 1 if ring[0] == ring[-1] else len(ring), "soil_sample_points": len(points), "soil_points_with_data": len(layers), "area_ha": round(area_ha, 2),
                         "note": "Climate comes from one NASA POWER grid cell (~50 km) at the field centre, so it is identical across a small field. Soil is sampled at up to 4 points inside your boundary (SoilGrids, 250 m, modelled). Samples are indicative."},
            "provenance": [_prov(results[0], "recent weather"), _prov(results[1], "climate normals")] + [_prov(r, f"soil sample {i + 1}") for i, r in enumerate(results[2:])],
            "climate": climate, "normals": normals, "soil": soil_sum, "ranked": ranked, "priorities": prio, "profit_available": bool(pc), "weights": {"climate": scoring.CLIMATE_WEIGHT},
            "previous_crops": previous, "rotation": rotation.build_rotation(crops, scores, prio, previous, seasons, centre["lat"]),
            "management": management.land_management(climate, soil_sum, ranked[0]["crop"] if ranked else None), "score_meaning": scoring.SUITABILITY_NOTE,
            "sources": ["NASA POWER Daily API", "NASA POWER climatology", "ISRIC SoilGrids 2.0", "FieldShift crop requirement guide"]}


def weather_summary(fc: dict[str, Any], normals: dict[str, Any] | None) -> dict[str, Any]:
    days = fc["days"]
    heat = [d["date"] for d in days if d["tmax"] is not None and d["tmax"] >= 35]
    heavy = [d["date"] for d in days if d["rain"] is not None and d["rain"] >= 50]
    out: dict[str, Any] = {"days": days, "current": fc["current"], "horizon_days": fc["horizon_days"], "heat_stress_days": heat, "extreme_rain_days": heavy,
                           "alerts": ([{"type": "heat", "text": f"{len(heat)} day(s) with a forecast maximum of 35 °C or more (threshold is a general heat-stress marker)."}] if heat else [])
                           + ([{"type": "rain", "text": f"{len(heavy)} day(s) with 50 mm or more of forecast rain."}] if heavy else [])}
    if normals:
        month = datetime.now().month - 1
        fut = [d["rain"] for d in days if d["rain"] is not None and d["date"] >= date.today().isoformat()][:14]
        if fut:
            expected = normals["rain_mm_month"][month] * len(fut) / 30.4
            out["rainfall_vs_normal"] = {"forecast_mm": round(sum(fut), 1), "normal_mm_for_same_days": round(expected, 1), "days": len(fut),
                                         "note": "Forecast rain versus the long-term monthly normal for the same number of days. A simple deficit indicator, not an SPI."}
    return out


async def weather(p, lat: float, lon: float) -> dict[str, Any]:
    fc, norm = await asyncio.gather(p.forecast(lat, lon), p.nasa_climatology(lat, lon))
    if not fc["ok"]:
        return {"available": False, "provenance": [_prov(fc, "forecast")], "error": fc["error"], "normals": _data(norm)}
    return {"available": True, **weather_summary(fc["data"], _data(norm)), "normals": _data(norm), "provenance": [_prov(fc, "forecast"), _prov(norm, "climate normals")]}


async def irrigation_plan(p, lat: float, lon: float, crop_id: str, sowing: date, method: str, sand_pct: float | None, clay_pct: float | None, soc_g_kg: float | None,
                          root_depth_m: float, depletion_fraction: float, max_mm_per_week: float | None) -> dict[str, Any]:
    crop = crop_by_id(crop_id)
    if crop is None:
        raise KeyError(crop_id)
    fc_r, soil_r = await asyncio.gather(p.forecast(lat, lon), p.soil(lat, lon))
    if not fc_r["ok"]:
        return {"available": False, "error": fc_r["error"], "provenance": [_prov(fc_r, "forecast")]}
    sv = _data(soil_r) or {}
    s = sand_pct if sand_pct is not None else (sv["sand"] / 10 if "sand" in sv else None)
    c = clay_pct if clay_pct is not None else (sv["clay"] / 10 if "clay" in sv else None)
    soc = soc_g_kg if soc_g_kg is not None else (sv["soc"] / 10 if "soc" in sv else None)
    if None in (s, c, soc):
        return {"available": False, "error": "Soil texture is unavailable for this point. Enter sand %, clay % and organic carbon to estimate water holding.", "provenance": [_prov(fc_r, "forecast"), _prov(soil_r, "soil")]}
    awc = soil.water_holding(s, c, soc)
    daily, skipped = [], 0
    for d in fc_r["data"]["days"]:
        if d["et0"] is None or d["rain"] is None:
            skipped += 1
            continue
        daily.append({"date": date.fromisoformat(d["date"]), "et0": float(d["et0"]), "rain": float(d["rain"])})
    if not daily:
        return {"available": False, "error": "Forecast has no ET0/rain values.", "provenance": [_prov(fc_r, "forecast")]}
    season_days = max(30, round(content.maturity_days(crop_id)))
    plan = irrigation.schedule(crop, daily, sowing, season_days, awc["awc_mm_per_m"], method, root_depth_m, depletion_fraction, max_mm_per_week=max_mm_per_week)
    return {"available": True, **plan, "water_holding": awc, "season_days": season_days, "days_skipped_missing_data": skipped, "horizon_days": len(daily),
            "tips": ["Irrigate early morning to cut evaporation losses.", "Mulch to reduce soil evaporation.", "Check soil moisture by hand before each scheduled event; the schedule is an estimate."],
            "provenance": [_prov(fc_r, "forecast"), _prov(soil_r, "soil")]}


async def pest_outlook(p, lat: float, lon: float, crop_id: str) -> dict[str, Any]:
    fc = await p.forecast(lat, lon)
    if not fc["ok"]:
        return {"available": False, "error": fc["error"], "provenance": [_prov(fc, "forecast")]}
    daily = pest_risk.daily_from_hourly(fc["data"]["hours"])
    risks = pest_risk.evaluate(daily, crop_id)
    return {"available": True, "crop_id": crop_id, "days_evaluated": len(daily), "risks": risks, "note": pest_risk.GENERAL_ADVICE,
            "provenance": [_prov(fc, "forecast")]}


def finance_report(crop_id: str, area_ha: float, yield_t_ha: float | None, price_per_t: float | None, costs: dict[str, float | None], ranges: dict[str, float] | None, provenance: dict[str, str]) -> dict[str, Any]:
    base = finance.evaluate(yield_t_ha, price_per_t, costs, area_ha)
    out: dict[str, Any] = {"crop_id": crop_id, "inputs": {"yield_t_ha": yield_t_ha, "price_per_t": price_per_t, "costs": costs}, "provenance": provenance, "result": base, "disclaimer": finance.DISCLAIMER}
    if base["net_profit_per_ha"] is not None:
        out["scenarios"] = finance.scenarios(yield_t_ha, price_per_t, base["cost_total_per_ha"], ranges)
        out["monte_carlo"] = finance.monte_carlo(yield_t_ha, price_per_t, base["cost_total_per_ha"], ranges)
        out["risk_adjusted_margin_per_ha"] = out["monte_carlo"]["risk_adjusted_margin_per_ha"]
    else:
        out["scenarios"] = out["monte_carlo"] = out["risk_adjusted_margin_per_ha"] = None
    return out


async def soil_health_report(p, lat: float, lon: float, crop_id: str | None, area_ha: float | None) -> dict[str, Any]:
    """Soil-health summary from modelled SoilGrids values. If soil data is unavailable the answer says so; nothing is estimated."""
    soil_r = await p.soil(lat, lon)
    prov = [_prov(soil_r, "soil")]
    vals = _data(soil_r)
    if not vals:
        return {"available": False, "error": (soil_r or {}).get("error") or "Soil data unavailable for this point.", "not_available": soil_health.UNAVAILABLE,
                "disclaimer": soil_health.DISCLAIMER, "sampling": soil_health.sampling_plan(area_ha), "provenance": prov}
    summary = soil_summary_from_layers([vals])
    crop = crop_by_id(crop_id) if crop_id else None
    out = soil_health.assess(summary, area_ha, crop)
    out["soil"] = {k: summary.get(k) for k in ("ph", "organic_carbon_g_kg", "clay_pct", "sand_pct", "silt_pct", "texture", "depth")}
    out["provenance"] = prov
    return out
