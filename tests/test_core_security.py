# AI-assisted: written with an AI coding assistant (see README, "AI tools used").
import json
import logging
import sqlite3
import time

import pytest

from app.config import ConfigError, Settings
from app.core import logging as flog
from app.core import ratelimit as rl
from app.core import security as sec
from app.db import migrations
from app.db.repo import Conflict, Database, NotFound, TooLarge, owner_for_guest, owner_for_user

TRUSTED = ["10.0.0.0/8"]


# ---------- D2: spoofable X-Forwarded-For ----------
def test_d2_xff_ignored_when_peer_is_not_a_trusted_proxy():
    # v0.4 trusted any X-Forwarded-For, so a client rotated this header to dodge the limit
    assert rl.client_key({"x-forwarded-for": "6.6.6.6"}, "203.0.113.5", TRUSTED) == "ip:203.0.113.5"
    assert rl.client_key({"x-forwarded-for": "6.6.6.6"}, "203.0.113.5", []) == "ip:203.0.113.5"


def test_d2_xff_honoured_only_from_trusted_proxy_and_rightmost_untrusted_hop_wins():
    assert rl.client_key({"x-forwarded-for": "198.51.100.7"}, "10.1.2.3", TRUSTED) == "ip:198.51.100.7"
    # attacker prepends a fake address; the proxy appended the real one on the right
    assert rl.client_key({"x-forwarded-for": "6.6.6.6, 198.51.100.7"}, "10.1.2.3", TRUSTED) == "ip:198.51.100.7"
    assert rl.client_key({"x-forwarded-for": "198.51.100.7, 10.9.9.9"}, "10.1.2.3", TRUSTED) == "ip:198.51.100.7"
    assert rl.client_key({"x-forwarded-for": "garbage"}, "10.1.2.3", TRUSTED) == "ip:10.1.2.3"


def test_authenticated_users_are_keyed_by_id_not_address():
    assert rl.client_key({"x-forwarded-for": "1.1.1.1"}, "203.0.113.5", TRUSTED, user_id="42") == "user:42"


def test_memory_limiter_sliding_window():
    t = [1000.0]
    lim = rl.MemoryLimiter(3, 60, clock=lambda: t[0])
    assert [lim.allow("a") for _ in range(4)] == [True, True, True, False]
    assert lim.allow("b")
    t[0] += 61
    assert lim.allow("a")


