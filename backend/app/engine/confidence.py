# AI-assisted: written with an AI coding assistant.
"""Visible confidence for each recommendation.

Combines (a) data completeness from scoring.confidence() with (b) how many of the crop's scoring parameters
are sourced rather than heuristic. Because every temperature/rain/pH range in crops.json is currently heuristic,
the level is capped at 'medium' and the UI shows an 'illustrative estimate' badge. The level describes how much
we trust the INPUTS, not the chance of a good harvest."""
from __future__ import annotations

from typing import Any

SCORING_PARAMS = ("temp", "rain", "ph", "water", "resilience")
RANGE_PARAMS = ("temp", "rain", "ph")
ORDER = {"low": 0, "medium": 1, "high": 2}
NAMES = {"temp": "temperature range", "rain": "rainfall range", "ph": "soil pH range", "water": "water class", "resilience": "resilience score"}


def _min_level(a: str, b: str) -> str:
    return a if ORDER[a] <= ORDER[b] else b


def assess(base: dict[str, Any], crop: dict[str, Any], soil_samples: int | None = None) -> dict[str, Any]:
    """`base` is the dict returned by scoring.confidence(); returns a copy extended with provenance information."""
    prov = crop.get("provenance", {})
    status = {k: (prov.get(k) or {}).get("status", "heuristic") for k in SCORING_PARAMS}
    heuristic = [k for k in SCORING_PARAMS if status[k] != "sourced"]
    sourced_share = (len(SCORING_PARAMS) - len(heuristic)) / len(SCORING_PARAMS)
    level = base.get("level", "low")
    reasons: list[str] = []
    if base.get("defaulted"):
        reasons.append("Some inputs were missing and replaced by neutral defaults: " + ", ".join(base["defaulted"]) + ".")
    if any(status[k] != "sourced" for k in RANGE_PARAMS):
        level = _min_level(level, "medium")
        reasons.append("The crop's " + ", ".join(NAMES[k] for k in RANGE_PARAMS if status[k] != "sourced") + " are heuristic (not verified against a source).")
    if sourced_share < 0.6:
        level = _min_level(level, "medium")
    if soil_samples is not None and soil_samples < 2:
        level = _min_level(level, "medium")
        reasons.append("Soil comes from fewer than 2 modelled sample points.")
    reasons.append("Climate is one ~50 km NASA POWER grid cell; soil is modelled at 250 m. A local soil test is still needed.")
    illustrative = any(status[k] != "sourced" for k in RANGE_PARAMS)
    return {**base, "level": level, "illustrative": illustrative, "sourced_share": round(sourced_share, 2), "heuristic_params": heuristic, "reasons": reasons,
            "label": {"low": "Low confidence", "medium": "Medium confidence", "high": "High confidence"}[level],
            "meaning": "How much we trust the inputs behind this ranking (data completeness and whether crop parameters are verified). It says nothing about the chance of a good harvest."}
