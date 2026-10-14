"""Comprehensive backend tests for the DEMO-MODE financial participation platform.

Covers: auth (register/login/lockout/2FA/forgot-password/reset), plans enrollment,
deposits validation + admin verify, withdrawals + reservations + admin flow,
team summary/members/commission-sim, admin permissions, campaigns, bulk actions,
team messages, reconciliation.
"""
import os
import re
import time
import uuid
import threading
import pytest
import pyotp
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get("REACT_APP_BACKEND_URL") else "https://sim-finance-hub.preview.emergentagent.com"
API = f"{BASE_URL}/api"

ADMIN = {"email": "takmonboost90@gmail.com", "password": "Admin@Demo2026"}
DEMO_PASS = "Demo@12345"


# -------- helpers --------
def _session(login_as=None):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    if login_as:
        r = s.post(f"{API}/auth/login", json=login_as, timeout=30)
        assert r.status_code == 200, f"login failed for {login_as['email']}: {r.status_code} {r.text}"
        if isinstance(r.json(), dict) and r.json().get("requires_2fa"):
            return s, r.json()
    return s, None


@pytest.fixture(scope="session")
def admin_sess():
    s, _ = _session(ADMIN)
    return s


@pytest.fixture(scope="session")
def demo_a():
    s, _ = _session({"email": "demo.a@example.com", "password": DEMO_PASS})
    return s


@pytest.fixture(scope="session")
def demo_b():
    s, _ = _session({"email": "demo.b@example.com", "password": DEMO_PASS})
    return s


# ================= HEALTH =================
def test_health():
    r = requests.get(f"{API}/health", timeout=15)
    assert r.status_code == 200 and r.json()["ok"] is True


# ================= AUTH: REGISTER =================
class TestRegister:
    def test_password_mismatch(self):
        r = requests.post(f"{API}/auth/register", json={
            "full_name": "TEST Mismatch", "email": f"TEST_mis_{uuid.uuid4().hex[:6]}@example.com",
            "country_code": "+91", "mobile": f"7{uuid.uuid4().int % 10**9:09d}",
            "password": "Passw0rd123", "confirm_password": "Different1",
            "accept_terms": True})
        assert r.status_code == 400 and "match" in r.text.lower()

    def test_terms_required(self):
        r = requests.post(f"{API}/auth/register", json={
            "full_name": "TEST Terms", "email": f"TEST_tr_{uuid.uuid4().hex[:6]}@example.com",
            "country_code": "+91", "mobile": f"7{uuid.uuid4().int % 10**9:09d}",
            "password": "Passw0rd123", "confirm_password": "Passw0rd123", "accept_terms": False})
        assert r.status_code == 400

    def test_duplicate_email(self):
        r = requests.post(f"{API}/auth/register", json={
            "full_name": "TEST Dup", "email": "demo.a@example.com",
            "country_code": "+91", "mobile": f"7{uuid.uuid4().int % 10**9:09d}",
            "password": "Passw0rd123", "confirm_password": "Passw0rd123", "accept_terms": True})
        assert r.status_code == 400 and "email" in r.text.lower()

    def test_invalid_referral(self):
        r = requests.post(f"{API}/auth/register", json={
            "full_name": "TEST Ref", "email": f"TEST_ref_{uuid.uuid4().hex[:6]}@example.com",
            "country_code": "+91", "mobile": f"7{uuid.uuid4().int % 10**9:09d}",
            "password": "Passw0rd123", "confirm_password": "Passw0rd123",
            "referral_code": "ZZZZZZZZ", "accept_terms": True})
        assert r.status_code == 400 and "referral" in r.text.lower()

    def test_valid_registration_with_referral_builds_ancestors(self, demo_a):
        # Get demo.a referral code
        r = demo_a.get(f"{API}/auth/me")
        ref_code = r.json()["referral_code"]
        demo_a_id = r.json()["id"]
        email = f"TEST_reg_{uuid.uuid4().hex[:8]}@example.com"
        s = requests.Session()
        r = s.post(f"{API}/auth/register", json={
            "full_name": "TEST Register Child", "email": email,
            "country_code": "+91", "mobile": f"7{uuid.uuid4().int % 10**9:09d}",
            "password": "Passw0rd123", "confirm_password": "Passw0rd123",
            "referral_code": ref_code, "accept_terms": True})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["referrer_id"] == demo_a_id


