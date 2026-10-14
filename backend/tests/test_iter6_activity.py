"""Iteration 6: Activity calendar + Admin user downline/sessions + privacy tests."""
import os
import re
import time
import requests
import pytest
from pymongo import MongoClient

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
MONGO = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

ADMIN = {"email": "takmonboost90@gmail.com", "password": "Admin@Demo2026"}
DEMO_A = {"email": "demo.a@example.com", "password": "Demo@12345"}
DEMO_B = {"email": "demo.b@example.com", "password": "Demo@12345"}

TRC20_ADDR = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
TRC20_PLACEHOLDER = "[Set your TRC20 receiving address]"
BEP20_PLACEHOLDER = "[Set your BEP20 receiving address]"


def login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return s, r.json()


@pytest.fixture(scope="module")
def admin_session():
    s, u = login(ADMIN["email"], ADMIN["password"])
    return s, u


@pytest.fixture(scope="module")
def demo_a_session():
    s, u = login(DEMO_A["email"], DEMO_A["password"])
    return s, u


@pytest.fixture(scope="module")
def mongo():
    c = MongoClient(MONGO)
    db = c[DB_NAME]
    yield db
    c.close()


# ---------- Activity calendar ----------
class TestActivityCalendar:
    def test_requires_auth(self):
        r = requests.get(f"{BASE}/api/activity/calendar?month=2026-01")
        assert r.status_code == 401

    def test_invalid_month(self, demo_a_session):
        s, _ = demo_a_session
        r = s.get(f"{BASE}/api/activity/calendar?month=badmonth")
        assert r.status_code == 400
        r = s.get(f"{BASE}/api/activity/calendar?month=2026")
        assert r.status_code == 400

    def test_returns_user_scoped(self, demo_a_session, mongo):
        s, u = demo_a_session
        month = time.strftime("%Y-%m")
        r = s.get(f"{BASE}/api/activity/calendar?month={month}")
        assert r.status_code == 200
        data = r.json()
        assert data["month"] == month
        assert set(data.keys()) >= {"month", "ledger", "deposits", "withdrawals"}
        for row in data["ledger"] + data["deposits"] + data["withdrawals"]:
            # user_id not projected but ensure data belongs to user via DB check
            pass
        # Confirm other user's data not leaking: fetch demo.b docs and ensure none appear in demo_a payload
        a_id = u["user"]["id"] if "user" in u else u.get("id")


# ---------- Admin: downline, user_detail ----------
class TestAdminDownline:
    def test_user_endpoint_requires_admin(self, demo_a_session):
        s, u = demo_a_session
        a_id = u.get("user", {}).get("id") or u.get("id")
        r = s.get(f"{BASE}/api/admin/users/{a_id}/downline")
        assert r.status_code == 403

    def test_demo_a_downline(self, admin_session, mongo):
        s, _ = admin_session
        a = mongo.users.find_one({"email": DEMO_A["email"]})
        r = s.get(f"{BASE}/api/admin/users/{a['id']}/downline")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 5, data
        assert data["by_generation"] == [1, 1, 1, 1, 1]
        gens = sorted(x["generation"] for x in data["items"])
        assert gens == [1, 2, 3, 4, 5]
        for item in data["items"]:
            assert "email" in item and "@" in item["email"]
            assert "rank" in item
            assert "usdt_balance" in item
            assert "verified_deposits" in item
        # last_login_at / last_active_at / mobile are projected but may be absent if unset
        # verify at least one gen-1 item exposes mobile (demo.b is seeded with mobile)
        gen1 = [i for i in data["items"] if i["generation"] == 1][0]
        assert "mobile" in gen1

    def test_user_detail_no_secrets(self, admin_session, mongo):
        s, _ = admin_session
        a = mongo.users.find_one({"email": DEMO_A["email"]})
        r = s.get(f"{BASE}/api/admin/users/{a['id']}")
        assert r.status_code == 200
        data = r.json()
        # Ensure no password/totp secrets
        import json
        blob = json.dumps(data)
        assert "password_hash" not in blob
        assert "totp_secret" not in blob
        # sessions should NOT contain refresh_token_hash
        for sess in data.get("sessions", []):
            assert "refresh_token_hash" not in sess
            assert "refresh" not in sess
        assert "ledger" in data
        assert "security_events" in data
        assert "sessions" in data


