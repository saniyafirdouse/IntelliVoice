import { useCallback, useEffect, useMemo, useState } from "react";
import { Icon } from "../../components/Icon";
import { useAuth } from "../../context/AuthContext";
import { ApiError } from "../../lib/api";
import { adminApi, formatWhen, type ActivityItem } from "../../lib/adminApi";
import { Button, Card, EmptyState, Loading, Notice, PageTitle } from "./AdminUi";

// Admin activity log (2026-10-15): every sign-in, failed sign-in, lockout,
// upload, undo, template download, resolved question and callback update.

const ICONS: Record<string, { icon: string; color: string }> = {
  login: { icon: "login", color: "#a7f3d0" },
  login_failed: { icon: "password", color: "#fcd34d" },
  login_locked: { icon: "lock", color: "#fca5a5" },
  upload_preview: { icon: "upload_file", color: "#bfc2ff" },
  upload_confirm: { icon: "task_alt", color: "#a7f3d0" },
  upload_cancel: { icon: "cancel", color: "#e5e7eb" },
  upload_undo: { icon: "undo", color: "#fcd34d" },
  template_download: { icon: "download", color: "#bfc2ff" },
  unanswered_resolve: { icon: "done_all", color: "#a7f3d0" },
  callback_update: { icon: "phone_callback", color: "#bfc2ff" },
};

const FILTERS: { id: string; label: string; match: (a: string) => boolean }[] = [
  { id: "all", label: "Everything", match: () => true },
  { id: "security", label: "Sign-ins & lockouts", match: (a) => a.startsWith("login") },
  { id: "data", label: "Data changes", match: (a) => a.startsWith("upload") || a === "template_download" },
  { id: "follow", label: "Follow-ups", match: (a) => a === "unanswered_resolve" || a === "callback_update" },
];

export default function AdminActivityPage() {
  const { token } = useAuth();
  const [items, setItems] = useState<ActivityItem[] | null>(null);
  const [filter, setFilter] = useState("all");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    setError(null);
    try {
      setItems((await adminApi.activity(token)).items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't load the activity log.");
      setItems([]);
    }
  }, [token]);

  useEffect(() => { void load(); }, [load]);

  const shown = useMemo(() => {
    const f = FILTERS.find((x) => x.id === filter) ?? FILTERS[0];
    return (items ?? []).filter((i) => f.match(i.action));
  }, [items, filter]);
  const warnings = (items ?? []).filter((i) => i.action === "login_failed" || i.action === "login_locked").length;

  return (
    <>
      <PageTitle
        title="Activity Log"
        subtitle="Who did what in the admin panel, newest first. Wrong passwords and lockouts are listed too."
        actions={<Button icon="refresh" onClick={() => void load()}>Refresh</Button>}
      />

      {error && <Notice kind="error" onClose={() => setError(null)}>{error}</Notice>}
      {warnings > 0 && (
        <Notice kind="warn">
          {warnings} wrong-password or lockout event{warnings === 1 ? "" : "s"} in this list. After 3 wrong passwords an account is locked for 15 minutes.
        </Notice>
      )}

      <Card
        title="Recent activity"
        icon="manage_history"
        actions={
          <div className="flex flex-wrap gap-1.5" role="tablist" aria-label="Filter activity">
            {FILTERS.map((f) => (
              <button
                key={f.id}
                type="button"
                role="tab"
                aria-selected={filter === f.id}
                onClick={() => setFilter(f.id)}
                className={`px-3.5 py-1.5 rounded-full text-[13px] font-semibold border transition-colors ${filter === f.id ? "text-white border-white/40 bg-white/20" : "text-white/75 border-white/15 hover:bg-white/10"}`}
              >
                {f.label}
              </button>
            ))}
          </div>
        }
      >
        {items === null && <Loading label="Loading activity…" />}
        {items && shown.length === 0 && (
          <EmptyState icon="manage_history" title="Nothing here yet">Admin sign-ins, uploads and other changes will be listed here.</EmptyState>
        )}
        {shown.length > 0 && (
          <ol className="flex flex-col">
            {shown.map((it) => {
              const look = ICONS[it.action] ?? { icon: "info", color: "#e5e7eb" };
              return (
                <li key={it.id} className="flex items-start gap-3 py-3 border-t border-white/10 first:border-t-0">
                  <span className="w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 bg-black/30 border border-white/15">
                    <Icon name={look.icon} className="text-[19px]" style={{ color: look.color }} />
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                      <span className="font-body-md text-body-md text-white font-semibold">{it.label}</span>
                      <span className="font-body-sm text-body-sm text-white/65">{formatWhen(it.at)}</span>
                    </div>
                    <div className="font-body-sm text-body-sm text-white/75 break-words">
                      {it.admin}{it.details ? <span className="text-white/55"> · {it.details}</span> : null}
                    </div>
                  </div>
                </li>
              );
            })}
          </ol>
        )}
      </Card>
    </>
  );
}
