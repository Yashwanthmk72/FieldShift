# AI-assisted: written with an AI coding assistant (see README, "AI tools used").
"""App factory, middleware and lifespan only."""
from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import assistant
from .api import routes_auth, routes_data, routes_market
from .api.deps import Ctx
from .config import ROOT, VERSION, Settings
from .core import logging as flog
from .core import ratelimit
from .core.errors import ApiError
from .db.repo import Database
from .providers.clients import Providers
from .providers.prices import PriceService

log = logging.getLogger("fieldshift")
API_CSP = "default-src 'none'; frame-ancestors 'none'"
APP_CSP = ("default-src 'self'; script-src 'self' https://unpkg.com; style-src 'self' 'unsafe-inline' https://unpkg.com https://fonts.googleapis.com; font-src https://fonts.gstatic.com; "
           "img-src 'self' data: blob: https:; connect-src 'self' https://nominatim.openstreetmap.org https://server.arcgisonline.com https://tile.openstreetmap.org https://unpkg.com; worker-src blob:; frame-ancestors 'none'")


def create_app(settings: Settings | None = None, providers: Providers | None = None, llm=None, prices: PriceService | None = None) -> FastAPI:
    s = settings or Settings.from_env()
    flog.setup()
    db = Database(s.db_path)
    limiter = ratelimit.SqlLimiter(db.connect, s.assistant_limit, s.assistant_window_s) if s.production else ratelimit.MemoryLimiter(s.assistant_limit, s.assistant_window_s)
    login_limiter = ratelimit.SqlLimiter(db.connect, 10, 60) if s.production else ratelimit.MemoryLimiter(10, 60)
    if llm is None and s.llm_api_key:
        llm = assistant.OpenAILLM(s.llm_api_key, s.llm_model) if s.llm_model else None  # no model name configured -> automatic explanations only
    if s.sentry_dsn:
        try:
            import sentry_sdk
            sentry_sdk.init(dsn=s.sentry_dsn, send_default_pii=False)
        except ImportError:
            log.warning("SENTRY_DSN set but sentry-sdk is not installed")

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield

    app = FastAPI(title="FieldShift API", version=VERSION, description="Decision support for climate-resilient crop planning. Estimates, not guarantees.", lifespan=lifespan)
    app.state.ctx = Ctx(settings=s, db=db, providers=providers or Providers(), kb=assistant.BM25(assistant.load_kb()), limiter=limiter, login_limiter=login_limiter, llm=llm,
                     prices=prices or PriceService(settings={"DATA_GOV_IN_API_KEY": s.data_gov_in_api_key, "FX_API_URL": s.fx_api_url}))
    app.add_middleware(CORSMiddleware, allow_origins=s.cors_origins, allow_credentials=True, allow_methods=["GET", "POST", "PUT", "DELETE"],
                       allow_headers=["Authorization", "Content-Type", "X-Workspace-ID", "X-Requested-With"])

    @app.middleware("http")
    async def guard(request: Request, call_next):
        rid = request.headers.get("x-request-id", "")[:64] or uuid.uuid4().hex[:16]
        flog.request_id.set(rid)
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > s.max_body_bytes:
            return JSONResponse({"detail": "Request too large"}, status_code=413)
        try:
            response = await call_next(request)
        except Exception as exc:  # no stack traces to clients
            log.error("unhandled error: %s", type(exc).__name__, extra={"ctx": {"path": request.url.path}})
            response = JSONResponse({"detail": "Internal error", "request_id": rid}, status_code=500)
        h = response.headers
        h["X-Request-ID"] = rid
        h["X-Content-Type-Options"] = "nosniff"
        h["Referrer-Policy"] = "no-referrer"
        h["Content-Security-Policy"] = API_CSP if request.url.path.startswith(("/api", "/healthz", "/readyz")) else APP_CSP
        h["X-Frame-Options"] = "DENY"
        if s.cookie_secure:
            h["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    @app.exception_handler(ApiError)
    async def api_error(_: Request, exc: ApiError):
        return JSONResponse({"detail": exc.detail}, status_code=exc.status)

    app.include_router(routes_auth.router)
    app.include_router(routes_market.router)  # before routes_data so the honest /api/health wins
    app.include_router(routes_data.router)
    if (ROOT / "frontend").exists():
        app.mount("/", StaticFiles(directory=ROOT / "frontend", html=True), name="frontend")
    return app


def _default() -> FastAPI:
    return create_app()


try:
    app = _default()
except Exception as _exc:  # misconfiguration should fail loudly at import under uvicorn
    raise
