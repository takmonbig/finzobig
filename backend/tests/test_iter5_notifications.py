"""Iteration 5 backend tests - campaigns/notifications, team announcements, push, deposit presets, pixels."""
import os
import time
import uuid
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE}/api"

ADMIN = ("takmonboost90@gmail.com", "Admin@Demo2026")
DEMO_A = ("demo.a@example.com", "Demo@12345")
DEMO_B = ("demo.b@example.com", "Demo@12345")
VALID_TRC20 = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"


def _login(sess, email, password):
    r = sess.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"login failed {email}: {r.text}"
    return r.json()


@pytest.fixture(scope="module")
def admin_sess():
    s = requests.Session()
    _login(s, *ADMIN)
    return s


@pytest.fixture(scope="module")
def user_a_sess():
    s = requests.Session()
    _login(s, *DEMO_A)
    return s


@pytest.fixture(scope="module")
def user_b_sess():
    s = requests.Session()
    _login(s, *DEMO_B)
    return s


@pytest.fixture(scope="module")
def user_a(user_a_sess):
    return user_a_sess.get(f"{API}/auth/me").json()


@pytest.fixture(scope="module")
def user_b(user_b_sess):
    return user_b_sess.get(f"{API}/auth/me").json()


# ---------------- health / plans removal ----------------
def test_health_ok():
    r = requests.get(f"{API}/health", timeout=10)
    assert r.status_code == 200


def test_plans_route_redirect_served(user_a_sess):
    # Frontend-only redirect; backend /plans still exists for admin page, user list_plans is accessible via /plans
    r = user_a_sess.get(f"{API}/plans")
    assert r.status_code == 200


# ---------------- push endpoints ----------------
class TestPush:
    def test_subscribe_valid(self, user_a_sess):
        payload = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/TEST_" + uuid.uuid4().hex,
            "keys": {"p256dh": "BExampleKey123", "auth": "authtokenexample"},
        }
        r = user_a_sess.post(f"{API}/push/subscribe", json=payload)
        assert r.status_code == 200, r.text
        # unsubscribe
        r2 = user_a_sess.post(f"{API}/push/unsubscribe", json=payload)
        assert r2.status_code == 200

    def test_subscribe_invalid(self, user_a_sess):
        r = user_a_sess.post(f"{API}/push/subscribe", json={"endpoint": "http://notsecure/x", "keys": {}})
        assert r.status_code == 400

    def test_permission_states(self, user_a_sess):
        for state in ("later", "denied", "default"):
            r = user_a_sess.post(f"{API}/push/permission", json={"state": state})
            assert r.status_code == 200, f"state={state} -> {r.text}"
        r = user_a_sess.post(f"{API}/push/permission", json={"state": "nope"})
        assert r.status_code == 422

    def test_public_key(self, user_a_sess):
        r = user_a_sess.get(f"{API}/push/public-key")
        assert r.status_code == 200
        assert "publicKey" in r.json()


# ---------------- pixels ----------------
class TestPixels:
    created_ids = []

    def test_create_valid(self, admin_sess):
        pid = "123456789012345"
        # delete any existing
        existing = admin_sess.get(f"{API}/admin/pixels").json().get("items", [])
        for p in existing:
            if p["pixel_id"] == pid:
                admin_sess.delete(f"{API}/admin/pixels/{p['id']}")
        r = admin_sess.post(f"{API}/admin/pixels", json={"name": "TEST pixel", "pixel_id": pid, "events": ["PageView", "CompleteRegistration", "InitiateCheckout"], "active": True})
        assert r.status_code == 200, r.text
        TestPixels.created_ids.append(r.json()["id"])

    def test_public_pixels_served(self):
        r = requests.get(f"{API}/public/pixels")
        assert r.status_code == 200
        ids = [p["pixel_id"] for p in r.json()]
        assert "123456789012345" in ids

    def test_create_invalid_id(self, admin_sess):
        r = admin_sess.post(f"{API}/admin/pixels", json={"name": "x", "pixel_id": "123", "events": ["PageView"], "active": True})
        assert r.status_code in (400, 422)

    def test_pause_hides_from_public(self, admin_sess):
        pid_doc = next(p for p in admin_sess.get(f"{API}/admin/pixels").json()["items"] if p["pixel_id"] == "123456789012345")
        r = admin_sess.put(f"{API}/admin/pixels/{pid_doc['id']}", json={"name": pid_doc["name"], "pixel_id": "123456789012345", "events": ["PageView"], "active": False})
        assert r.status_code == 200
        pub = requests.get(f"{API}/public/pixels").json()
        assert all(p["pixel_id"] != "123456789012345" for p in pub)

    def test_cleanup(self, admin_sess):
        for pid in TestPixels.created_ids:
            admin_sess.delete(f"{API}/admin/pixels/{pid}")
        pub = requests.get(f"{API}/public/pixels").json()
        assert all(p["pixel_id"] != "123456789012345" for p in pub)


