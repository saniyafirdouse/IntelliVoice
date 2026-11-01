import { useState, type FormEvent, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Icon } from "../../components/Icon";
import { PageShell } from "../../components/PageShell";
import { useAuth } from "../../context/AuthContext";
import { ApiError } from "../../lib/api";
import { EMAIL_RE } from "./AuthCard";

// Create-account page (2026-10-15 redesign) — same look as the sign-in page:
// college photo, message on the left, frosted glass form on the right. Logic unchanged.

interface Form { name: string; email: string; phone: string; password: string; confirm: string }

/** Keeps digits only; drops a leading +91 / 91 / 0 when pasted. */
function cleanPhone(raw: string): string {
  let d = raw.replace(/\D/g, "");
  if (d.length > 10 && d.startsWith("91")) d = d.slice(2);
  if (d.length > 10 && d.startsWith("0")) d = d.slice(1);
  return d.slice(0, 10);
}

function validate(f: Form): string | null {
  if (f.name.trim().length < 2) return "Please enter your full name.";
  if (!EMAIL_RE.test(f.email.trim())) return "Please enter a valid email address.";
  if (!/^[6-9]\d{9}$/.test(f.phone)) return "Please enter a valid 10-digit Indian mobile number.";
  if (f.password.length < 8) return "Password must be at least 8 characters.";
  if (f.password !== f.confirm) return "Passwords don't match.";
  return null;
}

const serif = { fontFamily: '"Cormorant Garamond", Georgia, serif' };
const SAGE = "#c2cc99";
const SAGE_TEXT = "#1d2214";
const inputClass = "flex-1 min-w-0 bg-transparent border-none outline-none p-0 text-[17px] text-white placeholder:text-white/40 focus:ring-0";

function LineField({ id, label, icon, children }: { id: string; label: string; icon?: string; children: ReactNode }) {
  return (
    <div className="group">
      <label htmlFor={id} className="block text-[13px] font-semibold uppercase tracking-[0.12em] text-white/65">{label}</label>
      <div className="mt-2 flex items-center gap-3 border-b border-white/35 pb-2.5 transition-colors group-focus-within:border-[#c2cc99]">
        {children}
        {icon && <Icon name={icon} className="text-[21px] text-white/60 group-focus-within:text-[#c2cc99] transition-colors" filled />}
      </div>
    </div>
  );
}

