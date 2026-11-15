# Security (v0.6.0)

| Control | Implementation | Evidence |
|---|---|---|
| Password hashing | stdlib scrypt, per-user salt, constant-time verify; policy: 10+ chars, not common, not containing email name | Verified (unit tests) |
| Tokens | HMAC-SHA256 signed access tokens (15 min), typ checked; refresh token random, **only its SHA-256 stored**, rotated on use; reuse revokes the family | Verified (unit tests on primitives and repo) |
| Cookies | refresh cookie `HttpOnly`, `Secure` (+`SameSite=None`) when `FIELDSHIFT_COOKIE_SECURE`, path-scoped; access token kept in JS memory only, nothing in localStorage | Implemented, **unverified** (server not run) |
| CSRF | cookie endpoints require `X-Requested-With: fieldshift` and an allow-listed Origin | Unverified |
| Authorization | every repository query filters by `owner` (`u:<id>`/`g:<uuid>`); plan→farm attachment checked against owner | **Verified** (IDOR tests: farms, plans, settings, guest vs user) |
| Login throttling | per-IP limiter + per-account lockout (5 failures → 15 min) | Lockout verified at DB layer; HTTP path unverified |
| Rate limiting / XFF (D2) | `X-Forwarded-For` honoured only from `TRUSTED_PROXIES`, right-most untrusted hop; per-user keys; SQL-backed limiter shared across workers | **Verified** (spoofing tests) |
| Input limits | Pydantic size caps on every field; body-size middleware (1 MB); assistant context now recomputed server-side | Unverified at HTTP level |
| XSS (D5) | escape-by-default `html```/`setHtml`; no direct `innerHTML` assignment (tested); every server string replaced by an `<img onerror>` probe in Chromium → nothing executes | **Verified** (stand-in server) |
| Headers | CSP (strict for `/api`, app CSP for static), nosniff, no-referrer, X-Frame-Options DENY, HSTS when secure | Unverified |
| CORS | explicit allow-list; wildcard rejected in production config | Config validation verified |
| Logging | JSON, request id, secret redaction (bearer, `sk-…`, password/token fields) | **Verified** |
| Config | production refuses short secret, insecure cookies, wildcard CORS | **Verified** |
| Dependency audit | `pip-audit` in CI | **Not run** |

Gaps: see KNOWN_LIMITATIONS.md (no orgs/roles, no password recovery/email verification, scrypt not Argon2id, account enumeration on register).
