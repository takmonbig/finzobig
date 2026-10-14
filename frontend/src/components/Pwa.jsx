import { useEffect, useState } from "react";
import { Download, ShieldCheck, Lock } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";

let deferred = null;
const subs = new Set();
const emit = () => subs.forEach((f) => f());
const KEY = "pwa_prompt_at";
const GAP = 3.5 * 3600 * 1000;

if (typeof window !== "undefined") {
  window.addEventListener("beforeinstallprompt", (e) => { e.preventDefault(); deferred = e; emit(); });
  window.addEventListener("appinstalled", () => { deferred = null; localStorage.setItem("pwa_installed", "1"); emit(); });
  if ("serviceWorker" in navigator) window.addEventListener("load", () => { navigator.serviceWorker.register("/sw.js").catch(() => {}); });
}

const standalone = () => window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone === true;
const isIOS = () => /iphone|ipad|ipod/i.test(navigator.userAgent);

export function usePwa() {
  const [, force] = useState(0);
  useEffect(() => {
    const f = () => force((n) => n + 1);
    subs.add(f);
    return () => { subs.delete(f); };
  }, []);
  const install = async () => {
    if (!deferred) return false;
    deferred.prompt();
    const r = await deferred.userChoice;
    deferred = null;
    emit();
    return r.outcome === "accepted";
  };
  return { installed: standalone() || localStorage.getItem("pwa_installed") === "1", canPrompt: !!deferred, ios: isIOS(), install };
}

function Steps({ ios }) {
  return ios
    ? <p className="text-sm text-slate-300">On iPhone or iPad: tap the <b>Share</b> button in Safari, then choose <b>Add to Home Screen</b>.</p>
    : <p className="text-sm text-slate-300">Open the browser menu (⋮) in Chrome or Edge and choose <b>Install app</b> or <b>Add to Home screen</b>.</p>;
}

function InstallDialog({ open, onClose }) {
  const p = usePwa();
  const go = async () => { if (await p.install()) onClose(); };
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="bg-[#0C1120] border-amber-500/30 max-w-sm" data-testid="pwa-install-dialog">
        <DialogHeader>
          <div className="mx-auto mb-2"><img src="/img/favicon-192.png" alt="" className="w-16 h-16" /></div>
          <DialogTitle className="text-center">Install the Finzo.cc app</DialogTitle>
          <DialogDescription className="text-center">Faster access from your home screen, full-screen view and instant notifications.</DialogDescription>
        </DialogHeader>
        {p.canPrompt ? <button className="btn-gold w-full" onClick={go} data-testid="pwa-install-confirm-btn"><Download className="w-4 h-4" />Install app</button> : <Steps ios={p.ios} />}
        <button className="btn-ghost w-full" onClick={onClose} data-testid="pwa-later-btn">Maybe later</button>
      </DialogContent>
    </Dialog>
  );
}

export function InstallButton({ className = "" }) {
  const p = usePwa();
  const [open, setOpen] = useState(false);
  if (p.installed) return null;
  const click = async () => { if (!p.canPrompt || !(await p.install())) setOpen(true); };
  return (<>
    <button onClick={click} className={`inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-full border border-amber-400/50 text-amber-200 bg-amber-500/10 hover:bg-amber-500/20 transition-colors ${className}`} data-testid="pwa-install-btn">
      <Download className="w-3.5 h-3.5" />Install app
    </button>
    <InstallDialog open={open} onClose={() => setOpen(false)} />
  </>);
}

export function InstallPopup() {
  const p = usePwa();
  const [open, setOpen] = useState(false);
  useEffect(() => {
    if (p.installed) return undefined;
    const check = () => { if (Date.now() - Number(localStorage.getItem(KEY) || 0) >= GAP) setOpen(true); };
    const t = setTimeout(check, 2500);
    const i = setInterval(check, 10 * 60 * 1000);
    return () => { clearTimeout(t); clearInterval(i); };
  }, [p.installed]);
  const close = () => { localStorage.setItem(KEY, String(Date.now())); setOpen(false); };
  if (p.installed) return null;
  return <InstallDialog open={open} onClose={close} />;
}

export const TrustBadge = () => (
  <span className="inline-flex items-center gap-1.5 text-[10px] px-2.5 py-1 rounded-full border border-emerald-500/30 bg-emerald-500/5 text-emerald-300/90" data-testid="trust-badge">
    <ShieldCheck className="w-3 h-3" />Secure sessions<span className="text-slate-600">·</span><Lock className="w-3 h-3" />On-chain verified USDT payments
  </span>
);