# ---------------- campaigns (super admin notifications) ----------------
class TestCampaigns:
    created = []

    def test_audience_preview_all(self, admin_sess):
        r = admin_sess.post(f"{API}/admin/campaigns/audience-preview", json={"type": "all"})
        assert r.status_code == 200
        assert r.json()["count"] > 0

    def test_invalid_audience(self, admin_sess):
        r = admin_sess.post(f"{API}/admin/campaigns", json={
            "title": "x", "message": "y", "audience": {"type": "selected"}, "channels": ["inbox"]
        })
        assert r.status_code in (400, 422)

    def test_create_selected_campaign(self, admin_sess, user_a):
        payload = {
            "title": "TEST_Campaign_notif",
            "message": "Hello from admin, visit www.example.com and https://docs.google.com/ or inv.com for info",
            "audience": {"type": "selected", "user_ids": [user_a["id"]]},
            "channels": ["inbox", "popup", "push"],
            "priority": "high",
        }
        r = admin_sess.post(f"{API}/admin/campaigns", json=payload)
        assert r.status_code == 200, r.text
        c = r.json()
        TestCampaigns.created.append(c["id"])
        assert c["title"] == "TEST_Campaign_notif"
        # dispatched immediately -> status should be 'sent' or similar
        # Verify recipient exists for user_a
        time.sleep(0.5)
        notifs = requests.Session()
        _login(notifs, *DEMO_A)
        inbox = notifs.get(f"{API}/notifications?size=50").json()
        assert any(n.get("campaign_id") == c["id"] for n in inbox["items"]), "Campaign notification not in demo.a inbox"

    def test_popups_endpoint(self, admin_sess, user_a):
        # Fetch popups for user_a
        s = requests.Session()
        _login(s, *DEMO_A)
        r = s.get(f"{API}/notifications/popups")
        assert r.status_code == 200
        # Should contain our campaign popup
        items = r.json()
        assert any(x.get("campaign_id") in TestCampaigns.created for x in items)

    def test_disable_hides_popup(self, admin_sess, user_a):
        if not TestCampaigns.created:
            pytest.skip("no campaign")
        cid = TestCampaigns.created[0]
        r = admin_sess.post(f"{API}/admin/campaigns/{cid}/disable", json={})
        assert r.status_code == 200
        s = requests.Session()
        _login(s, *DEMO_A)
        pop = s.get(f"{API}/notifications/popups").json()
        assert all(p.get("campaign_id") != cid for p in pop), "Disabled campaign still shows in popups"

    def test_scheduled_campaign_future(self, admin_sess, user_a):
        # Create scheduled 90 seconds in future - verify it is 'scheduled' not immediately dispatched
        from datetime import datetime, timedelta, timezone
        future = (datetime.now(timezone.utc) + timedelta(seconds=90)).isoformat().replace("+00:00", "Z")
        payload = {
            "title": "TEST_Scheduled",
            "message": "Scheduled message",
            "audience": {"type": "selected", "user_ids": [user_a["id"]]},
            "channels": ["inbox"],
            "scheduled_at": future,
        }
        r = admin_sess.post(f"{API}/admin/campaigns", json=payload)
        assert r.status_code == 200
        c = r.json()
        TestCampaigns.created.append(c["id"])
        assert c["status"] == "scheduled"
        assert c["scheduled_at"] is not None

    def test_cleanup(self, admin_sess):
        for cid in TestCampaigns.created:
            admin_sess.post(f"{API}/admin/campaigns/{cid}/disable", json={})
        # delete recipients + campaigns at db level - skip since no admin delete endpoint
        # Mark recipients as read & delete via mongo through unauth path not available.


# ---------------- team announcements ----------------
class TestTeamAnnouncements:
    sent_id = None

    def test_member_cannot_send(self):
        # demo.f has rank Member (no downline)
        s = requests.Session()
        _login(s, "demo.f@example.com", "Demo@12345")
        r = s.post(f"{API}/team-messages", json={"scope": "team", "title": "Hi", "message": "Test"})
        assert r.status_code == 403, r.text

    def test_bronze_sends_team(self, user_a_sess, user_a):
        r = user_a_sess.post(f"{API}/team-messages", json={"scope": "team", "title": "TEST_TeamAnnounce", "message": "Hello team, see https://example.com"})
        assert r.status_code == 200, r.text
        doc = r.json()
        TestTeamAnnouncements.sent_id = doc["id"]
        assert doc["delivered"] >= 1

    def test_downline_receives(self, user_b_sess):
        inbox = user_b_sess.get(f"{API}/notifications?size=50").json()
        assert any(n.get("team_message_id") == TestTeamAnnouncements.sent_id for n in inbox["items"]), "demo.b did not receive team announcement"

    def test_report_announcement(self, user_b_sess):
        inbox = user_b_sess.get(f"{API}/notifications?size=50").json()
        n = next((x for x in inbox["items"] if x.get("team_message_id") == TestTeamAnnouncements.sent_id), None)
        assert n
        r = user_b_sess.post(f"{API}/notifications/{n['id']}/report", json={"reason": "TEST_report_reason_spam"})
        assert r.status_code == 200

    def test_admin_sees_report_and_hides(self, admin_sess):
        msgs = admin_sess.get(f"{API}/admin/team-messages").json()
        msg = next((m for m in msgs if m["id"] == TestTeamAnnouncements.sent_id), None)
        assert msg
        assert msg["reports"] >= 1
        r = admin_sess.post(f"{API}/admin/team-messages/{msg['id']}/hide", json={})
        assert r.status_code == 200


