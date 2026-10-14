from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

import os
import asyncio
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from starlette.middleware.cors import CORSMiddleware

from core import db, client, iso, uid, hash_password, verify_password, ensure_wallets, post_ledger, get_settings, user_from_token, ws_manager, recompute_ancestors
from routes_auth import router as auth_router, new_referral_code
from routes_user import router as user_router
from routes_admin import router as admin_router, plan_doc, PlanIn
from jobs import scheduler_loop
from seed_data import PLANS, PLAN_NAMES, REWARDS, reward_extra, METHODS, CONTENT

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
app = FastAPI(title="Finzo.cc API")
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(admin_router)
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=os.environ["CORS_ORIGINS"].split(","), allow_methods=["*"], allow_headers=["*"])


@app.get("/api/health")
async def health():
    return {"ok": True}


@app.websocket("/api/ws")
async def ws_endpoint(ws: WebSocket):
    try:
        user = await user_from_token(ws.cookies.get("access_token"))
    except Exception:
        await ws.close(code=4401)
        return
    await ws.accept()
    await ws_manager.connect(user["id"], ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(user["id"], ws)


async def create_indexes():
    u = db.users
    await u.create_index("id", unique=True)
    await u.create_index("email", unique=True)
    await u.create_index("referral_code", unique=True)
    await u.create_index([("country_code", 1), ("mobile", 1)], unique=True)
    for i in range(5):
        await u.create_index(f"ancestors.{i}")
    await db.sessions.create_index("id", unique=True)
    await db.sessions.create_index("user_id")
    await db.login_attempts.create_index("identifier")
    await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)
    await db.rate_limits.create_index("expires", expireAfterSeconds=0)
    await db.rate_limits.create_index([("key", 1), ("at", 1)])
    await db.wallet_accounts.create_index([("user_id", 1), ("account", 1)], unique=True)
    await db.ledger_transactions.create_index("idem_key", unique=True, sparse=True)
    await db.ledger_transactions.create_index([("user_id", 1), ("created_at", -1)])
    await db.demo_calculation_entries.create_index([("enrollment_id", 1), ("day_index", 1)], unique=True)
    await db.demo_plan_enrollments.create_index("idem_key", unique=True)
    idx = await db.payment_submissions.index_information()
    if "method_type_1_reference_norm_1" in idx and "partialFilterExpression" not in idx["method_type_1_reference_norm_1"]:
        await db.payment_submissions.drop_index("method_type_1_reference_norm_1")
    await db.payment_submissions.create_index([("method_type", 1), ("reference_norm", 1)], unique=True, partialFilterExpression={"reference_norm": {"$type": "string"}})
    await db.payment_submissions.create_index([("status", 1), ("next_check_at", 1)])
    await db.withdrawal_requests.create_index("payout_ref_norm", unique=True, partialFilterExpression={"payout_ref_norm": {"$type": "string"}})
    await db.withdrawal_requests.create_index("open_lock", unique=True, sparse=True)
    await db.withdrawal_requests.create_index("idem_key", unique=True, sparse=True)
    await db.push_subscriptions.create_index("endpoint", unique=True)
    await db.notification_recipients.create_index([("user_id", 1), ("created_at", -1)])
    await db.notification_recipients.create_index("campaign_id")
    await db.job_locks.create_index("name", unique=True)
    await db.website_content.create_index("key", unique=True)
    await db.rewards.create_index("slug", unique=True)
    await db.admin_audit_logs.create_index("created_at")
    await db.security_events.create_index("created_at")


async def seed_user(email, password, name, role="user", referrer=None, mobile="9000000000"):
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        if not verify_password(password, existing["password_hash"]):
            await db.users.update_one({"email": email}, {"$set": {"password_hash": hash_password(password)}})
        return existing
    ancestors = [referrer["id"]] + referrer.get("ancestors", [])[:19] if referrer else []
    user = {"id": uid(), "full_name": name, "email": email, "country_code": "+91", "mobile": mobile, "mobile_verified": True, "email_verified": True,
            "password_hash": hash_password(password), "role": role, "status": "active", "kyc_status": "verified" if role == "super_admin" else "not_submitted",
            "referral_code": await new_referral_code(), "referrer_id": referrer["id"] if referrer else None, "ancestors": ancestors, "rank": "Member",
            "totp_enabled": False, "registration_ip": "seed", "group": "demo" if role == "user" else "staff",
            "prefs": {"allow_team_messages": True, "marketing_push": True, "push_reminders": True}, "created_at": iso(), "deleted": False}
    await db.users.insert_one(dict(user))
    await ensure_wallets(user["id"])
    if role == "user":
        s = await get_settings()
        await post_ledger(user["id"], "demo_coins", int(s["signup_demo_grant"]) * 100, "signup_grant", "Welcome coins", idem_key=f"grant:{user['id']}")
        if referrer:
            await db.referral_relationships.insert_one({"id": uid(), "user_id": user["id"], "referrer_id": referrer["id"], "ancestors": ancestors, "created_at": iso()})
        await recompute_ancestors(user)
    return user


async def seed():
    await get_settings()
    await seed_user(os.environ["ADMIN_EMAIL"].lower(), os.environ["ADMIN_PASSWORD"], "Super Admin", "super_admin", mobile="9999999999")
    if not await db.demo_plan_definitions.count_documents({}):
        for (dep, daily, days), name in zip(PLANS, PLAN_NAMES):
            await db.demo_plan_definitions.insert_one(plan_doc(PlanIn(name=f"{name} Simulation", description=f"Hypothetical {days}-day illustration for a {dep:,} coin simulated deposit.",
                                                                      deposit=dep, daily=daily, duration_days=days, payout_schedule="daily")))
    for r in REWARDS:
        await db.rewards.update_one({"slug": r["slug"]}, {"$setOnInsert": {"id": uid(), **r, "milestone": r["milestone"] * 100, **reward_extra(r), "created_at": iso()}}, upsert=True)
    if not await db.payment_methods.count_documents({}):
        for i, m in enumerate(METHODS):
            await db.payment_methods.insert_one({"id": uid(), **m, "qr_url": None, "active": True, "test_mode": True, "sort": i, "created_at": iso()})
    for k, v in CONTENT.items():
        await db.website_content.update_one({"key": k}, {"$setOnInsert": {"key": k, "value": v, "updated_at": iso()}}, upsert=True)
    prev = None
    for i, letter in enumerate("ABCDEF"):
        prev = await seed_user(f"demo.{letter.lower()}@example.com", os.environ["DEMO_USER_PASSWORD"], f"Demo Person {letter}", referrer=prev, mobile=f"90000000{i:02d}")


@app.on_event("startup")
async def startup():
    await create_indexes()
    await seed()
    asyncio.create_task(scheduler_loop())


@app.on_event("shutdown")
async def shutdown():
    client.close()
