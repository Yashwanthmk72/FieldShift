# AI-assisted: written with an AI coding assistant (see README, "AI tools used").
"""Crop database loader with schema validation. Pure: no network, no web framework."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parents[1] / "data"
STATUSES = {"sourced", "heuristic"}
RANGE_KEYS = ("temp", "rain", "ph")
REQUIRED_PROVENANCE = ("temp", "rain", "ph", "water", "resilience", "kc", "stage_fraction")
WATER_LEVELS = {"very low", "low", "low–medium", "medium", "medium–high", "high"}


class CropDataError(ValueError):
    pass


def validate_crop(c: dict[str, Any]) -> None:
    cid = c.get("id", "?")
    for k in ("id", "name", "family", "season", "water", "fixer", "resilience", "kc", "stage_fraction", "provenance", *RANGE_KEYS):
        if k not in c:
            raise CropDataError(f"{cid}: missing field '{k}'")
    for k in RANGE_KEYS:
        lo, hi = c[k]
        if not lo < hi:
            raise CropDataError(f"{cid}: {k} range must be increasing, got {c[k]}")
    if c["water"].lower() not in WATER_LEVELS:
        raise CropDataError(f"{cid}: unknown water level '{c['water']}'")
    if not 0 <= c["resilience"] <= 100:
        raise CropDataError(f"{cid}: resilience must be 0-100")
    if abs(sum(c["stage_fraction"].values()) - 1) > 0.02:
        raise CropDataError(f"{cid}: stage_fraction must sum to 1")
    if not all(0 < c["kc"][s] < 2 for s in ("ini", "mid", "end")):
        raise CropDataError(f"{cid}: kc values out of range")
    for k in REQUIRED_PROVENANCE:
        p = c["provenance"].get(k)
        if not p or p.get("status") not in STATUSES or not p.get("source"):
            raise CropDataError(f"{cid}: provenance for '{k}' needs status (sourced|heuristic) and a source note")
        if p["status"] == "sourced" and not p.get("url"):
            raise CropDataError(f"{cid}: sourced parameter '{k}' needs a url")


def validate(doc: dict[str, Any]) -> list[dict[str, Any]]:
    crops = doc.get("crops")
    if not isinstance(crops, list) or not crops:
        raise CropDataError("crops.json has no crops")
    ids = [c.get("id") for c in crops]
    if len(ids) != len(set(ids)):
        raise CropDataError("duplicate crop ids")
    for c in crops:
        validate_crop(c)
    return crops


@lru_cache(maxsize=1)
def load_crops(path: str | None = None) -> tuple[dict[str, Any], ...]:
    doc = json.loads(Path(path or DATA / "crops.json").read_text(encoding="utf-8"))
    return tuple(validate(doc))


def crop_by_id(cid: str) -> dict[str, Any] | None:
    return next((c for c in load_crops() if c["id"] == cid), None)


def heuristic_params(c: dict[str, Any]) -> list[str]:
    return sorted(k for k, p in c["provenance"].items() if p["status"] == "heuristic")
