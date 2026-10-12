// Small building blocks shared by the admin pages.
// The glass look is copied from the Voice Chat page (pages/chat/SidePanels.tsx and ChatPage.tsx)
// so the admin panel matches the rest of the site.

import type { ButtonHTMLAttributes, CSSProperties, ReactNode } from "react";
import { Icon } from "../../components/Icon";
import type { UploadStatus } from "../../lib/adminApi";

export const ACCENT = "rgb(88, 92, 176)";
export const LAVENDER = "#bfc2ff";

/** Same as the Voice Chat side panels (panelStyle in SidePanels.tsx). */
export const glassCard: CSSProperties = {
  background: "rgba(14, 18, 26, 0.25)",
  backdropFilter: "blur(24px)",
  WebkitBackdropFilter: "blur(24px)",
  border: "1px solid rgba(255, 255, 255, 0.22)",
  textShadow: "rgba(0, 0, 0, 0.7) 0px 1px 3px",
};

/** Same as the Voice Chat pipeline bar (the strip at the top of the chat page). */
export const glassStrip: CSSProperties = {
  background: "linear-gradient(135deg, rgba(32,20,56,0.32), rgba(24,18,44,0.26))",
  backdropFilter: "blur(24px)",
  WebkitBackdropFilter: "blur(24px)",
  border: "1px solid rgba(216,180,254,0.3)",
  textShadow: "rgba(0, 0, 0, 0.7) 0px 1px 3px",
};

/** Shadow + corner used by every chat panel. */
export const GLASS_PANEL = "rounded-lg shadow-[0_12px_36px_rgba(0,0,0,0.6)]";

