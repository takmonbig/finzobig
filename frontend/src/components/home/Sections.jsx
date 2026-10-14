import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import * as Icons from "lucide-react";
import { AreaChart, Area, ResponsiveContainer, XAxis, Tooltip } from "recharts";
import { Glass } from "@/components/common";

export const Reveal = ({ children, delay = 0, className = "" }) => (
  <motion.div className={className} initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: "-60px" }} transition={{ duration: 0.55, delay }}>{children}</motion.div>
);

export const SectionHead = ({ eyebrow, title, text }) => (
  <Reveal className="max-w-3xl mb-12">
    <p className="eyebrow mb-3">{eyebrow}</p>
    <h2 className="font-display text-3xl sm:text-4xl font-bold text-white leading-tight">{title}</h2>
    {text && <p className="text-slate-400 mt-4 text-base">{text}</p>}
  </Reveal>
);

const PREVIEW = Array.from({ length: 14 }, (_, i) => ({ d: `D${i + 1}`, v: 40 + Math.round(30 * Math.sin(i / 2) + i * 6) }));

function DashboardPreview() {
  return (
    <motion.div initial={{ opacity: 0, scale: 0.95, rotate: -1 }} animate={{ opacity: 1, scale: 1, rotate: 0 }} transition={{ duration: 0.8, delay: 0.2 }} className="relative" data-testid="hero-dashboard-preview">
      <div className="absolute -inset-6 animated-gradient blur-3xl rounded-[2rem] opacity-70" />
      <div className="relative glass p-5 space-y-4">
        <div className="flex items-center justify-between">
          <span className="text-xs text-slate-400">Balance</span>
          
        </div>
        <p className="font-num text-3xl text-white">12,480.00 <span className="text-amber-400 text-base">DC</span></p>
        <div className="h-36">
          <ResponsiveContainer width="100%" height={144} debounce={50}><AreaChart data={PREVIEW}>
            <defs><linearGradient id="hg" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#F59E0B" stopOpacity={0.5} /><stop offset="100%" stopColor="#F59E0B" stopOpacity={0} /></linearGradient></defs>
            <XAxis dataKey="d" hide /><Tooltip contentStyle={{ background: "#0C1120", border: "1px solid #334155", borderRadius: 12 }} />
            <Area type="monotone" dataKey="v" stroke="#F59E0B" fill="url(#hg)" strokeWidth={2} />
          </AreaChart></ResponsiveContainer>
        </div>
        <div className="grid grid-cols-3 gap-3 text-center">
          {[["Team", "48", "text-blue-300"], ["Rank", "Silver", "text-slate-200"], ["Plans", "3", "text-violet-300"]].map(([l, v, c]) => (
            <div key={l} className="rounded-xl bg-slate-950/60 border border-slate-800 py-3"><p className="text-[11px] text-slate-500">{l}</p><p className={`font-semibold ${c}`}>{v}</p></div>
          ))}
        </div>
      </div>
      <motion.div className="absolute -bottom-6 -left-6 glass px-4 py-3 hidden sm:flex items-center gap-3" animate={{ y: [0, -8, 0] }} transition={{ repeat: Infinity, duration: 5 }}>
        <Icons.BellRing className="w-4 h-4 text-amber-400" /><span className="text-xs text-slate-300">Payment record verified</span>
      </motion.div>
    </motion.div>
  );
}

export function Hero({ c }) {
  return (
    <section className="max-w-7xl mx-auto px-4 sm:px-6 pt-16 sm:pt-24 pb-20 grid lg:grid-cols-[1.15fr_1fr] gap-14 items-center">
      <div>
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="eyebrow mb-5">USDT wallet · plans · team network</motion.p>
        <motion.h1 initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }} className="font-display text-4xl sm:text-5xl lg:text-6xl font-bold text-white leading-[1.05]" data-testid="hero-headline">
          {c?.headline || "One Platform. Complete Financial Account Management."}
        </motion.h1>
        <motion.p initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.1 }} className="text-slate-300 mt-6 text-base sm:text-lg max-w-xl">{c?.description}</motion.p>
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.2 }} className="flex flex-wrap gap-3 mt-8">
          <Link to="/register" className="btn-gold" data-testid="hero-create-account-btn">Create Account <Icons.ArrowRight className="w-4 h-4" /></Link>
          <a href="#benefits" className="btn-ghost" data-testid="hero-explore-btn">Explore Platform</a>
          <a href="#plans" className="btn-ghost !text-violet-200 !border-violet-400/40" data-testid="hero-demo-plans-btn">View Plans</a>
        </motion.div>
        {c?.disclaimer && <div className="mt-8 flex gap-3 items-start rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 max-w-xl" data-testid="hero-disclaimer">
          <Icons.AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <p className="text-xs sm:text-sm text-amber-100/90">{c.disclaimer}</p>
        </div>}
      </div>
      <DashboardPreview />
    </section>
  );
}

