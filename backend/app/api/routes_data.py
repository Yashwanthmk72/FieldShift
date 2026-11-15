# AI-assisted: written with an AI coding assistant (see README, "AI tools used").
"""Fields, analysis, crops, weather, soil, pests, irrigation, finance, sources, assistant."""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response

from .. import assistant, reports, services
from ..db.repo import Conflict, NotFound, TooLarge
from ..engine import content, finance, geo, scoring
from ..engine.crops import crop_by_id, load_crops
from ..providers import clients
from .deps import Ctx, get_ctx, identity, limiter_key
from .schemas import AnalyzeIn, ExplainIn, FarmIn, IrrigationIn, PlanIn, RecommendIn, SettingsIn

router = APIRouter()
LAT = Query(ge=-90, le=90)
LON = Query(ge=-180, le=180)
DATA = Path(__file__).resolve().parents[1] / "data"


def _guard(fn, *a, **k):
    try:
        return fn(*a, **k)
    except NotFound as e:
        raise HTTPException(404, str(e))
    except Conflict as e:
        raise HTTPException(409, str(e))
    except TooLarge as e:
        raise HTTPException(413, str(e))


# ---------- health / meta ----------
@router.get("/healthz")
def healthz(): return {"status": "ok"}


@router.get("/readyz")
def readyz(ctx: Ctx = Depends(get_ctx)):
    try:
        with ctx.db.connect() as con:
            con.execute("SELECT 1")
    except Exception:
        raise HTTPException(503, "database unavailable")
    try:
        n = len(load_crops())
    except Exception:
        raise HTTPException(503, "crop data invalid")
    return {"status": "ready", "crops_loaded": n}


@router.get("/api/crops")
@router.get("/api/v1/crops")
def crops(): return list(load_crops())


@router.get("/api/v1/sources")
def sources(ctx: Ctx = Depends(get_ctx)):
    return {"sources": json.loads((DATA / "sources.json").read_text(encoding="utf-8")), "status": ctx.providers.status()}


# ---------- fields (legacy /api/farms and /api/v1/fields share handlers) ----------
def _farm_routes(base: str) -> None:
    @router.get(base)
    def list_(request: Request, ctx: Ctx = Depends(get_ctx)):
        return ctx.db.list_farms(identity(request)["owner"])

    @router.post(base)
    def create(farm: FarmIn, request: Request, ctx: Ctx = Depends(get_ctx)):
        data = farm.model_dump()
        fid = _guard(ctx.db.create_farm, identity(request)["owner"], farm.name, data)
        return {"id": fid, **data, "saved": True}

    @router.get(base + "/{farm_id}")
    def get(farm_id: int, request: Request, ctx: Ctx = Depends(get_ctx)):
        return _guard(ctx.db.get_farm, identity(request)["owner"], farm_id)

    @router.put(base + "/{farm_id}")
    def update(farm_id: int, farm: FarmIn, request: Request, ctx: Ctx = Depends(get_ctx)):
        data = farm.model_dump()
        _guard(ctx.db.update_farm, identity(request)["owner"], farm_id, farm.name, data)
        return {"id": farm_id, **data, "saved": True}

    @router.delete(base + "/{farm_id}")
    def delete(farm_id: int, request: Request, ctx: Ctx = Depends(get_ctx)):
        _guard(ctx.db.delete_farm, identity(request)["owner"], farm_id)
        return {"deleted": True}


_farm_routes("/api/farms")
_farm_routes("/api/v1/fields")


@router.get("/api/settings")
@router.get("/api/v1/settings")
def get_settings(request: Request, ctx: Ctx = Depends(get_ctx)): return ctx.db.get_settings(identity(request)["owner"])


@router.put("/api/settings")
@router.put("/api/v1/settings")
def put_settings(body: SettingsIn, request: Request, ctx: Ctx = Depends(get_ctx)):
    _guard(ctx.db.put_settings, identity(request)["owner"], body.data)
    return body.data


# ---------- analysis ----------
@router.get("/api/climate")
async def climate(lat: float = LAT, lon: float = LON, ctx: Ctx = Depends(get_ctx)):
    res = await ctx.providers.nasa_daily(lat, lon)
    if not res["ok"]:
        raise HTTPException(502, res["error"])
    return {**res["data"], "source": res["source"], "fetched_at": res["fetched_at"], "kind": res["kind"], "coverage": res["coverage"]}


@router.get("/api/soil")
@router.get("/api/v1/soil")
async def soil(lat: float = LAT, lon: float = LON, ctx: Ctx = Depends(get_ctx)):
    res = await ctx.providers.soil(lat, lon)
    return {"source": res["source"], "values": res["data"] or {}, "kind": res["kind"], "fetched_at": res["fetched_at"], "coverage": res["coverage"], "error": res["error"],
            "note": "Modelled soil data cannot replace a laboratory test."}


