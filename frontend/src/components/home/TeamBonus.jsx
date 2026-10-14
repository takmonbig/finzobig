import { useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Crown, Gem, Medal, Award, Shield, UserRound, ChevronRight, Info } from "lucide-react";
import { Glass } from "@/components/common";
import { SectionHead, Reveal } from "@/components/home/Sections";

const STYLE = {
  Bronze: { icon: Medal, ring: "border-orange-700/50", grad: "from-orange-700/25", text: "text-orange-300", bar: "bg-orange-500" },
  Silver: { icon: Shield, ring: "border-slate-400/50", grad: "from-slate-400/20", text: "text-slate-200", bar: "bg-slate-300" },
  Gold: { icon: Award, ring: "border-amber-400/60", grad: "from-amber-500/25", text: "text-amber-300", bar: "bg-amber-400" },
  Platinum: { icon: Crown, ring: "border-sky-400/50", grad: "from-sky-500/20", text: "text-sky-300", bar: "bg-sky-400" },
  Diamond: { icon: Gem, ring: "border-violet-400/60", grad: "from-violet-500/25", text: "text-violet-300", bar: "bg-violet-400" },
};
const pct = (bp) => `${(bp / 100).toFixed(2)}%`;
const TIERS = ["T1", "T2", "T3", "T4", "T5"];
const TIER_TEXT = ["People you personally refer", "Referred by your T1 members", "Referred by your T2 members", "Referred by your T3 members", "Referred by your T4 members"];

function RankCard({ r, rates, i, active, onPick }) {
  const s = STYLE[r.name];
  const I = s.icon;
  const max = 500;
  return (
    <Reveal delay={0.06 * i}>
      <button onClick={onPick} data-testid={`bonus-rank-${r.name.toLowerCase()}`}
        className={`w-full text-left glass p-5 border bg-gradient-to-b ${s.grad} to-transparent transition-transform duration-200 hover:-translate-y-1 ${active ? `${s.ring} ring-1 ring-offset-0` : "border-slate-800"}`}>
        <div className="flex items-center justify-between mb-4">
          <span className={`w-11 h-11 rounded-xl grid place-items-center bg-slate-950/60 ${s.text}`}><I className="w-6 h-6" /></span>
          <span className={`text-xs font-semibold ${s.text}`}>{pct(rates[0])} T1</span>
        </div>
        <p className={`font-display text-xl font-bold ${s.text}`}>{r.name}</p>
        <p className="text-xs text-slate-400 mt-1">{r.min_direct} direct · {r.min_team}+ team</p>
        <div className="mt-4 space-y-1.5">{rates.map((bp, t) => (
          <div key={t} className="flex items-center gap-2 text-[11px]"><span className="w-5 text-slate-500">{TIERS[t]}</span>
            <div className="flex-1 h-1.5 rounded-full bg-slate-800 overflow-hidden"><motion.div initial={{ width: 0 }} whileInView={{ width: `${(bp / max) * 100}%` }} viewport={{ once: true }} transition={{ duration: 0.8, delay: 0.05 * t }} className={`h-full ${s.bar}`} /></div>
            <span className="w-11 text-right font-num text-slate-300">{pct(bp)}</span></div>))}</div>
      </button>
    </Reveal>
  );
}

export function TeamBonus({ ranks = [], commission = {} }) {
  const [pick, setPick] = useState("Gold");
  if (!ranks.length) return null;
  const rates = commission[pick] || [];
  return (
    <section id="team-bonus" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20" data-testid="team-bonus-section">
      <SectionHead eyebrow="Team bonus" title="Five ranks. Five generations. One growing team." text="Build your team, qualify for higher ranks and unlock a higher percentage on every generation from T1 to T5." />
      <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {ranks.map((r, i) => <RankCard key={r.name} r={r} rates={commission[r.name] || []} i={i} active={pick === r.name} onPick={() => setPick(r.name)} />)}
      </div>
      <div className="grid lg:grid-cols-[1.1fr_1fr] gap-6 mt-8">
        <Reveal><Glass data-testid="bonus-generations">
          <h3 className="font-semibold text-white mb-1">How T1 to T5 work</h3>
          <p className="text-sm text-slate-400 mb-5">Your <span className={STYLE[pick].text}>{pick}</span> rank sets the percentage for each generation. Tap a rank card to compare.</p>
          <div className="space-y-2">
            <div className="flex items-center gap-3 p-3 rounded-xl bg-amber-500/10 border border-amber-500/30"><UserRound className="w-5 h-5 text-amber-300" /><span className="text-white font-semibold text-sm">You</span></div>
            {TIERS.map((t, i) => (
              <motion.div key={t} initial={{ opacity: 0, x: -10 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true }} transition={{ delay: 0.08 * i }}
                className="flex items-center gap-3 p-3 rounded-xl bg-slate-950/50 border border-slate-800" style={{ marginLeft: (i + 1) * 12 }} data-testid={`bonus-tier-${t}`}>
                <ChevronRight className="w-4 h-4 text-slate-600" /><span className="font-num text-amber-300 w-7">{t}</span>
                <span className="text-sm text-slate-300 flex-1">{TIER_TEXT[i]}</span><span className={`font-num text-sm ${STYLE[pick].text}`}>{pct(rates[i] || 0)}</span>
              </motion.div>))}
          </div>
        </Glass></Reveal>
        <Reveal delay={0.1}><Glass className="overflow-x-auto" data-testid="bonus-table">
          <h3 className="font-semibold text-white mb-4">Rank & bonus table</h3>
          <table className="tbl"><thead><tr><th>Rank</th><th>Direct</th><th>Team</th>{TIERS.map((t) => <th key={t} className="text-right">{t}</th>)}</tr></thead>
            <tbody>{ranks.map((r) => <tr key={r.name} className={pick === r.name ? "bg-amber-500/5" : ""} onClick={() => setPick(r.name)}>
              <td className={`font-semibold ${STYLE[r.name].text}`}>{r.name}</td><td className="font-num">{r.min_direct}</td><td className="font-num">{r.min_team}{r.name === "Bronze" ? "–49" : "+"}</td>
              {(commission[r.name] || []).map((bp, t) => <td key={t} className="font-num text-right">{pct(bp)}</td>)}</tr>)}</tbody></table>
          <p className="text-xs text-slate-500 mt-4">Direct members are people you personally refer. Total team counts your direct members and everyone below them across five generations. Both conditions must be met to qualify.</p>
          <p className="text-[11px] text-slate-500 mt-2 flex gap-1.5" data-testid="bonus-note"><Info className="w-3.5 h-3.5 shrink-0" />Bonus percentages are shown for the rank structure and the in-dashboard calculator; team bonus payouts are not currently active.</p>
          <Link to="/register" className="btn-gold mt-5 w-full sm:w-auto" data-testid="bonus-join-btn">Start building your team</Link>
        </Glass></Reveal>
      </div>
    </section>
  );
}
