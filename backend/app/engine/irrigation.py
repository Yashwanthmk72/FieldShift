# AI-assisted: written with an AI coding assistant (see README, "AI tools used").
"""FAO-56 style irrigation planning. Pure functions.

ETc = Kc x ET0 (FAO Irrigation and Drainage Paper 56). A daily root-zone water balance decides when to
irrigate. Root depth, depletion fraction, efficiencies and the effective-rain rule are ASSUMPTIONS the user can
change; they are not crop-specific sourced values."""
from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Any

GSC = 0.0820  # solar constant, MJ m-2 min-1 (FAO-56 eq. 21)
EFFICIENCY = {"drip": 0.90, "sprinkler": 0.75, "furrow": 0.60}  # ASSUMPTION: typical application efficiencies
ASSUMPTIONS = {"root_depth_m": 0.6, "depletion_fraction": 0.5, "effective_rain_fraction": 0.8, "rain_ignore_mm": 2.0, "efficiency": EFFICIENCY}
RAIN_RULE = "Effective rain = 80 % of daily rain above 2 mm (simple rule, assumption)."


def extraterrestrial_radiation_mm(lat_deg: float, doy: int) -> float:
    """Ra in mm/day equivalent (FAO-56 eqs. 21-25). Valid away from polar day/night (clamped)."""
    phi = math.radians(lat_deg)
    dr = 1 + 0.033 * math.cos(2 * math.pi * doy / 365)
    delta = 0.409 * math.sin(2 * math.pi * doy / 365 - 1.39)
    x = max(-1.0, min(1.0, -math.tan(phi) * math.tan(delta)))
    ws = math.acos(x)
    ra = (24 * 60 / math.pi) * GSC * dr * (ws * math.sin(phi) * math.sin(delta) + math.cos(phi) * math.cos(delta) * math.sin(ws))
    return ra * 0.408


def hargreaves_et0(tmin: float, tmax: float, lat_deg: float, doy: int) -> float:
    """Hargreaves-Samani reference evapotranspiration (mm/day): fallback when no ET0 provider is available."""
    tmean = (tmin + tmax) / 2
    return max(0.0, 0.0023 * (tmean + 17.8) * math.sqrt(max(tmax - tmin, 0.0)) * extraterrestrial_radiation_mm(lat_deg, doy))


def kc_at(crop: dict[str, Any], days_after_sowing: int, season_days: int) -> tuple[float, str]:
    """Piecewise FAO-56 Kc curve: ini flat, linear rise to mid, mid flat, linear fall to end."""
    f, kc = crop["stage_fraction"], crop["kc"]
    x = days_after_sowing / max(season_days, 1)
    if x < 0:
        return kc["ini"], "pre-sowing"
    if x < f["ini"]:
        return kc["ini"], "initial"
    if x < f["ini"] + f["dev"]:
        return kc["ini"] + (kc["mid"] - kc["ini"]) * (x - f["ini"]) / f["dev"], "development"
    if x < f["ini"] + f["dev"] + f["mid"]:
        return kc["mid"], "mid-season"
    if x <= 1:
        return kc["mid"] + (kc["end"] - kc["mid"]) * (x - f["ini"] - f["dev"] - f["mid"]) / f["late"], "late"
    return kc["end"], "past maturity"


def effective_rain(rain_mm: float, fraction: float = ASSUMPTIONS["effective_rain_fraction"], ignore: float = ASSUMPTIONS["rain_ignore_mm"]) -> float:
    return fraction * rain_mm if rain_mm > ignore else 0.0


