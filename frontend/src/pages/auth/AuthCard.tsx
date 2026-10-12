import { useState, type ReactNode } from "react";
import { Icon } from "../../components/Icon";
import { PageShell } from "../../components/PageShell";

export const fieldWrap = "flex items-center gap-2 bg-black/40 border border-white/20 rounded-full px-4 py-2.5 focus-within:border-secondary";
export const fieldInput = "bg-transparent border-none outline-none w-full min-w-0 font-body-md text-body-md text-white placeholder:text-white/40 p-0 focus:ring-0";
export const labelClass = "font-label-lg text-label-lg text-white/90 font-medium";
export const submitStyle = { background: "linear-gradient(135deg, rgb(109, 40, 217), rgb(79, 70, 229))", border: "1.5px solid rgba(255,255,255,0.45)" };

/** Shared frame for the Sign In and Sign Up pages. */
export function AuthCard({ title, subtitle, background, width, pageTitle, scope, children }: {
  title: string;
  subtitle: string;
  background: string;
  width: "md" | "lg";
  pageTitle: string;
  scope: string;
  children: ReactNode;
}) {
  return (
    <PageShell scope={scope} variant="app" title={pageTitle} className="bg-background font-body-md text-on-surface antialiased">
      <main className="w-full min-h-screen relative">
        <div className="fixed inset-0 z-0 pointer-events-none bg-cover bg-center" style={{ backgroundImage: `url("${background}")` }} aria-hidden="true">
          <div className="absolute inset-0 bg-black/40" />
          <div className="absolute inset-0 bg-gradient-to-b from-black/50 via-transparent to-black/70" />
        </div>
        <div className="relative z-10 w-full px-margin-mobile pt-28 pb-12 flex justify-center">
          <div
            className={`w-full ${width === "md" ? "max-w-md" : "max-w-lg"} rounded-xl p-space-lg md:p-space-xl flex flex-col gap-space-lg shadow-[0_20px_50px_rgba(0,0,0,0.7)]`}
            style={{ background: "linear-gradient(135deg, rgba(20,16,38,0.62), rgba(28,22,54,0.55))", backdropFilter: "blur(24px)", WebkitBackdropFilter: "blur(24px)", border: "1px solid rgba(191,194,255,0.28)", textShadow: "rgba(0,0,0,0.6) 0px 1px 2px" }}
          >
            <div className="flex flex-col items-center text-center gap-2">
              <div className="w-14 h-14 rounded-full flex items-center justify-center bg-white/15 border border-white/30 p-1">
                <img src="/assets/svit-logo.png" alt="SVIT logo" className="w-full h-full object-contain rounded-full" />
              </div>
              <h1 className="font-headline-md text-[26px] leading-tight text-white font-bold">{title}</h1>
              <p className="font-body-md text-body-md text-white/80">{subtitle}</p>
            </div>
            {children}
          </div>
        </div>
      </main>
    </PageShell>
  );
}

export function PasswordField({ id, label, value, onChange, autoComplete, placeholder, withIcon = true }: {
  id: string; label: string; value: string; onChange: (v: string) => void;
  autoComplete: string; placeholder: string; withIcon?: boolean;
}) {
  const [show, setShow] = useState(false);
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className={labelClass}>{label}</label>
      <div className={fieldWrap}>
        {withIcon && <Icon name="lock" className="text-[18px] text-white/60" />}
        <input id={id} type={show ? "text" : "password"} autoComplete={autoComplete} placeholder={placeholder} value={value} onChange={(e) => onChange(e.target.value)} className={fieldInput} />
        <button type="button" onClick={() => setShow((s) => !s)} className="text-white/60 hover:text-white" aria-label={show ? "Hide password" : "Show password"}>
          <Icon name={show ? "visibility_off" : "visibility"} className="text-[18px]" />
        </button>
      </div>
    </div>
  );
}

export function FormMessage({ message }: { message: { text: string; ok: boolean } | null }) {
  if (!message) return null;
  return (
    <p
      role="alert"
      className={`font-body-sm text-body-sm rounded-DEFAULT px-3 py-2 border ${message.ok
        ? "bg-emerald-500/15 border-emerald-300/40 text-emerald-100"
        : "bg-red-500/15 border-red-300/40 text-red-100"}`}
    >
      {message.text}
    </p>
  );
}

export const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
