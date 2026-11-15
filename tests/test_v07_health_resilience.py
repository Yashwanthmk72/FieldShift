# AI-assisted: written with an AI coding assistant.
"""/api/health logic and provider resilience (retries, timeouts, circuit breaker) against a scripted fake httpx. No network is used."""
import asyncio
import sys
import types

from app import health
from app.providers import base
from app.providers.base import CircuitBreaker


def run(c):
    return asyncio.run(c)


def up(ms=12.0):
    return {"state": "up", "latency_ms": ms}


def build(core=None, prices=None, core_status=None, price_status=None):
    core = core or {"nasa_power": up(), "soilgrids": up()}
    prices = prices or {"imf_fred": up(), "frankfurter": up(), "agmarknet": {"state": "not_configured", "detail": "key"}}
    return health.build(core, core_status or [], prices, price_status or [], "0.9.0", 27, "2026-11-14T00:00:00Z")


def test_health_ok_when_all_up_and_not_configured_does_not_degrade():
    h = build()
    assert h["status"] == "ok" and h["degraded_providers"] == [] and h["crops_loaded"] == 27
    states = {p["id"]: p["state"] for p in h["providers"]}
    assert states["agmarknet"] == "not_configured" and states["nasa_power"] == "up"
    assert {"nasa_power", "soilgrids"} <= set(states) and any(p["kind"] == "price" for p in h["providers"])


def test_health_degraded_when_any_provider_down_and_names_it():
    h = build(core={"nasa_power": {"state": "down", "detail": "Timeout", "latency_ms": 6000}, "soilgrids": up()})
    assert h["status"] == "degraded" and h["degraded_providers"] == ["nasa_power"]
    assert next(p for p in h["providers"] if p["id"] == "nasa_power")["detail"] == "Timeout"


def test_health_open_circuit_counts_as_down_even_if_probe_skipped():
    h = build(core_status=[{"provider": "soilgrids", "state": "open", "circuit": "open", "last_success": "2026-11-13T10:00:00Z", "last_error": "Timeout", "consecutive_failures": 4, "last_latency_ms": 90.0}])
    assert h["status"] == "degraded"
    e = next(p for p in h["providers"] if p["id"] == "soilgrids")
    assert e["circuit"] == "open" and e["last_success"] == "2026-11-13T10:00:00Z" and e["consecutive_failures"] == 4


def test_health_reports_last_success_and_latency_for_each_provider():
    h = build(core_status=[{"provider": "nasa_power", "circuit": "closed", "last_success": "2026-11-14T00:00:00Z", "consecutive_failures": 0}])
    e = next(p for p in h["providers"] if p["id"] == "nasa_power")
    assert e["last_success"] == "2026-11-14T00:00:00Z" and e["last_latency_ms"] == 12.0


def test_health_probe_results_are_cached_45_seconds():
    calls = {"n": 0}
    class P:
        async def probe(self):
            calls["n"] += 1
            return {"nasa_power": up(), "soilgrids": up()}
        def status(self): return []
    class Pr:
        async def probe(self): return {"imf_fred": up(), "frankfurter": up(), "agmarknet": {"state": "not_configured"}}
        def status(self): return []
    ctx = types.SimpleNamespace(providers=P(), prices=Pr(), health_cache={"value": None, "at": 0.0})
    t = [100.0]
    a = run(health.collect(ctx, "0.9.0", 27, "now", clock=lambda: t[0])); run(health.collect(ctx, "0.9.0", 27, "now", clock=lambda: t[0]))
    assert calls["n"] == 1
    t[0] += 50
    run(health.collect(ctx, "0.9.0", 27, "now", clock=lambda: t[0]))
    assert calls["n"] == 2 and a["status"] == "ok"


# ---------- resilience against a scripted fake httpx ----------
def fake_httpx(script):
    calls = []
    class Resp:
        def __init__(self, code, body):
            self.status_code, self.body = code, body
            self.text = body if isinstance(body, str) else ""
        def json(self): return self.body
        def raise_for_status(self):
            if self.status_code >= 400:
                e = RuntimeError(f"HTTP {self.status_code}"); e.response = self; raise e
    class Client:
        def __init__(self, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url, params=None):
            calls.append(url)
            item = script.pop(0)
            if isinstance(item, Exception):
                raise item
            return Resp(*item)
    m = types.ModuleType("httpx"); m.AsyncClient = Client
    return m, calls


async def nosleep(_):
    return None


def with_httpx(script, coro_fn):
    mod, calls = fake_httpx(script)
    old = sys.modules.get("httpx"); sys.modules["httpx"] = mod
    try:
        return run(coro_fn()), calls
    finally:
        sys.modules.pop("httpx") if old is None else sys.modules.__setitem__("httpx", old)


def attempt(fn, *a, **k):
    try:
        return fn(*a, **k), None
    except RuntimeError as e:
        return None, str(e)


def test_fetch_text_retries_server_errors_then_succeeds_and_records_latency():
    b = CircuitBreaker()
    async def go(): return await base.fetch_text(b, "https://x/csv", sleep=nosleep)
    out, calls = with_httpx([(500, ""), (503, ""), (200, "a,b\n1,2\n")], go)
    assert out == "a,b\n1,2\n" and len(calls) == 3 and b.failures == 0 and b.last_success and b.last_latency_ms is not None


def test_fetch_text_gives_up_after_retries_and_counts_one_breaker_failure():
    b = CircuitBreaker()
    async def go():
        try: await base.fetch_text(b, "https://x", sleep=nosleep)
        except RuntimeError as e: return str(e)
    out, calls = with_httpx([(500, ""), (500, ""), (500, "")], go)
    assert "server error 500" in out and len(calls) == 3 and b.failures == 1


def test_fetch_text_does_not_retry_client_errors_and_retries_timeouts():
    b = CircuitBreaker()
    async def go4():
        try: await base.fetch_text(b, "https://x", sleep=nosleep)
        except RuntimeError as e: return str(e)
    out, calls = with_httpx([(404, "")], go4)
    assert len(calls) == 1 and out
    async def got():
        return await base.fetch_text(b, "https://x", sleep=nosleep)
    out, calls = with_httpx([TimeoutError(), (200, "ok")], got)
    assert out == "ok" and len(calls) == 2


def test_fetch_json_429_is_retried():
    b = CircuitBreaker()
    async def go(): return await base.fetch_json(b, "https://x", sleep=nosleep)
    out, calls = with_httpx([(429, {}), (200, {"a": 1})], go)
    assert out == {"a": 1} and len(calls) == 2


def test_circuit_opens_after_repeated_failures_then_refuses_without_calling_then_half_opens():
    t = [0.0]
    b = CircuitBreaker(threshold=2, cooldown=30, clock=lambda: t[0])
    async def go():
        for _ in range(2):
            try: await base.fetch_text(b, "https://x", retries=0, sleep=nosleep)
            except RuntimeError: pass
        try: await base.fetch_text(b, "https://x", retries=0, sleep=nosleep)
        except RuntimeError as e: return str(e)
    msg, calls = with_httpx([(500, ""), (500, ""), (200, "never")], go)
    assert "circuit open" in msg and len(calls) == 2 and b.state == "open"
    t[0] += 31
    assert b.allow() and b.state == "closed"  # half-open: one probe allowed
    async def probe(): return await base.fetch_text(b, "https://x", retries=0, sleep=nosleep)
    out, _ = with_httpx([(200, "back")], probe)
    assert out == "back" and b.failures == 0
