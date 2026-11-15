# AI-assisted: written with an AI coding assistant (see README, "AI tools used").
"""Application context and request identity. One place decides who the caller is."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from fastapi import HTTPException, Request

from .. import assistant
from ..config import Settings
from ..core import ratelimit, security
from ..db.repo import Database, owner_for_guest, owner_for_user
from ..providers.clients import Providers


@dataclass
class Ctx:
    settings: Settings
    db: Database
    providers: Providers
    kb: assistant.BM25
    limiter: Any
    login_limiter: Any
    budget: assistant.TokenBudget = field(default_factory=assistant.TokenBudget)
    llm: Any = None
    prices: Any = None
    health_cache: dict = field(default_factory=lambda: {"value": None, "at": 0.0})


def get_ctx(request: Request) -> Ctx:
    return request.app.state.ctx


def bearer(request: Request) -> str | None:
    h = request.headers.get("authorization", "")
    return h[7:].strip() if h.lower().startswith("bearer ") else None


def identity(request: Request) -> dict[str, Any]:
    """Resolve the caller. Returns {'owner', 'user_id'|None, 'kind'}. A bad/expired bearer token is a 401 (never silently demoted to guest)."""
    ctx = get_ctx(request)
    tok = bearer(request)
    if tok is not None:
        payload = security.verify_token(tok, ctx.settings.secret_key)
        if not payload or payload.get("typ") != "access":
            raise HTTPException(401, "Invalid or expired token")
        uid = int(payload["sub"])
        if not ctx.db.user_by_id(uid):
            raise HTTPException(401, "Invalid or expired token")
        return {"owner": owner_for_user(uid), "user_id": uid, "kind": "user"}
    ws = request.headers.get("x-workspace-id")
    if ws:
        try:
            return {"owner": owner_for_guest(ws), "user_id": None, "kind": "guest"}
        except ValueError:
            raise HTTPException(400, "A valid guest workspace ID is required")
    raise HTTPException(401, "Sign in or provide a guest workspace ID")


def require_user(request: Request) -> dict[str, Any]:
    who = identity(request)
    if who["user_id"] is None:
        raise HTTPException(401, "An account is required")
    return who


def limiter_key(request: Request, who: dict[str, Any] | None = None) -> str:
    ctx = get_ctx(request)
    peer = request.client.host if request.client else None
    return ratelimit.client_key(request.headers, peer, ctx.settings.trusted_proxies, str(who["user_id"]) if who and who.get("user_id") else None)


def new_workspace_id() -> str:
    return str(uuid.uuid4())
