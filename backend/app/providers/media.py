# AI-assisted: written with an AI coding assistant (see README, "AI tools used").
"""Wikimedia Commons image lookup (never invents URLs; returns [] on failure)."""
from __future__ import annotations

import re
from typing import Any

from .base import fetch_json

import os

# Wikimedia's API policy asks for a descriptive User-Agent with real contact details; generic or vague agents are often
# refused with 403, which is exactly how every photo silently disappeared. Set FIELDSHIFT_CONTACT to your own URL/email.
CONTACT = os.environ.get("FIELDSHIFT_CONTACT", "https://github.com/fieldshift/fieldshift")
UA = {"User-Agent": f"FieldShift/0.9 (farm decision-support; {CONTACT}) python-httpx", "Accept": "application/json"}
_gate = None


def _semaphore():
    global _gate
    import asyncio
    if _gate is None:
        _gate = asyncio.Semaphore(4)  # never hit Commons with more than 4 requests at once
    return _gate


def _strip_html(text: str | None) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", text or "")).strip()


def parse_commons(raw: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for page in sorted((raw.get("query", {}).get("pages", {}) or {}).values(), key=lambda p: p.get("index", 99)):
        info = (page.get("imageinfo") or [{}])[0]
        thumb = info.get("thumburl")
        if not thumb or (info.get("width") or 0) < 500:
            continue
        meta = info.get("extmetadata", {})
        out.append({"url": thumb, "page": info.get("descriptionurl"), "license": _strip_html((meta.get("LicenseShortName") or {}).get("value")) or "see file page",
                    "author": _strip_html((meta.get("Artist") or {}).get("value"))[:80], "title": page.get("title", "").replace("File:", "")})
        if len(out) >= limit:
            break
    return out


async def wiki_images(providers, query: str, limit: int = 1, width: int = 720) -> list[dict[str, Any]]:
    key = f"wiki:{query}:{limit}:{width}"
    if (hit := providers.cache.get(key)) is not None:
        return hit
    out: list[dict[str, Any]] = []
    try:
        async with _semaphore():
            for term in (f"filetype:bitmap {query}", query):  # second pass: plain search if the filtered one finds nothing
                params = {"action": "query", "generator": "search", "gsrsearch": term, "gsrnamespace": 6, "gsrlimit": limit + 6, "prop": "imageinfo", "iiprop": "url|extmetadata|size", "iiurlwidth": width, "format": "json", "origin": "*"}
                raw = await fetch_json(providers.breakers["wikimedia"], "https://commons.wikimedia.org/w/api.php", params, headers=UA, timeout=12)
                out = parse_commons(raw, limit)
                if out:
                    break
    except Exception:
        return providers.cache.set(key, [], 45)  # failures are retried soon, never remembered for long
    return providers.cache.set(key, out, 86400 if out else 600)