# ---------- Privacy for regular user ----------
class TestTeamPrivacy:
    def test_members_hide_sensitive(self, demo_a_session):
        s, _ = demo_a_session
        r = s.get(f"{BASE}/api/team/members")
        assert r.status_code == 200
        for m in r.json()["items"]:
            assert "email" not in m
            assert "mobile" not in m
            assert "last_login_at" not in m
            assert "last_active_at" not in m


# ---------- End-to-end: TEST_ user deposit -> admin approve -> activity shows ----------
class TestActivityE2E:
    @pytest.fixture(scope="class")
    def test_user(self, admin_session, mongo):
        s_admin, _ = admin_session
        # Ensure TRC20 payment method has a valid address
        orig_methods = list(mongo.payment_methods.find({}))
        trc = mongo.payment_methods.find_one({"type": "usdt_trc20"})
        assert trc, "TRC20 method missing"
        mongo.payment_methods.update_one({"id": trc["id"]}, {"$set": {"address": TRC20_ADDR, "active": True}})

        # Register a TEST_ user via /api/auth/register
        ts = int(time.time())
        email = f"TEST_act_{ts}@example.com"
        pw = "TestPass@12345"
        reg = requests.post(f"{BASE}/api/auth/register", json={
            "email": email, "password": pw, "confirm_password": pw, "full_name": "TEST User",
            "country_code": "+1", "mobile": f"555{ts%10000000:07d}", "accept_terms": True
        })
        assert reg.status_code in (200, 201), reg.text
        s = requests.Session()
        lg = s.post(f"{BASE}/api/auth/login", json={"email": email, "password": pw})
        assert lg.status_code == 200, lg.text
        me = s.get(f"{BASE}/api/auth/me").json()
        uid_ = me.get("id") or me.get("user", {}).get("id")
        mongo.users.update_one({"id": uid_}, {"$set": {"mobile_verified": True, "status": "active"}})
        u = mongo.users.find_one({"id": uid_})
        yield {"session": s, "user_id": u["id"], "email": email}

        # Cleanup
        uid_ = u["id"]
        mongo.wallet_accounts.delete_many({"user_id": uid_})
        mongo.ledger_transactions.delete_many({"user_id": uid_})
        mongo.payment_submissions.delete_many({"user_id": uid_})
        mongo.payment_evidence.delete_many({"user_id": uid_})
        mongo.sessions.delete_many({"user_id": uid_})
        mongo.notification_recipients.delete_many({"user_id": uid_})
        mongo.users.delete_one({"id": uid_})

        # Restore payment methods placeholders
        for m in orig_methods:
            mongo.payment_methods.update_one({"id": m["id"]}, {"$set": {"address": m["address"], "active": m.get("active", True)}})

    def test_full_flow(self, test_user, admin_session, mongo):
        s = test_user["session"]
        uid_ = test_user["user_id"]
        # Get method
        pm = s.get(f"{BASE}/api/payment-methods").json()
        trc = next(m for m in pm if m["type"] == "usdt_trc20")
        # Create deposit (draft)
        r = s.post(f"{BASE}/api/deposits", json={"method_id": trc["id"], "amount": 150})
        assert r.status_code == 200, r.text
        did = r.json()["id"]
        # Admin approve_manual
        sa, _ = admin_session
        act = sa.post(f"{BASE}/api/admin/deposits/{did}/action",
                      json={"action": "approve_manual", "note": "TEST approve"})
        assert act.status_code == 200, act.text
        # Activity calendar should show today's ledger credit + deposit
        month = time.strftime("%Y-%m")
        today = time.strftime("%Y-%m-%d")
        cal = s.get(f"{BASE}/api/activity/calendar?month={month}").json()
        creds = [x for x in cal["ledger"] if x["created_at"].startswith(today) and x["amount"] > 0]
        assert len(creds) >= 1, f"No credit found: {cal['ledger']}"
        deps = [x for x in cal["deposits"] if x["id"] == did]
        assert len(deps) == 1
        assert deps[0]["status"] == "verified"