export default function SignupPage() {
  const { signup } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState<Form>({ name: "", email: "", phone: "", password: "", confirm: "" });
  const [showPw, setShowPw] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ text: string; ok: boolean } | null>(null);
  const set = (k: keyof Form) => (v: string) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const problem = validate(form);
    if (problem) return setMessage({ text: problem, ok: false });
    setBusy(true);
    try {
      await signup(form.name.trim(), form.email.trim(), form.phone, form.password);
      // If email/phone verification is added later, show the code step here before redirecting.
      setMessage({ text: "Account created. Taking you to Voice Chat…", ok: true });
      window.setTimeout(() => navigate("/chat"), 700);
    } catch (err) {
      setMessage({ text: err instanceof ApiError ? err.message : "Something went wrong. Please try again.", ok: false });
      setBusy(false);
    }
  };

  const pwType = showPw ? "text" : "password";
  const eye = (
    <button type="button" onClick={() => setShowPw((s) => !s)} className="text-white/55 hover:text-white" aria-label={showPw ? "Hide passwords" : "Show passwords"}>
      <Icon name={showPw ? "visibility_off" : "visibility"} className="text-[19px]" />
    </button>
  );

  return (
    <PageShell scope="pg-signup" variant="app" title="Create Account" className="bg-background font-body-md text-on-surface antialiased">
      <main className="relative w-full min-h-screen overflow-hidden">
        <div className="fixed inset-0 z-0 bg-cover bg-center" style={{ backgroundImage: 'url("/assets/campus-evening.jpg")' }} aria-hidden="true">
          <div className="absolute inset-0" style={{ background: "linear-gradient(90deg, rgba(10, 14, 20, 0.55) 0%, rgba(10, 14, 20, 0.2) 45%, rgba(10, 14, 20, 0.15) 100%)" }} />
          <div className="absolute inset-x-0 bottom-0 h-1/3" style={{ background: "linear-gradient(0deg, rgba(8, 10, 14, 0.55), transparent)" }} />
        </div>

        <div className="relative z-10 min-h-screen grid grid-cols-1 lg:grid-cols-2">
          {/* left: message */}
          <section className="flex items-end lg:items-center px-margin-mobile lg:px-[clamp(40px,6vw,96px)] pt-28 lg:pt-20 pb-6 lg:pb-0">
            <div className="max-w-[520px]">
              <p className="text-[12px] font-semibold uppercase tracking-[0.3em] text-white/80">Students & parents</p>
              <h1 className="mt-4 text-white leading-[1.02]" style={{ ...serif, fontSize: "clamp(44px, 5.6vw, 76px)", fontWeight: 500, textShadow: "0 2px 18px rgba(0,0,0,0.45)" }}>
                Don't have<br />an account?
              </h1>
              <p className="mt-5 text-[16px] lg:text-[17px] leading-relaxed text-white/88" style={{ textShadow: "0 1px 8px rgba(0,0,0,0.5)" }}>
                It's optional. An account keeps your questions between visits and lets the SVIT admissions team call you back if IntelliVoice can't answer.
              </p>
            </div>
          </section>

          {/* right: frosted glass panel */}
          <section
            className="relative flex items-center justify-center px-margin-mobile lg:px-[clamp(40px,5vw,88px)] pt-6 pb-12 lg:pt-24 lg:pb-10"
            style={{ background: "linear-gradient(180deg, rgba(20, 26, 34, 0.38), rgba(16, 20, 26, 0.5))", backdropFilter: "blur(18px) saturate(120%)", WebkitBackdropFilter: "blur(18px) saturate(120%)", borderLeft: "1px solid rgba(255, 255, 255, 0.12)" }}
          >
            <div className="w-full max-w-[540px]">
              <h2 className="text-white" style={{ ...serif, fontSize: "clamp(44px, 4.2vw, 58px)", fontWeight: 500, lineHeight: 1.05 }}>Create account</h2>

              <form onSubmit={submit} className="mt-8 flex flex-col gap-6" noValidate>
                <LineField id="name" label="Full name" icon="person">
                  <input id="name" autoComplete="name" placeholder="e.g. Ananya Rao" value={form.name} onChange={(e) => set("name")(e.target.value)} className={inputClass} />
                </LineField>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                  <LineField id="email" label="Email" icon="mail">
                    <input id="email" type="email" autoComplete="email" placeholder="you@example.com" value={form.email} onChange={(e) => set("email")(e.target.value)} className={inputClass} />
                  </LineField>
                  <LineField id="phone" label="Mobile number" icon="call">
                    <span className="text-[17px] text-white/70 font-medium">+91</span>
                    <input
                      id="phone" type="tel" inputMode="numeric" autoComplete="tel-national" placeholder="10-digit number"
                      value={form.phone}
                      onChange={(e) => set("phone")(cleanPhone(e.target.value))}
                      className={inputClass}
                    />
                  </LineField>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                  <LineField id="password" label="Password" icon="lock">
                    <input id="password" type={pwType} autoComplete="new-password" placeholder="At least 8 characters" value={form.password} onChange={(e) => set("password")(e.target.value)} className={inputClass} />
                    {eye}
                  </LineField>
                  <LineField id="confirm" label="Confirm password" icon="lock">
                    <input id="confirm" type={pwType} autoComplete="new-password" placeholder="Re-enter password" value={form.confirm} onChange={(e) => set("confirm")(e.target.value)} className={inputClass} />
                  </LineField>
                </div>

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
                    {busy ? "Creating…" : "Create account"}
                    <Icon name="arrow_forward" className="text-[20px]" />
                  </button>
                  <Link to="/login" className="text-[15.5px] text-white/85 underline underline-offset-4 decoration-[#c2cc99] hover:text-white">Have an account? Sign in</Link>
                </div>
              </form>

              <Link to="/chat" className="mt-9 inline-flex items-center gap-1.5 text-[15px] text-white/70 hover:text-white">
                Continue without an account <Icon name="north_east" className="text-[16px]" />
              </Link>
            </div>
          </section>
        </div>
      </main>
    </PageShell>
  );
}
