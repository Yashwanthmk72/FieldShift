# AI-assisted: written with an AI coding assistant.
"""Daily NASA POWER values vs the long-term monthly climatology, with anomalies. Pure; no I/O."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

DAYS = [31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
MAX_DAYS = 731


def _interp(monthly: list[float], d: date) -> float:
    """Smooth normal: linear interpolation between month mid-points so the baseline has no steps at month boundaries."""
    dim = DAYS[d.month - 1]
    pos = d.month - 1 + (d.day - 0.5) / dim - 0.5  # 0 at the middle of month 0
    i0 = int(pos // 1) % 12
    f = pos - (pos // 1)
    return monthly[i0] * (1 - f) + monthly[(i0 + 1) % 12] * f


def _roll(vals: list[float | None], n: int) -> list[float | None]:
    out: list[float | None] = []
    for i in range(len(vals)):
        w = [v for v in vals[max(0, i - n + 1): i + 1] if v is not None]
        out.append(round(sum(w) / len(w), 2) if len(w) >= max(2, n // 2) else None)
    return out


def build(daily: dict[str, Any], normals: dict[str, Any] | None, today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    dates = [date.fromisoformat(x) for x in daily["dates"]]
    n = len(dates)
    res: dict[str, Any] = {"dates": daily["dates"], "n_days": n, "first_date": daily["dates"][0] if n else None, "last_date": daily["dates"][-1] if n else None}
    last_valid = max((dates[i] for i in range(n) if any(daily[k][i] is not None for k in ("temperature_c", "rain_mm", "solar_mj_m2"))), default=None)
    res["latest_data_date"] = last_valid.isoformat() if last_valid else None
    res["lag_days"] = (today - last_valid).days if last_valid else None
    res["normals_available"] = bool(normals)

    def block(key: str, normal_monthly: list[float] | None, interpolate: bool) -> dict[str, Any]:
        vals = daily[key]
        if not normal_monthly:
            return {"values": vals, "normal": None, "anomaly": None, "anomaly_7d": None}
        normal = [round(_interp(normal_monthly, d) if interpolate else normal_monthly[d.month - 1], 2) for d in dates]
        anom = [None if v is None else round(v - normal[i], 2) for i, v in enumerate(vals)]
        return {"values": vals, "normal": normal, "anomaly": anom, "anomaly_7d": _roll(anom, 7)}

    res["temperature_c"] = block("temperature_c", (normals or {}).get("temperature_c"), True)
    rain_daily_normals = [(normals["rain_mm_month"][m] / DAYS[m]) for m in range(12)] if normals else None
    res["rain_mm"] = block("rain_mm", rain_daily_normals, False)
    res["solar_mj_m2"] = block("solar_mj_m2", (normals or {}).get("solar_mj_m2_day"), True)

    if normals and n:
        cum, cumn, a, b = [], [], 0.0, 0.0
        for i, v in enumerate(daily["rain_mm"]):
            a += v or 0.0
            b += res["rain_mm"]["normal"][i]
            cum.append(round(a, 1))
            cumn.append(round(b, 1))
        res["rain_cumulative"] = {"actual": cum, "normal": cumn}
    s: dict[str, Any] = {}
    tv = [v for v in (res["temperature_c"]["anomaly"] or []) if v is not None]
    if tv:
        s["temp_anomaly_mean_c"] = round(sum(tv) / len(tv), 2)
    if normals and n:
        s["rain_total_mm"] = res["rain_cumulative"]["actual"][-1]
        s["rain_normal_mm"] = res["rain_cumulative"]["normal"][-1]
        if s["rain_normal_mm"] > 0:
            s["rain_vs_normal_pct"] = round((s["rain_total_mm"] / s["rain_normal_mm"] - 1) * 100)
    res["summary"] = s
    res["notes"] = ["NASA POWER daily values lag real time by a few days; the newest days can be missing or revised.",
                    "Each value describes one ~50 km (0.5°) grid cell, not your field. Local rain can differ a lot from the grid-cell value.",
                    "The 'normal' is NASA POWER's long-term monthly climatology, smoothed between month mid-points. Anomalies are day value minus normal; shading uses a 7-day mean."]
    return res


def clamp_range(start: date | None, end: date | None, today: date | None = None, default_days: int = 180) -> tuple[date, date]:
    today = today or date.today()
    end = min(end or (today - timedelta(days=2)), today)
    start = start or end - timedelta(days=default_days - 1)
    if start > end:
        raise ValueError("start must not be after end")
    if (end - start).days + 1 > MAX_DAYS:
        raise ValueError(f"range too long (max {MAX_DAYS} days)")
    return start, end
