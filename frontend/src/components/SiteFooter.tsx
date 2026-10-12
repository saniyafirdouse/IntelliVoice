import type { CSSProperties } from "react";
import { Link } from "react-router-dom";
import type { HeaderVariant } from "./SiteHeader";

const LOOK: Record<HeaderVariant, {
  footer: { className: string; style: CSSProperties };
  gap: string; name: string; badge: { className: string; style?: CSSProperties };
  line1: string; line2: string; project: string; tagline: string; link: string; dot: string;
}> = {
  marketing: {
    footer: {
      className: "relative z-10 w-full transition-all duration-300",
      style: { background: "rgba(20, 16, 28, 0.5)", backdropFilter: "blur(20px)", WebkitBackdropFilter: "blur(20px)", borderTop: "1px solid rgba(255, 255, 255, 0.22)", boxShadow: "rgba(0, 0, 0, 0.35) 0px -10px 30px" },
    },
    gap: "gap-1",
    name: "font-mk-display font-bold text-white text-base glass-text-glow",
    badge: { className: "text-xs font-bold text-white border border-white/30 px-2 py-0.5 rounded-full shadow-sm", style: { background: "rgba(191, 194, 255, 0.35)" } },
    line1: "text-xs text-slate-200 font-medium glass-text-glow",
    line2: "text-xs text-slate-300 font-mono font-medium glass-text-glow",
    project: "text-xs font-bold text-white tracking-wide glass-text-glow",
    tagline: "text-xs text-slate-200 font-medium glass-text-glow",
    link: "text-xs text-mk-secondary font-semibold hover:underline underline-offset-4 transition-colors glass-text-glow",
    dot: "text-slate-400",
  },
  app: {
    footer: {
      className: "w-full shadow-[0_-4px_30px_rgba(0,0,0,0.6)] mt-space-2xl",
      style: { background: "rgba(12, 14, 14, 0.9)", backdropFilter: "blur(24px)", WebkitBackdropFilter: "blur(24px)", borderTop: "1px solid rgba(255, 255, 255, 0.25)", textShadow: "rgba(0, 0, 0, 0.8) 0px 1px 3px" },
    },
    gap: "gap-space-xs",
    name: "font-title-md text-title-md text-white font-bold",
    badge: { className: "font-label-sm text-label-sm text-white font-bold bg-[#585cb0] px-2 py-0.5 rounded border border-white/20" },
    line1: "font-body-sm text-body-sm text-white/95 font-medium",
    line2: "font-label-sm text-label-sm text-white/80 font-medium",
    project: "font-label-md text-label-md text-secondary font-bold",
    tagline: "font-body-sm text-body-sm text-white/95 font-medium",
    link: "font-label-sm text-label-sm text-white font-medium hover:underline transition-colors",
    dot: "text-white/60",
  },
};

export function SiteFooter({ variant }: { variant: HeaderVariant }) {
  const look = LOOK[variant];
  return (
    <footer className={look.footer.className} style={look.footer.style}>
      <div className="w-full px-margin-mobile lg:px-margin py-space-xl flex flex-col md:flex-row items-center justify-between gap-space-lg">
        <div className={`flex flex-col items-center md:items-start text-center md:text-left ${look.gap}`}>
          <div className="flex flex-wrap items-center justify-center gap-2">
            <span className={look.name}>Sai Vidya Institute of Technology</span>
            <span className={look.badge.className} style={look.badge.style}>Autonomous</span>
          </div>
          <p className={look.line1}>NAAC &apos;A&apos; Grade Accredited | Approved by AICTE, Affiliated to VTU Belagavi</p>
          <p className={look.line2}>Rajanukunte, Doddaballapur Road, Bengaluru, Karnataka 560064</p>
        </div>
        <div className={`flex flex-col items-center md:items-end text-center md:text-right ${look.gap}`}>
          <span className={look.project}>ISE Final Year Major Project 2026-27</span>
          <p className={look.tagline}>IntelliVoice — Multilingual Voice Assistant for SVIT Admissions</p>
          <div className="flex items-center gap-4 mt-2">
            <Link className={look.link} to="/help">Help &amp; FAQ</Link>
            <span className={look.dot}>•</span>
            <Link className={look.link} to="/about">About the Project</Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
