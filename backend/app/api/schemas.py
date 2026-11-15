# AI-assisted: written with an AI coding assistant (see README, "AI tools used").
"""Pydantic request models. Every field has a size cap (audit defect D2)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from ..engine.finance import COST_CATEGORIES

ProvTag = Literal["measured/observed", "modelled", "user-entered", "assumption"]
CropId = Field(min_length=1, max_length=40, pattern=r"^[a-z0-9_-]+$")


class FarmIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    geometry: dict[str, Any] | None = None
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    area_ha: float | None = Field(default=None, gt=0, le=1_000_000)
    soil: dict[str, Any] = Field(default_factory=dict)
    priorities: dict[str, float] = Field(default_factory=dict)
    notes: str = Field(default="", max_length=1000)
    previous_crops: list[str] = Field(default_factory=list, max_length=12)
    analysis: dict[str, Any] | None = None
    done_actions: list[str] = Field(default_factory=list, max_length=200)


class AnalyzeIn(BaseModel):
    geometry: dict[str, Any]
    priorities: dict[str, float] = Field(default_factory=lambda: {"resilience": .34, "profit": 0, "soil": .33, "water": .33})
    previous_crops: list[str] = Field(default_factory=list, max_length=12)
    seasons: int = Field(default=4, ge=2, le=8)
    margins: dict[str, float] = Field(default_factory=dict, max_length=40)  # user's risk-adjusted margin per ha by crop id; enables the profit priority


class RecommendIn(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    soil: dict[str, Any] = Field(default_factory=dict)
    priorities: dict[str, float] = Field(default_factory=lambda: {"resilience": .3, "profit": .2, "soil": .25, "water": .25})
    previous_crops: list[str] = Field(default_factory=list, max_length=12)
    margins: dict[str, float] = Field(default_factory=dict, max_length=40)


class SettingsIn(BaseModel):
    data: dict[str, Any]


class ExplainIn(BaseModel):
    """v0.4 sent an uncapped client-built `context`. Now the server recomputes the facts from coordinates."""
    crop: str = Field(max_length=100)
    question: str = Field(default="Explain this result.", max_length=500)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    context: dict[str, Any] | None = Field(default=None, description="Deprecated; ignored.")

    @field_validator("context")
    @classmethod
    def _cap(cls, v):
        if v is not None and len(str(v)) > 3500:
            raise ValueError("context too large")
        return v


class RegisterIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=1, max_length=128)


class LoginIn(RegisterIn):
    pass


class DeleteAccountIn(BaseModel):
    password: str = Field(min_length=1, max_length=128)


class PlanIn(BaseModel):
    crop_id: str = CropId
    farm_id: int | None = None
    area_ha: float = Field(default=1.0, gt=0, le=1_000_000)
    yield_t_ha: float | None = Field(default=None, ge=0, le=1000)
    price_per_t: float | None = Field(default=None, ge=0, le=1e9)
    costs: dict[str, float | None] = Field(default_factory=dict)
    ranges: dict[str, float] | None = None
    currency: str = Field(default="USD", max_length=3, pattern=r"^[A-Z]{3}$")
    provenance: dict[str, ProvTag] = Field(default_factory=dict, max_length=20)
    notes: str = Field(default="", max_length=500)

    @field_validator("costs")
    @classmethod
    def _costs(cls, v):
        for k, x in v.items():
            if k not in COST_CATEGORIES:
                raise ValueError(f"unknown cost category {k}")
            if x is not None and not 0 <= x <= 1e9:
                raise ValueError("cost out of range")
        return v

    @field_validator("ranges")
    @classmethod
    def _ranges(cls, v):
        if v is not None:
            for k, x in v.items():
                if k not in ("yield", "price", "cost") or not 0 <= x <= 0.9:
                    raise ValueError("ranges: yield/price/cost fractions between 0 and 0.9")
        return v


class IrrigationIn(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    crop_id: str = CropId
    sowing_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    method: Literal["drip", "sprinkler", "furrow", "rainfed"] = "drip"
    sand_pct: float | None = Field(default=None, ge=0, le=100)
    clay_pct: float | None = Field(default=None, ge=0, le=100)
    soc_g_kg: float | None = Field(default=None, ge=0, le=600)
    root_depth_m: float = Field(default=0.6, ge=0.1, le=3)
    depletion_fraction: float = Field(default=0.5, ge=0.1, le=0.9)
    max_mm_per_week: float | None = Field(default=None, gt=0, le=500)


class RiskIn(BaseModel):
    crop_id: str = CropId
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class GrossValueIn(BaseModel):
    crop_id: str = CropId
    country: str = Field(default="WORLD", min_length=2, max_length=5, pattern=r"^[A-Za-z]+$")
    area_ha: float = Field(gt=0, le=1_000_000)
    yield_t_ha: float = Field(gt=0, le=200)  # entered by the user; FieldShift has no yield data
    currency: str = Field(default="USD", min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$")
