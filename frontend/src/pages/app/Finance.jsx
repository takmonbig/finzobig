import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Copy, Check, Info, ShieldAlert } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api, coins, errMsg, fdate, newKey } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Glass, PageHeader, Loader, Empty, ErrorBox, StatusBadge, Field, Pager, Confirm, ImageUpload, TelegramButton, Stat } from "@/components/common";

const get = (url, params) => api.get(url, { params }).then((r) => r.data);

function Wallet() {
  const [account, setAccount] = useState("");
  const [page, setPage] = useState(1);
  const { data, isLoading } = useQuery({ queryKey: ["wallet", account, page], queryFn: () => get("/wallet", { account: account || undefined, page, size: 20 }) });
  return (
    <div data-testid="wallet-page">
      <PageHeader title="Wallet & ledger" subtitle="Every entry is immutable. Corrections appear as separate reversing entries. Simulated and verified balances are kept in separate accounts." />
      {isLoading ? <Loader /> : (<>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {Object.entries(data.wallets).map(([k, w]) => <Stat key={k} label={w.label} value={coins(w.available)} testid={`wallet-${k}`} hint={w.reserved ? `${coins(w.reserved)} reserved` : `Balance ${coins(w.balance)}`} />)}
        </div>
        <Tabs value={account || "all"} onValueChange={(v) => { setAccount(v === "all" ? "" : v); setPage(1); }}>
          <TabsList className="bg-slate-900 flex-wrap h-auto">{["all", "demo_coins", "sim_earnings", "verified", "promo"].map((a) => <TabsTrigger key={a} value={a} data-testid={`ledger-tab-${a}`}>{a.replace("_", " ")}</TabsTrigger>)}</TabsList>
        </Tabs>
        <Glass className="mt-4">
          {data.ledger.items.length ? <div className="overflow-x-auto"><table className="tbl" data-testid="ledger-table"><thead><tr><th>Date</th><th>Account</th><th>Type</th><th>Memo</th><th className="text-right">Amount</th><th className="text-right">Balance after</th></tr></thead>
            <tbody>{data.ledger.items.map((e) => <tr key={e.id}><td className="whitespace-nowrap">{fdate(e.created_at)}</td><td>{e.account}</td><td>{e.type}</td><td>{e.memo}</td>
              <td className={`text-right font-num ${e.amount < 0 ? "text-red-300" : "text-emerald-300"}`}>{e.amount > 0 ? "+" : ""}{coins(e.amount)}</td><td className="text-right font-num">{coins(e.balance_after)}</td></tr>)}</tbody></table></div> : <Empty title="No ledger entries" />}
          <Pager page={page} size={20} total={data.ledger.total} onPage={setPage} />
        </Glass>
      </>)}
    </div>
  );
}

function CopyBtn({ text, testid }) {
  const [ok, setOk] = useState(false);
  return <button className="btn-ghost !py-1.5 !px-3 text-xs" data-testid={testid} onClick={async () => { await navigator.clipboard.writeText(text); setOk(true); toast.success("Copied"); setTimeout(() => setOk(false), 1500); }}>{ok ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}{ok ? "Copied" : "Copy"}</button>;
}

const REF_HINT = { upi: "12-digit UTR / UPI reference", usdt_trc20: "64-character transaction hash", usdt_bep20: "0x + 64-character transaction hash" };

