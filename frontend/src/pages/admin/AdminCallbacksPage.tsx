// Admin -> Callbacks (2026-11-20): parents/students who asked the office to call them back.
// Backend: GET/PATCH /api/admin/callbacks (routes/callbacks.py). Each change is in the Activity Log.
import { useCallback, useEffect, useState } from "react";
import { Icon } from "../../components/Icon";
import { useAuth } from "../../context/AuthContext";
import { ApiError } from "../../lib/api";
import { LANGUAGE_NAMES, adminApi, formatWhen, type CallbackItem, type CallbackStatus } from "../../lib/adminApi";
import { Button, Card, EmptyState, Loading, Notice, PageTitle } from "./AdminUi";

const TABS: { id: CallbackStatus | "all"; label: string }[] = [
  { id: "new", label: "To call" },
  { id: "called", label: "Called" },
  { id: "resolved", label: "Resolved" },
  { id: "all", label: "All" },
];
const STATUS_CHIP: Record<CallbackStatus, { label: string; cls: string; icon: string }> = {
  new: { label: "To call", cls: "bg-amber-500/20 border-amber-300/40 text-amber-100", icon: "hourglass_top" },
  called: { label: "Called", cls: "bg-sky-500/20 border-sky-300/40 text-sky-100", icon: "call" },
  resolved: { label: "Resolved", cls: "bg-emerald-500/20 border-emerald-300/40 text-emerald-100", icon: "check_circle" },
};

