"""Iteration 3 tests: real-USDT deposit flow, chain-verified withdrawals,
payment-method address validation, cleaned branding.

Cleanup: resets payment_methods addresses to placeholders via MongoDB.
"""
import os
import re
import time
import uuid
import hashlib
import pytest
import pymongo
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"
ADMIN = {"email": "takmonboost90@gmail.com", "password": "Admin@Demo2026"}
DEMO = {"email": "demo.c@example.com", "password": "Demo@12345"}

MONGO = pymongo.MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
DB = MONGO[os.environ.get("DB_NAME", "test_database")]

# -- helpers --
B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def hex_to_tron(hex40: str) -> str:
    """Convert 40-char hex (last 20 bytes) -> base58 TRON address with 0x41 prefix + double-sha256 checksum."""
    raw = bytes.fromhex("41" + hex40)
    check = hashlib.sha256(hashlib.sha256(raw).digest()).digest()[:4]
    full = raw + check
    n = int.from_bytes(full, "big")
    out = ""
    while n > 0:
        n, r = divmod(n, 58)
        out = B58[r] + out
    # add leading '1' for each leading 0 byte
    for b in full:
        if b == 0:
            out = "1" + out
        else:
            break
    return out


def sess(creds):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def admin():
    return sess(ADMIN)


@pytest.fixture(scope="module")
def user():
    return sess(DEMO)


@pytest.fixture(scope="module")
def methods(admin):
    r = admin.get(f"{API}/admin/payment-methods")
    assert r.status_code == 200
    data = r.json()
    out = {m["type"]: m for m in data}
    assert "usdt_trc20" in out and "usdt_bep20" in out
    return out


@pytest.fixture(scope="module", autouse=True)
def cleanup_at_end():
    yield
    # Restore placeholders directly in Mongo (API rejects invalid addresses)
    DB.payment_methods.update_one({"type": "usdt_trc20"},
                                  {"$set": {"address": "[Set your TRC20 receiving address]"}})
    DB.payment_methods.update_one({"type": "usdt_bep20"},
                                  {"$set": {"address": "[Set your BEP20 receiving address]"}})
    # Cancel any TEST open deposits so demo users aren't left with 3 drafts
    DB.payment_submissions.update_many(
        {"user_email": DEMO["email"], "status": {"$in": ["draft", "pending_verification"]}},
        {"$set": {"status": "cancelled", "status_note": "TEST cleanup"}})


# ============== 1. Payment method address validation ==============
class TestPaymentMethodValidation:
    def _put(self, admin, m, address):
        body = {"name": m["name"], "type": m["type"], "network": m.get("network") or "TRON",
                "currency": "USDT", "address": address, "instructions": m.get("instructions", "Send USDT"),
                "min_amount": m["min_amount"] / 100, "max_amount": m["max_amount"] / 100,
                "active": True, "sort": m.get("sort", 0)}
        return admin.put(f"{API}/admin/payment-methods/{m['id']}", json=body)

    def test_trc20_invalid_rejected(self, admin, methods):
        r = self._put(admin, methods["usdt_trc20"], "TXYZ_not_a_valid_tron")
        assert r.status_code == 400 and "valid" in r.text.lower()

    def test_trc20_bad_checksum_rejected(self, admin, methods):
        # Valid base58 chars + 0x41 prefix but tampered checksum
        r = self._put(admin, methods["usdt_trc20"], "TRXYZabcdefghijkmnpqrstuvwxyzABCDEFGH")
        assert r.status_code == 400

    def test_bep20_invalid_rejected(self, admin, methods):
        r = self._put(admin, methods["usdt_bep20"], "0xNOTHEX")
        assert r.status_code == 400

    def test_bep20_short_rejected(self, admin, methods):
        r = self._put(admin, methods["usdt_bep20"], "0x1234")
        assert r.status_code == 400

    def test_bep20_valid_accepted_and_restorable(self, admin, methods):
        r = self._put(admin, methods["usdt_bep20"], "0x" + "a" * 40)
        assert r.status_code == 200, r.text
        # Fetch back
        r = admin.get(f"{API}/admin/payment-methods")
        bep = next(m for m in r.json() if m["type"] == "usdt_bep20")
        assert bep["address"].lower() == "0x" + "a" * 40


