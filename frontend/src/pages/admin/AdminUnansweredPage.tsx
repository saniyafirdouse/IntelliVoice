import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Icon } from "../../components/Icon";
import { useAuth } from "../../context/AuthContext";
import { ApiError } from "../../lib/api";
import { LANGUAGE_NAMES, adminApi, formatWhen, prettyIntent, type Unanswered } from "../../lib/adminApi";
import { Button, Card, EmptyState, Loading, Notice, PageTitle, PeriodPicker } from "./AdminUi";

export default function AdminUnansweredPage() {
  const { token } = useAuth();
  const [days, setDays] = useState(7);
  const [includeResolved, setIncludeResolved] = useState(false);
  const [data, setData] = useState<Unanswered | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<{ kind: "ok" | "error"; text: string } | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      setData(await adminApi.unanswered(token, days, includeResolved));
    } catch (err) {
      setMsg({ kind: "error", text: err instanceof ApiError ? err.message : "Couldn't load the list." });
    } finally {
      setLoading(false);
    }
  }, [token, days, includeResolved]);

  useEffect(() => { void load(); }, [load]);

  const resolve = async (key: string, ids: string[], what: string) => {
    if (!token) return;
    setBusy(key); setMsg(null);
    try {
      const r = await adminApi.resolve(token, ids);
      setMsg({ kind: "ok", text: `Marked as handled: ${what} (${r.resolved} question${r.resolved === 1 ? "" : "s"}).` });
      await load();
    } catch (err) {
      setMsg({ kind: "error", text: err instanceof ApiError ? err.message : "Couldn't update the list." });
    } finally { setBusy(null); }
  };

  const nothing = data && data.missing_data.length === 0 && data.out_of_scope.length === 0;

  return (
    <>
      <PageTitle
        title="Questions We Couldn't Answer"
        subtitle="Shows what data to add next. When you've added it, mark the topic as handled."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <PeriodPicker days={days} onChange={setDays} />
            <label className="inline-flex items-center gap-2 font-label-lg text-label-lg text-white/80 cursor-pointer select-none">
              <input type="checkbox" checked={includeResolved} onChange={(e) => setIncludeResolved(e.target.checked)} className="form-checkbox rounded text-[rgb(88,92,176)] bg-black/40 border-white/30" />
              Show handled
            </label>
          </div>
        }
      />

      {msg && <Notice kind={msg.kind} onClose={() => setMsg(null)}>{msg.text}</Notice>}
      {loading && !data && <Loading label="Loading…" />}

      {nothing && (
        <Card>
          <EmptyState icon="celebration" title="Nothing missing">
            Every question in this period was answered{includeResolved ? "" : ", or has already been marked as handled"}.
          </EmptyState>
        </Card>
      )}

      {data && data.missing_data.length > 0 && (
        <Card
          title="Missing data"
          icon="database"
          subtitle="IntelliVoice understood these questions, but the college data has no answer yet. Add this data first."
        >
          <ul className="flex flex-col gap-space-md">
            {data.missing_data.map((g) => {
              const key = `${g.intent}-${g.collection}`;
              return (
                <li key={key} className="rounded border border-white/15 bg-white/5 p-space-md flex flex-col gap-3">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="flex flex-col gap-0.5">
                      <span className="font-title-md text-title-md text-white">{prettyIntent(g.intent)}</span>
                      <span className="font-body-sm text-body-sm text-white/60">
                        Data area: <code className="bg-white/10 px-1.5 py-0.5 rounded">{g.collection ?? "unknown"}</code>
                      </span>
                    </div>
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/15 border border-amber-300/40 text-amber-50 font-label-lg text-label-lg">
                      <Icon name="person" className="text-[18px]" />
                      Asked <strong className="tabular-nums">{g.count}</strong> time{g.count === 1 ? "" : "s"}
                    </span>
                  </div>

                  {g.entities_asked.length > 0 && (
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className="font-label-md text-label-md text-white/60">Asked about:</span>
                      {g.entities_asked.map((e) => (
                        <span key={e.value} className="px-2 py-0.5 rounded-full bg-white/10 border border-white/15 font-body-sm text-body-sm text-white/85">
                          {e.value} <span className="text-white/55">×{e.count}</span>
                        </span>
                      ))}
                    </div>
                  )}

                  <ul className="flex flex-col gap-1.5">
                    {groupExamples(g.examples).map((ex, i) => (
                      <li key={i} className="flex items-start gap-2 font-body-md text-body-md">
                        <Icon name="format_quote" className="text-[18px] text-white/40 mt-0.5" />
                        <span className="flex-1 text-white/90" lang={ex.language ?? undefined}>{ex.text}</span>
                        <span className="font-body-sm text-body-sm text-white/50 whitespace-nowrap">
                          {ex.times > 1 && <strong className="text-white/80 tabular-nums">×{ex.times} · </strong>}
                          {LANGUAGE_NAMES[ex.language ?? ""] ?? ""} · {formatWhen(ex.asked_at)}
                        </span>
                      </li>
                    ))}
                  </ul>

                  <div className="flex flex-wrap gap-2">
                    <Link to="/admin/data" className="inline-flex items-center gap-1 px-3 py-2 rounded-full font-label-lg text-label-lg text-secondary hover:bg-white/10">
                      <Icon name="upload_file" className="text-[18px]" /> Add this data
                    </Link>
                    <Button icon="done_all" busy={busy === key} onClick={() => void resolve(key, g.log_ids, prettyIntent(g.intent))}>Mark as handled</Button>
                  </div>
                </li>
              );
            })}
          </ul>
        </Card>
      )}

      {data && data.out_of_scope.length > 0 && (
        <Card
          title="Outside what IntelliVoice handles"
          icon="do_not_disturb_on"
          subtitle="Questions that aren't about SVIT admissions, or that the assistant didn't understand. Same questions are grouped."
        >
          <ul className="flex flex-col divide-y divide-white/10">
            {data.out_of_scope.map((q) => {
              const key = `oos-${q.text}`;
              return (
                <li key={key} className="py-2.5 first:pt-0 last:pb-0 flex flex-wrap items-center gap-3">
                  <span className="flex-1 min-w-[12rem] font-body-md text-body-md text-white/90" lang={q.language ?? undefined}>{q.text}</span>
                  <span className="font-body-sm text-body-sm text-white/55 whitespace-nowrap">
                    {q.count > 1 && <strong className="text-white/80 tabular-nums">×{q.count} · </strong>}
                    {LANGUAGE_NAMES[q.language ?? ""] ?? ""} · {formatWhen(q.last_asked)}
                  </span>
                  <Button icon="done" busy={busy === key} onClick={() => void resolve(key, q.log_ids, `"${q.text}"`)}>Handled</Button>
                </li>
              );
            })}
          </ul>
        </Card>
      )}
    </>
  );
}

/** The same question asked several times is shown once, with how often (newest time kept). */
function groupExamples(examples: Unanswered["missing_data"][number]["examples"]) {
  const out: (typeof examples[number] & { times: number })[] = [];
  for (const ex of examples) {
    const key = ex.text.trim().toLowerCase().replace(/\s+/g, " ");
    const hit = out.find((o) => o.text.trim().toLowerCase().replace(/\s+/g, " ") === key);
    if (hit) hit.times += 1;
    else out.push({ ...ex, times: 1 });
  }
  return out;
}