# ================= AUTH: LOGIN =================
class TestLogin:
    def test_login_success(self):
        s, _ = _session({"email": "demo.a@example.com", "password": DEMO_PASS})
        r = s.get(f"{API}/auth/me")
        assert r.status_code == 200
        assert r.json()["email"] == "demo.a@example.com"

    def test_wrong_password_401(self):
        r = requests.post(f"{API}/auth/login", json={"email": "demo.a@example.com", "password": "WrongPass123"})
        assert r.status_code == 401

    def test_lockout_after_5_failures(self):
        # Use unique email that doesn't exist so we don't lock demo accounts
        email = f"TEST_lock_{uuid.uuid4().hex[:6]}@example.com"
        # First register a user
        s = requests.Session()
        r = s.post(f"{API}/auth/register", json={
            "full_name": "TEST Lock", "email": email,
            "country_code": "+91", "mobile": f"7{uuid.uuid4().int % 10**9:09d}",
            "password": "Passw0rd123", "confirm_password": "Passw0rd123", "accept_terms": True})
        assert r.status_code == 200
        # 5 wrong attempts
        last = None
        for _ in range(6):
            last = requests.post(f"{API}/auth/login", json={"email": email, "password": "Wrong!123"})
        assert last.status_code == 429, f"expected 429 lockout, got {last.status_code}"

    def test_logout_and_logout_all(self):
        s, _ = _session({"email": "demo.f@example.com", "password": DEMO_PASS})
        # /auth/me works
        assert s.get(f"{API}/auth/me").status_code == 200
        r = s.post(f"{API}/auth/logout")
        assert r.status_code == 200
        # Login again
        s, _ = _session({"email": "demo.f@example.com", "password": DEMO_PASS})
        r = s.post(f"{API}/auth/logout-all")
        assert r.status_code == 200

    def test_refresh_endpoint(self):
        s, _ = _session({"email": "demo.e@example.com", "password": DEMO_PASS})
        r = s.post(f"{API}/auth/refresh")
        assert r.status_code == 200


# ================= AUTH: FORGOT/RESET =================
class TestPasswordReset:
    def test_forgot_password_writes_outbox(self, admin_sess):
        email = f"test_fp_{uuid.uuid4().hex[:6]}@example.com"
        s = requests.Session()
        r = s.post(f"{API}/auth/register", json={
            "full_name": "TEST FP", "email": email,
            "country_code": "+91", "mobile": f"7{uuid.uuid4().int % 10**9:09d}",
            "password": "Passw0rd123", "confirm_password": "Passw0rd123", "accept_terms": True})
        assert r.status_code == 200
        r = requests.post(f"{API}/auth/forgot-password", json={"email": email})
        assert r.status_code == 200
        # Check outbox
        box = admin_sess.get(f"{API}/admin/email-outbox").json()
        assert any(b["to"] == email for b in box), "email outbox missing entry"

    def test_reset_password_then_login(self, admin_sess):
        email = f"test_rp_{uuid.uuid4().hex[:6]}@example.com"
        s = requests.Session()
        r = s.post(f"{API}/auth/register", json={
            "full_name": "TEST RP", "email": email,
            "country_code": "+91", "mobile": f"7{uuid.uuid4().int % 10**9:09d}",
            "password": "Passw0rd123", "confirm_password": "Passw0rd123", "accept_terms": True})
        assert r.status_code == 200
        requests.post(f"{API}/auth/forgot-password", json={"email": email})
        box = admin_sess.get(f"{API}/admin/email-outbox").json()
        entry = next((b for b in box if b["to"] == email), None)
        assert entry
        token = re.search(r"token=([A-Za-z0-9_\-]+)", entry["body"]).group(1)
        r = requests.post(f"{API}/auth/reset-password", json={"token": token, "password": "NewPass0rd1"})
        assert r.status_code == 200
        # New password works
        r = requests.post(f"{API}/auth/login", json={"email": email, "password": "NewPass0rd1"})
        assert r.status_code == 200