export default function AdminCallbacksPage() {
  const { token } = useAuth();
  const [tab, setTab] = useState<CallbackStatus | "all">("new");
  const [data, setData] = useState<{ items: CallbackItem[]; counts: Record<CallbackStatus, number> } | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState<{ kind: "ok" | "error"; text: string } | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      setData(await adminApi.callbacks(token, tab));
    } catch (err) {
      setMsg({ kind: "error", text: err instanceof ApiError ? err.message : "Couldn't load the callback requests." });
    } finally {
      setLoading(false);
    }
  }, [token, tab]);

  useEffect(() => { void load(); }, [load]);

  const update = async (item: CallbackItem, change: { status?: CallbackStatus; note?: string }, done: string) => {
    if (!token) return;
    setBusy(`${item.id}-${change.status ?? "note"}`);
    setMsg(null);
    try {
      await adminApi.updateCallback(token, item.id, change);
      setMsg({ kind: "ok", text: `${item.name ?? "Request"}: ${done}.` });
      await load();
    } catch (err) {
      setMsg({ kind: "error", text: err instanceof ApiError ? err.message : "Couldn't update the request." });
    } finally {
      setBusy(null);
    }
  };

  const total = data ? data.counts.new + data.counts.called + data.counts.resolved : 0;

  return (
    <>
      <PageTitle
        title="Callback Requests"
        subtitle="Parents and students who asked the admission office to call them back. Call them, then mark the request."
        actions={<Button icon="refresh" onClick={() => void load()} busy={loading}>Refresh</Button>}
      />

      <div className="flex flex-wrap gap-2" role="tablist">
        {TABS.map((t) => {
          const count = t.id === "all" ? total : data?.counts[t.id];
          return (
            <button
              key={t.id}
              type="button"
              role="tab"
              aria-selected={tab === t.id}
              onClick={() => setTab(t.id)}
              className={`px-4 py-2 rounded-full font-label-lg text-label-lg border transition-colors ${tab === t.id ? "bg-white/20 border-white/40 text-white" : "bg-white/5 border-white/15 text-white/75 hover:bg-white/10"}`}
            >
              {t.label}{typeof count === "number" && <span className="ml-1.5 tabular-nums text-white/70">{count}</span>}
            </button>
          );
        })}
      </div>

      {msg && <Notice kind={msg.kind} onClose={() => setMsg(null)}>{msg.text}</Notice>}
      {loading && !data && <Loading label="Loading…" />}

      {data && data.items.length === 0 && (
        <Card>
          <EmptyState icon="phone_callback" title={tab === "new" ? "No one is waiting for a call" : "Nothing here"}>
            New requests appear here when a visitor uses “Request a callback” in the chat.
          </EmptyState>
        </Card>
      )}

      {data && data.items.length > 0 && (
        <div className="flex flex-col gap-space-md">
          {data.items.map((c) => {
            const chip = STATUS_CHIP[c.status] ?? STATUS_CHIP.new;
            const note = notes[c.id] ?? c.note ?? "";
            return (
              <Card key={c.id}>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="flex flex-col gap-1 min-w-0">
                    <span className="font-title-md text-title-md text-white flex items-center gap-2">
                      <Icon name="person" className="text-[20px] text-secondary" />{c.name || "—"}
                      {c.email && <span className="font-body-sm text-body-sm text-white/55">· signed in ({c.email})</span>}
                    </span>
                    {c.phone && (
                      <a href={`tel:+91${c.phone}`} className="font-title-md text-title-md underline underline-offset-2" style={{ color: "#bfc2ff" }}>
                        {c.phone.replace(/(\d{5})(\d{5})/, "$1 $2")}
                      </a>
                    )}
                    <span className="font-body-sm text-body-sm text-white/60">
                      Asked {formatWhen(c.created_at)}
                      {c.preferred_time && <> · Best time: {c.preferred_time}</>}
                      {c.language && LANGUAGE_NAMES[c.language] && <> · {LANGUAGE_NAMES[c.language]}</>}
                    </span>
                  </div>
                  <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full border font-label-lg text-label-lg ${chip.cls}`}>
                    <Icon name={chip.icon} className="text-[17px]" />{chip.label}
                  </span>
                </div>

                {c.question && (
                  <p className="font-body-md text-body-md text-white/90 flex items-start gap-2">
                    <Icon name="format_quote" className="text-[18px] text-white/40 mt-0.5" />{c.question}
                  </p>
                )}

                {c.recent_conversation.length > 0 && (
                  <details className="rounded border border-white/10 bg-white/5 px-3 py-2">
                    <summary className="cursor-pointer font-label-lg text-label-lg text-white/80">Chat before the request ({c.recent_conversation.length})</summary>
                    <ul className="mt-2 flex flex-col gap-2">
                      {c.recent_conversation.map((t, i) => (
                        <li key={i} className="font-body-sm text-body-sm">
                          <span className="text-white/90"><strong>Q:</strong> {t.question}</span>
                          <span className="block text-white/65"><strong>Eva:</strong> {t.answer}</span>
                        </li>
                      ))}
                    </ul>
                  </details>
                )}

                <div className="flex flex-col gap-2">
                  <textarea
                    value={note}
                    onChange={(e) => setNotes((n) => ({ ...n, [c.id]: e.target.value }))}
                    rows={2}
                    maxLength={500}
                    placeholder="Note for the team (e.g. called, will visit on Monday)"
                    className="w-full rounded border border-white/20 bg-black/30 px-3 py-2 font-body-md text-body-md text-white placeholder:text-white/40"
                    aria-label={`Note for ${c.name ?? "this request"}`}
                  />
                  <div className="flex flex-wrap gap-2">
                    {c.status !== "called" && <Button icon="call" busy={busy === `${c.id}-called`} onClick={() => void update(c, { status: "called", note }, "marked as called")}>Mark as called</Button>}
                    {c.status !== "resolved" && <Button kind="success" icon="check_circle" busy={busy === `${c.id}-resolved`} onClick={() => void update(c, { status: "resolved", note }, "marked as resolved")}>Mark as resolved</Button>}
                    {c.status !== "new" && <Button icon="undo" busy={busy === `${c.id}-new`} onClick={() => void update(c, { status: "new", note }, "moved back to “To call”")}>Back to “To call”</Button>}
                    {note !== (c.note ?? "") && <Button icon="save" busy={busy === `${c.id}-note`} onClick={() => void update(c, { note }, "note saved")}>Save note</Button>}
                  </div>
                  {c.handled_by && <span className="font-body-sm text-body-sm text-white/50">Last updated by {c.handled_by} · {formatWhen(c.updated_at)}</span>}
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </>
  );
}
