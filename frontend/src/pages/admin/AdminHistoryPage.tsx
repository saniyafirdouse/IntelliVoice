import { useCallback, useEffect, useState } from "react";
import { Icon } from "../../components/Icon";
import { useAuth } from "../../context/AuthContext";
import { ApiError } from "../../lib/api";
import { AdminConflictError, adminApi, formatWhen, type UploadSummary } from "../../lib/adminApi";
import { Button, Card, EmptyState, Loading, Notice, PageTitle, StatusChip } from "./AdminUi";
import { UploadPreview } from "./UploadPreview";

type Msg = { kind: "ok" | "error" | "info"; text: string; records?: string[] } | null;

export default function AdminHistoryPage() {
  const { token } = useAuth();
  const [uploads, setUploads] = useState<UploadSummary[] | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [details, setDetails] = useState<Record<string, UploadSummary>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [confirmUndo, setConfirmUndo] = useState<string | null>(null);
  const [msg, setMsg] = useState<Msg>(null);

  const load = useCallback(async () => {
    if (!token) return;
    try {
      setUploads(await adminApi.history(token));
    } catch (err) {
      setMsg({ kind: "error", text: err instanceof ApiError ? err.message : "Couldn't load the upload history." });
      setUploads([]);
    }
  }, [token]);

  useEffect(() => { void load(); }, [load]);

  const toggle = async (id: string) => {
    if (open === id) return setOpen(null);
    setOpen(id);
    if (!details[id] && token) {
      try {
        const d = await adminApi.uploadDetail(token, id);
        setDetails((m) => ({ ...m, [id]: d }));
      } catch (err) {
        setMsg({ kind: "error", text: err instanceof ApiError ? err.message : "Couldn't load this upload." });
      }
    }
  };

  const undo = async (u: UploadSummary) => {
    if (!token) return;
    setBusy(u.upload_id); setMsg(null); setConfirmUndo(null);
    try {
      await adminApi.undo(token, u.upload_id);
      setMsg({ kind: "ok", text: `Undone: ${u.filename ?? "the upload"} from ${formatWhen(u.applied_at ?? u.uploaded_at)}. All its records are back to their earlier values.` });
      await load();
      // refresh the open details so they show the new status
      const fresh = await adminApi.uploadDetail(token, u.upload_id).catch(() => null);
      setDetails((m) => { const n = { ...m }; if (fresh) n[u.upload_id] = fresh; else delete n[u.upload_id]; return n; });
    } catch (err) {
      if (err instanceof AdminConflictError) setMsg({ kind: "error", text: err.message, records: err.records });
      else setMsg({ kind: "error", text: err instanceof ApiError ? err.message : "Couldn't undo this upload." });
    } finally { setBusy(null); }
  };

  return (
    <>
      <PageTitle
        title="Upload History"
        subtitle="Every Excel upload, who made it and when. An applied upload can be undone in one click."
        actions={<Button icon="refresh" onClick={() => void load()}>Refresh</Button>}
      />

      {msg && (
        <Notice kind={msg.kind} onClose={() => setMsg(null)}>
          {msg.text}
          {msg.records && msg.records.length > 0 && <ul className="list-disc pl-5 mt-1">{msg.records.map((r) => <li key={r}>{r}</li>)}</ul>}
        </Notice>
      )}

      {uploads === null && <Loading label="Loading history…" />}

      {uploads && uploads.length === 0 && (
        <Card><EmptyState icon="history" title="No uploads yet">Uploads you make on the Update Data page will be listed here.</EmptyState></Card>
      )}

      {uploads && uploads.length > 0 && (
        <Card>
          <ul className="flex flex-col divide-y divide-white/10">
            {uploads.map((u) => {
              const isOpen = open === u.upload_id;
              return (
                <li key={u.upload_id} className="py-3 first:pt-0 last:pb-0 flex flex-col gap-3">
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
                    <button
                      type="button"
                      onClick={() => void toggle(u.upload_id)}
                      aria-expanded={isOpen}
                      className="flex items-center gap-2 min-w-0 flex-1 text-left group"
                    >
                      <Icon name={isOpen ? "expand_less" : "expand_more"} className="text-[22px] text-white/60 group-hover:text-white" />
                      <span className="flex flex-col min-w-0">
                        <span className="font-title-md text-title-md text-white truncate">{u.filename ?? "Upload"}</span>
                        <span className="font-body-sm text-body-sm text-white/60">
                          {u.dataset} · {formatWhen(u.uploaded_at)} · by {u.uploaded_by ?? "admin"}
                        </span>
                      </span>
                    </button>
                    <span className="font-body-sm text-body-sm text-white/75 tabular-nums whitespace-nowrap">
                      {u.counts.updated} updated · {u.counts.new} new
                      {u.counts.errors > 0 && <span className="text-red-200"> · {u.counts.errors} errors</span>}
                    </span>
                    <StatusChip status={u.status} />
                    {u.status === "applied" && (confirmUndo === u.upload_id ? (
                      <span className="flex items-center gap-2">
                        <span className="font-body-sm text-body-sm text-white/80">Undo all changes?</span>
                        <Button kind="danger" icon="undo" busy={busy === u.upload_id} onClick={() => void undo(u)}>Yes, undo</Button>
                        <Button onClick={() => setConfirmUndo(null)}>No</Button>
                      </span>
                    ) : (
                      <Button icon="undo" onClick={() => setConfirmUndo(u.upload_id)} disabled={busy !== null}>Undo</Button>
                    ))}
                  </div>
                  {isOpen && (
                    <div className="pl-0 sm:pl-8">
                      {details[u.upload_id] ? <UploadPreview upload={details[u.upload_id]} /> : <Loading label="Loading changes…" />}
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        </Card>
      )}
    </>
  );
}
