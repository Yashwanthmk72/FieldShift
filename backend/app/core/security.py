# AI-assisted: written with an AI coding assistant (see README, "AI tools used").
"""Password hashing, tokens and CSRF primitives using only the standard library."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import time
from typing import Any

SCRYPT_N, SCRYPT_R, SCRYPT_P = 2 ** 14, 8, 1
COMMON = {"password", "password1", "password123", "1234567890", "qwertyuiop", "letmein123", "iloveyou12", "fieldshift", "administrator"}
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,255}\.[^@\s]{2,}$")


def b64e(b: bytes) -> str: return base64.urlsafe_b64encode(b).rstrip(b"=").decode()
def b64d(s: str) -> bytes: return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    h = hashlib.scrypt(password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32, maxmem=64 * 1024 * 1024)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${b64e(salt)}${b64e(h)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, h = stored.split("$")
        if scheme != "scrypt":
            return False
        calc = hashlib.scrypt(password.encode(), salt=b64d(salt), n=int(n), r=int(r), p=int(p), dklen=32, maxmem=64 * 1024 * 1024)
        return hmac.compare_digest(calc, b64d(h))
    except Exception:
        return False


def password_problems(password: str, email: str = "") -> list[str]:
    out = []
    if len(password) < 10:
        out.append("Use at least 10 characters.")
    if len(password) > 128:
        out.append("Use at most 128 characters.")
    if password.lower() in COMMON or len(set(password)) < 4:
        out.append("That password is too common or too repetitive.")
    local = email.split("@")[0].lower()
    if local and len(local) >= 4 and local in password.lower():
        out.append("Do not include your email name in the password.")
    return out


def valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email))


def sign_token(payload: dict[str, Any], secret: str, ttl_s: int, now: float | None = None) -> str:
    body = {**payload, "exp": int((now or time.time()) + ttl_s), "jti": secrets.token_hex(8)}
    raw = b64e(json.dumps(body, separators=(",", ":")).encode())
    return f"{raw}.{b64e(hmac.new(secret.encode(), raw.encode(), hashlib.sha256).digest())}"


def verify_token(token: str, secret: str, now: float | None = None) -> dict[str, Any] | None:
    """Returns the payload, or None for any malformed, forged or expired token."""
    try:
        raw, sig = token.split(".")
        good = b64e(hmac.new(secret.encode(), raw.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, good):
            return None
        body = json.loads(b64d(raw))
        if not isinstance(body, dict) or body.get("exp", 0) < (now or time.time()):
            return None
        return body
    except Exception:
        return None


def new_refresh_token() -> tuple[str, str]:
    """(token for the cookie, sha256 hash for the database). Only the hash is stored."""
    t = secrets.token_urlsafe(32)
    return t, hashlib.sha256(t.encode()).hexdigest()


def hash_refresh(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_csrf() -> str:
    return secrets.token_urlsafe(24)


def csrf_ok(cookie_value: str | None, header_value: str | None) -> bool:
    return bool(cookie_value) and bool(header_value) and hmac.compare_digest(cookie_value, header_value)
