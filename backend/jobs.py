import asyncio
from datetime import datetime, timedelta

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from core import db, iso, now, uid, get_settings, post_ledger, notify_user, send_push, log


async def acquire_lock(name, seconds):
    try:
        r = await db.job_locks.find_one_and_update(
            {"name": name, "$or": [{"until": {"$lt": iso()}}, {"until": None}]},
            {"$set": {"until": iso(now() + timedelta(seconds=seconds))}}, upsert=True, return_document=ReturnDocument.AFTER)
        return bool(r)
    except DuplicateKeyError:
        return False


async def release_lock(name):
    await db.job_locks.update_one({"name": name}, {"$set": {"until": None}})


async def run_simulation():
    """Idempotent: each (enrollment, day) entry is unique; ledger postings use idempotency keys."""
    if not await acquire_lock("simulation", 120):
        return {"skipped": "already running"}
    created = 0
    try:
        s = await get_settings()
        day_s = max(int(s["simulation_day_seconds"]), 60)
        async for e in db.demo_plan_enrollments.find({"status": "active"}, {"_id": 0}):
            elapsed = int((now() - datetime.fromisoformat(e["started_at"])).total_seconds() // day_s)
            target = min(elapsed, e["duration_days"])
            for day in range(e["days_credited"] + 1, target + 1):
                try:
                    await db.demo_calculation_entries.insert_one({"id": uid(), "enrollment_id": e["id"], "user_id": e["user_id"], "day_index": day,
                                                                  "amount": e["daily"], "hypothetical": True, "created_at": iso()})
                except DuplicateKeyError:
                    continue
                await post_ledger(e["user_id"], "sim_earnings", e["daily"], "simulation_accrual", f"Day {day} — {e['plan_name']}", ref=e["id"], idem_key=f"sim:{e['id']}:{day}")
                created += 1
            if target > e["days_credited"]:
                done = target >= e["duration_days"]
                await db.demo_plan_enrollments.update_one({"id": e["id"]}, {"$set": {"days_credited": target, "credited_total": target * e["daily"], "status": "completed" if done else "active"}})
                if done:
                    await notify_user(e["user_id"], "Plan completed", f"{e['plan_name']} has finished its term.", kind="plan")
    finally:
        await release_lock("simulation")
    return {"entries_created": created}


async def resolve_audience(aud):
    base = {"role": "user", "status": "active", "deleted": {"$ne": True}}
    t = aud.get("type")
    if t == "selected":
        base["id"] = {"$in": aud.get("user_ids") or []}
    elif t == "group":
        base["group"] = aud.get("group")
    elif t == "push_enabled":
        base["push_permission"] = "granted"
    elif t == "push_disabled":
        base["push_permission"] = {"$ne": "granted"}
    elif t == "active_recent":
        base["last_active_at"] = {"$gte": iso(now() - timedelta(days=int(aud.get("days") or 7)))}
    elif t == "inactive":
        base["$or"] = [{"last_active_at": {"$lt": iso(now() - timedelta(days=int(aud.get("days") or 30)))}}, {"last_active_at": None}]
    return [u["id"] for u in await db.users.find(base, {"_id": 0, "id": 1}).to_list(200000)]


async def dispatch_campaign(cid):
    c = await db.notification_campaigns.find_one_and_update({"id": cid, "status": "scheduled"}, {"$set": {"status": "sending", "sending_at": iso()}},
                                                            projection={"_id": 0}, return_document=ReturnDocument.AFTER)
    if not c:
        return None
    ids = await resolve_audience(c["audience"])
    stats = {"eligible": len(ids), "permission_enabled": 0, "permission_denied": 0, "subscription_unavailable": 0, "inbox_delivered": 0,
             "push_sent": 0, "push_failed": 0, "push_skipped_opt_out": 0, "clicked": 0}
    users = {u["id"]: u for u in await db.users.find({"id": {"$in": ids}}, {"_id": 0, "id": 1, "push_permission": 1, "prefs": 1}).to_list(200000)}
    in_app = any(ch in c["channels"] for ch in ("inbox", "popup", "dashboard"))
    for i in ids:
        u = users.get(i, {})
        perm = u.get("push_permission")
        stats["permission_enabled" if perm == "granted" else "permission_denied" if perm == "denied" else "subscription_unavailable"] += 1
        n = None
        if in_app or "push" in c["channels"]:
            n = await notify_user(i, c["title"], c["message"], kind="campaign", link=c["link"], image_url=c["image_url"], campaign_id=cid,
                                  cta_label=c["cta_label"], popup="popup" in c["channels"], priority=c["priority"], expires_at=c.get("expires_at"))
            stats["inbox_delivered"] += 1
        if "push" in c["channels"]:
            if not (u.get("prefs") or {}).get("marketing_push", True):
                stats["push_skipped_opt_out"] += 1
                continue
            r = await send_push(i, {"title": c["title"], "body": c["message"][:180], "url": c["link"] or "/app/notifications", "image": c["image_url"], "nid": n["id"] if n else None})
            if r == "sent":
                stats["push_sent"] += 1
            elif r == "failed":
                stats["push_failed"] += 1
            await db.notification_recipients.update_one({"id": n["id"]}, {"$set": {"push_status": r}})
    await db.notification_campaigns.update_one({"id": cid}, {"$set": {"status": "sent", "sent_at": iso(), "stats": stats}})
    return await db.notification_campaigns.find_one({"id": cid}, {"_id": 0})


async def dispatch_due():
    async for c in db.notification_campaigns.find({"status": "scheduled", "scheduled_at": {"$ne": None, "$lte": iso()}}, {"_id": 0, "id": 1}):
        await dispatch_campaign(c["id"])


async def scheduler_loop():
    while True:
        try:
            await run_simulation()
            await dispatch_due()
            from chain import recheck_deposits
            await recheck_deposits()
        except Exception as e:
            log.exception(f"scheduler error: {e}")
        await asyncio.sleep(30)
