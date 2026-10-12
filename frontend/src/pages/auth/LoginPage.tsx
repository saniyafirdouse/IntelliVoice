import { useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Icon } from "../../components/Icon";
import { useAuth } from "../../context/AuthContext";
import { ApiError } from "../../lib/api";
import type { Role } from "../../lib/types";
import { AuthCard, EMAIL_RE, FormMessage, PasswordField, fieldInput, fieldWrap, labelClass, submitStyle } from "./AuthCard";

/** Where an admin lands after signing in. Change this once the admin dashboard exists. */
const ADMIN_HOME = "/";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [role, setRole] = useState<Role>(params.get("role") === "admin" ? "admin" : "student");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
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
      window.setTimeout(() => navigate(user.role === "admin" ? ADMIN_HOME : "/chat"), 500);
    } catch (err) {
      setMessage({ text: err instanceof ApiError ? err.message : "Something went wrong. Please try again.", ok: false });
      setBusy(false);
    }
  };

  const tab = (r: Role, icon: string, label: string) => (
    <button
      type="button"
      role="tab"
      aria-selected={role === r}
      onClick={() => switchRole(r)}
      className={`py-2 rounded-full font-label-lg text-label-lg font-semibold flex items-center justify-center gap-1.5 transition-colors ${role === r ? "text-white" : "text-white/70"}`}
      style={{ background: role === r ? "rgb(88, 92, 176)" : "transparent" }}
    >
      <Icon name={icon} className="text-[18px]" />
      {label}
    </button>
  );

  return (
    <AuthCard
      scope="pg-login"
      pageTitle="Sign In"
      title="Welcome back"
      subtitle="Sign in to IntelliVoice. Signing in is optional — you can ask questions without an account."
      background="/assets/campus-lobby.jpg"
      width="md"
    >
      <div role="tablist" className="grid grid-cols-2 gap-1 p-1 rounded-full bg-black/40 border border-white/15">
        {tab("student", "school", "Student / Parent")}
        {tab("admin", "admin_panel_settings", "Admin")}
      </div>

      <form onSubmit={submit} className="flex flex-col gap-space-md" noValidate>
        <div className="flex flex-col gap-1.5">
          <label htmlFor="email" className={labelClass}>Email</label>
          <div className={fieldWrap}>
            <Icon name="mail" className="text-[18px] text-white/60" />
            <input id="email" type="email" autoComplete="email" placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} className={fieldInput} />
          </div>
        </div>
        <PasswordField id="password" label="Password" value={password} onChange={setPassword} autoComplete="current-password" placeholder="Your password" />

        {role === "admin" && (
          <p className="font-body-sm text-body-sm text-white/75 bg-white/10 border border-white/15 rounded-DEFAULT px-3 py-2">
            Admin accounts are created by the IntelliVoice team. Contact the project team if you need access.
          </p>
        )}
        <FormMessage message={message} />

        <button type="submit" disabled={busy} className="w-full py-3 rounded-full text-white font-title-md text-title-md font-bold flex items-center justify-center gap-2 transition-all hover:brightness-110 active:scale-[0.98] disabled:opacity-60" style={submitStyle}>
          <span>{role === "admin" ? "Sign In as Admin" : "Sign In"}</span>
          <Icon name="arrow_forward" className="text-[20px]" />
        </button>
      </form>

      {role === "student" && (
        <div className="flex flex-col items-center gap-2 text-center font-body-md text-body-md">
          <p className="text-white/80">New here? <Link to="/signup" className="text-secondary font-semibold hover:underline">Create an account</Link></p>
          <Link to="/chat" className="text-white/70 hover:text-white hover:underline inline-flex items-center gap-1">
            Continue without signing in <Icon name="north_east" className="text-[16px]" />
          </Link>
        </div>
      )}
    </AuthCard>
  );
}