export function Card({ title, icon, actions, children, className = "", subtitle }: {
  title?: string; icon?: string; actions?: ReactNode; children: ReactNode; className?: string; subtitle?: string;
}) {
  return (
    <section className={`${GLASS_PANEL} p-space-lg flex flex-col gap-space-md ${className}`} style={glassCard}>
      {(title || actions) && (
        <header className="flex flex-wrap items-start justify-between gap-space-sm">
          <div className="flex flex-col gap-0.5 min-w-0">
            {title && (
              <h2 className="font-title-md text-title-md text-white font-bold flex items-center gap-2">
                {icon && <Icon name={icon} className="text-[20px] text-secondary font-bold" />}
                {title}
              </h2>
            )}
            {subtitle && <p className="font-body-sm text-body-sm text-white/80">{subtitle}</p>}
          </div>
          {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
        </header>
      )}
      {children}
    </section>
  );
}

type ButtonKind = "primary" | "ghost" | "danger" | "success";
const BUTTON: Record<ButtonKind, { className: string; style?: CSSProperties }> = {
  primary: { className: "text-white shadow-[0_4px_14px_rgba(0,0,0,0.35)]", style: { backgroundColor: ACCENT, border: "1px solid rgba(255,255,255,0.35)" } },
  ghost: { className: "text-white bg-white/10 hover:bg-white/20 border border-white/20" },
  danger: { className: "text-red-100 bg-red-500/20 hover:bg-red-500/30 border border-red-300/40" },
  success: { className: "text-emerald-50 bg-emerald-500/25 hover:bg-emerald-500/35 border border-emerald-300/45" },
};

export function Button({ kind = "ghost", icon, children, busy, className = "", ...rest }: {
  kind?: ButtonKind; icon?: string; busy?: boolean; className?: string; children: ReactNode;
} & ButtonHTMLAttributes<HTMLButtonElement>) {
  const look = BUTTON[kind];
  return (
    <button
      type="button"
      {...rest}
      disabled={busy || rest.disabled}
      className={`inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-full font-label-lg text-label-lg font-semibold transition-all hover:brightness-110 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed ${look.className} ${className}`}
      style={look.style}
    >
      <Icon name={busy ? "progress_activity" : icon || ""} className={`text-[18px] ${busy ? "animate-spin" : ""} ${!busy && !icon ? "hidden" : ""}`} />
      {children}
    </button>
  );
}

export function StatTile({ label, value, hint, icon, tone = LAVENDER, progress }: {
  label: string; value: string; hint?: string; icon: string;
  /** colour of the icon chip and progress bar */
  tone?: string;
  /** 0–100: draws a small bar under the number (e.g. answered rate) */
  progress?: number;
}) {
  return (
    <div className={`${GLASS_PANEL} px-space-lg py-space-md flex flex-col gap-1.5 min-w-0 relative overflow-hidden`} style={glassCard}>
      {/* soft colour glow in the corner so each tile is recognisable at a glance */}
      <span className="absolute -top-10 -right-10 w-28 h-28 rounded-full blur-2xl pointer-events-none" style={{ background: `${tone}40` }} aria-hidden="true" />
      <span className="font-label-md text-label-md text-white/85 flex items-center gap-2">
        <span className="inline-flex items-center justify-center w-8 h-8 rounded-full flex-shrink-0" style={{ background: `${tone}33`, border: `1px solid ${tone}80` }}>
          <Icon name={icon} filled className="text-[18px]" style={{ color: tone }} />
        </span>
        {label}
      </span>
      <span className="font-headline-md text-headline-md text-white font-bold tabular-nums">{value}</span>
      {progress !== undefined && (
        <span className="h-1.5 rounded-full bg-white/10 overflow-hidden" aria-hidden="true">
          <span className="block h-full rounded-full" style={{ width: `${Math.max(0, Math.min(100, progress))}%`, background: tone }} />
        </span>
      )}
      {hint && <span className="font-body-sm text-body-sm text-white/70">{hint}</span>}
    </div>
  );
}

export function Notice({ kind, children, onClose }: { kind: "ok" | "error" | "warn" | "info"; children: ReactNode; onClose?: () => void }) {
  const look = {
    ok: { cls: "bg-emerald-500/15 border-emerald-300/40 text-emerald-50", icon: "check_circle" },
    error: { cls: "bg-red-500/15 border-red-300/40 text-red-50", icon: "error" },
    warn: { cls: "bg-amber-500/15 border-amber-300/40 text-amber-50", icon: "warning" },
    info: { cls: "bg-white/10 border-white/20 text-white/90", icon: "info" },
  }[kind];
  return (
    <div role={kind === "error" ? "alert" : "status"} className={`flex items-start gap-2 rounded border px-4 py-3 backdrop-blur-md font-body-md text-body-md ${look.cls}`}>
      <Icon name={look.icon} className="text-[20px] mt-px flex-shrink-0" />
      <div className="flex-1 min-w-0">{children}</div>
      {onClose && (
        <button type="button" onClick={onClose} aria-label="Dismiss" className="opacity-70 hover:opacity-100">
          <Icon name="close" className="text-[18px]" />
        </button>
      )}
    </div>
  );
}

const STATUS: Record<UploadStatus, { label: string; icon: string; cls: string }> = {
  pending: { label: "Waiting for confirm", icon: "hourglass_top", cls: "bg-amber-500/20 border-amber-300/40 text-amber-100" },
  applied: { label: "Applied", icon: "check_circle", cls: "bg-emerald-500/20 border-emerald-300/40 text-emerald-100" },
  cancelled: { label: "Cancelled", icon: "block", cls: "bg-white/10 border-white/25 text-white/75" },
  undone: { label: "Undone", icon: "undo", cls: "bg-sky-500/20 border-sky-300/40 text-sky-100" },
  expired: { label: "Expired", icon: "timer_off", cls: "bg-white/10 border-white/25 text-white/65" },
};

export function StatusChip({ status }: { status: UploadStatus }) {
  const s = STATUS[status] ?? STATUS.cancelled;
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full border font-label-md text-label-md whitespace-nowrap ${s.cls}`}>
      <Icon name={s.icon} className="text-[15px]" />
      {s.label}
    </span>
  );
}

export const PERIODS = [
  { days: 1, label: "Today" },
  { days: 7, label: "7 days" },
  { days: 30, label: "30 days" },
  { days: 90, label: "90 days" },
];

export function PeriodPicker({ days, onChange }: { days: number; onChange: (d: number) => void }) {
  return (
    <div role="group" aria-label="Time period" className="flex items-center gap-1 p-1 rounded-full bg-white/10 border border-white/20 backdrop-blur-md">
      {PERIODS.map((p) => {
        const on = p.days === days;
        return (
          <button
            key={p.days}
            type="button"
            aria-pressed={on}
            onClick={() => onChange(p.days)}
            className={`px-3 py-1 rounded-full font-label-md text-label-md transition-colors ${on ? "text-white font-semibold" : "text-white/70 hover:text-white hover:bg-white/10"}`}
            style={on ? { background: ACCENT } : undefined}
          >
            {p.label}
          </button>
        );
      })}
    </div>
  );
}

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-10 text-white/75" role="status">
      <Icon name="progress_activity" className="animate-spin text-[22px]" />
      {label}
    </div>
  );
}

export function EmptyState({ icon, title, children }: { icon: string; title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center text-center gap-2 py-8 px-4">
      <Icon name={icon} className="text-[40px] text-secondary/80" />
      <p className="font-title-md text-title-md text-white">{title}</p>
      {children && <div className="font-body-md text-body-md text-white/70 max-w-md">{children}</div>}
    </div>
  );
}

/** Admin page title row */
export function PageTitle({ title, subtitle, actions }: { title: string; subtitle: string; actions?: ReactNode }) {
  return (
    <div className={`${GLASS_PANEL} px-space-lg py-space-md flex flex-wrap items-center justify-between gap-space-md`} style={glassStrip}>
      <div className="flex flex-col gap-0.5 min-w-0">
        <h1 className="font-title-lg text-title-lg text-white font-bold glass-text-glow">{title}</h1>
        <p className="font-body-sm text-body-sm text-white/85">{subtitle}</p>
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}
