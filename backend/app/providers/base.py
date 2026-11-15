# AI-assisted: written with an AI coding assistant (see README, "AI tools used").
"""Provider plumbing: result envelope, TTL cache, circuit breaker, retrying fetch (httpx imported lazily)."""
from __future__ import annotations

import asyncio
import random
import time
from datetime import datetime, timezone
from typing import Any, Callable

TIMEOUT_S = 8.0
RETRIES = 2


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def result(source: str, data: Any = None, coverage: str = "", ttl: int = 0, error: str | None = None, kind: str = "observed", url: str = "") -> dict[str, Any]:
    """Every provider response uses this envelope. `kind` is observed | climatology | forecast | modelled."""
    return {"ok": error is None and data is not None, "data": data, "source": source, "kind": kind, "fetched_at": now_iso(), "coverage": coverage, "ttl": ttl, "error": error, "source_url": url}


def unavailable(source: str, why: str, kind: str = "observed") -> dict[str, Any]:
    return result(source, None, error=f"{source} unavailable ({why}) at {now_iso()}", kind=kind)


class TTLCache:
    def __init__(self, clock: Callable[[], float] = time.time, max_items: int = 2000):
        self.clock, self.max, self.items = clock, max_items, {}

    def get(self, key: str) -> Any | None:
        e = self.items.get(key)
        return e[1] if e and e[0] > self.clock() else None

    def set(self, key: str, value: Any, ttl: int) -> Any:
        if len(self.items) >= self.max:
            now = self.clock()
            for k in [k for k, v in self.items.items() if v[0] <= now][:self.max // 4] or list(self.items)[:self.max // 4]:
                self.items.pop(k, None)
        self.items[key] = (self.clock() + ttl, value)
        return value


class CircuitBreaker:
    """Opens after `threshold` consecutive failures; half-opens after `cooldown` seconds."""

    def __init__(self, threshold: int = 4, cooldown: float = 60.0, clock: Callable[[], float] = time.time):
        self.threshold, self.cooldown, self.clock = threshold, cooldown, clock
        self.failures, self.opened_at = 0, None
        self.last_success: str | None = None
        self.last_success_epoch: float | None = None
        self.last_latency_ms: float | None = None
        self.last_error: str | None = None

    def allow(self) -> bool:
        if self.opened_at is None:
            return True
        if self.clock() - self.opened_at >= self.cooldown:
            return True  # half-open: let one attempt through
        return False

    def success(self, latency_ms: float | None = None) -> None:
        self.failures, self.opened_at, self.last_success = 0, None, now_iso()
        self.last_success_epoch = self.clock()
        if latency_ms is not None:
            self.last_latency_ms = round(latency_ms, 1)

    def failure(self, why: str) -> None:
        self.failures += 1
        self.last_error = f"{why} at {now_iso()}"
        if self.failures >= self.threshold:
            self.opened_at = self.clock()

    @property
    def state(self) -> str:
        return "open" if self.opened_at is not None and self.clock() - self.opened_at < self.cooldown else "closed"


def round_coord(v: float, step: float = 0.1) -> float:
    """Cache key rounding so nearby fields share data (default 0.1 degree)."""
    return round(round(v / step) * step, 4)


async def fetch_json(breaker: CircuitBreaker, url: str, params: Any = None, headers: dict[str, str] | None = None, timeout: float = TIMEOUT_S,
                     retries: int = RETRIES, sleep=asyncio.sleep) -> Any:
    """GET JSON with timeout, jittered-backoff retries and a circuit breaker. Raises RuntimeError with a short reason."""
    import httpx  # lazy so the engine and tests do not need the web stack

    if not breaker.allow():
        raise RuntimeError("circuit open after repeated failures")
    last = "unknown error"
    for attempt in range(retries + 1):
        try:
            t0 = time.perf_counter()
            async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
                r = await client.get(url, params=params)
            if r.status_code == 429:
                last = "rate limited (429)"
            elif r.status_code >= 500:
                last = f"server error {r.status_code}"
            else:
                r.raise_for_status()
                try:
                    data = r.json()
                except ValueError as exc:
                    raise RuntimeError("malformed JSON") from exc
                breaker.success((time.perf_counter() - t0) * 1000)
                return data
        except RuntimeError:
            breaker.failure("malformed JSON")
            raise
        except Exception as exc:  # timeouts, DNS, 4xx
            last = type(exc).__name__
            if getattr(getattr(exc, "response", None), "status_code", 500) < 500 and getattr(exc, "response", None) is not None:
                break  # a 4xx will not improve with retries
        if attempt < retries:
            await sleep(min(4.0, 0.5 * 2 ** attempt) * (0.5 + random.random() / 2))
    breaker.failure(last)
    raise RuntimeError(last)


async def fetch_text(breaker: CircuitBreaker, url: str, params: Any = None, headers: dict[str, str] | None = None, timeout: float = TIMEOUT_S,
                     retries: int = RETRIES, sleep=asyncio.sleep) -> str:
    """GET text (e.g. CSV) with the same timeout / retry / circuit-breaker behaviour as fetch_json. Raises RuntimeError with a short reason."""
    import httpx

    if not breaker.allow():
        raise RuntimeError("circuit open after repeated failures")
    last = "unknown error"
    for attempt in range(retries + 1):
        try:
            t0 = time.perf_counter()
            async with httpx.AsyncClient(timeout=timeout, headers=headers, follow_redirects=True) as client:
                r = await client.get(url, params=params)
            if r.status_code == 429:
                last = "rate limited (429)"
            elif r.status_code >= 500:
                last = f"server error {r.status_code}"
            else:
                r.raise_for_status()
                breaker.success((time.perf_counter() - t0) * 1000)
                return r.text
        except Exception as exc:  # timeouts, DNS, 4xx
            last = type(exc).__name__
            resp = getattr(exc, "response", None)
            if resp is not None and getattr(resp, "status_code", 500) < 500:
                break  # a 4xx will not improve with retries
        if attempt < retries:
            await sleep(min(4.0, 0.5 * 2 ** attempt) * (0.5 + random.random() / 2))
    breaker.failure(last)
    raise RuntimeError(last)