def schedule(crop: dict[str, Any], days: list[dict[str, Any]], sowing: date, season_days: int, awc_mm_per_m: float, method: str = "drip",
             root_depth_m: float = ASSUMPTIONS["root_depth_m"], depletion_fraction: float = ASSUMPTIONS["depletion_fraction"],
             start_depletion_mm: float = 0.0, max_mm_per_week: float | None = None) -> dict[str, Any]:
    """Daily balance over `days` = [{date: date, et0: mm, rain: mm}]. Dr is root-zone depletion (mm); 0 = field capacity.

    rainfed: no irrigation is scheduled; days where depletion exceeds readily available water are reported as stress days."""
    if method not in EFFICIENCY and method != "rainfed":
        raise ValueError(f"unknown method {method}")
    taw = awc_mm_per_m * root_depth_m
    raw = depletion_fraction * taw
    eff = EFFICIENCY.get(method, 1.0)
    dr = min(max(start_depletion_mm, 0.0), taw)
    rows, events, stress = [], [], 0
    week_used: dict[int, float] = {}
    for d in days:
        dt: date = d["date"]
        dap = (dt - sowing).days
        kc, stage = kc_at(crop, dap, season_days)
        etc = kc * d["et0"]
        pe = effective_rain(d["rain"])
        dr = dr - pe + etc
        irrigated_net = 0.0
        if dr >= raw and method != "rainfed" and 0 <= dap <= season_days:
            need = dr
            wk = (dt - days[0]["date"]).days // 7
            if max_mm_per_week is not None:
                room = max(0.0, max_mm_per_week - week_used.get(wk, 0.0))
                need = min(need, room * eff)
            if need > 0:
                irrigated_net = need
                gross = need / eff
                week_used[wk] = week_used.get(wk, 0.0) + gross
                events.append({"date": dt.isoformat(), "net_mm": round(need, 1), "gross_mm": round(gross, 1)})
                dr -= need
        dr = min(max(dr, 0.0), taw)  # below 0 = deep percolation; above TAW = crop already stressed (capped)
        is_stress = dr >= raw and irrigated_net == 0 and 0 <= dap <= season_days
        stress += is_stress
        rows.append({"date": dt.isoformat(), "stage": stage, "kc": round(kc, 2), "et0_mm": round(d["et0"], 2), "etc_mm": round(etc, 2), "eff_rain_mm": round(pe, 2),
                     "depletion_mm": round(dr, 1), "stress": bool(is_stress)})
    weeks: dict[int, dict[str, Any]] = {}
    for e in events:
        w = (date.fromisoformat(e["date"]) - days[0]["date"]).days // 7
        weeks.setdefault(w, {"week": w + 1, "events": 0, "net_mm": 0.0, "gross_mm": 0.0})
        weeks[w]["events"] += 1; weeks[w]["net_mm"] += e["net_mm"]; weeks[w]["gross_mm"] += e["gross_mm"]
    return {"taw_mm": round(taw, 1), "raw_mm": round(raw, 1), "method": method, "efficiency": None if method == "rainfed" else eff, "events": events,
            "weekly": [{**v, "net_mm": round(v["net_mm"], 1), "gross_mm": round(v["gross_mm"], 1)} for _, v in sorted(weeks.items())], "stress_days": int(stress), "daily": rows,
            "assumptions": {"root_depth_m": root_depth_m, "depletion_fraction": depletion_fraction, "awc_mm_per_m": awc_mm_per_m, "rain_rule": RAIN_RULE,
                            "efficiency_note": "Application efficiencies are typical assumed values, not measurements."},
            "limitations": ["ET0 and rain come from a forecast, so schedules beyond a few days are indicative.", "Crop coefficients follow FAO-56 Table 12; stage lengths are scaled from one reference row.",
                            "Water-holding capacity is a pedotransfer estimate from modelled soil data. Verify in the field."]}


def season_water_need(crop: dict[str, Any], daily_et0: list[float], season_days: int) -> float:
    """Total crop evapotranspiration (mm) over the season for a list of daily ET0 values (repeated to fill the season)."""
    if not daily_et0:
        raise ValueError("need ET0 values")
    return sum(kc_at(crop, d, season_days)[0] * daily_et0[d % len(daily_et0)] for d in range(season_days))
