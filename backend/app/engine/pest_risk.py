# AI-assisted: written with an AI coding assistant (see README, "AI tools used").
"""Weather-driven pest and disease *risk indicators*. Pure functions.

These flag weather conditions that favour disease. They are NOT diagnoses and do not detect disease.
Each rule states its basis; only rules with a literature reference are marked as such."""
from __future__ import annotations

from typing import Any

RULES: dict[str, dict[str, Any]] = {
    "smith_period": {"name": "Late blight (Smith period)", "crops": ["potato"], "status": "literature",
                     "rule": "Two consecutive days with minimum temperature >= 10 C and at least 11 h of relative humidity >= 90 % on each day.",
                     "source": "Smith (1956), the UK 'Smith period' blight-warning rule; reference not re-verified in this session."},
    "wet_spell": {"name": "Fungal leaf disease favourability", "crops": ["wheat", "maize", "soybean", "groundnut", "chickpea", "sunflower", "sorghum", "millet", "cowpea", "rice", "potato"], "status": "heuristic",
                  "rule": "Three consecutive days with >= 10 h of relative humidity >= 90 % and mean temperature 12-28 C.", "source": "FieldShift heuristic (generic leaf-wetness proxy); not crop-calibrated."},
    "hot_humid": {"name": "Hot, humid conditions (bacterial and fungal pressure)", "crops": ["rice", "maize", "soybean", "groundnut", "cowpea"], "status": "heuristic",
                  "rule": "Two consecutive days with mean temperature > 28 C and >= 12 h of relative humidity >= 90 %.", "source": "FieldShift heuristic; not crop-calibrated."},
}
LEVELS = ("low", "elevated", "high")
GENERAL_ADVICE = "General guidance only. Scout fields, confirm any problem locally, and follow local label and regulations for any treatment. This is not a diagnosis."


def _streak(days: list[dict[str, Any]], pred, n: int) -> list[str]:
    hits, run = [], []
    for d in days:
        if pred(d):
            run.append(d["date"])
            if len(run) >= n:
                hits.append(d["date"])
        else:
            run = []
    return hits


def evaluate(days: list[dict[str, Any]], crop_id: str) -> list[dict[str, Any]]:
    """days: [{date, tmin, tmean, rh_hours_ge90}] oldest first. Returns one entry per applicable rule."""
    out = []
    preds = {
        "smith_period": (lambda d: d["tmin"] >= 10 and d["rh_hours_ge90"] >= 11, 2),
        "wet_spell": (lambda d: d["rh_hours_ge90"] >= 10 and 12 <= d["tmean"] <= 28, 3),
        "hot_humid": (lambda d: d["tmean"] > 28 and d["rh_hours_ge90"] >= 12, 2),
    }
    for rid, rule in RULES.items():
        if crop_id not in rule["crops"]:
            continue
        pred, n = preds[rid]
        hits = _streak(days, pred, n)
        level = "high" if len(hits) >= 2 else "elevated" if hits else "low"
        out.append({"id": rid, "name": rule["name"], "level": level, "triggered_on": hits, "rule": rule["rule"], "source": rule["source"], "basis": rule["status"], "advice": GENERAL_ADVICE})
    return out


def daily_from_hourly(hours: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate hourly [{time: 'YYYY-MM-DDTHH:MM', t: C, rh: %}] into the daily records evaluate() needs."""
    by: dict[str, list[dict[str, Any]]] = {}
    for h in hours:
        if h.get("t") is None or h.get("rh") is None:
            continue
        by.setdefault(h["time"][:10], []).append(h)
    return [{"date": day, "tmin": min(x["t"] for x in hs), "tmean": sum(x["t"] for x in hs) / len(hs), "rh_hours_ge90": sum(1 for x in hs if x["rh"] >= 90), "hours": len(hs)}
            for day, hs in sorted(by.items()) if len(hs) >= 20]  # require near-complete days
