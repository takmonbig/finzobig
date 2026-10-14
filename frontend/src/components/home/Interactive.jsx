import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Calculator, ArrowRight, Users } from "lucide-react";
import { LineChart, Line, ResponsiveContainer, XAxis, YAxis, Tooltip, ReferenceLine, CartesianGrid } from "recharts";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { api, coins, errMsg } from "@/lib/api";
import { Glass, ErrorBox } from "@/components/common";
import { SectionHead, Reveal } from "@/components/home/Sections";

export function PlansSection({ plans = [] }) {
  const [sel, setSel] = useState(null);
  return (
    <section id="plans" className="max-w-7xl mx-auto px-4 sm:px-6 py-20">
      <SectionHead eyebrow="Participation plans" title="Eight participation plans." text="Choose a plan that fits your goals and follow every day of progress from your dashboard." />
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {plans.map((p, i) => (
          <Reveal key={p.id} delay={i * 0.04}>
            <button onClick={() => setSel(p)} data-testid={`plan-card-${i}`}
              className={`glass glass-hover w-full text-left p-5 ${sel?.id === p.id ? "!border-amber-400/70 shadow-[0_0_30px_rgba(245,158,11,.2)]" : ""}`}>
              <div className="flex items-center justify-between"><span className="text-sm text-slate-400">{p.name}</span></div>
              <p className="font-num text-3xl text-white mt-3">{coins(p.deposit, 0)}</p>
              <p className="text-xs text-slate-500">plan amount (coins)</p>
              <div className="grid grid-cols-2 gap-2 mt-4 text-xs">
                <div><p className="text-slate-500">Daily</p><p className="font-num text-amber-300">{coins(p.daily, 0)}</p></div>
                <div><p className="text-slate-500">Duration</p><p className="font-num text-slate-200">{p.duration_days} days</p></div>
                <div><p className="text-slate-500">Total payout</p><p className="font-num text-slate-200">{coins(p.total_payout, 0)}</p></div>
                <div><p className="text-slate-500">Net gain</p><p className="font-num text-violet-300">{coins(p.net_gain, 0)}</p></div>
              </div>
            </button>
          </Reveal>
        ))}
      </div>
      <PlanCalculator plans={plans} selected={sel} onSelect={setSel} />
    </section>
  );
}

