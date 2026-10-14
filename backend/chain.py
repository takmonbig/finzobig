import os
import re
import hashlib
from datetime import datetime, timedelta

import httpx

from core import db, iso, now, post_ledger, notify_user, log

TRANSFER = "ddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
NET = {"usdt_trc20": "tron", "usdt_bep20": "bsc"}
NET_LABEL = {"tron": "TRON (TRC20)", "bsc": "BNB Smart Chain (BEP20)"}
DEC = {"tron": 6, "bsc": 18}
B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


class ChainError(Exception):
    pass


def tron_hex(addr):
    n = 0
    for c in addr or "":
        if c not in B58:
            return None
        n = n * 58 + B58.index(c)
    if n.bit_length() > 200:
        return None
    raw = n.to_bytes(25, "big")
    if raw[0] != 0x41 or hashlib.sha256(hashlib.sha256(raw[:-4]).digest()).digest()[:4] != raw[-4:]:
        return None
    return raw[1:21].hex()


def valid_address(mtype, addr):
    addr = (addr or "").strip()
    if NET.get(mtype) == "tron":
        return tron_hex(addr) is not None
    return bool(re.fullmatch(r"0x[0-9a-fA-F]{40}", addr))


def addr_key(mtype, addr):
    return tron_hex(addr.strip()) if NET[mtype] == "tron" else addr.strip().lower()[2:]


def norm_hash(mtype, h):
    h = (h or "").strip().lower()
    h = h[2:] if h.startswith("0x") else h
    if not re.fullmatch(r"[0-9a-f]{64}", h):
        return None
    return h if NET[mtype] == "tron" else "0x" + h


def raw_units(mtype, cents):
    return int(cents) * 10 ** (DEC[NET[mtype]] - 2)


def cents_from_raw(mtype, raw):
    return int(raw) * 100 // 10 ** DEC[NET[mtype]]


def display_raw(mtype, raw):
    d = DEC[NET[mtype]]
    whole, frac = divmod(int(raw), 10 ** d)
    return f"{whole}.{str(frac).rjust(d, '0')[:4]}"


def required_confirmations(mtype):
    return int(os.environ["TRON_MIN_CONFIRMATIONS"] if NET[mtype] == "tron" else os.environ["BSC_MIN_CONFIRMATIONS"])


async def _tron(h):
    base = os.environ["TRONGRID_BASE"]
    key = os.environ.get("TRONGRID_API_KEY")
    headers = {"TRON-PRO-API-KEY": key} if key else {}
    contract = tron_hex(os.environ["TRON_USDT_CONTRACT"])
    async with httpx.AsyncClient(timeout=15) as c:
        info = (await c.post(f"{base}/wallet/gettransactioninfobyid", json={"value": h}, headers=headers)).raise_for_status().json()
        if not info or "id" not in info or not info.get("blockNumber"):
            return {"state": "not_found"}
        head = (await c.post(f"{base}/wallet/getnowblock", json={}, headers=headers)).raise_for_status().json()
    if info.get("receipt", {}).get("result") != "SUCCESS":
        return {"state": "failed"}
    transfers = []
    for i, lg in enumerate(info.get("log", [])):
        topics = [t.lower().removeprefix("0x") for t in lg.get("topics", [])]
        if len(topics) >= 3 and topics[0] == TRANSFER and lg.get("address", "").lower()[-40:] == contract:
            transfers.append({"to": topics[2][-40:], "raw": int(lg.get("data") or "0", 16), "index": i})
    conf = head["block_header"]["raw_data"]["number"] - info["blockNumber"] + 1
    return {"state": "mined", "confirmations": conf, "timestamp": info.get("blockTimeStamp", 0) // 1000, "transfers": transfers}


async def _rpc(c, method, params):
    r = (await c.post(os.environ["BSC_RPC_URL"], json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params})).raise_for_status().json()
    if r.get("error"):
        raise ChainError(str(r["error"]))
    return r["result"]


async def _bsc(h):
    contract = os.environ["BSC_USDT_CONTRACT"].lower()
    async with httpx.AsyncClient(timeout=15) as c:
        rc = await _rpc(c, "eth_getTransactionReceipt", [h])
        if not rc:
            return {"state": "not_found"}
        if rc.get("status") != "0x1":
            return {"state": "failed"}
        head = int(await _rpc(c, "eth_blockNumber", []), 16)
        blk = await _rpc(c, "eth_getBlockByNumber", [rc["blockNumber"], False])
    transfers = []
    for i, lg in enumerate(rc.get("logs", [])):
        topics = [t.lower().removeprefix("0x") for t in lg.get("topics", [])]
        if len(topics) >= 3 and topics[0] == TRANSFER and lg.get("address", "").lower() == contract:
            transfers.append({"to": topics[2][-40:], "raw": int(lg.get("data") or "0x0", 16), "index": i})
    return {"state": "mined", "confirmations": head - int(rc["blockNumber"], 16) + 1, "timestamp": int(blk["timestamp"], 16), "transfers": transfers}


