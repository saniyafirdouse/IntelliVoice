import { useState, type FormEvent, type ReactNode } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Icon } from "../../components/Icon";
import { PageShell } from "../../components/PageShell";
import { useAuth } from "../../context/AuthContext";
import { ApiError } from "../../lib/api";
import type { Role } from "../../lib/types";
import { EMAIL_RE } from "./AuthCard";

// Sign-in page (2026-10-15 redesign, reference: split layout over a full-screen photo).
// Left: a message that changes with the chosen role. Right: frosted glass panel with
// the Student / Parent | Admin switch. Sign-in logic is unchanged.

/** Where an admin lands after signing in. */
const ADMIN_HOME = "/admin";

const COPY: Record<Role, { eyebrow: string; title: ReactNode; text: string }> = {
  student: {
    eyebrow: "Students & parents",
    title: <>Welcome to<br />IntelliVoice</>,
    text: "Sign in to keep your questions and answers between visits. You can also ask without an account — in English, ಕನ್ನಡ or हिंदी.",
  },
  admin: {
    eyebrow: "SVIT admissions team",
    title: <>Admin<br />Console</>,
    text: "Manage admission data, review unanswered questions and see what parents are asking. For authorised staff only.",
  },
};

const serif = { fontFamily: '"Cormorant Garamond", Georgia, serif' };
// sage accent (same as the Voice Chat send button)
const SAGE = "#c2cc99";
const SAGE_LIGHT = "#c2cc99";
const SAGE_TEXT = "#1d2214";

function LineField({ id, label, icon, children }: { id: string; label: string; icon: string; children: ReactNode }) {
  return (
    <div className="group">
      <label htmlFor={id} className="block text-[13px] font-semibold uppercase tracking-[0.12em] text-white/65">{label}</label>
      <div className="mt-2 flex items-center gap-3 border-b border-white/35 pb-3 transition-colors group-focus-within:border-[#c2cc99]">
        {children}
        <Icon name={icon} className="text-[22px] text-white/60 group-focus-within:text-[#c2cc99] transition-colors" filled />
      </div>
    </div>
  );
}

