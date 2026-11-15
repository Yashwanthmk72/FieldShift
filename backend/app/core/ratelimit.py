# AI-assisted: written with an AI coding assistant (see README, "AI tools used").
"""Rate limiting with trusted-proxy-aware client identification (audit defect D2)."""
from __future__ import annotations

import ipaddress
import sqlite3
import time
from collections import defaultdict, deque
from typing import Mapping


def _ip(value: str):
    try:
        return ipaddress.ip_address(value.strip())
    except ValueError:
        return None


def client_key(headers: Mapping[str, str], peer: str | None, trusted: list[str], user_id: str | None = None) -> str:
    """Rate-limit identity. Authenticated users are keyed by id. Otherwise X-Forwarded-For is honoured ONLY when the
    direct peer is a trusted proxy, and then the right-most address that is not itself a trusted proxy is used
    (a client can add entries on the left of the header but cannot forge the right-most hop a trusted proxy appends)."""
    if user_id:
        return f"user:{user_id}"
    nets = [ipaddress.ip_network(t, strict=False) for t in trusted]
    peer_ip = _ip(peer or "")
    if peer_ip is not None and any(peer_ip in n for n in nets):
        xff = [x for x in (headers.get("x-forwarded-for", "") or "").split(",") if x.strip()]
        for hop in reversed(xff):
            ip = _ip(hop)
            if ip is None:
                break  # malformed entry: stop trusting the header
            if not any(ip in n for n in nets):
                return f"ip:{ip}"
    return f"ip:{peer_ip or 'unknown'}"


class MemoryLimiter:
    """Sliding window, per process. Local development only: production uses SqlLimiter (shared across workers)."""

    def __init__(self, limit: int, window_s: int, clock=time.time):
        self.limit, self.window, self.clock = limit, window_s, clock
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = self.clock()
        q = self.hits[key]
        while q and q[0] <= now - self.window:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        if len(self.hits) > 5000:
            for k in [k for k, v in self.hits.items() if not v or v[-1] <= now - self.window][:2000]:
                self.hits.pop(k, None)
        return True


class SqlLimiter:
    """Counter in the database so every worker process shares it (fixed window)."""

    def __init__(self, connect, limit: int, window_s: int, clock=time.time):
        self.connect, self.limit, self.window, self.clock = connect, limit, window_s, clock

    def allow(self, key: str) -> bool:
        bucket = int(self.clock() // self.window)
        with self.connect() as con:
            con.execute("DELETE FROM rate_limits WHERE bucket < ?", (bucket - 1,))
            row = con.execute("SELECT count FROM rate_limits WHERE key=? AND bucket=?", (key, bucket)).fetchone()
            n = row[0] if row else 0
            if n >= self.limit:
                return False
            con.execute("INSERT INTO rate_limits(key,bucket,count) VALUES (?,?,1) ON CONFLICT(key,bucket) DO UPDATE SET count=count+1", (key, bucket))
            return True
