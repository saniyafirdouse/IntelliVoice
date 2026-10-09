import { useEffect, useState, type CSSProperties } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useLanguage } from "../context/LanguageContext";
import type { LangCode } from "../lib/types";
import { Icon } from "./Icon";

export type HeaderVariant = "marketing" | "app";

const NAV = [
  { to: "/", label: "Home", end: true },
  { to: "/chat", label: "Voice Chat" },
  { to: "/about", label: "About" },
  { to: "/help", label: "Help & FAQ" },
];

const LANGS: { code: LangCode; label: string }[] = [
  { code: "en", label: "ENG" },
  { code: "kn", label: "KN" },
  { code: "hi", label: "HI" },
];

// Two looks exported from Stitch: "marketing" (Home, About) and "app" (Chat, FAQ, Sign in).
const LOOK: Record<HeaderVariant, {
  header: { className: string; style: CSSProperties };
  bar: string; barFill: { className: string; style?: CSSProperties };
  logoWrap: string; title: string; badge: string; subtitle: string;
  nav: { className: string; style?: CSSProperties };
  link: string; linkActive: { className: string; style: CSSProperties };
  langWrap: { className: string; style?: CSSProperties };
  lang: string; langActive: { className: string; style: CSSProperties };
  divider: string; live: string; liveDot: string; liveText: string;
}> = {
  marketing: {
    header: {
      className: "fixed top-0 left-0 w-full z-50 transition-all duration-300",
      style: { background: "rgba(12, 14, 24, 0.18)", backdropFilter: "blur(16px)", WebkitBackdropFilter: "blur(16px)", borderBottom: "1px solid rgba(255, 255, 255, 0.15)", boxShadow: "rgba(0, 0, 0, 0.2) 0px 4px 24px" },
    },
    bar: "w-full h-[3px] bg-[#bfc2ff]/40",
    barFill: { className: "h-full bg-white w-1/3 transition-all duration-300 shadow-[0_0_12px_rgba(255,255,255,0.8)]" },
    logoWrap: "w-11 h-11 rounded-full bg-[#7E82C2]/50 border border-white/40 flex items-center justify-center text-white shadow-[0_0_20px_rgba(126,130,194,0.45)]",
    title: "font-mk-display font-bold text-lg tracking-tight text-white flex items-center gap-1.5 drop-shadow-sm",
    badge: "text-[10px] tracking-wider text-[#10134f] bg-[#EBE7F5] px-2 py-0.5 rounded-full uppercase font-bold shadow-sm",
    subtitle: "text-xs text-white/85 font-medium tracking-wide",
    nav: { className: "hidden xl:flex items-center gap-space-xs p-1.5 rounded-full", style: { background: "rgba(20, 22, 36, 0.18)", backdropFilter: "blur(16px)", border: "1px solid rgba(255, 255, 255, 0.16)" } },
    link: "px-space-md py-space-xs rounded-full text-sm font-medium text-white/85 hover:text-white hover:bg-white/20 transition-all",
    linkActive: { className: "px-space-md py-space-xs rounded-full font-semibold text-white shadow-md text-sm transition-all", style: { background: "rgba(126, 130, 194, 0.75)", border: "1px solid rgba(255, 255, 255, 0.5)", boxShadow: "rgba(126, 130, 194, 0.45) 0px 2px 14px" } },
    langWrap: { className: "hidden sm:flex items-center gap-1 p-1 rounded-full", style: { background: "rgba(14, 16, 26, 0.22)", backdropFilter: "blur(16px)", border: "1px solid rgba(255, 255, 255, 0.18)" } },
    lang: "px-3 py-1 rounded-full text-xs text-white/85 hover:text-white hover:bg-white/20 transition-colors font-medium",
    langActive: { className: "px-3 py-1 rounded-full text-xs text-white font-bold transition-all shadow-sm", style: { background: "rgba(126, 130, 194, 0.85)", border: "1px solid rgba(255, 255, 255, 0.5)" } },
    divider: "h-6 w-px bg-white/30 hidden sm:block",
    live: "hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-full glass-card text-white text-xs font-semibold tracking-wide",
    liveDot: "w-2 h-2 rounded-full bg-emerald-400 animate-pulse",
    liveText: "",
  },
  app: {
    header: {
      className: "fixed top-0 left-0 w-full z-50 bg-primary-container/45 backdrop-blur-xl shadow-[0_4px_30px_rgba(10,3,7,0.45)]",
      style: { background: "rgba(255, 255, 255, 0.06)", backdropFilter: "blur(20px)", WebkitBackdropFilter: "blur(20px)", borderBottom: "1px solid rgba(255, 255, 255, 0.18)" },
    },
    bar: "w-full h-[3px] bg-secondary/30",
    barFill: { className: "h-full bg-secondary w-1/3 transition-all duration-300", style: { background: "linear-gradient(90deg, rgb(114, 47, 55), rgb(155, 61, 86))" } },
    logoWrap: "w-10 h-10 rounded-full bg-secondary-container/40 flex items-center justify-center text-secondary shadow-[0_0_16px_rgba(191,194,255,0.2)]",
    title: "font-title-lg text-title-lg tracking-tight text-on-surface flex items-center gap-space-xs",
    badge: "font-label-sm text-label-sm text-secondary bg-secondary-container/60 px-space-xs py-0.5 rounded-full uppercase",
    subtitle: "font-label-sm text-label-sm text-on-surface-variant",
    nav: { className: "hidden xl:flex items-center gap-space-xs bg-surface-container-lowest/40 backdrop-blur-md p-1.5 rounded-full" },
    link: "px-space-md py-space-xs rounded-full font-body-md text-body-md text-on-surface-variant hover:text-on-surface hover:bg-surface-variant transition-all",
    linkActive: { className: "px-space-md py-space-xs rounded-full transition-all bg-secondary-container text-on-secondary-container font-title-md", style: { backgroundColor: "rgb(126, 130, 194)", color: "rgb(255, 255, 255)", border: "1px solid rgba(255, 255, 255, 0.25)" } },
    langWrap: { className: "hidden sm:flex items-center gap-1 bg-surface-container-lowest/50 p-1 rounded-full" },
    lang: "px-2.5 py-1 rounded-full font-label-sm text-label-sm text-on-surface-variant hover:text-white hover:bg-white/10 transition-colors",
    langActive: { className: "px-2.5 py-1 rounded-full font-label-sm text-label-sm text-white font-medium shadow-sm transition-all", style: { backgroundColor: "rgb(126, 130, 194)", color: "rgb(255, 255, 255)", border: "1px solid rgba(255, 255, 255, 0.25)" } },
    divider: "h-6 w-px bg-outline-variant/40 hidden sm:block",
    live: "hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-surface-container-high/60 backdrop-blur-md",
    liveDot: "w-2 h-2 rounded-full bg-secondary animate-pulse",
    liveText: "font-label-sm text-label-sm text-secondary",
  },
};