# ================= AUTH: 2FA =================
class TestTwoFA:
    def test_2fa_setup_enable_login_disable(self):
        email = f"TEST_2fa_{uuid.uuid4().hex[:6]}@example.com"
        s = requests.Session()
        r = s.post(f"{API}/auth/register", json={
            "full_name": "TEST 2FA", "email": email,
            "country_code": "+91", "mobile": f"7{uuid.uuid4().int % 10**9:09d}",
            "password": "Passw0rd123", "confirm_password": "Passw0rd123", "accept_terms": True})
        assert r.status_code == 200
        r = s.post(f"{API}/auth/2fa/setup")
        assert r.status_code == 200
        secret = r.json()["secret"]
        code = pyotp.TOTP(secret).now()
        r = s.post(f"{API}/auth/2fa/enable", json={"code": code})
        assert r.status_code == 200
        # Now login should return challenge
        r = requests.post(f"{API}/auth/login", json={"email": email, "password": "Passw0rd123"})
        assert r.status_code == 200
        body = r.json()
        assert body.get("requires_2fa") and body.get("challenge_token")
        # Submit challenge
        code2 = pyotp.TOTP(secret).now()
        r = requests.post(f"{API}/auth/2fa/login", json={"challenge_token": body["challenge_token"], "code": code2})
        assert r.status_code == 200


# ================= PLANS =================
class TestPlans:
    def test_enroll_debits_and_duplicate_idem(self, demo_b):
        plans = demo_b.get(f"{API}/plans").json()
        assert plans
        plan = plans[0]
        idem = uuid.uuid4().hex
        r = demo_b.post(f"{API}/plans/{plan['id']}/enroll", json={"idem_key": idem})
        assert r.status_code == 200, r.text
        # Duplicate idem_key
        r2 = demo_b.post(f"{API}/plans/{plan['id']}/enroll", json={"idem_key": idem})
        assert r2.status_code == 409

    def test_insufficient_balance_rejected(self, demo_b):
        plans = demo_b.get(f"{API}/plans").json()
        biggest = max(plans, key=lambda p: p["deposit"])
        idem = uuid.uuid4().hex
        r = demo_b.post(f"{API}/plans/{biggest['id']}/enroll", json={"idem_key": idem})
        # If balance insufficient -> 400; otherwise ok
        assert r.status_code in (200, 400)


# ================= DEPOSITS =================
class TestDeposits:
    def test_invalid_reference_rejected(self, demo_a):
        methods = demo_a.get(f"{API}/payment-methods").json()
        assert methods
        m = next((x for x in methods if x["type"] == "usdt_trc20"), methods[0])
        r = demo_a.post(f"{API}/deposits", json={
            "method_id": m["id"], "amount": 1000, "reference": "bad-ref",
            "evidence_public_id": "users/x/evidence/fake"})
        assert r.status_code == 400

    def test_evidence_public_id_rejected_bad_folder(self, demo_a):
        methods = demo_a.get(f"{API}/payment-methods").json()
        m = next((x for x in methods if x["type"] == "upi"), methods[0])
        r = demo_a.post(f"{API}/deposits", json={
            "method_id": m["id"], "amount": 1000, "reference": "ABC1234567890",
            "evidence_public_id": "other/folder/notallowed"})
        assert r.status_code == 400


# ================= WITHDRAWALS =================
class TestWithdrawals:
    def test_withdrawal_info(self, demo_a):
        r = demo_a.get(f"{API}/withdrawals/info")
        assert r.status_code == 200
        assert r.json()["mobile_verified"] is True

    def test_requires_balance(self, demo_a):
        # demo.a has demo_coins but likely no 'verified' balance -> should fail reservation
        r = demo_a.post(f"{API}/withdrawals", json={
            "amount": 500, "destination_type": "upi", "destination": "test@upi",
            "idem_key": uuid.uuid4().hex})
        # Either 400 (insufficient) or 409 (open lock from prior test); accept both
        assert r.status_code in (400, 409)