def test_sql_limiter_is_shared_between_instances(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    a, b = rl.SqlLimiter(db.connect, 2, 60), rl.SqlLimiter(db.connect, 2, 60)  # two "workers"
    assert a.allow("k") and b.allow("k") and not a.allow("k") and not b.allow("k")


# ---------- passwords and tokens ----------
def test_password_hash_verifies_and_is_salted():
    h1, h2 = sec.hash_password("correct horse battery"), sec.hash_password("correct horse battery")
    assert h1 != h2 and sec.verify_password("correct horse battery", h1) and not sec.verify_password("wrong", h1)
    assert not sec.verify_password("x", "garbage") and "correct horse" not in h1


def test_password_policy():
    assert sec.password_problems("Tr0ub4dor&3xyz") == []
    assert sec.password_problems("short")
    assert sec.password_problems("password123")
    assert sec.password_problems("aaaaaaaaaaaa")
    assert sec.password_problems("yashwanth-2026!", "yashwanth@example.com")
    assert sec.valid_email("a@b.co") and not sec.valid_email("nope") and not sec.valid_email("a b@c.com")


def test_tokens_expire_and_reject_forgery():
    tok = sec.sign_token({"sub": "7"}, "s" * 40, 60, now=1000)
    assert sec.verify_token(tok, "s" * 40, now=1030)["sub"] == "7"
    assert sec.verify_token(tok, "s" * 40, now=1061) is None  # expired
    assert sec.verify_token(tok, "other" * 8, now=1030) is None  # wrong key
    raw, sig = tok.split(".")
    forged = sec.b64e(json.dumps({"sub": "1", "exp": 9999999999}).encode()) + "." + sig
    assert sec.verify_token(forged, "s" * 40, now=1030) is None
    for junk in ("", "a.b", "....", "not-a-token", tok + "x"):
        assert sec.verify_token(junk, "s" * 40, now=1030) is None


def test_csrf_double_submit():
    t = sec.new_csrf()
    assert sec.csrf_ok(t, t) and not sec.csrf_ok(t, "other") and not sec.csrf_ok(None, t) and not sec.csrf_ok(t, None) and not sec.csrf_ok("", "")


# ---------- database: migrations ----------
V04_SCHEMA = ["CREATE TABLE farms (id INTEGER PRIMARY KEY AUTOINCREMENT, workspace_id TEXT NOT NULL, name TEXT NOT NULL, data TEXT NOT NULL, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)",
              "CREATE TABLE settings (workspace_id TEXT PRIMARY KEY, data TEXT NOT NULL)"]
WS = "123e4567-e89b-12d3-a456-426614174000"


def v04_db(path):
    con = sqlite3.connect(path)
    for s in V04_SCHEMA:
        con.execute(s)
    con.execute("INSERT INTO farms(workspace_id,name,data) VALUES (?,?,?)", (WS, "Old farm", json.dumps({"latitude": 1, "longitude": 2})))
    con.execute("INSERT INTO settings VALUES (?,?)", (WS, json.dumps({"name": "Asha"})))
    con.commit(); con.close()


def test_v04_database_is_upgraded_in_place_and_stays_guest_data(tmp_path):
    p = str(tmp_path / "old.db"); v04_db(p)
    db = Database(p)
    guest = owner_for_guest(WS)
    assert [f["name"] for f in db.list_farms(guest)] == ["Old farm"] and db.get_settings(guest) == {"name": "Asha"}
    uid = db.create_user("a@b.co", sec.hash_password("a-long-password"))
    assert db.list_farms(owner_for_user(uid)) == []  # guest data is never merged into an account
    db.put_settings(guest, {"name": "Asha2"})  # upsert on legacy row must not violate the unique owner index
    assert db.get_settings(guest) == {"name": "Asha2"}


def test_migrations_down_and_up_on_populated_db(tmp_path):
    p = str(tmp_path / "m.db"); v04_db(p)
    db = Database(p)
    with db.connect() as con:
        assert migrations.current_version(con) == 2
        assert migrations.migrate(con, 1) == 1
        assert not con.execute("SELECT 1 FROM sqlite_master WHERE name='users'").fetchone()
        assert con.execute("SELECT name FROM farms").fetchone()[0] == "Old farm"  # data survives the downgrade
        assert migrations.migrate(con, 2) == 2
    assert [f["name"] for f in db.list_farms(owner_for_guest(WS))] == ["Old farm"]


def test_migrations_on_empty_db(tmp_path):
    db = Database(str(tmp_path / "e.db"))
    with db.connect() as con:
        assert migrations.current_version(con) == 2 and migrations.migrate(con) == 2


# ---------- authorization: user A cannot touch user B's data by changing any id ----------
@pytest.fixture
def two_users(tmp_path):
    db = Database(str(tmp_path / "a.db"))
    a, b = owner_for_user(db.create_user("a@x.io", "h")), owner_for_user(db.create_user("b@x.io", "h"))
    return db, a, b


def test_idor_farms(two_users):
    db, a, b = two_users
    fid = db.create_farm(a, "A's field", {"latitude": 1})
    for call in (lambda: db.get_farm(b, fid), lambda: db.update_farm(b, fid, "hijack", {}), lambda: db.delete_farm(b, fid)):
        with pytest.raises(NotFound):
            call()
    assert db.list_farms(b) == [] and db.get_farm(a, fid)["name"] == "A's field"


def test_idor_plans_and_cross_owner_farm_attachment(two_users):
    db, a, b = two_users
    fa = db.create_farm(a, "f", {})
    pid = db.save_plan(a, "maize", {"price_per_t": 1}, farm_id=fa)
    with pytest.raises(NotFound):
        db.get_plan(b, pid)
    with pytest.raises(NotFound):
        db.delete_plan(b, pid)
    with pytest.raises(NotFound):
        db.save_plan(b, "maize", {}, plan_id=pid)  # overwrite someone else's plan
    with pytest.raises(NotFound):
        db.save_plan(b, "maize", {}, farm_id=fa)  # attach own plan to someone else's farm
    assert db.list_plans(b) == [] and db.get_plan(a, pid)["price_per_t"] == 1


def test_idor_settings_and_guest_vs_user_separation(two_users):
    db, a, b = two_users
    db.put_settings(a, {"k": "a"})
    assert db.get_settings(b) == {}
    g = owner_for_guest(WS)
    db.create_farm(g, "guest farm", {})
    assert db.list_farms(a) == [] and db.list_farms(g)[0]["name"] == "guest farm"
    with pytest.raises(ValueError):
        owner_for_guest("1")  # user-id lookalikes are not valid guest ids
    assert owner_for_user(1) != owner_for_guest(WS)


def test_limits_and_size_caps(two_users):
    db, a, _ = two_users
    with pytest.raises(TooLarge):
        db.create_farm(a, "x", {"blob": "x" * 500_000})
    with pytest.raises(TooLarge):
        db.put_settings(a, {"blob": "x" * 9000})
    for i in range(60):
        db.create_farm(a, str(i), {})
    with pytest.raises(Conflict):
        db.create_farm(a, "61st", {})


def test_refresh_token_rotation_and_reuse_detection(two_users):
    db, _, _ = two_users
    uid = db.user_by_email("a@x.io")["id"]
    t1, h1 = sec.new_refresh_token(); db.store_refresh(h1, uid, "fam", time.time() + 100)
    assert db.rotate_refresh(h1) == (uid, "fam")
    t2, h2 = sec.new_refresh_token(); db.store_refresh(h2, uid, "fam", time.time() + 100)
    assert db.rotate_refresh(h1) is None  # replay of a used token: whole family revoked
    assert db.rotate_refresh(h2) is None
    t3, h3 = sec.new_refresh_token(); db.store_refresh(h3, uid, "f2", time.time() - 1)
    assert db.rotate_refresh(h3) is None  # expired
    assert db.rotate_refresh("unknown") is None


def test_login_lockout_counts_failures(two_users):
    db, _, _ = two_users
    uid = db.user_by_email("a@x.io")["id"]
    for _ in range(5):
        db.record_login(uid, False, now=1000)
    assert db.user_by_email("a@x.io")["locked_until"] == 1000 + 900
    db.record_login(uid, True)
    u = db.user_by_email("a@x.io")
    assert u["failed_logins"] == 0 and u["locked_until"] == 0


def test_duplicate_email_and_account_deletion_removes_everything(two_users):
    db, a, b = two_users
    with pytest.raises(Conflict):
        db.create_user("A@X.io", "h")  # emails are case-insensitive
    uid = db.user_by_email("a@x.io")["id"]
    fid = db.create_farm(a, "f", {}); db.save_plan(a, "maize", {}, farm_id=fid); db.put_settings(a, {"x": 1})
    _, h = sec.new_refresh_token(); db.store_refresh(h, uid, "f", time.time() + 100)
    exported = db.export_user(uid)
    assert exported["farms"] and exported["financial_plans"] and exported["account"]["email"] == "a@x.io" and "password_hash" not in json.dumps(exported)
    db.delete_user(uid)
    assert db.user_by_id(uid) is None and db.list_farms(a) == [] and db.list_plans(a) == [] and db.get_settings(a) == {}
    with db.connect() as con:
        assert con.execute("SELECT COUNT(*) FROM refresh_tokens").fetchone()[0] == 0
    assert db.user_by_email("b@x.io")  # other users untouched


# ---------- config ----------
def test_config_fails_fast_on_bad_production_settings():
    with pytest.raises(ConfigError, match="SECRET_KEY"):
        Settings.from_env({"FIELDSHIFT_ENV": "production", "FIELDSHIFT_COOKIE_SECURE": "1"})
    with pytest.raises(ConfigError, match="CORS"):
        Settings.from_env({"FIELDSHIFT_ENV": "production", "FIELDSHIFT_SECRET_KEY": "k" * 40, "FIELDSHIFT_COOKIE_SECURE": "1", "FIELDSHIFT_CORS_ORIGINS": "*"})
    with pytest.raises(ConfigError, match="COOKIE_SECURE"):
        Settings.from_env({"FIELDSHIFT_ENV": "production", "FIELDSHIFT_SECRET_KEY": "k" * 40})
    with pytest.raises(ConfigError, match="TRUSTED_PROXIES"):
        Settings.from_env({"TRUSTED_PROXIES": "not-an-ip"})
    ok = Settings.from_env({"FIELDSHIFT_ENV": "production", "FIELDSHIFT_SECRET_KEY": "k" * 40, "FIELDSHIFT_COOKIE_SECURE": "1", "FIELDSHIFT_CORS_ORIGINS": "https://a.example", "TRUSTED_PROXIES": "10.0.0.0/8, 172.16.0.0/12"})
    assert ok.production and ok.trusted_proxies == ["10.0.0.0/8", "172.16.0.0/12"] and Settings.from_env({}).env == "development"


# ---------- logging ----------
def test_logs_are_json_with_request_id_and_redact_secrets():
    rec = logging.LogRecord("t", logging.INFO, "f", 1, "login failed Authorization: Bearer abc.def.ghi key=sk-ABCDEFGH12345 password=hunter2", (), None)
    rec.ctx = {"password": "hunter2", "api_key": "sk-1", "nested": {"token": "t"}, "ok": "fine"}
    flog.request_id.set("req-1")
    out = json.loads(flog.JsonFormatter().format(rec))
    blob = json.dumps(out)
    assert out["request_id"] == "req-1" and out["ctx"]["ok"] == "fine"
    for secret in ("hunter2", "abc.def.ghi", "sk-ABCDEFGH12345", "sk-1"):
        assert secret not in blob