async def find_transfer(mtype, tx_hash, to_address, expected_raw=None):
    """Look up a USDT transfer to `to_address` inside `tx_hash`. Raises ChainError on lookup problems."""
    try:
        r = await (_tron(tx_hash) if NET[mtype] == "tron" else _bsc(tx_hash))
    except (httpx.HTTPError, KeyError, ValueError) as e:
        raise ChainError(str(e))
    r["required"] = required_confirmations(mtype)
    key = addr_key(mtype, to_address)
    to_us = [t for t in r.get("transfers", []) if t["to"] == key]
    r["to_us"] = bool(to_us)
    r["match"] = next((t for t in to_us if expected_raw is None or t["raw"] == int(expected_raw)), None)
    if r["state"] == "mined":
        r["state"] = "confirmed" if r["confirmations"] >= r["required"] else "pending"
    return r


async def _set(did, status, note, extra=None, from_status=("pending_verification",)):
    upd = {"$set": {"status": status, "status_note": note, **(extra or {})}}
    if status != "pending_verification":
        upd["$push"] = {"history": {"status": status, "at": iso(), "note": note}}
    return await db.payment_submissions.find_one_and_update({"id": did, "status": {"$in": list(from_status)}}, upd)


async def check_deposit(did, admin_credit=False):
    d = await db.payment_submissions.find_one({"id": did}, {"_id": 0})
    allowed = ("pending_verification", "failed") if admin_credit else ("pending_verification",)
    if not d or d["status"] not in allowed:
        return d
    mtype = d["method_type"]
    net = NET_LABEL[NET[mtype]]
    try:
        r = await find_transfer(mtype, d["reference_norm"], d["address"], None if admin_credit else d["expected_raw"])
    except ChainError as e:
        log.warning(f"chain lookup failed for {did}: {e}")
        await _set(did, "pending_verification", "Blockchain lookup temporarily unavailable. Retrying automatically.",
                   {"next_check_at": iso(now() + timedelta(seconds=60))}, allowed)
        return await db.payment_submissions.find_one({"id": did}, {"_id": 0})
    age = (now() - datetime.fromisoformat(d["submitted_at"])).total_seconds()
    fail = None
    if r["state"] == "not_found":
        if age > 7200:
            fail = f"Transaction not found on {net}."
        else:
            await _set(did, "pending_verification", "Waiting for the transaction to appear on-chain.", {"next_check_at": iso(now() + timedelta(seconds=45))}, allowed)
    elif r["state"] == "failed":
        fail = "The transaction failed on-chain."
    elif not r["match"]:
        fail = ("A transfer to the deposit address was found, but not for the exact amount requested. Contact support."
                if r["to_us"] else "No USDT transfer to the deposit address was found in this transaction.")
    elif not admin_credit and r["timestamp"] < datetime.fromisoformat(d["created_at"]).timestamp() - 600:
        fail = "This transaction was made before the deposit request was created."
    elif r["state"] == "pending":
        await _set(did, "pending_verification", f"Confirming on-chain ({r['confirmations']}/{r['required']}).",
                   {"confirmations": r["confirmations"], "next_check_at": iso(now() + timedelta(seconds=30))}, allowed)
    else:
        cents = cents_from_raw(mtype, r["match"]["raw"])
        done = await _set(did, "verified", f"Confirmed on-chain with {r['confirmations']} confirmations.",
                          {"confirmations": r["confirmations"], "credited_amount": cents, "received_raw": str(r["match"]["raw"]), "verified_at": iso()}, allowed)
        if done:
            await post_ledger(d["user_id"], "verified", cents, "deposit_confirmed", f"USDT deposit {d['reference_norm'][:12]}…", ref=did, idem_key=f"dep:{did}")
            await notify_user(d["user_id"], "Deposit confirmed", f"{cents / 100:,.2f} USDT has been added to your USDT balance.", kind="payment", link="/app/deposit")
    if fail:
        if await _set(did, "failed", fail, None, allowed):
            await notify_user(d["user_id"], "Deposit could not be confirmed", fail, kind="payment", link="/app/deposit")
    return await db.payment_submissions.find_one({"id": did}, {"_id": 0, "reference_norm": 0})


async def recheck_deposits():
    await db.payment_submissions.update_many({"status": "draft", "expires_at": {"$lt": iso()}},
                                             {"$set": {"status": "failed", "status_note": "Deposit request expired before a transaction was submitted."},
                                              "$push": {"history": {"status": "failed", "at": iso(), "note": "expired"}}})
    due = await db.payment_submissions.find({"status": "pending_verification", "next_check_at": {"$lte": iso()}}, {"id": 1}).to_list(50)
    for d in due:
        await check_deposit(d["id"])