export function Benefits({ items = [] }) {
  return (
    <section id="benefits" className="max-w-7xl mx-auto px-4 sm:px-6 py-20">
      <SectionHead eyebrow="Platform benefits" title="Everything about your account, in one transparent place." />
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {items.map((b, i) => {
          const Icon = Icons[b.icon] || Icons.Sparkles;
          return (
            <Reveal key={b.title} delay={i * 0.05}>
              <Glass className="glass-hover h-full" data-testid={`benefit-card-${i}`}>
                <span className={`inline-flex p-2.5 rounded-xl mb-4 ${["bg-amber-500/10 text-amber-400", "bg-blue-500/10 text-blue-400", "bg-violet-500/10 text-violet-400"][i % 3]}`}><Icon className="w-5 h-5" /></span>
                <h3 className="font-semibold text-white">{b.title}</h3>
                <p className="text-sm text-slate-400 mt-2">{b.text}</p>
              </Glass>
            </Reveal>
          );
        })}
      </div>
    </section>
  );
}

export function HowItWorks({ steps = [] }) {
  return (
    <section id="how" className="max-w-7xl mx-auto px-4 sm:px-6 py-20">
      <SectionHead eyebrow="How it works" title="Six steps from sign-up to a complete dashboard." />
      <div className="grid md:grid-cols-3 gap-5 relative">
        {steps.map((s, i) => (
          <Reveal key={s} delay={i * 0.07}>
            <div className="glass glass-hover p-6 h-full relative overflow-hidden" data-testid={`how-step-${i + 1}`}>
              <span className="absolute -right-3 -top-6 font-heading text-8xl text-amber-500/10">{i + 1}</span>
              <p className="font-num text-amber-400 text-sm">STEP 0{i + 1}</p>
              <p className="text-white font-semibold mt-2 text-lg">{s}</p>
            </div>
          </Reveal>
        ))}
      </div>
    </section>
  );
}

const MARKET_ICONS = [Icons.Bitcoin, Icons.Globe2, Icons.Gem, Icons.IndianRupee, Icons.MapPinned];

export function Trading({ items = [], risks = [] }) {
  return (
    <section id="markets" className="max-w-7xl mx-auto px-4 sm:px-6 py-20">
      <SectionHead eyebrow="Trading information" title="Five market categories — and their real risks." text="These descriptions are educational. No trading activity produces consistent or guaranteed profits." />
      <div className="grid lg:grid-cols-[1.4fr_1fr] gap-6">
        <div className="grid sm:grid-cols-2 gap-4">
          {items.map((m, i) => {
            const Icon = MARKET_ICONS[i] || Icons.LineChart;
            return (
              <Reveal key={m.title} delay={i * 0.05}>
                <Glass className="glass-hover h-full" data-testid={`market-card-${i}`}>
                  <Icon className="w-6 h-6 text-blue-400 mb-3" />
                  <h3 className="text-white font-semibold">{m.title}</h3>
                  <p className="text-sm text-slate-400 mt-2">{m.text}</p>
                  <p className="text-xs text-red-300/90 mt-3 border-t border-slate-800 pt-3"><span className="font-semibold">Key risks:</span> {m.risks}</p>
                </Glass>
              </Reveal>
            );
          })}
        </div>
        <Reveal>
          <div className="glass p-6 border-red-500/20 h-full" data-testid="risk-panel">
            <p className="eyebrow !text-red-300 mb-4">Risk education</p>
            <ul className="space-y-4">
              {risks.map((r) => <li key={r} className="flex gap-3 text-sm text-slate-300"><Icons.AlertOctagon className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />{r}</li>)}
            </ul>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
