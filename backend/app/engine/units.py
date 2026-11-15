# AI-assisted: written with an AI coding assistant (see README, "AI tools used").
"""Unit and currency conversions in one place. Pure functions."""
from __future__ import annotations

HA_TO_ACRE = 2.4710538146717
KG_PER_LB = 0.45359237
# US bushel weights (lb/bushel) for the grains where the figure is a standard commercial weight.
BUSHEL_LB = {"maize": 56.0, "wheat": 60.0, "soybean": 60.0, "sorghum": 56.0}


def ha_to_acre(x: float) -> float: return x * HA_TO_ACRE
def acre_to_ha(x: float) -> float: return x / HA_TO_ACRE
def kg_to_t(x: float) -> float: return x / 1000.0
def t_to_kg(x: float) -> float: return x * 1000.0
def kg_to_lb(x: float) -> float: return x / KG_PER_LB
def lb_to_kg(x: float) -> float: return x * KG_PER_LB
def mm_to_in(x: float) -> float: return x / 25.4
def in_to_mm(x: float) -> float: return x * 25.4
def c_to_f(x: float) -> float: return x * 9 / 5 + 32
def f_to_c(x: float) -> float: return (x - 32) * 5 / 9


def bushel_kg(crop_id: str) -> float:
    if crop_id not in BUSHEL_LB:
        raise ValueError(f"No standard bushel weight for '{crop_id}'")
    return BUSHEL_LB[crop_id] * KG_PER_LB


def t_per_ha_to_bu_per_acre(t_ha: float, crop_id: str) -> float:
    return t_per_ha_to_kg(t_ha) / bushel_kg(crop_id) / HA_TO_ACRE


def t_per_ha_to_kg(t_ha: float) -> float: return t_ha * 1000.0


def convert_currency(amount: float, rate: float) -> float:
    """Multiply by a user-visible, dated rate (units of target currency per unit of source)."""
    if rate <= 0:
        raise ValueError("rate must be positive")
    return amount * rate
