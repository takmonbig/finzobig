import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Plus, Pencil, AlertTriangle } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { api, coins, errMsg, fdate } from "@/lib/api";
import { Glass, PageHeader, Stat, Loader, Empty, ErrorBox, StatusBadge, Field, Pager, ImageUpload } from "@/components/common";
import { get, sel } from "@/pages/admin/AdminCore";

function ActionDialog({ target, actions, onClose, onDone, endpoint, needsConfirm }) {
  const [f, setF] = useState({ action: "", note: "", payout_ref: "" });
  const [err, setErr] = useState(null);
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    setBusy(true); setErr(null);
    try { const r = await api.post(`${endpoint}/${target.id}/action`, f); toast.success(r.data.note || "Status updated"); onDone(); onClose(); } catch (e) { setErr(errMsg(e)); }
    setBusy(false);
  };
  return (
    <Dialog open={!!target} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="bg-[#0C1120] border-amber-500/20 max-w-lg max-h-[88vh] overflow-y-auto" data-testid="review-dialog">
        <DialogHeader><DialogTitle>Review {target?.user_email}</DialogTitle></DialogHeader>
        {target?.evidence_url && <a href={target.evidence_url} target="_blank" rel="noopener noreferrer"><img src={target.evidence_url} alt="Payment evidence" className="max-h-64 rounded-xl mx-auto" data-testid="review-evidence" /></a>}
        <p className="text-sm">Amount <span className="font-num text-white">{target?.expected_display || coins(target?.amount)} USDT</span> · <span className="font-num text-xs break-all">{target?.reference || target?.destination}</span></p>
        {target?.status_note && <p className="text-xs text-slate-400">{target.status_note}</p>}
        <div className="flex flex-wrap gap-2">{actions(target).map((a) => <button key={a} onClick={() => setF({ ...f, action: a })} data-testid={`review-action-${a}`}
          className={`px-3 py-1.5 rounded-lg text-sm border ${f.action === a ? "border-amber-400 bg-amber-500/10 text-amber-200" : "border-slate-700"}`}>{a.replace("_", " ")}</button>)}</div>
        {f.action === "credit_onchain" && <p className="text-xs text-amber-200 flex gap-2"><AlertTriangle className="w-4 h-4 shrink-0" />Credits the actual on-chain amount received at the deposit address in this transaction, even if it differs from the requested amount.</p>}
        {f.action === "completed" && <Input className="inp font-num" placeholder="Payout transaction hash (verified on-chain)" value={f.payout_ref} onChange={(e) => setF({ ...f, payout_ref: e.target.value })} data-testid="review-payout-ref" />}
        <Textarea className="inp" placeholder="Note shown to the user (required)" value={f.note} onChange={(e) => setF({ ...f, note: e.target.value })} data-testid="review-note-input" />
        <ErrorBox error={err} />
        <button className="btn-gold" disabled={!f.action || f.note.length < 3 || busy} onClick={submit} data-testid="review-submit-btn">Apply</button>
      </DialogContent>
    </Dialog>
  );
}

