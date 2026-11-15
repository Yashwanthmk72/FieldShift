# AI-assisted: written with an AI coding assistant (see README, "AI tools used").
"""Rotation planning. Pure functions."""
from __future__ import annotations

from typing import Any

from . import content


def build_rotation(crops: list[dict[str, Any]] | tuple[dict[str, Any], ...], scores: dict[str, float], priorities: dict[str, float], previous: list[str], seasons: int, lat: float = 0.0) -> list[dict[str, Any]]:
    """Field-aware rotation: pick the best-suited crop each season while alternating families,
    avoiding the last two crops, and bringing in a legume when none was grown recently."""
    crops = [c for c in crops if not c.get("perennial")]  # perennials (banana, sugarcane) do not fit a season-by-season rotation
    legumes = {c["id"] for c in crops if c["fixer"]}
    plan: list[dict[str, Any]] = []
    recent = list(previous[-2:])
    for n in range(seasons):
        last_family = plan[-1]["family"] if plan else None
        want_legume = not any(c in legumes for c in recent[-2:])
        best, best_val = None, -1e9
        for c in crops:
            if c["id"] in recent[-2:] or c["family"] == last_family:
                continue
            val = scores.get(c["id"], 50) + (15 if want_legume and c["fixer"] else 0) + (6 * priorities["soil"] if c["fixer"] else 0)
            if val > best_val:
                best, best_val = c, val
        pick = best or next(c for c in crops if c["id"] not in recent[-1:])
        window = content.sow_window(pick["id"], lat)
        reason = ("Legume phase fixes nitrogen and breaks cereal pest cycles" if pick["fixer"]
                  else "Diversifies the crop family and spreads climate, disease and market risk")
        plan.append({"season": n + 1, "crop": pick["name"], "id": pick["id"], "family": pick["family"], "fixer": pick["fixer"], "score": round(scores.get(pick["id"], 50)),
                     "reason": reason, "sow_months": window["sow_months"], "harvest_months": window["harvest_months"], "window_note": window["note"]})
        recent.append(pick["id"])
    return plan
