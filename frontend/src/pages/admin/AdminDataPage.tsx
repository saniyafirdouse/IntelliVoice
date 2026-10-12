import { useCallback, useEffect, useRef, useState, type DragEvent } from "react";
import { Link } from "react-router-dom";
import { Icon } from "../../components/Icon";
import { useAuth } from "../../context/AuthContext";
import { ApiError } from "../../lib/api";
import { AdminConflictError, adminApi, formatDay, type Dataset, type UploadSummary } from "../../lib/adminApi";
import { Button, Card, Loading, Notice, PageTitle, glassCard } from "./AdminUi";
import { UploadPreview } from "./UploadPreview";

type Msg = { kind: "ok" | "error" | "warn" | "info"; text: string; records?: string[] } | null;

export default function AdminDataPage() {
  const { token } = useAuth();
  const [datasets, setDatasets] = useState<Dataset[] | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [preview, setPreview] = useState<UploadSummary | null>(null);
  const [applied, setApplied] = useState<UploadSummary | null>(null);
  const [busy, setBusy] = useState<"download" | "upload" | "confirm" | "cancel" | "undo" | null>(null);
  const [msg, setMsg] = useState<Msg>(null);
  const [dragging, setDragging] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  const loadDatasets = useCallback(async () => {
    if (!token) return;
    try {
      const list = await adminApi.datasets(token);
      setDatasets(list);
      setSelected((s) => s ?? list[0]?.name ?? null);
    } catch (err) {
      setMsg({ kind: "error", text: err instanceof ApiError ? err.message : "Couldn't load the datasets." });
      setDatasets([]);
    }
  }, [token]);

  useEffect(() => { void loadDatasets(); }, [loadDatasets]);

  const current = datasets?.find((d) => d.name === selected) ?? null;

  const fail = (err: unknown, fallback: string) => {
    if (err instanceof AdminConflictError) setMsg({ kind: "error", text: err.message, records: err.records });
    else setMsg({ kind: "error", text: err instanceof ApiError ? err.message : fallback });
  };

  const download = async () => {
    if (!token || !current) return;
    setBusy("download"); setMsg(null);
    try {
      const name = await adminApi.downloadTemplate(token, current.name);
      setMsg({ kind: "ok", text: `Downloaded ${name}. Edit it in Excel, save, then upload it below.` });
    } catch (err) { fail(err, "Couldn't download the template."); }
    finally { setBusy(null); }
  };

  const upload = async (file: File | undefined) => {
    if (!token || !current || !file) return;
    if (!/\.(xlsx|csv)$/i.test(file.name)) {
      setMsg({ kind: "error", text: "Please choose an .xlsx (Excel) or .csv file." });
      return;
    }
    setBusy("upload"); setMsg(null); setPreview(null); setApplied(null);
    try {
      setPreview(await adminApi.upload(token, current.name, file));
    } catch (err) { fail(err, "Couldn't read the file."); }
    finally {
      setBusy(null);
      if (fileInput.current) fileInput.current.value = "";
    }
  };

  const confirm = async () => {
    if (!token || !preview) return;
    setBusy("confirm"); setMsg(null);
    try {
      const done = await adminApi.confirm(token, preview.upload_id);
      setApplied(done);
      setPreview(null);
      setMsg({ kind: "ok", text: `Saved. ${done.counts.updated} updated and ${done.counts.new} new record(s). The assistant now answers with the new data.` });
      void loadDatasets();
    } catch (err) { fail(err, "Couldn't save the changes."); }
    finally { setBusy(null); }
  };

  const cancel = async () => {
    if (!token || !preview) return;
    setBusy("cancel");
    try {
      await adminApi.cancel(token, preview.upload_id);
      setPreview(null);
      setMsg({ kind: "info", text: "Preview cancelled. Nothing was changed." });
    } catch (err) { fail(err, "Couldn't cancel the preview."); }
    finally { setBusy(null); }
  };

  const undo = async () => {
    if (!token || !applied) return;
    setBusy("undo");
    try {
      await adminApi.undo(token, applied.upload_id);
      setApplied(null);
      setMsg({ kind: "ok", text: "Undone. Every record is back to how it was before this upload." });
      void loadDatasets();
    } catch (err) { fail(err, "Couldn't undo the upload."); }
    finally { setBusy(null); }
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    void upload(e.dataTransfer.files?.[0]);
  };

  return (
    <>
      <PageTitle title="Update College Data" subtitle="Change fees and other details with an Excel file. No coding needed, and nothing is saved until you confirm." />

      {msg && (
        <Notice kind={msg.kind} onClose={() => setMsg(null)}>
          {msg.text}
          {msg.records && msg.records.length > 0 && (
            <ul className="list-disc pl-5 mt-1">{msg.records.map((r) => <li key={r}>{r}</li>)}</ul>
          )}
          {applied && msg.kind === "ok" && (
            <div className="mt-2 flex flex-wrap gap-2">
              <Button kind="ghost" icon="undo" onClick={() => void undo()} busy={busy === "undo"}>Undo this upload</Button>
              <Link to="/admin/history" className="inline-flex items-center gap-1 px-3 py-2 font-label-lg text-label-lg text-secondary hover:underline">
                Upload history <Icon name="arrow_forward" className="text-[18px]" />
              </Link>
            </div>
          )}
        </Notice>
      )}

      {datasets === null && <Loading label="Loading data types…" />}

      {datasets && datasets.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-space-md" role="radiogroup" aria-label="Which data to update">
          {datasets.map((d) => {
            const on = d.name === selected;
            return (
              <button
                key={d.name}
                type="button"
                role="radio"
                aria-checked={on}
                onClick={() => { setSelected(d.name); setPreview(null); }}
                className={`text-left rounded-lg shadow-[0_12px_36px_rgba(0,0,0,0.6)] px-space-lg py-space-md flex items-start gap-3 transition-all ${on ? "" : "hover:bg-white/10"}`}
                style={on ? { ...glassCard, background: "rgba(88,92,176,0.35)", border: "1px solid rgba(191,194,255,0.6)" } : glassCard}
              >
                <Icon name="table_view" className="text-[28px] text-secondary" />
                <span className="flex flex-col gap-0.5">
                  <span className="font-title-md text-title-md text-white font-bold">{d.title}</span>
                  <span className="font-body-sm text-body-sm text-white/70">{d.records} records · last updated {formatDay(d.last_updated)}</span>
                </span>
              </button>
            );
          })}
        </div>
      )}

      {current && (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-space-lg">
          <Card title="Step 1 · Download the template" icon="download" subtitle="It already contains all the current data, so you only change what's new.">
            <ul className="flex flex-col gap-1.5 font-body-md text-body-md text-white/80">
              <li className="flex gap-2"><Icon name="check" className="text-[18px] text-secondary" />Dropdowns for branch, exam, quota and payment mode</li>
              <li className="flex gap-2"><Icon name="check" className="text-[18px] text-secondary" />An "Instructions" sheet explains every column</li>
              <li className="flex gap-2"><Icon name="check" className="text-[18px] text-secondary" />Rows you delete are never deleted from the system</li>
            </ul>
            <Button kind="primary" icon="download" onClick={() => void download()} busy={busy === "download"} className="self-start">
              Download {current.title} template
            </Button>
          </Card>

          <Card title="Step 2 · Upload the edited file" icon="upload_file" subtitle="Excel (.xlsx) or CSV. You'll see a preview first.">
            <label
              onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
              onDragLeave={() => setDragging(false)}
              onDrop={onDrop}
              className={`flex flex-col items-center justify-center gap-2 rounded border-2 border-dashed px-4 py-8 text-center cursor-pointer transition-colors ${dragging ? "border-secondary bg-secondary/10" : "border-white/25 hover:border-white/50 hover:bg-white/5"}`}
            >
              <Icon name={busy === "upload" ? "progress_activity" : "cloud_upload"} className={`text-[36px] text-secondary ${busy === "upload" ? "animate-spin" : ""}`} />
              <span className="font-title-md text-title-md text-white">{busy === "upload" ? "Checking your file…" : "Drop the file here, or click to choose"}</span>
              <span className="font-body-sm text-body-sm text-white/60">Max 5 MB</span>
              <input
                ref={fileInput}
                type="file"
                accept=".xlsx,.csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/csv"
                className="sr-only"
                disabled={busy !== null}
                onChange={(e) => void upload(e.target.files?.[0])}
              />
            </label>
          </Card>
        </div>
      )}

      {preview && (
        <Card
          title="Step 3 · Check the preview"
          icon="preview"
          subtitle={`${preview.filename ?? "Your file"}: nothing has been saved yet.`}
          actions={
            <>
              <Button kind="ghost" icon="close" onClick={() => void cancel()} busy={busy === "cancel"} disabled={busy !== null}>Cancel</Button>
              <Button kind="success" icon="check" onClick={() => void confirm()} busy={busy === "confirm"} disabled={!preview.can_confirm || busy !== null}>
                Confirm &amp; save
              </Button>
            </>
          }
        >
          <UploadPreview upload={preview} />
          {!preview.can_confirm && preview.errors.length === 0 && preview.counts.new + preview.counts.updated === 0 && (
            <p className="font-body-sm text-body-sm text-white/60">There is nothing to save, so Confirm is turned off.</p>
          )}
        </Card>
      )}
    </>
  );
}