const inputClass = "flex-1 min-w-0 bg-transparent border-none outline-none p-0 text-[18px] text-white placeholder:text-white/40 focus:ring-0";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [role, setRole] = useState<Role>(params.get("role") === "admin" ? "admin" : "student");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ text: string; ok: boolean } | null>(null);

  const switchRole = (r: Role) => { setRole(r); setMessage(null); };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!EMAIL_RE.test(email.trim())) return setMessage({ text: "Please enter a valid email address.", ok: false });
    if (!password) return setMessage({ text: "Please enter your password.", ok: false });
    setBusy(true);
    try {
      const user = await login(email.trim(), password, role);
      setMessage({ text: "Signed in. Redirecting…", ok: true });
      // admins go back to the admin page they were trying to open (if any), otherwise the dashboard
      const next = params.get("next");
      const adminTarget = next && next.startsWith("/admin") ? next : ADMIN_HOME;
      window.setTimeout(() => navigate(user.role === "admin" ? adminTarget : "/chat"), 500);
    } catch (err) {
      setMessage({ text: err instanceof ApiError ? err.message : "Something went wrong. Please try again.", ok: false });
      setBusy(false);
    }
  };

  const copy = COPY[role];
  const isAdmin = role === "admin";

  return (
    <PageShell scope="pg-login" variant="app" title="Sign In" className="bg-background font-body-md text-on-surface antialiased">
      <main className="relative w-full min-h-screen overflow-hidden">
        {/* full-screen college photo */}
        <div className="fixed inset-0 z-0 bg-cover bg-center" style={{ backgroundImage: 'url("/assets/campus-evening.jpg")' }} aria-hidden="true">
          <div className="absolute inset-0" style={{ background: "linear-gradient(90deg, rgba(10, 14, 20, 0.55) 0%, rgba(10, 14, 20, 0.2) 45%, rgba(10, 14, 20, 0.15) 100%)" }} />
          <div className="absolute inset-x-0 bottom-0 h-1/3" style={{ background: "linear-gradient(0deg, rgba(8, 10, 14, 0.55), transparent)" }} />
        </div>

        <div className="relative z-10 min-h-screen grid grid-cols-1 lg:grid-cols-2">
          {/* left: message for the chosen role */}
          <section className="flex items-end lg:items-center px-margin-mobile lg:px-[clamp(40px,6vw,96px)] pt-28 lg:pt-20 pb-6 lg:pb-0">
            <div key={role} className="iv-fade max-w-[520px]" aria-live="polite">
              <p className="text-[12px] font-semibold uppercase tracking-[0.3em] text-white/80">{copy.eyebrow}</p>
              <h1 className="mt-4 text-white leading-[1.02]" style={{ ...serif, fontSize: "clamp(44px, 5.6vw, 76px)", fontWeight: 500, textShadow: "0 2px 18px rgba(0,0,0,0.45)" }}>
                {copy.title}
              </h1>
              <p className="mt-5 text-[16px] lg:text-[17px] leading-relaxed text-white/88" style={{ textShadow: "0 1px 8px rgba(0,0,0,0.5)" }}>{copy.text}</p>
            </div>
          </section>

          {/* right: frosted glass panel */}
          <section
            className="relative flex items-center justify-center px-margin-mobile lg:px-[clamp(40px,5vw,88px)] pt-6 pb-12 lg:pt-20 lg:pb-0"
            style={{ background: "linear-gradient(180deg, rgba(20, 26, 34, 0.38), rgba(16, 20, 26, 0.5))", backdropFilter: "blur(18px) saturate(120%)", WebkitBackdropFilter: "blur(18px) saturate(120%)", borderLeft: "1px solid rgba(255, 255, 255, 0.12)" }}
          >
            <div className="w-full max-w-[540px]">
              {/* role switch */}
              <div role="tablist" aria-label="Sign in as" className="relative grid grid-cols-2 p-1 rounded-full" style={{ background: "rgba(0, 0, 0, 0.3)", border: "1px solid rgba(255, 255, 255, 0.18)" }}>
                <span className="absolute top-1 bottom-1 w-[calc(50%-4px)] rounded-full transition-transform duration-300" style={{ left: 4, transform: isAdmin ? "translateX(100%)" : "none", background: SAGE, boxShadow: "0 4px 14px rgba(0, 0, 0, 0.25)" }} aria-hidden="true" />
                {([["student", "school", "Student / Parent"], ["admin", "admin_panel_settings", "Admin"]] as const).map(([r, icon, label]) => (
                  <button
                    key={r}
                    type="button"
                    role="tab"
                    aria-selected={role === r}
                    onClick={() => switchRole(r)}
                    className="relative h-12 rounded-full flex items-center justify-center gap-2 text-[15.5px] font-semibold transition-colors"
                    style={{ color: role === r ? SAGE_TEXT : "rgba(255,255,255,0.82)" }}
                  >
                    <Icon name={icon} className="text-[20px]" />
                    {label}
                  </button>
                ))}
              </div>

              <h2 className="mt-10 text-white" style={{ ...serif, fontSize: "clamp(44px, 4.2vw, 60px)", fontWeight: 500, lineHeight: 1.05 }}>
                {isAdmin ? "Admin sign in" : "Sign in"}
              </h2>

              <form onSubmit={submit} className="mt-9 flex flex-col gap-8" noValidate>
                <LineField id="email" label={isAdmin ? "Staff email" : "Email"} icon="mail">
                  <input id="email" type="email" autoComplete="email" placeholder={isAdmin ? "name@saividya.ac.in" : "you@example.com"} value={email} onChange={(e) => setEmail(e.target.value)} className={inputClass} />
                </LineField>
                <LineField id="password" label="Password" icon="lock">
                  <input id="password" type={showPw ? "text" : "password"} autoComplete="current-password" placeholder="Your password" value={password} onChange={(e) => setPassword(e.target.value)} className={inputClass} />
                  <button type="button" onClick={() => setShowPw((s) => !s)} className="text-white/55 hover:text-white" aria-label={showPw ? "Hide password" : "Show password"}>
                    <Icon name={showPw ? "visibility_off" : "visibility"} className="text-[19px]" />
                  </button>
                </LineField>

                {isAdmin && (
                  <p className="flex items-start gap-2 text-[14px] text-white/72">
                    <Icon name="verified_user" className="text-[18px] mt-px" style={{ color: SAGE_LIGHT }} />
                    Admin accounts are created by the IntelliVoice team. Contact the project team if you need access.
                  </p>
                )}
                {message && (
                  <p role="alert" className={`text-[13.5px] rounded-xl px-3.5 py-2.5 border ${message.ok ? "bg-emerald-500/15 border-emerald-300/40 text-emerald-100" : "bg-red-500/15 border-red-300/40 text-red-100"}`}>
                    {message.text}
                  </p>
                )}

                <div className="flex flex-wrap items-center justify-between gap-4 pt-1">
                  <button
                    type="submit"
                    disabled={busy}
                    className="h-[52px] pl-7 pr-6 rounded-full flex items-center gap-2 text-[16.5px] font-semibold transition-all hover:brightness-105 active:scale-[0.98] disabled:opacity-60"
                    style={{ background: SAGE, color: SAGE_TEXT, boxShadow: "0 8px 22px rgba(194, 204, 153, 0.25)" }}
                  >
                    {busy ? "Signing in…" : isAdmin ? "Sign in as admin" : "Sign in"}
                    <Icon name="arrow_forward" className="text-[20px]" />
                  </button>
                  {!isAdmin && (
                    <Link to="/signup" className="text-[15.5px] text-white/85 underline underline-offset-4 decoration-[#c2cc99] hover:text-white">Create an account</Link>
                  )}
                </div>
              </form>

              {!isAdmin && (
                <Link to="/chat" className="mt-10 inline-flex items-center gap-1.5 text-[15px] text-white/70 hover:text-white">
                  Continue without signing in <Icon name="north_east" className="text-[16px]" />
                </Link>
              )}
            </div>
          </section>
        </div>
        <style>{`
          @keyframes iv-fade { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
          .iv-fade { animation: iv-fade 0.35s ease-out; }
          @media (prefers-reduced-motion: reduce) { .iv-fade { animation: none; } }
        `}</style>
      </main>
    </PageShell>
  );
}
