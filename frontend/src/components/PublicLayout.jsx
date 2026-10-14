import { useState } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";
import { Menu, X, ShieldAlert } from "lucide-react";
import { useSite } from "@/components/common";
import { useAuth } from "@/context/AuthContext";

const NAV = [["Benefits", "/#benefits"], ["Plans", "/#plans"], ["How it works", "/#how"], ["Markets", "/#markets"], ["Team", "/#team"], ["Rewards", "/#rewards"], ["FAQ", "/#faq"]];
const FOOT = [["About Us", "about"], ["Contact", "contact"], ["Support", "support"], ["Privacy Policy", "privacy"], ["Terms and Conditions", "terms"], ["Risk Disclosure", "risk"],
  ["Refund Policy", "refund"], ["Complaint Resolution", "complaints"], ["Cookie Preferences", "cookies"], ["Company Information", "company"]];

export const Logo = ({ name }) => (
  <Link to="/" className="flex items-center gap-2.5" data-testid="brand-logo">
    <span className="w-9 h-9 rounded-xl bg-gradient-to-br from-amber-300 via-amber-500 to-amber-700 grid place-items-center text-slate-950 font-heading font-extrabold shadow-[0_0_18px_rgba(245,158,11,.4)]">{(name || "A")[0]}</span>
    <span className="font-heading font-bold text-lg text-white tracking-wide">{name}</span>
  </Link>
);

function TopNav({ name }) {
  const [open, setOpen] = useState(false);
  const { user } = useAuth();
  const dash = user?.role === "super_admin" ? "/admin" : "/app";
  return (
    <header className="sticky top-0 z-40 bg-[#070A12]/80 backdrop-blur-xl border-b border-slate-800/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        <Logo name={name} />
        <nav className="hidden lg:flex items-center gap-6 text-sm text-slate-300">
          {NAV.map(([l, h]) => <a key={h} href={h} className="hover:text-amber-300 transition-colors" data-testid={`nav-${l.toLowerCase().replace(/ /g, "-")}`}>{l}</a>)}
        </nav>
        <div className="hidden lg:flex items-center gap-3">
          {user ? <Link to={dash} className="btn-gold" data-testid="nav-dashboard-btn">Open dashboard</Link> : (<>
            <Link to="/login" className="text-sm text-slate-300 hover:text-white" data-testid="nav-login-btn">Sign in</Link>
            <Link to="/register" className="btn-gold !py-2" data-testid="nav-register-btn">Create Account</Link></>)}
        </div>
        <button className="lg:hidden p-2 text-slate-200" onClick={() => setOpen(!open)} aria-label="Menu" data-testid="mobile-menu-toggle">{open ? <X /> : <Menu />}</button>
      </div>
      {open && (
        <div className="lg:hidden border-t border-slate-800 bg-[#070A12] px-4 py-4 space-y-1" data-testid="mobile-menu">
          {NAV.map(([l, h]) => <a key={h} href={h} onClick={() => setOpen(false)} className="block py-3 text-slate-200 border-b border-slate-800/60">{l}</a>)}
          <div className="flex gap-3 pt-3">
            {user ? <Link to={dash} className="btn-gold flex-1">Dashboard</Link> : (<>
              <Link to="/login" className="btn-ghost flex-1" data-testid="mobile-login-btn">Sign in</Link>
              <Link to="/register" className="btn-gold flex-1" data-testid="mobile-register-btn">Create Account</Link></>)}
          </div>
        </div>
      )}
    </header>
  );
}

function Footer({ site }) {
  const c = site?.content?.footer || {};
  const s = site?.settings || {};
  return (
    <footer className="border-t border-slate-800 bg-[#05070d] mt-24">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-14 grid gap-10 md:grid-cols-[1.3fr_2fr]">
        <div className="space-y-4">
          <Logo name={s.site_name} />
          <p className="text-sm text-slate-400 max-w-sm">{c.about}</p>
          <p className="text-xs text-slate-500">{c.note}</p>
          <p className="text-xs text-slate-500">Contact: {s.contact?.email}</p>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-sm">
          {FOOT.map(([l, slug]) => <Link key={slug} to={`/legal/${slug}`} className="text-slate-400 hover:text-amber-300 transition-colors" data-testid={`footer-${slug}`}>{l}</Link>)}
        </div>
      </div>
      <div className="border-t border-slate-800/70 py-5 px-4 text-center text-xs text-slate-500 flex items-center justify-center gap-2">
        <ShieldAlert className="w-3.5 h-3.5 text-amber-500" /> DEMO MODE · simulated coins and hypothetical figures only · © {new Date().getFullYear()} {s.site_name}
      </div>
    </footer>
  );
}

export default function PublicLayout() {
  const { data } = useSite();
  const loc = useLocation();
  const banner = data?.content?.banners?.find((b) => b.active);
  return (
    <div className="min-h-screen mesh-bg grain text-slate-200" key={loc.pathname === "/" ? "home" : "page"}>
      {banner && <div className="bg-amber-500/10 border-b border-amber-500/30 text-amber-200 text-xs sm:text-sm text-center py-2 px-4" data-testid="site-banner">{banner.text}</div>}
      <TopNav name={data?.settings?.site_name || "AurumNet"} />
      <main className="relative z-10"><Outlet /></main>
      <Footer site={data} />
    </div>
  );
}