@router.post("/api/recommendations")
@router.post("/api/v1/recommendations")
async def recommendations(body: RecommendIn, ctx: Ctx = Depends(get_ctx)):
    return await services.recommend(ctx.providers, body.latitude, body.longitude, body.soil, body.priorities, body.previous_crops, body.margins)


@router.get("/api/v1/soil-health")
async def soil_health(lat: float = LAT, lon: float = LON, crop_id: str | None = Query(default=None, pattern=r"^[a-z0-9_-]{1,40}$"),
                      area_ha: float | None = Query(default=None, gt=0, le=1_000_000), ctx: Ctx = Depends(get_ctx)):
    if crop_id and not crop_by_id(crop_id):
        raise HTTPException(404, "Crop not found")
    return await services.soil_health_report(ctx.providers, lat, lon, crop_id, area_ha)


@router.post("/api/rotation")
async def rotation(body: RecommendIn, ctx: Ctx = Depends(get_ctx)):
    res = await services.recommend(ctx.providers, body.latitude, body.longitude, body.soil, body.priorities, body.previous_crops, body.margins)
    from ..engine import rotation as rot
    scores = {r["crop"]["id"]: r["score"] for r in res["ranked"]}
    return {"rotation": rot.build_rotation(list(load_crops()), scores, scoring.normalize_priorities(body.priorities), body.previous_crops, 4, body.latitude),
            "note": "Illustrative sequence; check local planting windows, disease history, seed availability and market access."}


@router.post("/api/analyze")
@router.post("/api/v1/analysis")
async def analyze(body: AnalyzeIn, ctx: Ctx = Depends(get_ctx)):
    try:
        return await services.analyze(ctx.providers, body.geometry, body.priorities, body.previous_crops, body.seasons, body.margins)
    except geo.GeometryError as e:
        raise HTTPException(422, str(e))


@router.get("/api/crop-info/{crop_id}")
@router.get("/api/v1/crops/{crop_id}")
async def crop_info(crop_id: str, lat: float = 0.0, light: bool = False, ctx: Ctx = Depends(get_ctx)):
    import asyncio
    from ..providers.media import wiki_images
    crop = crop_by_id(crop_id)
    if not crop:
        raise HTTPException(404, "Crop not found")
    lat = max(-90.0, min(90.0, lat))
    extra = content.crop_extra(crop_id, lat)
    hero, *stage_imgs = await asyncio.gather(wiki_images(ctx.providers, crop["image_query"], 1, 1000), *([] if light else [wiki_images(ctx.providers, f"{crop['name']} {s['term']}", 1, 640) for s in extra["stages"]]))
    for i, stage in enumerate(extra["stages"]):
        stage["image"] = stage_imgs[i][0] if i < len(stage_imgs) and stage_imgs[i] else None
    first = hero[0] if hero else None
    lic = first["license"] if first else None
    return {**crop, **extra, "image_url": first["url"] if first else None, "image_attribution_url": first["page"] if first else None, "image_license": lic, "image_author": first["author"] if first else None,
            "image_source": f"Wikimedia Commons · {lic or 'see file page for license'}" if first else "Image unavailable; crop details remain available.",
            "gallery": [s["image"] for s in extra["stages"] if s.get("image")], "heuristic_parameters": [k for k, p in crop["provenance"].items() if p["status"] == "heuristic"]}


@router.get("/api/media")
async def media(kind: str, key: str, limit: int = 1, ctx: Ctx = Depends(get_ctx)):
    from ..providers.media import wiki_images
    q = content.MEDIA_QUERIES.get((kind, key))
    if not q:
        raise HTTPException(404, "Unknown media key")
    return {"kind": kind, "key": key, "images": await wiki_images(ctx.providers, q, max(1, min(limit, 4)))}


# ---------- weather / pests / irrigation / geocode ----------
@router.get("/api/v1/weather")
async def weather(lat: float = LAT, lon: float = LON, ctx: Ctx = Depends(get_ctx)): return await services.weather(ctx.providers, lat, lon)


@router.get("/api/v1/pests")
async def pests(crop_id: str = Query(pattern=r"^[a-z0-9_-]{1,40}$"), lat: float = LAT, lon: float = LON, ctx: Ctx = Depends(get_ctx)):
    if not crop_by_id(crop_id):
        raise HTTPException(404, "Crop not found")
    out = await services.pest_outlook(ctx.providers, lat, lon, crop_id)
    out["known_issues"] = json.loads((DATA / "pests.json").read_text(encoding="utf-8")).get(crop_id, {})
    return out


@router.post("/api/v1/irrigation")
async def irrigation(body: IrrigationIn, ctx: Ctx = Depends(get_ctx)):
    try:
        sow = date.fromisoformat(body.sowing_date)
    except ValueError:
        raise HTTPException(422, "Invalid sowing date")
    try:
        return await services.irrigation_plan(ctx.providers, body.latitude, body.longitude, body.crop_id, sow, body.method, body.sand_pct, body.clay_pct, body.soc_g_kg,
                                              body.root_depth_m, body.depletion_fraction, body.max_mm_per_week)
    except KeyError:
        raise HTTPException(404, "Crop not found")


