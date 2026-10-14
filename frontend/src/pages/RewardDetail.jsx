import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, ArrowLeft } from "lucide-react";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Progress } from "@/components/ui/progress";
import { api, coins } from "@/lib/api";
import { Glass, Loader, Empty, StatusBadge, useSite } from "@/components/common";
import { useAuth } from "@/context/AuthContext";

const List = ({ title, items = [], testid }) => (
  <Glass data-testid={testid}>
    <h3 className="font-semibold text-white mb-3">{title}</h3>
    <ul className="space-y-2">{items.map((x) => <li key={x} className="flex gap-2 text-sm text-slate-300"><CheckCircle2 className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />{x}</li>)}</ul>
  </Glass>
);

function MyProgress({ rewardId }) {
  const { user } = useAuth();
  const q = useQuery({ queryKey: ["my-rewards"], queryFn: () => api.get("/rewards").then((r) => r.data), enabled: !!user });
  if (!user) return <Glass><p className="text-sm text-slate-400">Sign in to see your progress toward this milestone.</p><Link to="/login" className="btn-gold mt-3" data-testid="reward-login-btn">Sign in</Link></Glass>;
  const r = q.data?.rewards.find((x) => x.id === rewardId);
  if (!r) return <Loader />;
  return (
    <Glass data-testid="reward-progress">
      <p className="text-sm text-slate-400">Your team volume</p>
      <p className="font-num text-2xl text-white">{coins(q.data.team_volume, 0)}</p>
      <Progress value={r.progress_pct} className="h-2 mt-3" />
      <p className="text-xs text-slate-500 mt-2">{r.progress_pct}% of milestone</p>
      <div className="mt-3">Claim status: {r.claim ? <StatusBadge status={r.claim.status} testid="reward-claim-status" /> : <span className="text-sm text-slate-400">No claim</span>}</div>
      <Link to="/app/rewards" className="btn-ghost mt-4" data-testid="reward-goto-dashboard">Manage in dashboard</Link>
    </Glass>
  );
}

export default function RewardDetail() {
  const { slug } = useParams();
  const q = useQuery({ queryKey: ["reward", slug], queryFn: () => api.get(`/public/rewards/${slug}`).then((r) => r.data), retry: false });
  if (q.isLoading) return <Loader />;
  if (q.isError) return <div className="max-w-3xl mx-auto p-10"><Empty title="Reward not found" /></div>;
  const r = q.data;
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-12" data-testid="reward-detail-page">
      <Link to="/#rewards" className="text-sm text-slate-400 hover:text-amber-300 inline-flex items-center gap-1 mb-6"><ArrowLeft className="w-4 h-4" /> All rewards</Link>
      <div className="grid lg:grid-cols-[1.3fr_1fr] gap-8">
        <div className="space-y-6">
          <div className="rounded-2xl overflow-hidden border border-amber-500/20 aspect-[16/10]"><img src={r.image_url} alt={r.title} className="w-full h-full object-cover" /></div>
          <div className="flex gap-3 items-start rounded-xl border border-amber-500/30 bg-amber-500/5 p-4" data-testid="reward-disclaimer">
            <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0" />
            <p className="text-sm text-amber-100/90">Rewards are subject to campaign terms, eligibility review and availability. They are not guaranteed.</p>
          </div>
          <div className="grid md:grid-cols-2 gap-5">
            <List title="Qualification rules" items={r.qualification_rules} testid="reward-rules" />
            <List title="Eligibility requirements" items={r.eligibility} testid="reward-eligibility" />
            <List title="Redemption process" items={r.redemption} testid="reward-redemption" />
            <List title="Terms and conditions" items={r.terms} testid="reward-terms" />
          </div>
          <Glass>
            <h3 className="font-semibold text-white mb-2">FAQs</h3>
            <Accordion type="single" collapsible>{(r.faqs || []).map((f, i) => (
              <AccordionItem key={i} value={`r${i}`} className="border-slate-800"><AccordionTrigger className="text-left">{f.q}</AccordionTrigger><AccordionContent className="text-slate-400">{f.a}</AccordionContent></AccordionItem>
            ))}</Accordion>
          </Glass>
        </div>
        <div className="space-y-5 lg:sticky lg:top-24 self-start">
          <Glass>
            <p className="eyebrow mb-2">{r.category}</p>
            <h1 className="font-heading text-3xl sm:text-4xl text-white" data-testid="reward-title">{r.title}</h1>
            <p className="text-slate-400 mt-3 text-sm">{r.description}</p>
            <div className="grid grid-cols-2 gap-3 mt-5">
              <div className="rounded-xl bg-slate-950/60 border border-slate-800 p-3"><p className="text-[11px] text-slate-500">Team milestone</p><p className="font-num text-amber-300">{coins(r.milestone, 0)}</p></div>
              <div className="rounded-xl bg-slate-950/60 border border-slate-800 p-3"><p className="text-[11px] text-slate-500">Availability</p><p className="font-num text-white" data-testid="reward-inventory">{r.inventory > 0 ? `${r.inventory} units` : "Unavailable"}</p></div>
              {r.duration && <div className="rounded-xl bg-slate-950/60 border border-slate-800 p-3 col-span-2"><p className="text-[11px] text-slate-500">Duration</p><p className="text-white">{r.duration}</p></div>}
            </div>
          </Glass>
          <MyProgress rewardId={r.id} />
        </div>
      </div>
    </div>
  );
}

export function LegalPage() {
  const { slug } = useParams();
  const { data, isLoading } = useSite();
  if (isLoading) return <Loader />;
  const page = data?.content?.[`legal_${slug}`];
  if (!page) return <div className="max-w-3xl mx-auto p-10"><Empty title="Page not found" /></div>;
  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-14" data-testid={`legal-page-${slug}`}>
      <p className="eyebrow mb-3">Legal & information</p>
      <h1 className="font-display text-4xl font-bold text-white mb-8">{page.title}</h1>
      <Glass className="space-y-4">{(page.body || []).map((p, i) => <p key={i} className="text-slate-300 leading-relaxed">{p}</p>)}</Glass>
    </div>
  );
}
