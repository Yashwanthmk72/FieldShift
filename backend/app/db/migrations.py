# AI-assisted: written with an AI coding assistant (see README, "AI tools used").
"""Ordered, versioned SQL migrations (SQLite). Each has an up and a down; applied inside a transaction.

v0.4 databases (tables `farms`/`settings` keyed by workspace_id) are upgraded in place: migration 2 copies the
workspace id into `owner` as 'g:<uuid>' so guest data stays guest data and is never merged into an account."""
from __future__ import annotations

import sqlite3

MIGRATIONS: list[tuple[int, str, list[str], list[str]]] = [
    (1, "v0.4 baseline", [
        "CREATE TABLE IF NOT EXISTS farms (id INTEGER PRIMARY KEY AUTOINCREMENT, workspace_id TEXT NOT NULL, name TEXT NOT NULL, data TEXT NOT NULL, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS settings (workspace_id TEXT PRIMARY KEY, data TEXT NOT NULL)",
    ], []),
    (2, "ownership: users, tokens, owner columns, plans, rate limits", [
        "CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, failed_logins INTEGER NOT NULL DEFAULT 0, locked_until REAL NOT NULL DEFAULT 0)",
        "CREATE TABLE refresh_tokens (token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, family TEXT NOT NULL, expires_at REAL NOT NULL, used INTEGER NOT NULL DEFAULT 0, revoked INTEGER NOT NULL DEFAULT 0)",
        "ALTER TABLE farms ADD COLUMN owner TEXT",
        "UPDATE farms SET owner = 'g:' || workspace_id",
        "CREATE INDEX idx_farms_owner ON farms(owner)",
        "ALTER TABLE settings ADD COLUMN owner TEXT",
        "UPDATE settings SET owner = 'g:' || workspace_id",
        "CREATE UNIQUE INDEX idx_settings_owner ON settings(owner)",
        "CREATE TABLE fin_plans (id INTEGER PRIMARY KEY AUTOINCREMENT, owner TEXT NOT NULL, farm_id INTEGER, crop_id TEXT NOT NULL, data TEXT NOT NULL, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)",
        "CREATE INDEX idx_plans_owner ON fin_plans(owner)",
        "CREATE TABLE rate_limits (key TEXT NOT NULL, bucket INTEGER NOT NULL, count INTEGER NOT NULL, PRIMARY KEY (key, bucket))",
    ], [
        "DROP TABLE rate_limits", "DROP TABLE fin_plans", "DROP INDEX idx_settings_owner", "DROP INDEX idx_farms_owner",
        "ALTER TABLE settings DROP COLUMN owner", "ALTER TABLE farms DROP COLUMN owner", "DROP TABLE refresh_tokens", "DROP TABLE users",
    ]),
]


def current_version(con: sqlite3.Connection) -> int:
    con.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
    row = con.execute("SELECT MAX(version) FROM schema_version").fetchone()
    return row[0] or 0


def migrate(con: sqlite3.Connection, target: int | None = None) -> int:
    """Upgrade or downgrade to `target` (default: latest). Returns the resulting version."""
    target = MIGRATIONS[-1][0] if target is None else target
    ver = current_version(con)
    if ver == 0 and con.execute("SELECT 1 FROM sqlite_master WHERE name='farms'").fetchone():
        con.execute("INSERT INTO schema_version VALUES (1)")  # a v0.4 database already has the baseline tables
        ver = 1
    while ver < target:
        n, _, ups, _ = MIGRATIONS[ver]
        for sql in ups:
            con.execute(sql)
        ver = n
        con.execute("DELETE FROM schema_version"); con.execute("INSERT INTO schema_version VALUES (?)", (ver,))
    while ver > target:
        n, _, _, downs = MIGRATIONS[ver - 1]
        for sql in downs:
            con.execute(sql)
        ver = n - 1
        con.execute("DELETE FROM schema_version"); con.execute("INSERT INTO schema_version VALUES (?)", (ver,))
    con.commit()
    return ver
