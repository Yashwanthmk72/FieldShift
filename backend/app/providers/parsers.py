# AI-assisted: written with an AI coding assistant (see README, "AI tools used").
"""Pure parsers for provider JSON. Kept free of I/O so they can be tested with fixtures (including malformed/partial ones)."""
from __future__ import annotations

from typing import Any

MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
MONTH_DAYS = [31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
SOIL_DEPTH_WEIGHTS = {"0-5cm": 5, "5-15cm": 10, "15-30cm": 15}


def parse_power_daily(raw: dict[str, Any]) -> dict[str, Any]:
    props = (raw or {}).get("properties", {}).get("parameter", {})

    def series(name: str) -> list[tuple[str, float]]:
        return [(k, float(v)) for k, v in sorted((props.get(name) or {}).items()) if isinstance(v, (int, float)) and v > -900]

    def latest(name: str):
        s = series(name)
        return {"value": s[-1][1], "date": s[-1][0]} if s else None

    rain, temps = series("PRECTOTCORR"), series("T2M")
    if not rain and not temps:
        raise ValueError("no usable values")
    return {"latest": {"temperature_c": latest("T2M"), "rainfall_mm_day": latest("PRECTOTCORR"), "root_zone_wetness": latest("GWETROOT"), "solar_mj_m2_day": latest("ALLSKY_SFC_SW_DWN")},
            "temperature_14d_mean_c": round(sum(v for _, v in temps) / len(temps), 1) if temps else None,
            "rainfall_14d_mm": round(sum(v for _, v in rain), 1) if rain else None,
            "series": {"temperature_c": temps, "rainfall_mm_day": rain, "root_zone_wetness": series("GWETROOT"), "solar_mj_m2_day": series("ALLSKY_SFC_SW_DWN")}}


def parse_power_climatology(raw: dict[str, Any]) -> dict[str, Any]:
    par = raw["properties"]["parameter"]
    temps = [float(par["T2M"][m]) for m in MONTHS]
    rain = [float(par["PRECTOTCORR"][m]) * MONTH_DAYS[i] for i, m in enumerate(MONTHS)]
    if any(t < -900 for t in temps) or any(r < 0 for r in rain):
        raise ValueError("fill values in climatology")
    out = {"temperature_c": [round(t, 1) for t in temps], "rain_mm_month": [round(r, 1) for r in rain]}
    solar = par.get("ALLSKY_SFC_SW_DWN")
    if isinstance(solar, dict):  # optional: only present when requested
        sv = [solar.get(m) for m in MONTHS]
        if all(isinstance(v, (int, float)) and v > -900 for v in sv):
            out["solar_mj_m2_day"] = [round(float(v), 2) for v in sv]
    return out


def parse_power_range(raw: dict[str, Any]) -> dict[str, Any]:
    """NASA POWER daily point JSON -> aligned arrays (None for fill values). Raises ValueError when empty."""
    par = (raw or {}).get("properties", {}).get("parameter", {})
    t, r, s = par.get("T2M") or {}, par.get("PRECTOTCORR") or {}, par.get("ALLSKY_SFC_SW_DWN") or {}
    days = sorted(set(t) | set(r) | set(s))
    clean = lambda d, k: (float(d[k]) if isinstance(d.get(k), (int, float)) and d[k] > -900 else None)  # noqa: E731
    out = {"dates": [f"{d[:4]}-{d[4:6]}-{d[6:8]}" for d in days], "temperature_c": [clean(t, d) for d in days], "rain_mm": [clean(r, d) for d in days], "solar_mj_m2": [clean(s, d) for d in days]}
    if not any(v is not None for k in ("temperature_c", "rain_mm", "solar_mj_m2") for v in out[k]):
        raise ValueError("no usable values")
    return out


def parse_soilgrids(raw: dict[str, Any]) -> dict[str, float]:
    values: dict[str, float] = {}
    for layer in (raw or {}).get("properties", {}).get("layers", []):
        num = den = 0.0
        for depth in layer.get("depths") or []:
            v = (depth.get("values") or {}).get("mean")
            w = SOIL_DEPTH_WEIGHTS.get(depth.get("label"), 0)
            if v is not None and v != -32768 and w:
                num += v * w
                den += w
        if den:
            mean = num / den
            values[layer.get("name")] = mean / 10 if layer.get("name") == "phh2o" else mean
    return values


def parse_open_meteo(raw: dict[str, Any]) -> dict[str, Any]:
    daily = raw.get("daily") or {}
    times = daily.get("time")
    if not times:
        raise ValueError("no daily block")

    def col(name: str) -> list[Any]:
        c = daily.get(name) or [None] * len(times)
        return list(c) + [None] * (len(times) - len(c))

    days = [{"date": t, "tmax": a, "tmin": b, "rain": c, "et0": d} for t, a, b, c, d in zip(times, col("temperature_2m_max"), col("temperature_2m_min"), col("precipitation_sum"), col("et0_fao_evapotranspiration"))]
    hourly = raw.get("hourly") or {}
    hours = [{"time": t, "t": a, "rh": b} for t, a, b in zip(hourly.get("time") or [], hourly.get("temperature_2m") or [], hourly.get("relative_humidity_2m") or [])]
    return {"days": days, "hours": hours, "current": raw.get("current") or {}, "timezone": raw.get("timezone"), "horizon_days": len(days)}


def parse_nominatim(raw: Any) -> list[dict[str, Any]]:
    out = []
    for it in raw if isinstance(raw, list) else []:
        try:
            out.append({"name": str(it.get("display_name", ""))[:200], "lat": float(it["lat"]), "lon": float(it["lon"]), "country_code": (it.get("address") or {}).get("country_code")})
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
    return out
