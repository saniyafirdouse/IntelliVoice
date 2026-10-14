import { useEffect, useRef, useState, type CSSProperties } from "react";
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

/** Extra link shown in the header only to signed-in admins. */
const ADMIN_NAV = { to: "/admin", label: "Admin Panel", end: false };

// Language menu (2026-10-14): what you speak + how IntelliVoice replies.
// "in English letters" = romanized Kannada / Hindi, e.g. "CSE fees eshtu?"
type LangChoice = { id: string; short: string; label: string; hint?: string; code: LangCode | null; roman: boolean };
const LANG_CHOICES: LangChoice[] = [
  { id: "auto", short: "AUTO", label: "Auto-detect", hint: "Mixed languages, reply in the same", code: null, roman: false },
  { id: "en", short: "ENG", label: "English", code: "en", roman: false },
  { id: "kn", short: "ಕನ್ನಡ", label: "ಕನ್ನಡ · Kannada", code: "kn", roman: false },
  { id: "kn-Latn", short: "KN·ENG", label: "Kannada in English letters", hint: "e.g. \"CSE fees eshtu?\"", code: "kn", roman: true },
  { id: "hi", short: "हिंदी", label: "हिंदी · Hindi", code: "hi", roman: false },
  { id: "hi-Latn", short: "HI·ENG", label: "Hindi in English letters", hint: "e.g. \"CSE ki fees kitni hai?\"", code: "hi", roman: true },
];

function useLanguageChoice() {
  const { quickLanguage, romanized, setSpeechLanguage, setResponseLanguage, clearQuickLanguage } = useLanguage();
  const current =
    LANG_CHOICES.find((c) => c.code !== null && c.code === quickLanguage && (c.code === "en" || c.roman === romanized)) ?? LANG_CHOICES[0];
  const choose = (c: LangChoice) => {
    if (c.code === null) { clearQuickLanguage(); return; }
    setSpeechLanguage(c.code);
    setResponseLanguage(c.roman ? (`${c.code}-Latn` as "kn-Latn" | "hi-Latn") : c.code);
  };
  return { current, choose };
}