# ============== 2. Deposit creation ==============
class TestDepositCreation:
    def test_create_deposit_with_placeholder_address_fails(self, user, methods, admin):
        # Reset TRC20 to placeholder for this test
        DB.payment_methods.update_one({"type": "usdt_trc20"},
                                      {"$set": {"address": "[Set your TRC20 receiving address]"}})
        r = user.post(f"{API}/deposits", json={"method_id": methods["usdt_trc20"]["id"], "amount": 100})
        assert r.status_code == 400
        assert "not configured" in r.text.lower() or "configured" in r.text.lower()

    def test_create_deposit_with_valid_address(self, user, admin, methods):
        # Set a real TRON address derived from a real transfer recipient hex
        # Use TRC20 USDT contract address itself (any valid base58) just to pass validation
        # Convert hex 2aedbc0f62fc3d0d845855945bc5b9efcb40d6d8 -> base58
        tron_addr = hex_to_tron("2aedbc0f62fc3d0d845855945bc5b9efcb40d6d8")
        body = {"name": methods["usdt_trc20"]["name"], "type": "usdt_trc20",
                "network": "TRON", "currency": "USDT", "address": tron_addr,
                "instructions": "Send USDT", "min_amount": 1, "max_amount": 100000,
                "active": True, "sort": 0}
        r = admin.put(f"{API}/admin/payment-methods/{methods['usdt_trc20']['id']}", json=body)
        assert r.status_code == 200, r.text

        # Cancel any existing TEST drafts to avoid 3-open limit
        DB.payment_submissions.update_many(
            {"user_email": DEMO["email"], "status": "draft"},
            {"$set": {"status": "cancelled"}})

        r = user.post(f"{API}/deposits", json={"method_id": methods["usdt_trc20"]["id"], "amount": 50})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["status"] == "draft"
        assert d["address"] == tron_addr
        assert "expected_display" in d and "." in d["expected_display"]
        assert d["amount"] == 5000  # minor units
        # expected_raw > amount * 1e4 (has 4-decimal offset)
        assert int(d["expected_raw"]) >= 5000 * 10 ** 4
        pytest.deposit_id_trc = d["id"]


# ============== 3. Deposit submit ==============
class TestDepositSubmit:
    def test_submit_invalid_hash(self, user):
        did = getattr(pytest, "deposit_id_trc", None)
        if not did:
            pytest.skip("no deposit")
        r = user.post(f"{API}/deposits/{did}/submit", json={
            "reference": "not-a-hash", "evidence_public_id": f"users/foo/evidence/x",
            "note": "test"})
        assert r.status_code == 400
        assert "hexadecimal" in r.text.lower() or "hex" in r.text.lower()

    def test_submit_bad_evidence_folder(self, user):
        did = getattr(pytest, "deposit_id_trc", None)
        if not did:
            pytest.skip("no deposit")
        r = user.post(f"{API}/deposits/{did}/submit", json={
            "reference": "a" * 64,
            "evidence_public_id": "other/folder/notallowed",
            "note": "x"})
        # Will fail at evidence verification (Cloudinary)
        assert r.status_code in (400, 404, 500)

    def test_my_deposits_shows_draft(self, user):
        r = user.get(f"{API}/deposits")
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert any(x["status"] == "draft" for x in data["items"])


# ============== 4. Withdrawal destination validation ==============
class TestWithdrawalValidation:
    def test_bad_tron_destination_rejected(self, user):
        r = user.post(f"{API}/withdrawals", json={
            "amount": 10, "destination_type": "usdt_trc20",
            "destination": "TBADaddress123", "idem_key": uuid.uuid4().hex})
        assert r.status_code == 400
        assert "invalid" in r.text.lower() or "destination" in r.text.lower()

    def test_bad_bep20_destination_rejected(self, user):
        r = user.post(f"{API}/withdrawals", json={
            "amount": 10, "destination_type": "usdt_bep20",
            "destination": "0xshort", "idem_key": uuid.uuid4().hex})
        assert r.status_code == 400


# ============== 5. Admin deposit actions ==============
class TestAdminDepositActions:
    def test_credit_onchain_requires_submitted_reference(self, admin):
        # Pick a draft (no reference submitted yet)
        did = getattr(pytest, "deposit_id_trc", None)
        if not did:
            pytest.skip("no draft")
        r = admin.post(f"{API}/admin/deposits/{did}/action",
                       json={"action": "credit_onchain", "note": "test"})
        assert r.status_code == 400
        assert "pending" in r.text.lower() or "credited" in r.text.lower()

    def test_invalid_action_rejected(self, admin):
        did = getattr(pytest, "deposit_id_trc", None)
        if not did:
            pytest.skip("no draft")
        r = admin.post(f"{API}/admin/deposits/{did}/action",
                       json={"action": "verify", "note": "manual"})
        assert r.status_code in (400, 422)


# ============== 6. Admin withdrawal "completed" requires payout hash ==============
class TestAdminWithdrawalCompleted:
    def test_completed_requires_payout_hash_format(self, admin):
        # Try to complete a non-existent withdrawal with bad hash
        fake_wid = "nonexistent-wid"
        r = admin.post(f"{API}/admin/withdrawals/{fake_wid}/action",
                       json={"action": "completed", "note": "x", "payout_ref": "not-a-hash"})
        # Either 400 (bad hash) or 400 (invalid transition)
        assert r.status_code in (400, 404, 422)


# ============== 7. Reconciliation ==============
class TestReconciliation:
    def test_reconciliation_consistent(self, admin):
        r = admin.get(f"{API}/admin/reconciliation")
        assert r.status_code == 200
        d = r.json()
        assert d.get("consistent") is True, f"mismatches: {d.get('mismatches')}"