function Records({ kind }) {
  const qc = useQueryClient();
  const [status, setStatus] = useState(kind === "deposits" ? "pending_verification" : "");
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const [target, setTarget] = useState(null);
  const { data, isLoading } = useQuery({ queryKey: ["admin-" + kind, status, page, q], queryFn: () => get(`/admin/${kind}`, { status, page, q }) });
  const dep = kind === "deposits";
  const statuses = dep ? ["draft", "pending_verification", "verified", "rejected", "refunded", "failed"] : ["submitted", "under_review", "approved", "processing", "completed", "rejected", "cancelled"];
  const DEP_ACT = { draft: ["reject"], pending_verification: ["recheck", "credit_onchain", "reject"], failed: ["credit_onchain", "reject"], verified: ["refund"] };
  const WD_ACT = { submitted: ["under_review", "rejected"], under_review: ["approved", "rejected"], approved: ["processing", "rejected"], processing: ["completed"] };
  const acts = (t) => ((dep ? DEP_ACT : WD_ACT)[t?.status] || []);
  return (
    <div data-testid={`admin-${kind}-page`}>
      <PageHeader title={dep ? "Deposit verification" : "Withdrawal review"} subtitle={dep ? "Deposits are confirmed automatically on-chain. Re-check pending ones, or credit the actual on-chain amount when a user sent a different amount." : "Amounts are reserved at request time. Send the payout from your wallet, then complete with the transaction hash — it is verified on-chain before the balance is debited."} />
      <Glass>
        <div className="flex flex-wrap gap-2 mb-4">
          <select className={sel} value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }} data-testid={`${kind}-status-filter`}><option value="">All statuses</option>{statuses.map((s) => <option key={s}>{s}</option>)}</select>
          {dep && <Input className="inp max-w-xs" placeholder="Search reference or email" value={q} onChange={(e) => setQ(e.target.value)} data-testid="deposits-search-input" />}
        </div>
        {isLoading ? <Loader /> : data.items.length ? <div className="overflow-x-auto"><table className="tbl" data-testid={`${kind}-table`}><thead><tr><th>Date</th><th>User</th><th>{dep ? "Method" : "Destination"}</th><th>Amount</th>{dep ? <th>Reference</th> : <th>Net</th>}<th>Status</th><th /></tr></thead>
          <tbody>{data.items.map((r) => <tr key={r.id}><td className="whitespace-nowrap">{fdate(r.created_at)}</td><td>{r.user_email}</td><td className="text-xs break-all max-w-[160px]">{dep ? r.method_name : `${r.destination_type}: ${r.destination}`}</td>
            <td className="font-num">{coins(r.amount)}</td><td className="font-num text-xs break-all max-w-[160px]">{dep ? r.reference : coins(r.net_amount)}</td><td><StatusBadge status={r.status} /></td>
            <td>{acts(r).length > 0 && <button className="btn-ghost !py-1 !px-3 text-xs" onClick={() => setTarget(r)} data-testid={`review-btn-${r.id}`}>Review</button>}</td></tr>)}</tbody></table></div> : <Empty title="No records" />}
        {data && <Pager page={page} size={20} total={data.total} onPage={setPage} />}
      </Glass>
      <ActionDialog target={target} actions={acts} endpoint={`/admin/${kind}`} needsConfirm={dep} onClose={() => setTarget(null)} onDone={() => qc.invalidateQueries({ queryKey: ["admin-" + kind] })} />
    </div>
  );
}

const EMPTY_M = { name: "", type: "usdt_trc20", network: "TRON (TRC20)", currency: "USDT", address: "", instructions: "", min_amount: 100, max_amount: 100000, active: true, sort: 0 };