function DepositForm({ m, onDone }) {
  const [f, setF] = useState({ amount: "", reference: "", note: "" });
  const [ev, setEv] = useState(null);
  const [err, setErr] = useState(null);
  const mut = useMutation({
    mutationFn: () => api.post("/deposits", { method_id: m.id, amount: Number(f.amount), reference: f.reference, evidence_public_id: ev?.public_id, note: f.note || null }),
    onSuccess: () => { toast.success("Payment record submitted for verification"); setF({ amount: "", reference: "", note: "" }); setEv(null); setErr(null); onDone(); },
    onError: (e) => setErr(errMsg(e)),
  });
  const submit = () => {
    if (!f.amount || Number(f.amount) <= 0) return setErr("Enter a valid amount");
    if (f.reference.trim().length < 6) return setErr("Enter the payment reference");
    if (!ev) return setErr("Payment screenshot is required");
    mut.mutate();
  };
  return (
    <div className="space-y-4" data-testid="deposit-form">
      <div className="grid sm:grid-cols-2 gap-3">
        <Field label={`Amount (${m.currency})`} hint={`Min ${coins(m.min_amount, 0)} · Max ${coins(m.max_amount, 0)}`}><Input className="inp font-num" type="number" value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value })} data-testid="deposit-amount-input" /></Field>
        <Field label="Payment reference" hint={REF_HINT[m.type]}><Input className="inp font-num" value={f.reference} onChange={(e) => setF({ ...f, reference: e.target.value })} data-testid="deposit-reference-input" /></Field>
      </div>
      <Field label="Payment screenshot (required)"><ImageUpload sigPath="/uploads/signature" sigBody={{ purpose: "evidence" }} onUploaded={setEv} testid="deposit-screenshot" label="Upload payment screenshot" /></Field>
      <Field label="Note (optional)"><Input className="inp" value={f.note} onChange={(e) => setF({ ...f, note: e.target.value })} data-testid="deposit-note-input" /></Field>
      <p className="text-xs text-slate-500 flex gap-2"><Info className="w-4 h-4 shrink-0" />A screenshot does not prove payment. Records are verified independently against bank or blockchain confirmations before any status change.</p>
      <ErrorBox error={err} />
      <button className="btn-gold w-full" disabled={mut.isPending} onClick={submit} data-testid="deposit-submit-btn">{mut.isPending ? "Submitting…" : "Submit payment record"}</button>
    </div>
  );
}

function Deposit() {
  const qc = useQueryClient();
  const methods = useQuery({ queryKey: ["methods"], queryFn: () => get("/payment-methods") });
  const [page, setPage] = useState(1);
  const hist = useQuery({ queryKey: ["deposits", page], queryFn: () => get("/deposits", { page, size: 10 }) });
  const [sel, setSel] = useState(null);
  const m = sel || methods.data?.[0];
  return (
    <div data-testid="deposit-page">
      <PageHeader title="Deposit information" subtitle="Payment methods run in TEST MODE. No real investment deposits are accepted." />
      <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-3 mb-5 text-sm text-amber-100 flex gap-2" data-testid="deposit-test-mode-banner"><ShieldAlert className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />TEST MODE: do not send real funds. Verified records are credited only to a separate test balance.</div>
      {methods.isLoading ? <Loader /> : !methods.data?.length ? <Empty title="No payment methods available" /> : (
        <div className="grid lg:grid-cols-[1fr_1.2fr] gap-5">
          <div className="space-y-4">
            <div className="flex flex-wrap gap-2">{methods.data.map((x) => <button key={x.id} onClick={() => setSel(x)} data-testid={`method-${x.type}`}
              className={`px-4 py-2 rounded-xl text-sm border transition-colors ${m?.id === x.id ? "border-amber-400 bg-amber-500/10 text-amber-200" : "border-slate-700 text-slate-300 hover:border-slate-500"}`}>{x.name}</button>)}</div>
            <Glass className="space-y-4" data-testid="method-details">
              <div><p className="text-xs text-slate-500">Network</p><p className="text-white font-semibold" data-testid="method-network">{m.network}</p></div>
              <div><p className="text-xs text-slate-500">{m.type === "upi" ? "UPI ID" : "Wallet address"}</p>
                <div className="flex items-center gap-2 mt-1"><p className="font-num text-sm text-amber-200 break-all flex-1" data-testid="method-address">{m.address}</p><CopyBtn text={m.address} testid="copy-address-btn" /></div></div>
              <div className="bg-white rounded-xl p-3 w-fit mx-auto" data-testid="method-qr">{m.qr_url ? <img src={m.qr_url} alt="Payment QR" className="w-44 h-44 object-contain" /> : <QRCodeSVG value={m.address} size={176} />}</div>
              <p className="text-sm text-slate-300 whitespace-pre-wrap" data-testid="method-instructions">{m.instructions}</p>
            </Glass>
            <TelegramButton testid="deposit-telegram-btn" />
          </div>
          <Glass><DepositForm m={m} onDone={() => ["deposits", "dashboard"].forEach((k) => qc.invalidateQueries({ queryKey: [k] }))} /></Glass>
        </div>
      )}
      <Glass className="mt-6" data-testid="deposit-history">
        <h3 className="font-semibold text-white mb-3">Payment submissions</h3>
        {hist.data?.items.length ? <div className="overflow-x-auto"><table className="tbl"><thead><tr><th>Date</th><th>Method</th><th>Amount</th><th>Reference</th><th>Status</th><th>Explanation</th></tr></thead>
          <tbody>{hist.data.items.map((d) => <tr key={d.id}><td className="whitespace-nowrap">{fdate(d.created_at)}</td><td>{d.method_name}</td><td className="font-num">{coins(d.amount)} {d.currency}</td>
            <td className="font-num text-xs break-all max-w-[180px]">{d.reference}</td><td><StatusBadge status={d.status} testid={`deposit-status-${d.id}`} /></td><td className="text-xs text-slate-400 max-w-[260px]">{d.status_note}</td></tr>)}</tbody></table></div> : <Empty title="No submissions yet" />}
        {hist.data && <Pager page={page} size={10} total={hist.data.total} onPage={setPage} />}
      </Glass>
    </div>
  );
}

