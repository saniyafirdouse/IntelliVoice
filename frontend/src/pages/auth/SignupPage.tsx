import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Icon } from "../../components/Icon";
import { useAuth } from "../../context/AuthContext";
import { ApiError } from "../../lib/api";
import { AuthCard, EMAIL_RE, FormMessage, PasswordField, fieldInput, fieldWrap, labelClass, submitStyle } from "./AuthCard";

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

export default function SignupPage() {
  const { signup } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState<Form>({ name: "", email: "", phone: "", password: "", confirm: "" });
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

  return (
    <AuthCard
      scope="pg-signup"
      pageTitle="Create Account"
      title="Create your account"
      subtitle="Optional — an account lets the SVIT admissions team call you back if IntelliVoice can't answer your question."
      background="/assets/campus-lawn.jpg"
      width="lg"
    >
      <form onSubmit={submit} className="flex flex-col gap-space-md" noValidate>
        <div className="flex flex-col gap-1.5">
          <label htmlFor="name" className={labelClass}>Full name</label>
          <div className={fieldWrap}>
            <Icon name="person" className="text-[18px] text-white/60" />
            <input id="name" autoComplete="name" placeholder="e.g. Ananya Rao" value={form.name} onChange={(e) => set("name")(e.target.value)} className={fieldInput} />
          </div>
        </div>
        <div className="flex flex-col gap-1.5">
          <label htmlFor="email" className={labelClass}>Email</label>
          <div className={fieldWrap}>
            <Icon name="mail" className="text-[18px] text-white/60" />
            <input id="email" type="email" autoComplete="email" placeholder="you@example.com" value={form.email} onChange={(e) => set("email")(e.target.value)} className={fieldInput} />
          </div>
        </div>
        <div className="flex flex-col gap-1.5">
          <label htmlFor="phone" className={labelClass}>Mobile number</label>
          <div className={fieldWrap}>
            <span className="font-body-md text-body-md text-white/70 font-semibold">+91</span>
            <span className="w-px h-5 bg-white/20" />
            <input
              id="phone" type="tel" inputMode="numeric" autoComplete="tel-national" placeholder="10-digit mobile number"
              value={form.phone}
              onChange={(e) => set("phone")(cleanPhone(e.target.value))}
              className={fieldInput}
            />
          </div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-space-md">
          <PasswordField id="password" label="Password" value={form.password} onChange={set("password")} autoComplete="new-password" placeholder="At least 8 characters" withIcon={false} />
          <PasswordField id="confirm" label="Confirm password" value={form.confirm} onChange={set("confirm")} autoComplete="new-password" placeholder="Re-enter password" withIcon={false} />
        </div>

        <FormMessage message={message} />

        <button type="submit" disabled={busy} className="w-full py-3 rounded-full text-white font-title-md text-title-md font-bold flex items-center justify-center gap-2 transition-all hover:brightness-110 active:scale-[0.98] disabled:opacity-60" style={submitStyle}>
          Create Account
          <Icon name="arrow_forward" className="text-[20px]" />
        </button>
      </form>

      <div className="flex flex-col items-center gap-2 text-center font-body-md text-body-md">
        <p className="text-white/80">Already have an account? <Link to="/login" className="text-secondary font-semibold hover:underline">Sign in</Link></p>
        <Link to="/chat" className="text-white/70 hover:text-white hover:underline inline-flex items-center gap-1">
          Continue without an account <Icon name="north_east" className="text-[16px]" />
        </Link>
      </div>
    </AuthCard>
  );
}