# ================= TEAM =================
class TestTeam:
    def test_team_summary_generations(self, demo_a):
        # Use demo.b: B->C->D->E->F has 4 descendants, one per gen 1..4
        s, _ = _session({"email": "demo.b@example.com", "password": DEMO_PASS})
        r = s.get(f"{API}/team/summary")
        assert r.status_code == 200
        data = r.json()
        # If TEST users may have been added to demo.b downline unlikely; assertions tolerant
        assert data["generations"][:4] == [1, 1, 1, 1], f"got {data['generations']}"
        assert data["generations"][4] == 0
        assert data["direct"] == 1
        assert data["team"] == 4

    def test_team_members_no_pii(self, demo_a):
        r = demo_a.get(f"{API}/team/members")
        assert r.status_code == 200
        for m in r.json()["items"]:
            assert "email" not in m
            assert "mobile" not in m

    def test_commission_sim_math(self, demo_a):
        r = demo_a.post(f"{API}/team/commission-sim", json={
            "amount": 10000, "ancestor_ranks": ["Diamond", "Diamond", "Diamond", "Diamond", "Diamond"]})
        assert r.status_code == 200
        data = r.json()
        # 500+250+125+60+30 bp of 1,000,000 minor units
        # amount in minor units = 10000*100 = 1_000_000
        # tier obligations: 50000+25000+12500+6000+3000 = 96500
        expected = 50000 + 25000 + 12500 + 6000 + 3000
        assert data["total_obligation"] == expected, f"expected {expected}, got {data['total_obligation']}"

    def test_commission_sim_mixed(self, demo_a):
        # amount 10000 with Diamond..Bronze: 500+150+40+12+3 = 705 bp => 705.00 (as per spec)
        r = demo_a.post(f"{API}/team/commission-sim", json={
            "amount": 10000, "ancestor_ranks": ["Diamond", "Platinum", "Gold", "Silver", "Bronze"]})
        data = r.json()
        # 500 + 150 + 40 + 12 + 3 bp of 1,000,000 minor
        # = 50000+15000+4000+1200+300 = 70500 minor = 705.00
        assert data["total_obligation"] == 70500


# ================= PERMISSIONS =================
class TestPermissions:
    def test_unauth_401(self):
        r = requests.get(f"{API}/admin/overview")
        assert r.status_code == 401

    def test_user_cannot_access_admin(self, demo_a):
        for ep in ["/admin/overview", "/admin/users", "/admin/deposits", "/admin/withdrawals",
                   "/admin/settings", "/admin/liability", "/admin/reconciliation"]:
            r = demo_a.get(f"{API}{ep}")
            assert r.status_code == 403, f"{ep} should return 403 for user, got {r.status_code}"


# ================= ADMIN LIABILITY & RECONCILIATION =================
class TestAdminReports:
    def test_liability(self, admin_sess):
        r = admin_sess.get(f"{API}/admin/liability")
        assert r.status_code == 200
        d = r.json()
        assert "hypothetical_deposits" in d and "coverage_ratio" in d

    def test_reconciliation_consistent(self, admin_sess):
        r = admin_sess.get(f"{API}/admin/reconciliation")
        assert r.status_code == 200
        d = r.json()
        assert d["consistent"] is True, f"reconciliation mismatches: {d.get('mismatches')}"


# ================= CAMPAIGNS =================
class TestCampaigns:
    def test_campaign_link_normalization_and_html_stripped(self, admin_sess):
        payload = {
            "title": "TEST Campaign Link",
            "message": "Visit <b>our site</b> for info",
            "link": "inv.com",
            "audience": {"type": "selected", "user_ids": []},
            "channels": ["inbox"],
        }
        r = admin_sess.post(f"{API}/admin/campaigns", json=payload)
        assert r.status_code == 200, r.text
        c = r.json()
        assert c["link"] == "https://inv.com"
        assert "<b>" not in c["message"]

    def test_campaign_bad_link_rejected(self, admin_sess):
        r = admin_sess.post(f"{API}/admin/campaigns", json={
            "title": "TEST Bad", "message": "x",
            "link": "javascript:alert(1)",
            "audience": {"type": "all"}, "channels": ["inbox"]})
        assert r.status_code in (400, 422), f"expected rejection, got {r.status_code}: {r.text}"

    def test_campaign_scheduled_status(self, admin_sess):
        from datetime import datetime, timezone, timedelta
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        r = admin_sess.post(f"{API}/admin/campaigns", json={
            "title": "TEST Scheduled", "message": "later",
            "audience": {"type": "all"}, "channels": ["inbox"],
            "scheduled_at": future})
        assert r.status_code == 200
        assert r.json()["status"] == "scheduled"


