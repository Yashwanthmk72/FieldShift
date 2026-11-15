# AI-assisted: written with an AI coding assistant (see README, "AI tools used").
from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from ..core import security
from ..db.repo import Conflict
from .deps import Ctx, get_ctx, limiter_key, require_user
from .schemas import DeleteAccountIn, LoginIn, RegisterIn

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
REFRESH_COOKIE = "fs_refresh"
CSRF_HEADER = ("x-requested-with", "fieldshift")


def _csrf_guard(request: Request, ctx: Ctx) -> None:
    """Cookie-authenticated endpoints (refresh, logout) need a custom header, which forces a CORS pre-flight that only
    allow-listed origins pass, and an Origin that is on the allow-list when present."""
    if request.headers.get(CSRF_HEADER[0]) != CSRF_HEADER[1]:
        raise HTTPException(403, "Missing request header")
    origin = request.headers.get("origin")
    if origin and "*" not in ctx.settings.cors_origins and origin not in ctx.settings.cors_origins:
        raise HTTPException(403, "Origin not allowed")


def _issue(ctx: Ctx, response: Response, user_id: int, family: str | None = None) -> dict:
    s = ctx.settings
    access = security.sign_token({"sub": str(user_id), "typ": "access"}, s.secret_key, s.access_ttl_s)
    token, th = security.new_refresh_token()
    ctx.db.store_refresh(th, user_id, family or uuid.uuid4().hex, time.time() + s.refresh_ttl_s)
    response.set_cookie(REFRESH_COOKIE, token, max_age=s.refresh_ttl_s, httponly=True, secure=s.cookie_secure, samesite="none" if s.cookie_secure else "lax", path="/api/v1/auth")
    return {"access_token": access, "token_type": "bearer", "expires_in": s.access_ttl_s}


@router.post("/register", status_code=201)
def register(body: RegisterIn, request: Request, response: Response, ctx: Ctx = Depends(get_ctx)):
    if not ctx.login_limiter.allow("reg:" + limiter_key(request)):
        raise HTTPException(429, "Too many attempts. Try again later.")
    email = body.email.strip().lower()
    if not security.valid_email(email):
        raise HTTPException(422, "Enter a valid email address")
    problems = security.password_problems(body.password, email)
    if problems:
        raise HTTPException(422, " ".join(problems))
    try:
        uid = ctx.db.create_user(email, security.hash_password(body.password))
    except Conflict:
        raise HTTPException(409, "Could not create the account with those details")
    return {**_issue(ctx, response, uid), "user": {"id": uid, "email": email}}


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response, ctx: Ctx = Depends(get_ctx)):
    if not ctx.login_limiter.allow("login:" + limiter_key(request)):
        raise HTTPException(429, "Too many attempts. Try again later.")
    email = body.email.strip().lower()
    user = ctx.db.user_by_email(email)
    now = time.time()
    if user and user["locked_until"] > now:
        raise HTTPException(429, "Account temporarily locked after repeated failures. Try again later.")
    ok = security.verify_password(body.password, user["password_hash"]) if user else security.verify_password(body.password, "scrypt$16384$8$1$AAAA$AAAA")  # burn similar time for unknown emails
    if not user or not ok:
        if user:
            ctx.db.record_login(user["id"], False, now)
        raise HTTPException(401, "Incorrect email or password")
    ctx.db.record_login(user["id"], True)
    return {**_issue(ctx, response, user["id"]), "user": {"id": user["id"], "email": user["email"]}}


@router.post("/refresh")
def refresh(request: Request, response: Response, ctx: Ctx = Depends(get_ctx)):
    _csrf_guard(request, ctx)
    tok = request.cookies.get(REFRESH_COOKIE)
    got = ctx.db.rotate_refresh(security.hash_refresh(tok)) if tok else None
    if not got:
        response.delete_cookie(REFRESH_COOKIE, path="/api/v1/auth")
        raise HTTPException(401, "Session expired")
    user_id, family = got
    return _issue(ctx, response, user_id, family)


@router.post("/logout")
def logout(request: Request, response: Response, ctx: Ctx = Depends(get_ctx)):
    _csrf_guard(request, ctx)
    tok = request.cookies.get(REFRESH_COOKIE)
    if tok:
        ctx.db.revoke_family(security.hash_refresh(tok))
    response.delete_cookie(REFRESH_COOKIE, path="/api/v1/auth")
    return {"ok": True}


@router.get("/me")
def me(who=Depends(require_user), ctx: Ctx = Depends(get_ctx)):
    return ctx.db.user_by_id(who["user_id"])


@router.get("/export")
def export(who=Depends(require_user), ctx: Ctx = Depends(get_ctx)):
    return ctx.db.export_user(who["user_id"])


@router.delete("/account")
def delete_account(body: DeleteAccountIn, response: Response, who=Depends(require_user), ctx: Ctx = Depends(get_ctx)):
    user = ctx.db.user_by_email(ctx.db.user_by_id(who["user_id"])["email"])
    if not security.verify_password(body.password, user["password_hash"]):
        raise HTTPException(403, "Password is incorrect")
    ctx.db.delete_user(who["user_id"])
    response.delete_cookie(REFRESH_COOKIE, path="/api/v1/auth")
    return {"deleted": True}