const pill = "inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-bold text-white border border-white/35 no-underline";

function AuthMenu() {
  const { user, logout } = useAuth();
  if (!user) {
    return (
      <Link to="/login" aria-label="Sign In" className={pill} style={{ background: "rgb(88, 92, 176)" }}>
        <Icon name="login" className="text-[16px]" />
        <span className="hidden sm:inline">Sign In</span>
      </Link>
    );
  }
  const first = (user.name || "Account").split(" ")[0];
  return (
    <>
      <span className={pill} style={{ background: "rgba(88, 92, 176, 0.55)" }} title={user.email}>
        <Icon name="account_circle" className="text-[16px]" />
        <span className="hidden sm:inline">{first}{user.role === "admin" ? " · Admin" : ""}</span>
      </span>
      <button type="button" onClick={logout} className={`${pill} cursor-pointer`} style={{ background: "rgba(0, 0, 0, 0.35)" }}>
        <Icon name="logout" className="text-[16px]" />
        <span className="hidden sm:inline">Sign Out</span>
      </button>
    </>
  );
}

export function SiteHeader({ variant }: { variant: HeaderVariant }) {
  const look = LOOK[variant];
  const { quickLanguage: language, setQuickLanguage: setLanguage } = useLanguage();
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();

  useEffect(() => setMenuOpen(false), [location.pathname]);

  return (
    <header className={look.header.className} style={look.header.style}>
      <div className={look.bar}>
        <div className={look.barFill.className} style={look.barFill.style} />
      </div>
      <div className="h-20 w-full px-margin-mobile lg:px-margin flex items-center justify-between gap-space-md">
        <Link to="/" className="flex items-center gap-space-md flex-shrink-0 min-w-0">
          <div className={look.logoWrap}>
            <img src="/assets/svit-logo.png" alt="SVIT Logo" className="w-full h-full object-contain rounded-full" />
          </div>
          <div className="flex flex-col min-w-0">
            <span className={look.title}>
              IntelliVoice
              <span className={look.badge}>AI</span>
            </span>
            <span className={`${look.subtitle} truncate`}>SVIT Bengaluru Admission Hub</span>
          </div>
        </Link>

        <nav className={look.nav.className} style={look.nav.style} aria-label="Main">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => (isActive ? look.linkActive.className : look.link)}
              style={({ isActive }) => (isActive ? look.linkActive.style : undefined)}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="flex items-center gap-space-sm">
          <div className={look.langWrap.className} style={look.langWrap.style} role="group" aria-label="Quick language: speak and reply in">
            {LANGS.map((l) => {
              const active = l.code === language;
              return (
                <button
                  key={l.code}
                  type="button"
                  aria-pressed={active}
                  onClick={() => setLanguage(l.code)}
                  className={active ? look.langActive.className : look.lang}
                  style={active ? look.langActive.style : undefined}
                >
                  {l.label}
                </button>
              );
            })}
          </div>
          <div className={look.divider} />
          <div className="flex items-center gap-space-xs">
            <div className={look.live}>
              <span className={look.liveDot} />
              <span className={look.liveText}>Live</span>
            </div>
            <AuthMenu />
            <button
              type="button"
              className="xl:hidden w-9 h-9 rounded-full flex items-center justify-center text-white border border-white/30 bg-white/10 hover:bg-white/20"
              aria-label={menuOpen ? "Close menu" : "Open menu"}
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen((o) => !o)}
            >
              <Icon name={menuOpen ? "close" : "menu"} className="text-[20px]" />
            </button>
          </div>
        </div>
      </div>

      {menuOpen && (
        <nav
          aria-label="Mobile"
          className="xl:hidden mx-margin-mobile mb-3 p-2 rounded-2xl flex flex-col gap-1 border border-white/20"
          style={{ background: "rgba(14, 16, 26, 0.92)", backdropFilter: "blur(20px)" }}
        >
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `px-4 py-2.5 rounded-xl text-white font-semibold ${isActive ? "bg-[#7E82C2]/80" : "hover:bg-white/10"}`}
            >
              {item.label}
            </NavLink>
          ))}
          <div className="sm:hidden flex items-center gap-1 px-2 pt-2" role="group" aria-label="Quick language: speak and reply in">
            {LANGS.map((l) => (
              <button
                key={l.code}
                type="button"
                aria-pressed={l.code === language}
                onClick={() => setLanguage(l.code)}
                className={`px-3 py-1 rounded-full text-xs font-bold text-white border border-white/25 ${l.code === language ? "bg-[#7E82C2]" : "bg-white/5"}`}
              >
                {l.label}
              </button>
            ))}
          </div>
        </nav>
      )}
    </header>
  );
}