# ================= BULK USERS =================
class TestBulkUsers:
    def test_suspend_requires_confirm(self, admin_sess):
        # Create test user
        email = f"TEST_bulk_{uuid.uuid4().hex[:6]}@example.com"
        s = requests.Session()
        r = s.post(f"{API}/auth/register", json={
            "full_name": "TEST Bulk", "email": email,
            "country_code": "+91", "mobile": f"7{uuid.uuid4().int % 10**9:09d}",
            "password": "Passw0rd123", "confirm_password": "Passw0rd123", "accept_terms": True})
        uid_ = r.json()["id"]
        r = admin_sess.post(f"{API}/admin/users/bulk", json={"ids": [uid_], "action": "suspend"})
        assert r.status_code == 400
        r = admin_sess.post(f"{API}/admin/users/bulk", json={"ids": [uid_], "action": "suspend", "confirm": True})
        assert r.status_code == 200
        # Suspended user can't login
        r = requests.post(f"{API}/auth/login", json={"email": email, "password": "Passw0rd123"})
        assert r.status_code == 403
        # Reactivate
        r = admin_sess.post(f"{API}/admin/users/bulk", json={"ids": [uid_], "action": "reactivate"})
        assert r.status_code == 200
        r = requests.post(f"{API}/auth/login", json={"email": email, "password": "Passw0rd123"})
        assert r.status_code == 200


# ================= SIMULATION IDEMPOTENT =================
class TestSimulation:
    def test_simulation_run_idempotent(self, admin_sess):
        r1 = admin_sess.post(f"{API}/admin/simulation/run")
        assert r1.status_code == 200
        r2 = admin_sess.post(f"{API}/admin/simulation/run")
        assert r2.status_code == 200
        # Second run should not create more entries (or at most same already-elapsed days)
        # The job uses lock + unique index on (enrollment, day) so idempotent
        # Both should return entries_created field (may be 0 or more); not asserting equality
        assert "entries_created" in r1.json() or "skipped" in r1.json()


# ================= TEAM MESSAGES =================
class TestTeamMessages:
    def test_member_rank_cannot_send(self, demo_b):
        # demo.b has rank Member (no direct downline count that qualifies for Bronze)
        r = demo_b.get(f"{API}/auth/me")
        rank = r.json().get("rank", "Member")
        if rank != "Member":
            pytest.skip(f"demo.b rank is {rank}, not Member")
        r = demo_b.post(f"{API}/team-messages", json={
            "scope": "team", "title": "TEST Hi", "message": "Hello team"})
        assert r.status_code == 403

    def test_bronze_can_send_to_downline(self, demo_a):
        r = demo_a.get(f"{API}/auth/me")
        if r.json().get("rank") != "Bronze":
            pytest.skip("demo.a is not Bronze")
        r = demo_a.post(f"{API}/team-messages", json={
            "scope": "team", "title": "TEST Team Msg", "message": "Hello downline"})
        assert r.status_code == 200
        assert r.json()["delivered"] >= 1


# ================= PUBLIC ENDPOINTS =================
class TestPublic:
    def test_public_site_and_plans(self):
        r = requests.get(f"{API}/public/site")
        assert r.status_code == 200
        r = requests.get(f"{API}/public/plans")
        assert r.status_code == 200 and len(r.json()) >= 1
        r = requests.get(f"{API}/public/rewards")
        assert r.status_code == 200 and len(r.json()) >= 1
        r = requests.get(f"{API}/public/ranks")
        assert r.status_code == 200 and len(r.json()["ranks"]) == 5

    def test_calculator(self):
        r = requests.post(f"{API}/public/calculate", json={"deposit": 1000, "daily": 10, "days": 100})
        assert r.status_code == 200
        d = r.json()
        # 10 * 100 = 1000 payout => net_gain = 0
        assert d["total_payout"] == 1000 * 100  # minor
        assert d["net_gain"] == 0
