# AI-assisted: written with an AI coding assistant (see README, "AI tools used").
"""Data access. EVERY query on user data filters by `owner` ('u:<id>' for accounts, 'g:<uuid>' for guests).

Owner strings are built only by `owner_for_user` / `owner_for_guest`, so a guest id can never equal a user id."""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .migrations import migrate

MAX_FARMS = 60
MAX_PLANS = 300
MAX_BYTES = 400_000


class Conflict(Exception): pass
class NotFound(Exception): pass
class TooLarge(Exception): pass


def owner_for_user(user_id: int) -> str: return f"u:{int(user_id)}"


def owner_for_guest(workspace_id: str) -> str:
    return f"g:{uuid.UUID(workspace_id)}"  # raises ValueError for anything that is not a UUID


class Database:
    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as con:
            migrate(con)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        con = sqlite3.connect(self.path, timeout=10)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        try:
            yield con
            con.commit()
        finally:
            con.close()

    # ---- farms ----
    def list_farms(self, owner: str) -> list[dict[str, Any]]:
        with self.connect() as con:
            rows = con.execute("SELECT id,name,data,updated_at FROM farms WHERE owner=? ORDER BY updated_at DESC, id DESC", (owner,)).fetchall()
        return [self._farm(r) for r in rows]

    def get_farm(self, owner: str, farm_id: int) -> dict[str, Any]:
        with self.connect() as con:
            r = con.execute("SELECT id,name,data,updated_at FROM farms WHERE id=? AND owner=?", (farm_id, owner)).fetchone()
        if not r:
            raise NotFound("Farm not found")
        return self._farm(r)

    def create_farm(self, owner: str, name: str, data: dict[str, Any]) -> int:
        raw = self._raw(data)
        with self.connect() as con:
            if con.execute("SELECT COUNT(*) FROM farms WHERE owner=?", (owner,)).fetchone()[0] >= MAX_FARMS:
                raise Conflict(f"Limit of {MAX_FARMS} fields reached")
            return con.execute("INSERT INTO farms(workspace_id,owner,name,data) VALUES (?,?,?,?)", (owner, owner, name, raw)).lastrowid

    def update_farm(self, owner: str, farm_id: int, name: str, data: dict[str, Any]) -> None:
        raw = self._raw(data)
        with self.connect() as con:
            if not con.execute("UPDATE farms SET name=?, data=?, updated_at=CURRENT_TIMESTAMP WHERE id=? AND owner=?", (name, raw, farm_id, owner)).rowcount:
                raise NotFound("Farm not found")

    def delete_farm(self, owner: str, farm_id: int) -> None:
        with self.connect() as con:
            if not con.execute("DELETE FROM farms WHERE id=? AND owner=?", (farm_id, owner)).rowcount:
                raise NotFound("Farm not found")
            con.execute("DELETE FROM fin_plans WHERE farm_id=? AND owner=?", (farm_id, owner))

    # ---- settings ----
    def get_settings(self, owner: str) -> dict[str, Any]:
        with self.connect() as con:
            r = con.execute("SELECT data FROM settings WHERE owner=?", (owner,)).fetchone()
        return json.loads(r["data"]) if r else {}

    def put_settings(self, owner: str, data: dict[str, Any]) -> None:
        raw = json.dumps(data)
        if len(raw) > 8000:
            raise TooLarge("Settings too large")
        with self.connect() as con:
            con.execute("INSERT INTO settings(workspace_id,owner,data) VALUES (?,?,?) ON CONFLICT(owner) DO UPDATE SET data=excluded.data", (owner, owner, raw))

    # ---- financial plans ----
    def list_plans(self, owner: str, farm_id: int | None = None) -> list[dict[str, Any]]:
        with self.connect() as con:
            if farm_id is None:
                rows = con.execute("SELECT * FROM fin_plans WHERE owner=? ORDER BY updated_at DESC, id DESC", (owner,)).fetchall()
            else:
                rows = con.execute("SELECT * FROM fin_plans WHERE owner=? AND farm_id=? ORDER BY updated_at DESC, id DESC", (owner, farm_id)).fetchall()
        return [self._plan(r) for r in rows]

    def save_plan(self, owner: str, crop_id: str, data: dict[str, Any], farm_id: int | None = None, plan_id: int | None = None) -> int:
        raw = self._raw(data)
        with self.connect() as con:
            if farm_id is not None and not con.execute("SELECT 1 FROM farms WHERE id=? AND owner=?", (farm_id, owner)).fetchone():
                raise NotFound("Farm not found")  # a plan may only attach to a farm the same owner holds
            if plan_id is None:
                if con.execute("SELECT COUNT(*) FROM fin_plans WHERE owner=?", (owner,)).fetchone()[0] >= MAX_PLANS:
                    raise Conflict(f"Limit of {MAX_PLANS} plans reached")
                return con.execute("INSERT INTO fin_plans(owner,farm_id,crop_id,data) VALUES (?,?,?,?)", (owner, farm_id, crop_id, raw)).lastrowid
            if not con.execute("UPDATE fin_plans SET crop_id=?, farm_id=?, data=?, updated_at=CURRENT_TIMESTAMP WHERE id=? AND owner=?", (crop_id, farm_id, raw, plan_id, owner)).rowcount:
                raise NotFound("Plan not found")
            return plan_id

    def get_plan(self, owner: str, plan_id: int) -> dict[str, Any]:
        with self.connect() as con:
            r = con.execute("SELECT * FROM fin_plans WHERE id=? AND owner=?", (plan_id, owner)).fetchone()
        if not r:
            raise NotFound("Plan not found")
        return self._plan(r)

    def delete_plan(self, owner: str, plan_id: int) -> None:
        with self.connect() as con:
            if not con.execute("DELETE FROM fin_plans WHERE id=? AND owner=?", (plan_id, owner)).rowcount:
                raise NotFound("Plan not found")

    # ---- users and tokens ----
    def create_user(self, email: str, password_hash: str) -> int:
        with self.connect() as con:
            try:
                return con.execute("INSERT INTO users(email,password_hash) VALUES (?,?)", (email.lower(), password_hash)).lastrowid
            except sqlite3.IntegrityError as exc:
                raise Conflict("An account with that email already exists") from exc

    def user_by_email(self, email: str) -> dict[str, Any] | None:
        with self.connect() as con:
            r = con.execute("SELECT * FROM users WHERE email=?", (email.lower(),)).fetchone()
        return dict(r) if r else None

    def user_by_id(self, user_id: int) -> dict[str, Any] | None:
        with self.connect() as con:
            r = con.execute("SELECT id,email,created_at FROM users WHERE id=?", (user_id,)).fetchone()
        return dict(r) if r else None

    def record_login(self, user_id: int, ok: bool, now: float | None = None, max_fail: int = 5, lock_s: int = 900) -> None:
        now = now or time.time()
        with self.connect() as con:
            if ok:
                con.execute("UPDATE users SET failed_logins=0, locked_until=0 WHERE id=?", (user_id,))
            else:
                con.execute("UPDATE users SET failed_logins=failed_logins+1, locked_until=CASE WHEN failed_logins+1>=? THEN ? ELSE locked_until END WHERE id=?", (max_fail, now + lock_s, user_id))

    def store_refresh(self, token_hash: str, user_id: int, family: str, expires_at: float) -> None:
        with self.connect() as con:
            con.execute("INSERT INTO refresh_tokens(token_hash,user_id,family,expires_at) VALUES (?,?,?,?)", (token_hash, user_id, family, expires_at))

    def rotate_refresh(self, token_hash: str, now: float | None = None) -> tuple[int, str] | None:
        """Mark a refresh token used and return (user_id, family). Re-use of a used token revokes the whole family."""
        now = now or time.time()
        with self.connect() as con:
            r = con.execute("SELECT * FROM refresh_tokens WHERE token_hash=?", (token_hash,)).fetchone()
            if not r or r["revoked"] or r["expires_at"] < now:
                return None
            if r["used"]:
                con.execute("UPDATE refresh_tokens SET revoked=1 WHERE family=?", (r["family"],))
                return None
            con.execute("UPDATE refresh_tokens SET used=1 WHERE token_hash=?", (token_hash,))
            return r["user_id"], r["family"]

    def revoke_family(self, token_hash: str) -> None:
        with self.connect() as con:
            r = con.execute("SELECT family FROM refresh_tokens WHERE token_hash=?", (token_hash,)).fetchone()
            if r:
                con.execute("UPDATE refresh_tokens SET revoked=1 WHERE family=?", (r["family"],))

    def export_user(self, user_id: int) -> dict[str, Any]:
        owner = owner_for_user(user_id)
        return {"account": self.user_by_id(user_id), "farms": self.list_farms(owner), "settings": self.get_settings(owner), "financial_plans": self.list_plans(owner)}

    def delete_user(self, user_id: int) -> None:
        owner = owner_for_user(user_id)
        with self.connect() as con:
            con.execute("DELETE FROM farms WHERE owner=?", (owner,))
            con.execute("DELETE FROM fin_plans WHERE owner=?", (owner,))
            con.execute("DELETE FROM settings WHERE owner=?", (owner,))
            con.execute("DELETE FROM rate_limits WHERE key=?", (f"user:{user_id}",))
            con.execute("DELETE FROM users WHERE id=?", (user_id,))  # refresh tokens cascade

    # ---- helpers ----
    @staticmethod
    def _raw(data: dict[str, Any]) -> str:
        raw = json.dumps(data)
        if len(raw) > MAX_BYTES:
            raise TooLarge("Data is too large")
        return raw

    @staticmethod
    def _farm(r: sqlite3.Row) -> dict[str, Any]:
        return {"id": r["id"], "name": r["name"], "updated_at": r["updated_at"], **json.loads(r["data"])}

    @staticmethod
    def _plan(r: sqlite3.Row) -> dict[str, Any]:
        return {"id": r["id"], "farm_id": r["farm_id"], "crop_id": r["crop_id"], "updated_at": r["updated_at"], **json.loads(r["data"])}
