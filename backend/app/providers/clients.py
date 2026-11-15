# AI-assisted: written with an AI coding assistant (see README, "AI tools used").
"""Concrete provider clients. Each returns the common envelope and NEVER raises: failures become 'unavailable' results."""
from __future__ import annotations

import asyncio
import time
from datetime import date, timedelta
from typing import Any

from . import parsers
from .base import CircuitBreaker, TTLCache, fetch_json, result, round_coord, unavailable

UA = {"User-Agent": "FieldShift/0.6 (decision-support; contact via project repository)"}


class Providers:
    def __init__(self, cache: TTLCache | None = None):
        self.cache = cache or TTLCache()
        self.breakers = {n: CircuitBreaker() for n in ("nasa_power", "soilgrids", "open_meteo", "nominatim")}
        self.breakers["wikimedia"] = CircuitBreaker(threshold=15, cooldown=15.0)  # photos are optional: tolerate bursts, recover fast
        self._nominatim_last = 0.0
        self._nominatim_lock = asyncio.Lock()

    async def _cached(self, key: str, ttl: int, source: str, kind: str, producer):
        if (hit := self.cache.get(key)) is not None:
            return hit
        try:
            res = await producer()
        except Exception as exc:
            return unavailable(source, str(exc)[:80], kind)  # failures are not cached long: retry soon via breaker
        return self.cache.set(key, res, ttl)

    async def nasa_daily(self, lat: float, lon: float) -> dict[str, Any]:
        la, lo = round_coord(lat, 0.5), round_coord(lon, 0.5)  # POWER grid is ~0.5 degree
        async def go():
            end = date.today() - timedelta(days=3)
            params = {"parameters": "T2M,PRECTOTCORR,GWETROOT,ALLSKY_SFC_SW_DWN", "community": "AG", "longitude": lon, "latitude": lat, "start": (end - timedelta(days=13)).strftime("%Y%m%d"), "end": end.strftime("%Y%m%d"), "format": "JSON", "time-standard": "UTC"}
            raw = await fetch_json(self.breakers["nasa_power"], "https://power.larc.nasa.gov/api/temporal/daily/point", params)
            return result("NASA POWER daily", parsers.parse_power_daily(raw), "Global, ~0.5 degree grid; near-real-time, lags a few days", 3600, kind="observed", url="https://power.larc.nasa.gov/")
        return await self._cached(f"power:{la}:{lo}", 3600, "NASA POWER daily", "observed", go)

    async def nasa_climatology(self, lat: float, lon: float) -> dict[str, Any]:
        la, lo = round_coord(lat, 0.5), round_coord(lon, 0.5)
        async def go():
            params = {"parameters": "T2M,PRECTOTCORR,ALLSKY_SFC_SW_DWN", "community": "AG", "longitude": lon, "latitude": lat, "format": "JSON"}
            raw = await fetch_json(self.breakers["nasa_power"], "https://power.larc.nasa.gov/api/temporal/climatology/point", params)
            return result("NASA POWER climatology", parsers.parse_power_climatology(raw), "Global, ~0.5 degree grid; long-term monthly normals (reference period as defined in NASA POWER documentation)", 7 * 86400, kind="climatology", url="https://power.larc.nasa.gov/")
        return await self._cached(f"clim:{la}:{lo}", 7 * 86400, "NASA POWER climatology", "climatology", go)

    async def nasa_range(self, lat: float, lon: float, start: date, end: date) -> dict[str, Any]:
        """Daily NASA POWER values for a date range (max ~2 years), for the climate charts."""
        la, lo = round_coord(lat, 0.5), round_coord(lon, 0.5)
        async def go():
            params = {"parameters": "T2M,PRECTOTCORR,ALLSKY_SFC_SW_DWN", "community": "AG", "longitude": lon, "latitude": lat, "start": start.strftime("%Y%m%d"), "end": end.strftime("%Y%m%d"), "format": "JSON", "time-standard": "UTC"}
            raw = await fetch_json(self.breakers["nasa_power"], "https://power.larc.nasa.gov/api/temporal/daily/point", params, timeout=20)
            return result("NASA POWER daily", parsers.parse_power_range(raw), "Global, ~0.5 degree grid; near-real-time, lags a few days", 3600, kind="observed", url="https://power.larc.nasa.gov/")
        return await self._cached(f"powerr:{la}:{lo}:{start}:{end}", 3600, "NASA POWER daily", "observed", go)

    async def probe(self) -> dict[str, dict[str, Any]]:
        """Tiny live request to NASA POWER and SoilGrids for /api/health. Never raises."""
        async def one(name: str, url: str, params: Any):
            t0 = time.perf_counter()
            try:
                await fetch_json(self.breakers[name], url, params, retries=0, timeout=6.0)
                return name, {"state": "up", "latency_ms": round((time.perf_counter() - t0) * 1000, 1)}
            except Exception as exc:
                return name, {"state": "down", "detail": str(exc)[:80], "latency_ms": round((time.perf_counter() - t0) * 1000, 1)}
        end = date.today() - timedelta(days=5)
        power = {"parameters": "T2M", "community": "AG", "longitude": 77.6, "latitude": 13.0, "start": end.strftime("%Y%m%d"), "end": end.strftime("%Y%m%d"), "format": "JSON"}
        soil = [("lon", 77.6), ("lat", 13.0), ("property", "phh2o"), ("depth", "0-5cm"), ("value", "mean")]
        return dict(await asyncio.gather(one("nasa_power", "https://power.larc.nasa.gov/api/temporal/daily/point", power), one("soilgrids", "https://rest.isric.org/soilgrids/v2.0/properties/query", soil)))

    async def soil(self, lat: float, lon: float) -> dict[str, Any]:
        la, lo = round_coord(lat, 0.01), round_coord(lon, 0.01)
        async def go():
            params = [("lon", lon), ("lat", lat)] + [("property", p) for p in ("phh2o", "soc", "clay", "sand", "silt")] + [("depth", d) for d in parsers.SOIL_DEPTH_WEIGHTS] + [("value", "mean")]
            raw = await fetch_json(self.breakers["soilgrids"], "https://rest.isric.org/soilgrids/v2.0/properties/query", params, timeout=12)
            vals = parsers.parse_soilgrids(raw)
            if not vals:
                return result("ISRIC SoilGrids 2.0", None, "No data at this point (SoilGrids has gaps over water, ice and some built-up areas)", 3600, error="no soil values at this location (coverage gap)", kind="modelled")
            return result("ISRIC SoilGrids 2.0", vals, "Global land, 250 m, modelled; gaps over water/ice/some urban areas", 86400, kind="modelled", url="https://rest.isric.org/soilgrids/v2.0/docs")
        return await self._cached(f"soil:{la}:{lo}", 86400, "ISRIC SoilGrids 2.0", "modelled", go)

    async def forecast(self, lat: float, lon: float) -> dict[str, Any]:
        la, lo = round_coord(lat), round_coord(lon)
        async def go():
            params = {"latitude": lat, "longitude": lon, "timezone": "auto", "forecast_days": 16, "past_days": 3,
                      "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,et0_fao_evapotranspiration", "hourly": "temperature_2m,relative_humidity_2m",
                      "current": "temperature_2m,relative_humidity_2m,precipitation"}
            raw = await fetch_json(self.breakers["open_meteo"], "https://api.open-meteo.com/v1/forecast", params)
            return result("Open-Meteo forecast", parsers.parse_open_meteo(raw), "Global model forecast, up to 16 days; skill falls with lead time", 1800, kind="forecast", url="https://open-meteo.com/")
        return await self._cached(f"om:{la}:{lo}", 1800, "Open-Meteo forecast", "forecast", go)

    async def geocode(self, query: str) -> dict[str, Any]:
        key = f"geo:{query.strip().lower()[:100]}"
        async def go():
            async with self._nominatim_lock:  # Nominatim usage policy: at most 1 request per second
                wait = 1.05 - (time.time() - self._nominatim_last)
                if wait > 0:
                    await asyncio.sleep(wait)
                self._nominatim_last = time.time()
            raw = await fetch_json(self.breakers["nominatim"], "https://nominatim.openstreetmap.org/search", {"q": query, "format": "jsonv2", "limit": 5, "addressdetails": 1}, headers=UA)
            return result("OpenStreetMap Nominatim", parsers.parse_nominatim(raw), "Global place search; data (c) OpenStreetMap contributors (ODbL)", 86400, kind="observed", url="https://nominatim.org/")
        return await self._cached(key, 86400, "OpenStreetMap Nominatim", "observed", go)

    def status(self) -> list[dict[str, Any]]:
        return [{"provider": n, "state": b.state, "last_success": b.last_success, "last_latency_ms": b.last_latency_ms, "last_error": b.last_error, "consecutive_failures": b.failures} for n, b in self.breakers.items()]