function PlanCalculator({ plans, selected, onSelect }) {
  const [custom, setCustom] = useState({ deposit: 1000, daily: 120, days: 90 });
  const [res, setRes] = useState(null);
  const [err, setErr] = useState(null);
  const vals = selected ? { deposit: selected.deposit / 100, daily: selected.daily / 100, days: selected.duration_days } : custom;
  const run = async () => {
    setErr(null);
    try { setRes((await api.post("/public/calculate", vals)).data); } catch (e) { setErr(errMsg(e)); }
  };
  const series = useMemo(() => {
    if (!res) return [];
    const step = Math.max(1, Math.round(res.days / 30));
    return Array.from({ length: Math.floor(res.days / step) + 1 }, (_, i) => ({ day: i * step, payout: (res.daily * i * step) / 100 }));
  }, [res]);
  return (
    <Glass className="mt-10 grid lg:grid-cols-[1fr_1.3fr] gap-8" data-testid="plan-calculator">
      <div className="space-y-4">
        <div className="flex items-center gap-2"><Calculator className="w-5 h-5 text-amber-400" /><h3 className="font-display text-xl text-white font-semibold">Plan calculator</h3></div>
        <select className="w-full bg-slate-950/60 border border-slate-700 rounded-xl px-3 py-2.5 text-sm" value={selected?.id || ""} data-testid="calc-plan-select"
          onChange={(e) => onSelect(plans.find((p) => p.id === e.target.value) || null)}>
          <option value="">Custom values</option>
          {plans.map((p) => <option key={p.id} value={p.id}>{`${p.name} — ${coins(p.deposit, 0)}`}</option>)}
        </select>
        {[["deposit", "Plan amount"], ["daily", "Daily amount"], ["days", "Duration (days)"]].map(([k, l]) => (
          <label key={k} className="block text-sm"><span className="text-slate-400">{l}</span>
            <input type="number" min="1" disabled={!!selected} value={vals[k]} data-testid={`calc-${k}-input`} onChange={(e) => setCustom({ ...custom, [k]: Number(e.target.value) })}
              className="mt-1 w-full bg-slate-950/60 border border-slate-700 rounded-xl px-3 py-2.5 font-num disabled:opacity-60" />
          </label>
        ))}
        <button className="btn-gold w-full" onClick={run} data-testid="calc-run-btn">Calculate</button>
        <ErrorBox error={err} />
      </div>
      <div>
        {res ? (
          <div className="space-y-4" data-testid="calc-result">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[["Total payout", coins(res.total_payout)], ["Net gain", coins(res.net_gain)], ["Daily rate", `${res.simple_daily_rate_percent}%`], ["Break-even day", res.breakeven_day ?? "—"]].map(([l, v]) => (
                <div key={l} className="rounded-xl bg-slate-950/60 border border-slate-800 p-3"><p className="text-[11px] text-slate-500">{l}</p><p className="font-num text-white" data-testid={`calc-${l.toLowerCase().replace(/ /g, "-")}`}>{v}</p></div>
              ))}
            </div>
            <div className="h-48"><ResponsiveContainer><LineChart data={series}>
              <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" /><XAxis dataKey="day" stroke="#64748b" fontSize={11} /><YAxis stroke="#64748b" fontSize={11} />
              <Tooltip contentStyle={{ background: "#0C1120", border: "1px solid #334155", borderRadius: 12 }} />
              <ReferenceLine y={res.deposit / 100} stroke="#8B5CF6" strokeDasharray="4 4" label={{ value: "deposit", fill: "#a78bfa", fontSize: 11 }} />
              <Line dataKey="payout" stroke="#F59E0B" strokeWidth={2} dot={false} />
            </LineChart></ResponsiveContainer></div>
            <div className="text-xs text-slate-400 space-y-1 border-t border-slate-800 pt-3">
              <p><span className="text-slate-200 font-semibold">Assumptions:</span> total = daily amount × days; net gain = total − deposit; daily rate = daily ÷ deposit.</p>
              <p>No compounding, fees, taxes, market losses or counterparty failure are modelled. {res.note}</p>
            </div>
          </div>
        ) : <div className="h-full grid place-items-center text-slate-500 text-sm text-center p-8">Select a plan or enter custom values, then calculate to see how the arithmetic works.</div>}
      </div>
    </Glass>
  );
}

const GEN_INFO = [
  ["You (A)", "Your account and personal referral code."],
  ["Generation 1 — direct", "People who registered using your code (B). Direct referrals count toward rank qualification."],
  ["Generation 2 — indirect", "People referred by your direct referrals (C)."],
  ["Generation 3", "Referrals of generation-2 members (D)."],
  ["Generation 4", "Referrals of generation-3 members (E)."],
  ["Generation 5", "The deepest level counted for team size (F). Members beyond this are not counted."],
];

