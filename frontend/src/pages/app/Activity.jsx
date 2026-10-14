import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, ArrowDownToLine, ArrowUpFromLine, CircleDot } from "lucide-react";
import { api, coins, fdate } from "@/lib/api";

const get = (url, params) => api.get(url, { params }).then((r) => r.data);
import { Glass, PageHeader, Loader, Empty, StatusBadge } from "@/components/common";

const WEEK = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const ym = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;

function group(data) {
  const days = {};
  const add = (date, k, v) => { const d = (days[date] ||= { in: 0, out: 0, events: [] }); if (k) d[k] += v; };
  data.ledger.forEach((e) => { const day = e.created_at.slice(0, 10); add(day, e.amount >= 0 ? "in" : "out", Math.abs(e.amount));
    days[day].events.push({ id: e.id, at: e.created_at, kind: "ledger", label: e.memo || e.type, amount: e.amount }); });
  data.deposits.forEach((x) => { add(x.created_at.slice(0, 10)); days[x.created_at.slice(0, 10)].events.push({ id: x.id, at: x.created_at, kind: "deposit", label: `Deposit request · ${x.method_name}`, amount: x.amount, status: x.status }); });
  data.withdrawals.forEach((x) => { add(x.created_at.slice(0, 10)); days[x.created_at.slice(0, 10)].events.push({ id: x.id, at: x.created_at, kind: "withdrawal", label: `Withdrawal request · ${x.destination_type}`, amount: -x.amount, status: x.status }); });
  Object.values(days).forEach((d) => d.events.sort((a, b) => a.at.localeCompare(b.at)));
  return days;
}

function DayCell({ date, d, picked, onPick }) {
  const today = date === new Date().toISOString().slice(0, 10);
  return (
    <button onClick={onPick} data-testid={`cal-day-${date}`}
      className={`min-h-[64px] sm:min-h-[88px] rounded-xl border p-1.5 sm:p-2 text-left transition-colors ${picked ? "border-amber-400 bg-amber-500/10" : "border-slate-800 bg-slate-950/40 hover:border-slate-600"}`}>
      <span className={`text-[11px] font-num ${today ? "text-amber-300 font-bold" : "text-slate-400"}`}>{Number(date.slice(8))}</span>
      {d?.in > 0 && <p className="text-[10px] sm:text-xs font-num text-emerald-300 truncate">+{coins(d.in)}</p>}
      {d?.out > 0 && <p className="text-[10px] sm:text-xs font-num text-red-300 truncate">−{coins(d.out)}</p>}
      {d && !d.in && !d.out && <CircleDot className="w-3 h-3 text-sky-400 mt-1" />}
    </button>
  );
}

export default function Activity() {
  const [cur, setCur] = useState(() => new Date(new Date().getFullYear(), new Date().getMonth(), 1));
  const [pick, setPick] = useState(null);
  const month = ym(cur);
  const { data, isLoading } = useQuery({ queryKey: ["activity", month], queryFn: () => get("/activity/calendar", { month }) });
  const days = useMemo(() => (data ? group(data) : {}), [data]);
  const lead = (cur.getDay() + 6) % 7;
  const count = new Date(cur.getFullYear(), cur.getMonth() + 1, 0).getDate();
  const totals = Object.values(days).reduce((t, d) => ({ in: t.in + d.in, out: t.out + d.out }), { in: 0, out: 0 });
  const shift = (n) => { setCur(new Date(cur.getFullYear(), cur.getMonth() + n, 1)); setPick(null); };
  const sel = pick && days[pick];
  return (
    <div data-testid="activity-page">
      <PageHeader title="Activity calendar" subtitle="Your deposits, withdrawals and USDT balance changes, day by day." />
      <div className="grid sm:grid-cols-2 gap-4 mb-5">
        <Glass className="flex items-center gap-3"><ArrowDownToLine className="w-5 h-5 text-emerald-400" /><div><p className="text-xs text-slate-400">Credited this month</p><p className="font-num text-xl text-emerald-300" data-testid="cal-total-in">{coins(totals.in)} USDT</p></div></Glass>
        <Glass className="flex items-center gap-3"><ArrowUpFromLine className="w-5 h-5 text-red-400" /><div><p className="text-xs text-slate-400">Debited this month</p><p className="font-num text-xl text-red-300" data-testid="cal-total-out">{coins(totals.out)} USDT</p></div></Glass>
      </div>
      <Glass>
        <div className="flex items-center justify-between mb-4">
          <button className="btn-ghost !px-3" onClick={() => shift(-1)} data-testid="cal-prev"><ChevronLeft className="w-4 h-4" /></button>
          <p className="font-semibold text-white" data-testid="cal-month">{cur.toLocaleString(undefined, { month: "long", year: "numeric" })}</p>
          <button className="btn-ghost !px-3" onClick={() => shift(1)} data-testid="cal-next"><ChevronRight className="w-4 h-4" /></button>
        </div>
        {isLoading ? <Loader /> : (
          <div className="grid grid-cols-7 gap-1 sm:gap-2">
            {WEEK.map((w) => <p key={w} className="text-[10px] sm:text-xs text-slate-500 text-center">{w}</p>)}
            {Array.from({ length: lead }).map((_, i) => <div key={`l${i}`} />)}
            {Array.from({ length: count }).map((_, i) => { const date = `${month}-${String(i + 1).padStart(2, "0")}`; return <DayCell key={date} date={date} d={days[date]} picked={pick === date} onPick={() => setPick(date)} />; })}
          </div>
        )}
      </Glass>
      <Glass className="mt-5" data-testid="cal-day-details">
        <h3 className="font-semibold text-white mb-3">{pick ? fdate(`${pick}T12:00:00`).split(",")[0] : "Select a day"}</h3>
        {!pick ? <p className="text-sm text-slate-400">Tap any day to see its details.</p> : !sel ? <Empty title="No activity on this day" /> : (
          <div className="divide-y divide-slate-800">{sel.events.map((e) => (
            <div key={`${e.kind}-${e.id}`} className="py-2.5 flex items-center gap-3 text-sm">
              <span className="text-xs text-slate-500 font-num w-12">{e.at.slice(11, 16)}</span>
              <span className="flex-1 text-slate-200">{e.label}</span>
              {e.status && <StatusBadge status={e.status} />}
              <span className={`font-num ${e.amount >= 0 ? "text-emerald-300" : "text-red-300"}`}>{e.amount >= 0 ? "+" : "−"}{coins(Math.abs(e.amount))}</span>
            </div>))}</div>
        )}
      </Glass>
    </div>
  );
}
