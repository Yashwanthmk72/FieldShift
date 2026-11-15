# AI-assisted: written with an AI coding assistant.
"""Honest /api/health. Combines a short-lived active probe of every external provider with each circuit breaker's last success/latency.

status = "ok" when no provider is down; "degraded" when any provider is down or its circuit is open.
Providers that are not configured (e.g. no data.gov.in key) are reported as such and do NOT degrade the service."""
from __future__ import annotations

import time
from typing import Any

PROBE_TTL_S = 45


def _entry(pid: str, name: str, kind: str, probe: dict[str, Any] | None, breaker: dict[str, Any] | None) -> dict[str, Any]:
    probe = probe or {"state": "unknown"}
    b = breaker or {}
    state = probe["state"]
    if b.get("circuit") == "open" and state != "not_configured":
        state = "down"
    return {"id": pid, "name": name, "kind": kind, "state": state, "last_success": b.get("last_success"), "last_latency_ms": probe.get("latency_ms", b.get("last_latency_ms")),
            "last_error": b.get("last_error") if state == "down" else None, "circuit": b.get("circuit", "closed"), "consecutive_failures": b.get("consecutive_failures", 0), "detail": probe.get("detail")}


def build(core_probe: dict[str, dict[str, Any]], core_status: list[dict[str, Any]], price_probe: dict[str, dict[str, Any]], price_status: list[dict[str, Any]], version: str, crops_loaded: int, now: str) -> dict[str, Any]:
    cs = {s["provider"]: s for s in core_status}
    ps = {s["id"]: s for s in price_status}
    providers = [_entry("nasa_power", "NASA POWER (climate)", "data", core_probe.get("nasa_power"), cs.get("nasa_power")),
                 _entry("soilgrids", "ISRIC SoilGrids (soil)", "data", core_probe.get("soilgrids"), cs.get("soilgrids")),
                 _entry("imf_fred", "Price source: IMF commodity prices via FRED (monthly)", "price", price_probe.get("imf_fred"), ps.get("imf_fred")),
                 _entry("agmarknet", "Price source: Agmarknet India mandi (daily)", "price", price_probe.get("agmarknet"), ps.get("agmarknet")),
                 _entry("frankfurter", "Exchange rates: ECB via Frankfurter (daily)", "fx", price_probe.get("frankfurter"), ps.get("frankfurter"))]
    down = [p["id"] for p in providers if p["state"] == "down"]
    return {"status": "degraded" if down else "ok", "service": "FieldShift API", "version": version, "checked_at": now, "crops_loaded": crops_loaded, "degraded_providers": down, "providers": providers,
            "note": "Providers are probed live and cached for 45 s. 'not_configured' means a key is missing and the feature shows 'no data'. Status does not cover the browser map tiles."}


async def collect(ctx, version: str, crops_loaded: int, now: str, clock=time.time) -> dict[str, Any]:
    cache = getattr(ctx, "health_cache", None)
    if cache is not None and cache.get("value") is not None and clock() - cache["at"] < PROBE_TTL_S:
        return cache["value"]
    import asyncio
    core, prices = await asyncio.gather(ctx.providers.probe(), ctx.prices.probe())
    out = build(core, ctx.providers.status(), prices, ctx.prices.status(), version, crops_loaded, now)
    if cache is not None:
        cache["value"], cache["at"] = out, clock()
    return out