function Methods() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["admin-methods"], queryFn: () => get("/admin/payment-methods") });
  const [edit, setEdit] = useState(null);
  const [err, setErr] = useState(null);
  const save = useMutation({
    mutationFn: (m) => (m.id ? api.put(`/admin/payment-methods/${m.id}`, m) : api.post("/admin/payment-methods", m)),
    onSuccess: () => { toast.success("Payment method saved"); setEdit(null); qc.invalidateQueries({ queryKey: ["admin-methods"] }); }, onError: (e) => setErr(errMsg(e)),
  });
  const open = (m) => { setErr(null); setEdit(m ? { ...m, min_amount: m.min_amount / 100, max_amount: m.max_amount / 100, qr_public_id: null } : { ...EMPTY_M }); };
  return (
    <div data-testid="admin-methods-page">
      <PageHeader title="Payment methods" subtitle="Receiving addresses for USDT TRC20 and BEP20. Addresses are validated for the selected network." actions={<button className="btn-gold" onClick={() => open(null)} data-testid="add-method-btn"><Plus className="w-4 h-4" />Add method</button>} />
      {isLoading ? <Loader /> : <div className="grid md:grid-cols-3 gap-4">{data.map((m) => (
        <Glass key={m.id} data-testid={`admin-method-${m.type}`}>
          <div className="flex justify-between items-start"><div><p className="text-white font-semibold">{m.name}</p><p className="text-xs text-slate-500">{m.network} · {m.currency}</p></div><StatusBadge status={m.active ? "active" : "disabled"} /></div>
          <p className="font-num text-xs text-amber-200 break-all mt-3">{m.address}</p>
          {m.qr_url && <img src={m.qr_url} alt="QR" className="w-24 h-24 mt-3 rounded bg-white p-1" />}
          <p className="text-xs text-slate-400 mt-2">Limits {coins(m.min_amount, 0)} – {coins(m.max_amount, 0)}</p>
          <button className="btn-ghost !py-1.5 text-sm mt-3" onClick={() => open(m)} data-testid={`edit-method-${m.type}`}><Pencil className="w-3.5 h-3.5" />Edit</button>
        </Glass>
      ))}</div>}
      <Dialog open={!!edit} onOpenChange={(o) => !o && setEdit(null)}>
        <DialogContent className="bg-[#0C1120] border-amber-500/20 max-w-xl max-h-[88vh] overflow-y-auto" data-testid="method-dialog">
          <DialogHeader><DialogTitle>{edit?.id ? "Edit" : "Add"} payment method</DialogTitle></DialogHeader>
          {edit && <div className="grid sm:grid-cols-2 gap-3">
            <Field label="Name"><Input className="inp" value={edit.name} onChange={(e) => setEdit({ ...edit, name: e.target.value })} data-testid="method-name-input" /></Field>
            <Field label="Type"><select className={sel + " w-full"} value={edit.type} onChange={(e) => setEdit({ ...edit, type: e.target.value, currency: "USDT" })} data-testid="method-type-select"><option value="usdt_trc20">USDT TRC20</option><option value="usdt_bep20">USDT BEP20</option></select></Field>
            <Field label="Network"><Input className="inp" value={edit.network} onChange={(e) => setEdit({ ...edit, network: e.target.value })} data-testid="method-network-input" /></Field>
            <Field label="Currency"><Input className="inp" value={edit.currency} readOnly /></Field>
            <div className="sm:col-span-2"><Field label="Wallet address"><Input className="inp font-num" value={edit.address} onChange={(e) => setEdit({ ...edit, address: e.target.value })} data-testid="method-address-input" /></Field></div>
            <Field label="Min amount"><Input className="inp font-num" type="number" value={edit.min_amount} onChange={(e) => setEdit({ ...edit, min_amount: Number(e.target.value) })} data-testid="method-min-input" /></Field>
            <Field label="Max amount"><Input className="inp font-num" type="number" value={edit.max_amount} onChange={(e) => setEdit({ ...edit, max_amount: Number(e.target.value) })} data-testid="method-max-input" /></Field>
            <div className="sm:col-span-2"><Field label="Instructions"><Textarea className="inp" value={edit.instructions} onChange={(e) => setEdit({ ...edit, instructions: e.target.value })} data-testid="method-instructions-input" /></Field></div>
            <div className="sm:col-span-2"><ImageUpload sigPath="/admin/uploads/signature" sigBody={{ folder: "qr" }} value={edit.qr_url} onUploaded={(r) => setEdit((x) => ({ ...x, qr_public_id: r?.public_id || null }))} testid="method-qr-upload" label={edit.qr_url ? "Replace QR image" : "Upload QR image"} /></div>
            <label className="flex items-center gap-2 text-sm">Active <Switch checked={edit.active} onCheckedChange={(v) => setEdit({ ...edit, active: v })} data-testid="method-active-switch" /></label>
          </div>}
          <ErrorBox error={err} />
          <button className="btn-gold" disabled={save.isPending} onClick={() => save.mutate(edit)} data-testid="method-save-btn">Save method</button>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function FinanceAdmin() {
  const [page, setPage] = useState(1);
  const [f, setF] = useState({ account: "", type: "", user_id: "" });
  const led = useQuery({ queryKey: ["admin-ledger", page, f], queryFn: () => get("/admin/ledger", { page, ...f }) });
  const rec = useQuery({ queryKey: ["recon"], queryFn: () => get("/admin/reconciliation") });
  const lia = useQuery({ queryKey: ["liability"], queryFn: () => get("/admin/liability") });
  return (
    <div data-testid="admin-finance-page">
      <PageHeader title="Ledger, reconciliation & liability" />
      <Tabs defaultValue="liability"><TabsList className="bg-slate-900 mb-4 flex-wrap h-auto"><TabsTrigger value="liability" data-testid="fin-tab-liability">Liability analysis</TabsTrigger><TabsTrigger value="ledger" data-testid="fin-tab-ledger">Ledger report</TabsTrigger><TabsTrigger value="recon" data-testid="fin-tab-recon">Reconciliation & exceptions</TabsTrigger></TabsList>
        <TabsContent value="liability">{lia.isLoading ? <Loader /> : <div className="space-y-4" data-testid="liability-panel">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <Stat label="Plan amounts (coins)" value={coins(lia.data.hypothetical_deposits)} testid="lia-deposits" /><Stat label="Plan payout obligations" value={coins(lia.data.plan_payout_obligations)} tone="blue" testid="lia-plan" />
            <Stat label="5-tier commission obligations" value={coins(lia.data.commission_obligations)} tone="violet" testid="lia-commission" /><Stat label="Total obligations" value={coins(lia.data.total_obligations)} tone="emerald" testid="lia-total" />
          </div>
          <Glass><p className="text-sm">Coverage ratio (deposits ÷ obligations): <span className="font-num text-amber-300" data-testid="lia-coverage">{lia.data.coverage_ratio ?? "—"}</span> · Shortfall: <span className="font-num text-red-300" data-testid="lia-shortfall">{coins(lia.data.shortfall)}</span></p>
            <p className="text-sm mt-2">Per-tier obligations: {lia.data.tier_obligations.map((t, i) => <span key={i} className="font-num mr-3">T{i + 1}: {coins(t)}</span>)}</p>
            <p className="text-xs text-amber-200 mt-3 flex gap-2"><AlertTriangle className="w-4 h-4 shrink-0" />{lia.data.note}</p></Glass>
        </div>}</TabsContent>
        <TabsContent value="ledger"><Glass>
          <div className="flex flex-wrap gap-2 mb-3"><select className={sel} value={f.account} onChange={(e) => setF({ ...f, account: e.target.value })} data-testid="ledger-account-filter"><option value="">All accounts</option>{["demo_coins", "sim_earnings", "verified", "promo"].map((a) => <option key={a}>{a}</option>)}</select>
            <Input className="inp max-w-[200px]" placeholder="Type (e.g. deposit_verified)" value={f.type} onChange={(e) => setF({ ...f, type: e.target.value })} data-testid="ledger-type-filter" />
            <Input className="inp max-w-[260px]" placeholder="User ID" value={f.user_id} onChange={(e) => setF({ ...f, user_id: e.target.value })} data-testid="ledger-user-filter" /></div>
          {led.data && <div className="flex flex-wrap gap-3 mb-3">{Object.entries(led.data.totals).map(([k, t]) => <span key={k} className="text-xs px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800">{k}: <span className="font-num">{coins(t.sum)}</span> ({t.count})</span>)}</div>}
          {led.data?.items.length ? <div className="overflow-x-auto"><table className="tbl" data-testid="admin-ledger-table"><thead><tr><th>Date</th><th>User</th><th>Account</th><th>Type</th><th>Memo</th><th className="text-right">Amount</th><th className="text-right">Balance</th></tr></thead>
            <tbody>{led.data.items.map((e) => <tr key={e.id}><td className="whitespace-nowrap">{fdate(e.created_at)}</td><td className="font-num text-xs">{e.user_id.slice(0, 8)}</td><td>{e.account}</td><td>{e.type}</td><td className="text-xs">{e.memo}</td><td className={`text-right font-num ${e.amount < 0 ? "text-red-300" : "text-emerald-300"}`}>{coins(e.amount)}</td><td className="text-right font-num">{coins(e.balance_after)}</td></tr>)}</tbody></table></div> : <Empty />}
          {led.data && <Pager page={page} size={30} total={led.data.total} onPage={setPage} />}</Glass></TabsContent>
        <TabsContent value="recon">{rec.data && <Glass data-testid="recon-panel"><p className="text-sm">Wallets checked: <span className="font-num">{rec.data.wallets_checked}</span> · Status: <StatusBadge status={rec.data.consistent ? "verified" : "failed"} testid="recon-status" /> · Stale pending deposits (&gt;3 days): <span className="font-num">{rec.data.stale_pending_deposits}</span></p>
          {rec.data.mismatches.length ? <table className="tbl mt-3"><thead><tr><th>User</th><th>Account</th><th>Wallet</th><th>Ledger sum</th><th>Reserved</th></tr></thead><tbody>{rec.data.mismatches.map((m, i) => <tr key={i}><td className="font-num text-xs">{m.user_id}</td><td>{m.account}</td><td className="font-num">{coins(m.wallet_balance)}</td><td className="font-num">{coins(m.ledger_sum)}</td><td className="font-num">{coins(m.reserved)}</td></tr>)}</tbody></table> : <p className="text-sm text-emerald-300 mt-3">Every wallet balance equals the sum of its immutable ledger entries.</p>}</Glass>}</TabsContent>
      </Tabs>
    </div>
  );
}

const PAGES = { deposits: () => <Records kind="deposits" />, withdrawals: () => <Records kind="withdrawals" />, methods: Methods, finance: FinanceAdmin };
export default function AdminFinance({ page }) {
  const P = PAGES[page];
  return <P />;
}
