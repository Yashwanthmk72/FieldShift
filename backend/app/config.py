# AI-assisted: written with an AI coding assistant (see README, "AI tools used").
"""Environment-driven settings, validated at start-up (fails fast on bad config)."""
from __future__ import annotations

import ipaddress
import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERSION = "0.9.0"


class ConfigError(RuntimeError):
    pass


def _csv(v: str) -> list[str]:
    return [x.strip() for x in v.split(",") if x.strip()]


@dataclass(frozen=True)
class Settings:
    env: str = "development"
    db_path: str = str(ROOT / "backend" / "fieldshift.db")
    secret_key: str = ""
    cors_origins: list[str] = field(default_factory=lambda: ["http://localhost:8000", "http://127.0.0.1:8000", "http://localhost:8080", "http://127.0.0.1:8080"])
    trusted_proxies: list[str] = field(default_factory=list)
    access_ttl_s: int = 900
    refresh_ttl_s: int = 14 * 86400
    cookie_secure: bool = False
    assistant_limit: int = 12
    assistant_window_s: int = 300
    llm_api_key: str = ""
    llm_model: str = ""
    sentry_dsn: str = ""
    max_body_bytes: int = 1_000_000
    data_gov_in_api_key: str = ""
    fx_api_url: str = "https://api.frankfurter.dev/v1/latest"

    @property
    def production(self) -> bool:
        return self.env == "production"

    @staticmethod
    def from_env(environ: dict[str, str] | None = None) -> "Settings":
        e = os.environ if environ is None else environ
        s = Settings(
            env=e.get("FIELDSHIFT_ENV", "development"), db_path=e.get("FIELDSHIFT_DB", str(ROOT / "backend" / "fieldshift.db")),
            secret_key=e.get("FIELDSHIFT_SECRET_KEY", ""),
            cors_origins=_csv(e["FIELDSHIFT_CORS_ORIGINS"]) if "FIELDSHIFT_CORS_ORIGINS" in e else Settings().cors_origins,
            trusted_proxies=_csv(e.get("TRUSTED_PROXIES", "")), cookie_secure=e.get("FIELDSHIFT_COOKIE_SECURE", "").lower() in ("1", "true", "yes"),
            access_ttl_s=int(e.get("FIELDSHIFT_ACCESS_TTL", 900)), refresh_ttl_s=int(e.get("FIELDSHIFT_REFRESH_TTL", 14 * 86400)),
            assistant_limit=int(e.get("ASSISTANT_RATE_LIMIT", 12)), llm_api_key=e.get("OPENAI_API_KEY", ""), llm_model=e.get("OPENAI_MODEL", ""),
            sentry_dsn=e.get("SENTRY_DSN", ""), data_gov_in_api_key=e.get("DATA_GOV_IN_API_KEY", ""), fx_api_url=e.get("FX_API_URL", "https://api.frankfurter.dev/v1/latest"))
        s.validate()
        return s

    def validate(self) -> None:
        for p in self.trusted_proxies:
            try:
                ipaddress.ip_network(p, strict=False)
            except ValueError as exc:
                raise ConfigError(f"TRUSTED_PROXIES contains an invalid address/CIDR: {p!r}") from exc
        if "*" in self.cors_origins and self.production:
            raise ConfigError("CORS wildcard is not allowed in production; set FIELDSHIFT_CORS_ORIGINS")
        if self.production:
            if len(self.secret_key) < 32:
                raise ConfigError("FIELDSHIFT_SECRET_KEY must be at least 32 characters in production")
            if not self.cookie_secure:
                raise ConfigError("FIELDSHIFT_COOKIE_SECURE must be true in production")
        if self.access_ttl_s <= 0 or self.refresh_ttl_s <= 0:
            raise ConfigError("token lifetimes must be positive")