/** "ENG ▾" pill that opens the list of language choices (also used in the chat's question bar). */
export function LanguageMenu({ up = false, className = "hidden sm:block" }: { up?: boolean; className?: string }) {
  const { current, choose } = useLanguageChoice();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", esc);
    return () => { document.removeEventListener("mousedown", close); document.removeEventListener("keydown", esc); };
  }, [open]);
  return (
    <div ref={ref} className={`relative ${className}`}>
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        title="Language you speak and the reply language"
        onClick={() => setOpen((o) => !o)}
        className="h-[38px] pl-4 pr-3 rounded-full flex items-center gap-1.5 text-[14px] font-semibold text-white transition-colors hover:bg-white/10"
        style={{ background: "rgba(22, 26, 30, 0.75)", border: "1px solid rgba(255, 255, 255, 0.22)" }}
      >
        {current.short}
        <Icon name="expand_more" className={`text-[18px] transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <ul
          role="listbox"
          aria-label="Language"
          className={`absolute right-0 ${up ? "bottom-full mb-2" : "mt-2"} w-[250px] p-1.5 rounded-2xl z-50`}
          style={{ background: "rgba(22, 22, 26, 0.96)", border: "1px solid rgba(255, 255, 255, 0.14)", boxShadow: "0 18px 40px rgba(0,0,0,0.5)", backdropFilter: "blur(16px)" }}
        >
          {LANG_CHOICES.map((c) => {
            const active = c.id === current.id;
            return (
              <li key={c.id}>
                <button
                  type="button"
                  role="option"
                  aria-selected={active}
                  onClick={() => { choose(c); setOpen(false); }}
                  className={`w-full text-left px-3 py-2 rounded-xl flex items-center justify-between gap-2 transition-colors ${active ? "bg-white/12" : "hover:bg-white/8"}`}
                >
                  <span className="flex flex-col">
                    <span className="text-[14px] text-white font-medium">{c.label}</span>
                    {c.hint && <span className="text-[11.5px] text-white/55">{c.hint}</span>}
                  </span>
                  {active && <Icon name="check" className="text-[18px] text-[#b9cf94]" />}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

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
    // 2026-10-14: matches the Voice Chat reference — dark warm-to-cool bar, plain links, outlined pills
    header: {
      className: "fixed top-0 left-0 w-full z-50",
      style: { background: "linear-gradient(90deg, rgba(25, 19, 13, 0.94) 0%, rgba(30, 32, 36, 0.92) 55%, rgba(20, 20, 24, 0.94) 100%)", backdropFilter: "blur(14px)", WebkitBackdropFilter: "blur(14px)", borderBottom: "1px solid rgba(255, 255, 255, 0.07)" },
    },
    bar: "hidden",
    barFill: { className: "hidden" },
    logoWrap: "w-11 h-11 rounded-full flex items-center justify-center",
    title: "text-[17px] font-semibold tracking-tight text-white flex items-center gap-1.5",
    badge: "text-[17px] font-semibold text-[#b9cf94]",
    subtitle: "text-[12px] text-white/75",
    nav: { className: "hidden xl:flex items-center gap-1" },
    link: "relative px-4 py-2 rounded-full text-[14px] font-medium text-white/85 hover:text-white hover:bg-white/5 transition-colors",
    linkActive: { className: "relative px-4 py-2 rounded-full text-[14px] font-semibold text-white after:content-[''] after:absolute after:left-4 after:right-4 after:-bottom-0.5 after:h-[2px] after:rounded-full after:bg-white/70", style: { background: "rgba(255, 255, 255, 0.05)" } },
    langWrap: { className: "hidden" },
    lang: "",
    langActive: { className: "", style: {} },
    divider: "hidden",
    live: "hidden",
    liveDot: "",
    liveText: "",
  },
};

const pill = "inline-flex items-center gap-1.5 h-[38px] px-4 rounded-full text-[14px] font-semibold text-white no-underline transition-colors";

function AuthMenu() {
  const { user, logout } = useAuth();
  if (!user) {
    return (
      <Link to="/login" aria-label="Sign In" className={pill} style={{ background: "#363967", border: "1px solid rgba(255, 255, 255, 0.14)" }}>
        <Icon name="login" className="text-[16px]" />
        <span className="hidden sm:inline">Sign In</span>
      </Link>
    );
  }
  const first = (user.name || "Account").split(" ")[0];
  return (
    <>
      {/* name pill is hidden on phones so the menu button still fits */}
      <span className={`${pill} hidden sm:inline-flex`} style={{ background: "#363967", border: "1px solid rgba(255, 255, 255, 0.14)" }} title={user.email}>
        <Icon name="account_circle" className="text-[16px]" />
        <span className="hidden sm:inline">{first}{user.role === "admin" ? " · Admin" : ""}</span>
      </span>
      <button type="button" onClick={logout} className={`${pill} cursor-pointer hover:bg-white/10`} style={{ background: "rgba(22, 26, 30, 0.75)", border: "1px solid rgba(255, 255, 255, 0.22)" }}>
        <Icon name="logout" className="text-[16px]" />
        <span className="hidden sm:inline">Sign Out</span>
      </button>
    </>
  );
}

export function SiteHeader({ variant }: { variant: HeaderVariant }) {
  const look = LOOK[variant];
  const { current: langNow, choose: chooseLang } = useLanguageChoice();
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();
  const { user } = useAuth();
  const nav = user?.role === "admin" ? [...NAV, ADMIN_NAV] : NAV;

  useEffect(() => setMenuOpen(false), [location.pathname]);

  return (
    <header className={look.header.className} style={look.header.style}>
      <div className={look.bar}>
        <div className={look.barFill.className} style={look.barFill.style} />
      </div>
      <div className="h-20 w-full px-margin-mobile lg:px-margin flex items-center justify-between gap-space-md">
        <Link to="/" className="flex items-center gap-space-md min-w-0">
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
          {nav.map((item) => (
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
          <LanguageMenu />
          <div className="flex items-center gap-space-xs">
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
          {nav.map((item) => (
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
          <div className="sm:hidden flex flex-wrap items-center gap-1.5 px-2 pt-2" role="group" aria-label="Language: speak and reply in">
            {LANG_CHOICES.map((c) => (
              <button
                key={c.id}
                type="button"
                aria-pressed={c.id === langNow.id}
                title={c.label}
                onClick={() => chooseLang(c)}
                className={`px-3 py-1 rounded-full text-xs font-bold text-white border border-white/25 ${c.id === langNow.id ? "bg-white/25" : "bg-white/5"}`}
              >
                {c.short}
              </button>
            ))}
          </div>
        </nav>
      )}
    </header>
  );
}