function Withdraw() {
  const qc = useQueryClient();
  const { user } = useAuth();
  const info = useQuery({ queryKey: ["wd-info"], queryFn: () => get("/withdrawals/info") });
  const [page, setPage] = useState(1);
  const hist = useQuery({ queryKey: ["withdrawals", page], queryFn: () => get("/withdrawals", { page, size: 10 }) });
  const [f, setF] = useState({ amount: "", destination_type: "upi", destination: "", totp_code: "" });
  const [key, setKey] = useState(newKey);
  const [err, setErr] = useState(null);
  const refresh = () => ["withdrawals", "wd-info", "dashboard", "wallet"].forEach((k) => qc.invalidateQueries({ queryKey: [k] }));
  const mut = useMutation({ mutationFn: () => api.post("/withdrawals", { ...f, amount: Number(f.amount), idem_key: key, totp_code: f.totp_code || null }),
    onSuccess: () => { toast.success("Withdrawal request submitted"); setKey(newKey()); setF({ ...f, amount: "" }); setErr(null); refresh(); }, onError: (e) => setErr(errMsg(e)) });
  const cancel = useMutation({ mutationFn: (id) => api.post(`/withdrawals/${id}/cancel`), onSuccess: () => { toast.success("Request cancelled; balance released"); refresh(); }, onError: (e) => toast.error(errMsg(e)) });
  if (info.isLoading) return <Loader />;
  const i = info.data;
  const amt = Math.round(Number(f.amount || 0) * 100);
  const fee = Math.floor((amt * Math.round(i.config.fee_percent * 100)) / 10000) + Math.round(i.config.fee_flat * 100);
  return (
    <div data-testid="withdraw-page">
      <PageHeader title="Withdrawal information" subtitle="Only verified (TEST MODE) balances can be requested. Simulated coins and hypothetical earnings are never withdrawable." />
      <div className="grid lg:grid-cols-[1.2fr_1fr] gap-5">
        <Glass className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <Stat label="Available verified balance" value={coins(i.verified?.available)} testid="wd-available" />
            <Stat label="Reserved for open requests" value={coins(i.verified?.reserved)} tone="violet" testid="wd-reserved" />
          </div>
          {!i.enabled && <ErrorBox error="Withdrawals are currently disabled by the administrator." />}
          {!i.mobile_verified && <div className="text-sm text-amber-200 bg-amber-500/10 border border-amber-500/30 rounded-xl p-3" data-testid="wd-verify-notice">Verify your mobile number in Profile & security before requesting a withdrawal.</div>}
          <div className="grid sm:grid-cols-2 gap-3">
            <Field label="Amount" hint={`Min ${i.config.min} · Max ${i.config.max}`}><Input className="inp font-num" type="number" value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value })} data-testid="wd-amount-input" /></Field>
            <Field label="Destination method"><select className="w-full bg-slate-950/60 border border-slate-700 rounded-xl px-3 py-2 text-sm h-10" value={f.destination_type} onChange={(e) => setF({ ...f, destination_type: e.target.value })} data-testid="wd-method-select">
              <option value="upi">UPI</option><option value="usdt_trc20">USDT TRC20</option><option value="usdt_bep20">USDT BEP20</option></select></Field>
          </div>
          <Field label="Destination" hint={{ upi: "name@bank", usdt_trc20: "T… address (34 chars)", usdt_bep20: "0x… address (42 chars)" }[f.destination_type]}><Input className="inp font-num" value={f.destination} onChange={(e) => setF({ ...f, destination: e.target.value })} data-testid="wd-destination-input" /></Field>
          {user.totp_enabled && <Field label="2FA code"><Input className="inp font-num" value={f.totp_code} onChange={(e) => setF({ ...f, totp_code: e.target.value })} data-testid="wd-totp-input" /></Field>}
          <div className="rounded-xl bg-slate-950/60 border border-slate-800 p-3 text-sm grid grid-cols-3 gap-2" data-testid="wd-fee-preview">
            <div><p className="text-xs text-slate-500">Amount</p><p className="font-num">{coins(amt)}</p></div><div><p className="text-xs text-slate-500">Fee ({i.config.fee_percent}%{i.config.fee_flat ? ` + ${i.config.fee_flat}` : ""})</p><p className="font-num text-red-300">{coins(fee)}</p></div>
            <div><p className="text-xs text-slate-500">Net amount</p><p className="font-num text-emerald-300" data-testid="wd-net">{coins(Math.max(amt - fee, 0))}</p></div>
          </div>
          <ErrorBox error={err} />
          <Confirm testid="wd-confirm" title="Submit withdrawal request?" description={`${coins(amt)} will be reserved from your verified test balance until the request is completed, rejected or cancelled.`}
            onConfirm={() => mut.mutate()} trigger={<button className="btn-gold w-full" disabled={mut.isPending || !amt || !f.destination || !i.enabled} data-testid="wd-submit-btn">Submit request</button>} />
        </Glass>
        <div className="space-y-4"><TelegramButton testid="withdraw-telegram-btn" />
          <Glass className="text-sm text-slate-400 space-y-2"><p className="text-white font-semibold">How requests are protected</p><p>Only one open request is allowed at a time. The requested amount is reserved immediately, so two requests can never spend the same balance.</p><p>Every administrator action is recorded in the audit log.</p></Glass></div>
      </div>
      <Glass className="mt-6" data-testid="wd-history">
        <h3 className="font-semibold text-white mb-3">Withdrawal requests</h3>
        {hist.data?.items.length ? <div className="overflow-x-auto"><table className="tbl"><thead><tr><th>Date</th><th>Amount</th><th>Fee</th><th>Net</th><th>Destination</th><th>Status</th><th>Note</th><th /></tr></thead>
          <tbody>{hist.data.items.map((w) => <tr key={w.id}><td className="whitespace-nowrap">{fdate(w.created_at)}</td><td className="font-num">{coins(w.amount)}</td><td className="font-num">{coins(w.fee)}</td><td className="font-num">{coins(w.net_amount)}</td>
            <td className="font-num text-xs break-all max-w-[160px]">{w.destination}</td><td><StatusBadge status={w.status} testid={`wd-status-${w.id}`} /></td><td className="text-xs text-slate-400">{w.status_note}</td>
            <td>{["submitted", "under_review"].includes(w.status) && <button className="text-xs text-red-300" onClick={() => cancel.mutate(w.id)} data-testid={`wd-cancel-${w.id}`}>Cancel</button>}</td></tr>)}</tbody></table></div> : <Empty title="No withdrawal requests" />}
        {hist.data && <Pager page={page} size={10} total={hist.data.total} onPage={setPage} />}
      </Glass>
    </div>
  );
}

const PAGES = { wallet: Wallet, deposit: Deposit, withdraw: Withdraw };
export default function Finance({ page }) {
  const P = PAGES[page];
  return <P />;
}
