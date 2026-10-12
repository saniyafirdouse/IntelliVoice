import { useState } from "react";
import { Icon } from "../../components/Icon";
import { formatValue, type UploadSummary } from "../../lib/adminApi";
import { Notice } from "./AdminUi";

const SHOW_FIRST = 25;

/** Shows what an upload changes: counts, errors, warnings and every old → new value. */
export function UploadPreview({ upload }: { upload: UploadSummary }) {
  const [showAll, setShowAll] = useState(false);
  const changes = upload.changes ?? [];
  const visible = showAll ? changes : changes.slice(0, SHOW_FIRST);
  const c = upload.counts;

  return (
    <div className="flex flex-col gap-space-md">
      <div className="flex flex-wrap gap-2">
        <CountChip icon="add_circle" label="New" value={c.new} tone="text-emerald-200 border-emerald-300/40 bg-emerald-500/15" />
        <CountChip icon="edit" label="Updated" value={c.updated} tone="text-sky-100 border-sky-300/40 bg-sky-500/15" />
        <CountChip icon="check" label="Unchanged" value={c.unchanged} tone="text-white/80 border-white/20 bg-white/10" />
        {c.not_in_file > 0 && <CountChip icon="visibility_off" label="Not in file (kept as is)" value={c.not_in_file} tone="text-white/70 border-white/20 bg-white/5" />}
        {c.warnings > 0 && <CountChip icon="warning" label="Please check" value={c.warnings} tone="text-amber-100 border-amber-300/40 bg-amber-500/15" />}
        {c.errors > 0 && <CountChip icon="error" label="Errors" value={c.errors} tone="text-red-100 border-red-300/40 bg-red-500/15" />}
      </div>

      {upload.errors.length > 0 && (
        <Notice kind="error">
          <p className="font-semibold mb-1">Fix these rows in the file and upload it again. Nothing can be saved until then.</p>
          <ul className="list-disc pl-5 flex flex-col gap-0.5 max-h-56 overflow-y-auto">
            {upload.errors.map((e, i) => <li key={i}>{e.message}</li>)}
          </ul>
        </Notice>
      )}

      {upload.file_warnings.length > 0 && (
        <Notice kind="info">
          <ul className="list-disc pl-5">{upload.file_warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>
        </Notice>
      )}

      {changes.length === 0 && upload.errors.length === 0 && (
        <Notice kind="info">Nothing to change: every row in the file matches the current data.</Notice>
      )}

      {changes.length > 0 && (
        <div className="overflow-x-auto rounded border border-white/15">
          <table className="w-full text-left font-body-md text-body-md">
            <thead className="bg-white/10 text-white/80 font-label-md text-label-md uppercase tracking-wide">
              <tr>
                <th className="px-3 py-2 font-semibold w-16">Row</th>
                <th className="px-3 py-2 font-semibold">Record</th>
                <th className="px-3 py-2 font-semibold">What changes</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((ch) => (
                <tr key={`${ch.row}-${ch.label}`} className="border-t border-white/10 align-top">
                  <td className="px-3 py-2.5 text-white/60 tabular-nums">{ch.row}</td>
                  <td className="px-3 py-2.5">
                    <div className="flex flex-col gap-1">
                      <span className="text-white font-semibold">{ch.label}</span>
                      <span className={`self-start inline-flex items-center gap-1 px-2 py-0.5 rounded-full border font-label-sm text-label-sm ${ch.action === "new"
                        ? "text-emerald-100 border-emerald-300/40 bg-emerald-500/15"
                        : "text-sky-100 border-sky-300/40 bg-sky-500/15"}`}>
                        <Icon name={ch.action === "new" ? "add" : "edit"} className="text-[13px]" />
                        {ch.action === "new" ? "New record" : "Update"}
                      </span>
                    </div>
                  </td>
                  <td className="px-3 py-2.5">
                    <ul className="flex flex-col gap-1">
                      {ch.fields.map((f) => (
                        <li key={f.field} className="flex flex-wrap items-center gap-1.5">
                          <code className="text-white/70 text-[12px] bg-white/10 px-1.5 py-0.5 rounded">{f.field}</code>
                          {ch.action === "update" && (
                            <>
                              <span className="text-white/55 line-through tabular-nums">{formatValue(f.old)}</span>
                              <Icon name="arrow_forward" className="text-[16px] text-white/50" />
                            </>
                          )}
                          <span className="text-white font-semibold tabular-nums">{formatValue(f.new)}</span>
                        </li>
                      ))}
                    </ul>
                    {ch.warnings.length > 0 && (
                      <ul className="mt-2 flex flex-col gap-1">
                        {ch.warnings.map((w, i) => (
                          <li key={i} className="flex items-start gap-1.5 text-amber-100 bg-amber-500/15 border border-amber-300/30 rounded px-2 py-1 font-body-sm text-body-sm">
                            <Icon name="warning" className="text-[16px] mt-px" />{w}
                          </li>
                        ))}
                      </ul>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {changes.length > SHOW_FIRST && (
            <button type="button" onClick={() => setShowAll((s) => !s)} className="w-full py-2 border-t border-white/10 text-secondary font-label-lg text-label-lg hover:bg-white/5">
              {showAll ? "Show fewer" : `Show all ${changes.length} changes`}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function CountChip({ icon, label, value, tone }: { icon: string; label: string; value: number; tone: string }) {
  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full border font-label-lg text-label-lg ${tone}`}>
      <Icon name={icon} className="text-[17px]" />
      <span className="tabular-nums font-semibold">{value}</span> {label}
    </span>
  );
}
