# AI-assisted: written with an AI coding assistant.
"""Health, market prices (REST + SSE), climate series, credits and per-crop risks."""
from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from .. import health, services
from ..config import VERSION
from ..engine import climate_series, credits, risks
from ..engine.crops import crop_by_id, load_crops
from ..providers import base, prices
from .deps import Ctx, get_ctx
from .schemas import GrossValueIn, RiskIn

router = APIRouter()
LAT = Query(ge=-90, le=90)
LON = Query(ge=-180, le=180)


def _now() -> str:
    return base.now_iso()


@router.get("/api/health")
@router.get("/api/v1/health")
async def api_health(ctx: Ctx = Depends(get_ctx)):
    """Per-provider status with last success and latency. status is 'degraded' when any provider is down."""
    return await health.collect(ctx, VERSION, len(load_crops()), _now())


# ---------------- market ----------------
@router.get("/api/v1/market/meta")
def market_meta(ctx: Ctx = Depends(get_ctx)):
    return {"countries": [{"code": k, **v} for k, v in prices.COUNTRIES.items()], "providers": ctx.prices.providers(), "units": list(prices.UNIT_LABELS), "currencies": ["USD", "EUR", "INR", "BRL", "IDR", "MXN", "GBP", "JPY", "CNY", "ZAR"],
            "crops": [{"id": c["id"], "name": c["name"], "world": bool(ctx.prices.sources_for(c["id"], "WORLD")), "india": bool(ctx.prices.sources_for(c["id"], "IN"))} for c in load_crops()],
            "freshness_note": "Nothing here is real-time. Each price shows its own source, as-of date and cadence (daily or monthly). Where no source exists the board says 'no data'.",
            "links": {"fao_fpma": "https://fpma.fao.org/giews/fpmat4/#/dashboard/home"}}


@router.get("/api/v1/market/board")
async def market_board(country: str = Query(default="WORLD", min_length=2, max_length=5), ctx: Ctx = Depends(get_ctx)):
    return prices.slim(await ctx.prices.board(country))


@router.get("/api/v1/market/series")
async def market_series(crop: str = Query(min_length=1, max_length=40, pattern=r"^[a-z0-9_-]+$"), country: str = Query(default="WORLD", min_length=2, max_length=5),
                        currency: str | None = Query(default=None, min_length=3, max_length=3), unit: str | None = None, ctx: Ctx = Depends(get_ctx)):
    if not crop_by_id(crop):
        raise HTTPException(404, "Crop not found")
    try:
        return await ctx.prices.priced(crop, country, currency, unit)
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.get("/api/v1/market/fx")
async def market_fx(ctx: Ctx = Depends(get_ctx)):
    return await ctx.prices.fx()


@router.get("/api/v1/market/stream")
async def market_stream(country: str = Query(default="WORLD", min_length=2, max_length=5), interval: int = Query(default=60, ge=15, le=600), ctx: Ctx = Depends(get_ctx)):
    """Server-Sent Events. A 'prices' event is sent first and again only when cached data changes; 'tick' events are keep-alives."""
    return StreamingResponse(prices.stream(ctx.prices, country, float(interval)), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"})


@router.post("/api/v1/market/gross-value")
async def market_gross_value(body: GrossValueIn, ctx: Ctx = Depends(get_ctx)):
    if not crop_by_id(body.crop_id):
        raise HTTPException(404, "Crop not found")
    series = await ctx.prices.series(body.crop_id, body.country)
    fx = await ctx.prices.fx() if not series.get("no_data") and series["currency"] != body.currency.upper() else {}
    return prices.gross_value(series, body.area_ha, body.yield_t_ha, body.currency.upper(), lambda v, a, b: ctx.prices.convert(v, a, b, fx))


# ---------------- climate ----------------
@router.get("/api/v1/climate/series")
async def climate_series_route(lat: float = LAT, lon: float = LON, start: date | None = None, end: date | None = None, ctx: Ctx = Depends(get_ctx)):
    try:
        s, e = climate_series.clamp_range(start, end, datetime.now(timezone.utc).date())
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    import asyncio
    daily, norm = await asyncio.gather(ctx.providers.nasa_range(lat, lon, s, e), ctx.providers.nasa_climatology(lat, lon))
    if not daily["ok"]:
        raise HTTPException(502, daily["error"])
    out = climate_series.build(daily["data"], norm["data"] if norm["ok"] else None)
    return {**out, "range": {"start": s.isoformat(), "end": e.isoformat()}, "source": daily["source"], "fetched_at": daily["fetched_at"], "coverage": daily["coverage"],
            "normals_source": norm["source"] if norm["ok"] else None, "normals_error": None if norm["ok"] else norm["error"], "units": {"temperature_c": "°C", "rain_mm": "mm/day", "solar_mj_m2": "MJ/m²/day"},
            "location": {"latitude": lat, "longitude": lon, "grid": "NASA POWER ~0.5° cell"}}


# ---------------- credits & risks ----------------
@router.get("/api/v1/credits")
def credits_route():
    return credits.load()


@router.post("/api/v1/risks")
async def crop_risks(body: RiskIn, ctx: Ctx = Depends(get_ctx)):
    crop = crop_by_id(body.crop_id)
    if not crop:
        raise HTTPException(404, "Crop not found")
    import asyncio
    norm, soil = await asyncio.gather(ctx.providers.nasa_climatology(body.latitude, body.longitude), ctx.providers.soil(body.latitude, body.longitude))
    soil_vals = services.soil_summary_from_layers([soil["data"]]) if soil["ok"] else {}
    out = risks.build(crop, norm["data"] if norm["ok"] else None, soil_vals, body.latitude, 1 if soil["ok"] else 0)
    out["provenance"] = [services._prov(norm, "climate normals"), services._prov(soil, "soil")]
    return out
