# AI-assisted: written with an AI coding assistant (see README, "AI tools used").
"""Crop financial model. Pure functions; every input is user-entered or an editable labelled assumption.

Estimates, not guaranteed returns. Nothing here knows a market price: the caller supplies price,
yield and costs, and each result carries which inputs were missing."""
from __future__ import annotations

import random
from typing import Any

COST_CATEGORIES = ("seed", "fertilizer", "soil_prep", "irrigation", "labour", "pesticide", "machinery", "transport", "other")
VARIABLE = ("seed", "fertilizer", "irrigation", "labour", "pesticide", "transport")
DEFAULT_RANGES = {"yield": 0.20, "price": 0.25, "cost": 0.10}  # ASSUMPTION: symmetric +/- fractions, user-editable
MC_RUNS = 2000
MC_SEED = 42
DISCLAIMER = "Estimates, not guaranteed returns."


def _missing(costs: dict[str, float | None], cats: tuple[str, ...]) -> list[str]:
    return [c for c in cats if costs.get(c) is None]


def cost_totals(costs: dict[str, float | None]) -> dict[str, Any]:
    miss_all = _missing(costs, COST_CATEGORIES)
    miss_var = _missing(costs, VARIABLE)
    return {"total": None if miss_all else sum(float(costs[c]) for c in COST_CATEGORIES),
            "variable": None if miss_var else sum(float(costs[c]) for c in VARIABLE),
            "missing_all": miss_all, "missing_variable": miss_var}


def evaluate(yield_t_ha: float | None, price_per_t: float | None, costs: dict[str, float | None], area_ha: float = 1.0) -> dict[str, Any]:
    """Per-hectare economics. Returns None for anything that cannot be computed, with the reason."""
    out: dict[str, Any] = {"area_ha": area_ha, "disclaimer": DISCLAIMER, "partial": []}
    t = cost_totals(costs)
    out["cost_total_per_ha"], out["cost_variable_per_ha"] = t["total"], t["variable"]
    revenue = None
    if yield_t_ha is None or price_per_t is None:
        out["partial"].append("missing: " + ", ".join(n for n, v in (("yield", yield_t_ha), ("price", price_per_t)) if v is None))
    else:
        revenue = yield_t_ha * price_per_t
    out["revenue_per_ha"] = revenue
    out["gross_margin_per_ha"] = None if revenue is None or t["variable"] is None else revenue - t["variable"]
    out["net_profit_per_ha"] = None if revenue is None or t["total"] is None else revenue - t["total"]
    if t["missing_all"]:
        out["partial"].append("net profit partial: missing cost categories " + ", ".join(t["missing_all"]))
    total = t["total"]
    out["break_even_price_per_t"] = total / yield_t_ha if total is not None and yield_t_ha else None
    out["break_even_yield_t_ha"] = total / price_per_t if total is not None and price_per_t else None
    net = out["net_profit_per_ha"]
    out["roi"] = net / total if net is not None and total else None
    out["payback_seasons"] = total / net if net is not None and net > 0 and total else None  # seasons of this net profit needed to recover one season's outlay
    out["net_profit_total"] = None if net is None else net * area_ha
    return out


def scenarios(yield_t_ha: float, price_per_t: float, costs_total: float, ranges: dict[str, float] | None = None) -> dict[str, Any]:
    r = {**DEFAULT_RANGES, **(ranges or {})}
    def net(y: float, p: float, c: float) -> float: return yield_t_ha * y * price_per_t * p - costs_total * c
    return {"ranges": r, "ranges_label": "ASSUMPTION (editable)",
            "best": net(1 + r["yield"], 1 + r["price"], 1 - r["cost"]), "base": net(1, 1, 1), "worst": net(1 - r["yield"], 1 - r["price"], 1 + r["cost"])}


def percentile(sorted_vals: list[float], q: float) -> float:
    if not sorted_vals:
        raise ValueError("empty")
    pos = (len(sorted_vals) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo)


def monte_carlo(yield_t_ha: float, price_per_t: float, costs_total: float, ranges: dict[str, float] | None = None, runs: int = MC_RUNS, seed: int = MC_SEED) -> dict[str, Any]:
    """Independent triangular draws for yield, price and cost factors (mode 1, +/- range). Illustrative only."""
    r = {**DEFAULT_RANGES, **(ranges or {})}
    rng = random.Random(seed)
    nets = sorted(yield_t_ha * rng.triangular(1 - r["yield"], 1 + r["yield"], 1) * price_per_t * rng.triangular(1 - r["price"], 1 + r["price"], 1)
                  - costs_total * rng.triangular(1 - r["cost"], 1 + r["cost"], 1) for _ in range(runs))
    p10, p50, p90 = (percentile(nets, q) for q in (.1, .5, .9))
    return {"runs": runs, "seed": seed, "p10": p10, "p50": p50, "p90": p90, "prob_loss": sum(1 for n in nets if n < 0) / runs,
            "risk_adjusted_margin_per_ha": (p10 + p50) / 2, "label": "Illustrative simulation from assumed ranges; not a forecast.",
            "method": "risk-adjusted margin = mean of P10 and P50 net profit per hectare"}


def margin_indices(margins: dict[str, float], all_ids: list[str]) -> dict[str, Any]:
    """0-100 profit index for the advisor from users' risk-adjusted margins.

    Needs >= 2 crops with margins that differ; the index is *relative among the crops the user has costed*.
    Crops without a plan get a neutral 50, flagged in 'basis'. Returns {} when profit cannot be used."""
    vals = [v for v in margins.values() if v is not None]
    if len(vals) < 2 or max(vals) == min(vals):
        return {}
    lo, hi = min(vals), max(vals)
    return {cid: {"index": round(100 * (margins[cid] - lo) / (hi - lo), 1) if margins.get(cid) is not None else 50.0,
                  "basis": "user financial plan" if margins.get(cid) is not None else "no plan entered (neutral 50)"} for cid in all_ids}


def compare(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Order crops by risk-adjusted margin (None last) for side-by-side display."""
    return sorted(rows, key=lambda r: (r.get("risk_adjusted_margin_per_ha") is None, -(r.get("risk_adjusted_margin_per_ha") or 0)))


def to_csv(rows: list[dict[str, Any]]) -> str:
    cols = ["crop", "area_ha", "yield_t_ha", "price_per_t", "cost_total_per_ha", "revenue_per_ha", "gross_margin_per_ha", "net_profit_per_ha",
            "break_even_price_per_t", "break_even_yield_t_ha", "roi", "provenance"]
    def cell(v: Any) -> str:
        s = "" if v is None else (f"{v:.6g}" if isinstance(v, float) else str(v))
        if isinstance(v, str) and s[:1] in "=+-@":  # neutralise spreadsheet formula injection in text cells
            s = "'" + s
        return '"' + s.replace('"', '""') + '"'
    return "\n".join([",".join(cols)] + [",".join(cell(r.get(c)) for c in cols) for r in rows]) + "\n"