export function TeamDiagram({ ranks = [] }) {
  const [active, setActive] = useState(1);
  const colors = ["#F59E0B", "#3B82F6", "#8B5CF6", "#10B981", "#EC4899", "#06B6D4"];
  return (
    <section id="team" className="max-w-7xl mx-auto px-4 sm:px-6 py-20">
      <SectionHead eyebrow="Team network" title="An interactive five-generation network." text="Tap a generation to learn how it is counted. Uplines only see limited, masked information about their team." />
      <div className="grid lg:grid-cols-[1.4fr_1fr] gap-6">
        <Glass className="overflow-x-auto" data-testid="team-diagram">
          <div className="min-w-[520px] space-y-4">
            {GEN_INFO.map(([label], g) => (
              <motion.button key={g} onClick={() => setActive(g)} whileHover={{ x: 4 }} data-testid={`team-gen-${g}`}
                className={`w-full flex items-center gap-4 rounded-xl p-3 border transition-colors ${active === g ? "border-amber-400/60 bg-amber-500/5" : "border-slate-800 bg-slate-950/40"}`}>
                <span className="w-24 text-left text-xs text-slate-400 shrink-0">{g === 0 ? "Root" : `Gen ${g}`}</span>
                <div className="flex gap-2 flex-wrap">
                  {Array.from({ length: g === 0 ? 1 : Math.min(2 ** g, 12) }).map((_, i) => (
                    <span key={i} className="w-7 h-7 rounded-full grid place-items-center text-[10px] font-bold text-slate-950" style={{ background: colors[g], opacity: i === 0 ? 1 : 0.55 }}>{i === 0 ? "ABCDEF"[g] : ""}</span>
                  ))}
                </div>
              </motion.button>
            ))}
          </div>
        </Glass>
        <div className="space-y-4">
          <Glass data-testid="team-gen-info">
            <Users className="w-5 h-5 text-amber-400 mb-2" />
            <h3 className="text-white font-semibold">{GEN_INFO[active][0]}</h3>
            <p className="text-sm text-slate-400 mt-2">{GEN_INFO[active][1]}</p>
          </Glass>
          <Glass>
            <p className="eyebrow mb-3">Membership qualifications</p>
            <table className="tbl"><thead><tr><th>Rank</th><th>Direct</th><th>Total team</th></tr></thead>
              <tbody>{ranks.map((r) => <tr key={r.name}><td>{r.name}</td><td className="font-num">{r.min_direct}</td><td className="font-num">{r.min_team}</td></tr>)}</tbody></table>
            <p className="text-xs text-slate-500 mt-3">Both conditions must be met. Ranks update automatically.</p>
          </Glass>
        </div>
      </div>
    </section>
  );
}

export function RewardsSection({ rewards = [] }) {
  return (
    <section id="rewards" className="max-w-7xl mx-auto px-4 sm:px-6 py-20">
      <SectionHead eyebrow="Achievements" title="Rewards for team milestones." text="Rewards are subject to campaign terms, eligibility review and availability. They are not guaranteed." />
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {rewards.map((r, i) => (
          <Reveal key={r.id} delay={i * 0.06}>
            <Link to={`/rewards/${r.slug}`} className="group block glass overflow-hidden glass-hover" data-testid={`reward-card-${r.slug}`}>
              <div className="aspect-[4/3] overflow-hidden relative">
                <img src={r.image_url} alt={r.title} loading="lazy" className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700" />
                
              </div>
              <div className="p-5">
                <h3 className="font-heading text-lg text-white">{r.title}</h3>
                <p className="text-xs text-slate-400 mt-1">Team milestone</p>
                <p className="font-num text-amber-300">{coins(r.milestone, 0)}</p>
                <span className="text-sm text-amber-400 inline-flex items-center gap-1 mt-3">View details <ArrowRight className="w-3.5 h-3.5" /></span>
              </div>
            </Link>
          </Reveal>
        ))}
      </div>
    </section>
  );
}

export function FAQ({ items = [] }) {
  return (
    <section id="faq" className="max-w-4xl mx-auto px-4 sm:px-6 py-20">
      <SectionHead eyebrow="FAQ" title="Questions, answered plainly." />
      <Accordion type="single" collapsible className="glass px-5" data-testid="faq-list">
        {items.map((f, i) => (
          <AccordionItem key={i} value={`f${i}`} className="border-slate-800">
            <AccordionTrigger className="text-left text-white hover:no-underline" data-testid={`faq-item-${i}`}>{f.q}</AccordionTrigger>
            <AccordionContent className="text-slate-400">{f.a}</AccordionContent>
          </AccordionItem>
        ))}
      </Accordion>
    </section>
  );
}
