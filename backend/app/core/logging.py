# AI-assisted: written with an AI coding assistant (see README, "AI tools used").
"""Structured JSON logging with request ids and secret redaction."""
from __future__ import annotations

import contextvars
import json
import logging
import re
import time

request_id: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")
SENSITIVE_KEYS = re.compile(r"(password|passwd|secret|token|api[_-]?key|authorization|cookie|csrf)", re.I)
PREFIXED = [re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._\-]+"), re.compile(r"(?i)((?:password|token|api[_-]?key|secret)\s*[=:]\s*)[^\s,;&\"']+")]  # keep the label, hide the value
WHOLE = [re.compile(r"(?i)sk-[A-Za-z0-9_\-]{8,}")]  # API-key shaped strings are hidden entirely
REDACTED = "[REDACTED]"


def redact(value):
    if isinstance(value, dict):
        return {k: (REDACTED if SENSITIVE_KEYS.search(str(k)) else redact(v)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    if isinstance(value, str):
        out = value
        for p in PREFIXED:
            out = p.sub(lambda m: m.group(1) + REDACTED, out)
        for p in WHOLE:
            out = p.sub(REDACTED, out)
        return out
    return value


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)) + "Z", "level": record.levelname, "logger": record.name,
                 "msg": redact(record.getMessage()), "request_id": request_id.get()}
        extra = getattr(record, "ctx", None)
        if extra:
            entry["ctx"] = redact(extra)
        if record.exc_info:
            entry["exc_type"] = record.exc_info[0].__name__ if record.exc_info[0] else None  # no traceback text with possible secrets
        return json.dumps(entry, ensure_ascii=False)


def setup(level: str = "INFO") -> None:
    h = logging.StreamHandler()
    h.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [h]
    root.setLevel(level)