# ---------------- deposit presets end-to-end (approve_manual) ----------------
class TestDepositFlow:
    did = None

    @classmethod
    def setup_class(cls):
        # Ensure TRC20 address is set to a valid value for test
        s = requests.Session()
        _login(s, *ADMIN)
        methods = s.get(f"{API}/admin/payment-methods").json()
        trc = next((m for m in methods if m["type"] == "usdt_trc20"), None)
        assert trc, "TRC20 method not found"
        cls.original_addr = trc["address"]
        s.put(f"{API}/admin/payment-methods/{trc['id']}", json={**{k: trc[k] for k in ("type", "label", "network", "min_amount", "max_amount", "active", "note") if k in trc}, "address": VALID_TRC20})
        cls.admin_sess = s

    @classmethod
    def teardown_class(cls):
        methods = cls.admin_sess.get(f"{API}/admin/payment-methods").json()
        trc = next((m for m in methods if m["type"] == "usdt_trc20"), None)
        if trc:
            cls.admin_sess.put(f"{API}/admin/payment-methods/{trc['id']}", json={**{k: trc[k] for k in ("type", "label", "network", "min_amount", "max_amount", "active", "note") if k in trc}, "address": cls.original_addr})

    def test_create_deposit_preset_100(self, user_b_sess):
        methods = user_b_sess.get(f"{API}/payment-methods").json()
        trc = next(m for m in methods if m["type"] == "usdt_trc20")
        r = user_b_sess.post(f"{API}/deposits", json={"method_id": trc["id"], "amount": 100})
        assert r.status_code == 200, r.text
        d = r.json()
        TestDepositFlow.did = d["id"]
        assert d["status"] == "draft"
        assert "expected_display" in d
        assert d["amount"] == 10000

    def test_submit_bad_hash(self, user_b_sess):
        # Must send evidence_public_id to pass pydantic; use dummy
        r = user_b_sess.post(f"{API}/deposits/{TestDepositFlow.did}/submit", json={"reference": "notahash", "evidence_public_id": "users/dummy/evidence/x"})
        assert r.status_code == 400  # bad hash before evidence check
        assert "hex" in r.text.lower() or "hash" in r.text.lower()

    def test_approve_manual_credits(self, user_b_sess):
        # Approve draft directly (approve_manual allowed on draft/pending/failed)
        admin = TestDepositFlow.admin_sess
        before_wallet = user_b_sess.get(f"{API}/wallet").json()["wallets"]
        before_avail = before_wallet.get("verified", {}).get("available", 0)
        res = admin.post(f"{API}/admin/deposits/{TestDepositFlow.did}/action", json={"action": "approve_manual", "note": "TEST manual approval"})
        assert res.status_code == 200, res.text
        time.sleep(0.5)
        after_wallet = user_b_sess.get(f"{API}/wallet").json()["wallets"]
        assert after_wallet["verified"]["available"] == before_avail + 10000

    def test_double_approve_fails(self):
        admin = TestDepositFlow.admin_sess
        r = admin.post(f"{API}/admin/deposits/{TestDepositFlow.did}/action", json={"action": "approve_manual", "note": "TEST duplicate"})
        assert r.status_code == 400

    def test_withdraw_reserved_release(self, user_b_sess):
        # Request withdrawal of $100 (min)
        w = user_b_sess.post(f"{API}/withdrawals", json={"destination_type": "usdt_trc20", "destination": VALID_TRC20, "amount": 100, "idem_key": uuid.uuid4().hex})
        assert w.status_code == 200, w.text
        wd = w.json()
        wid = wd["id"]
        wallet_after_req = user_b_sess.get(f"{API}/wallet").json()["wallets"]
        assert wallet_after_req["verified"]["reserved"] >= 10000
        admin = TestDepositFlow.admin_sess
        # Reject
        r = admin.post(f"{API}/admin/withdrawals/{wid}/action", json={"action": "rejected", "note": "TEST reject"})
        assert r.status_code == 200
        wallet_after_rej = user_b_sess.get(f"{API}/wallet").json()["wallets"]
        assert wallet_after_rej["verified"]["reserved"] < wallet_after_req["verified"]["reserved"]