@router.get("/api/v1/geocode")
async def geocode(request: Request, q: str = Query(min_length=2, max_length=120), ctx: Ctx = Depends(get_ctx)):
    if not ctx.limiter.allow("geo:" + limiter_key(request)):
        raise HTTPException(429, "Too many searches. Try again shortly.")
    res = await ctx.providers.geocode(q)
    return {"results": res["data"] or [], "source": res["source"], "fetched_at": res["fetched_at"], "error": res["error"], "attribution": "© OpenStreetMap contributors"}


# ---------- finance ----------
def _stamp(prov: dict[str, str]) -> dict[str, Any]:
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    return {k: {"type": v, "recorded_at": now} for k, v in prov.items()}


@router.post("/api/v1/finance/evaluate")
def finance_evaluate(body: PlanIn):
    if not crop_by_id(body.crop_id):
        raise HTTPException(404, "Crop not found")
    costs = {k: body.costs.get(k) for k in finance.COST_CATEGORIES}
    return services.finance_report(body.crop_id, body.area_ha, body.yield_t_ha, body.price_per_t, costs, body.ranges, _stamp(body.provenance))


@router.get("/api/v1/finance/plans")
def plans_list(request: Request, farm_id: int | None = None, ctx: Ctx = Depends(get_ctx)): return ctx.db.list_plans(identity(request)["owner"], farm_id)


@router.post("/api/v1/finance/plans")
def plans_save(body: PlanIn, request: Request, plan_id: int | None = None, ctx: Ctx = Depends(get_ctx)):
    if not crop_by_id(body.crop_id):
        raise HTTPException(404, "Crop not found")
    data = body.model_dump(exclude={"crop_id", "farm_id"})
    data["provenance"] = _stamp(body.provenance)
    pid = _guard(ctx.db.save_plan, identity(request)["owner"], body.crop_id, data, body.farm_id, plan_id)
    return {"id": pid, "saved": True}


@router.delete("/api/v1/finance/plans/{plan_id}")
def plans_delete(plan_id: int, request: Request, ctx: Ctx = Depends(get_ctx)):
    _guard(ctx.db.delete_plan, identity(request)["owner"], plan_id)
    return {"deleted": True}


def _plans_for_export(request: Request, ctx: Ctx):
    plans = ctx.db.list_plans(identity(request)["owner"])
    for p in plans:
        p["provenance"] = {k: (v["type"] if isinstance(v, dict) else v) for k, v in p.get("provenance", {}).items()}
    return plans, {c["id"]: c["name"] for c in load_crops()}


@router.get("/api/v1/finance/export.csv")
def export_csv(request: Request, ctx: Ctx = Depends(get_ctx)):
    plans, names = _plans_for_export(request, ctx)
    return Response(finance.to_csv(reports.plan_rows(plans, names)), media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="fieldshift-finance.csv"'})


@router.get("/api/v1/finance/export.pdf")
def export_pdf(request: Request, ctx: Ctx = Depends(get_ctx)):
    plans, names = _plans_for_export(request, ctx)
    return Response(reports.pdf_report(plans, names), media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="fieldshift-finance.pdf"'})


# ---------- assistant ----------
@router.post("/api/assistant")
@router.post("/api/v1/assistant")
async def assistant_route(body: ExplainIn, request: Request, ctx: Ctx = Depends(get_ctx)):
    try:
        who = identity(request)
    except HTTPException:
        who = None  # v0.4 allowed anonymous use; keep that, but rate-limit by address
    key = limiter_key(request, who)
    if not ctx.limiter.allow("assist:" + key):
        raise HTTPException(429, "Field assistant limit reached. Try again in a few minutes.")
    if not ctx.budget.charge(key, body.question):
        raise HTTPException(429, "Daily assistant budget reached.")
    crop = next((c for c in load_crops() if c["id"] == body.crop.lower() or c["name"].lower() == body.crop.lower()), None)
    if crop is None:
        return {"answer": "I couldn't match that crop. Choose a crop card and I can explain its fit.", "mode": "automatic explanation", "evidence": [], "uncertainty": "", "follow_ups": []}
    if body.latitude is None or body.longitude is None:
        return {"answer": f"{crop['name']}: {crop['description']} Send the field location so I can explain its fit with current data.", "mode": "automatic explanation", "evidence": [f"crop-{crop['id']}"], "uncertainty": "No site data supplied.", "follow_ups": []}
    res = await services.recommend(ctx.providers, body.latitude, body.longitude, {}, {"resilience": .34, "soil": .33, "water": .33}, [])
    item = next(r for r in res["ranked"] if r["crop"]["id"] == crop["id"])
    return await assistant.answer(body.question, assistant.facts_from_result(item), ctx.kb, ctx.llm)
