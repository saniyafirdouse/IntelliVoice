// "Your chats" side panel extras (2026-11-20), for signed-in students:
//   SavedAnswers — the ⭐ answers they saved from the chat
//   MyChecklist  — their admission documents + next steps with tick-boxes (remembered), PDF download
//   ProfilePanel — exam, rank, category, preferred branches (Eva uses exam + rank for cutoff questions)
import { useCallback, useEffect, useState } from "react";
import { Icon } from "../../components/Icon";
import { EmailMeButton } from "./EmailMeButton";
import {
  ApiError, deleteSaved, downloadChecklist, getMyChecklist, getMyProfile, listSaved, saveMyChecklist, saveMyProfile,
  type MyChecklist, type MyProfile, type SavedAnswer,
} from "../../lib/api";

const BOX = { background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)" } as const;
const SMALL_BTN = "h-8 px-2 rounded-lg inline-flex items-center gap-1 text-[12.5px] text-white/65 hover:text-white hover:bg-white/10";

function Err({ text }: { text: string | null }) {
  if (!text) return null;
  return <p className="text-[13px] rounded-lg px-3 py-2" style={{ background: "rgba(110, 20, 20, 0.4)", color: "#ffd6d1" }} role="alert">{text}</p>;
}

export function SavedAnswers({ token, open }: { token: string; open: boolean }) {
  const [items, setItems] = useState<SavedAnswer[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    listSaved(token).then(setItems).catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load your starred answers."));
  }, [open, token]);

  const remove = async (id: string) => {
    try {
      await deleteSaved(token, id);
      setItems((xs) => xs?.filter((x) => x.id !== id) ?? null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't remove it.");
    }
  };

  return (
    <div className="flex-1 overflow-y-auto px-4 pt-3 pb-4 flex flex-col gap-2.5">
      <Err text={error} />
      {items === null && !error && <p className="py-2 text-[14px] text-white/60">Loading…</p>}
      {items && items.length > 0 && (
        <EmailMeButton kind="starred" label="Email me my starred answers" className="h-9 px-3 rounded-xl inline-flex items-center justify-center gap-1.5 text-[13.5px] text-white hover:bg-white/10 disabled:opacity-70" style={BOX} />
      )}
      {items && items.length === 0 && (
        <p className="py-2 text-[14px] text-white/65">No starred answers yet. Press <Icon name="star" className="text-[15px] align-middle" /> <strong>Star</strong> under any reply from Eva to keep it here.</p>
      )}
      {items?.map((s) => {
        const open = expanded === s.id;
        return (
          <div key={s.id} className="rounded-xl px-3.5 py-3" style={BOX}>
            {s.question && <p className="text-[13px] text-white/60 truncate" title={s.question}>Q: {s.question}</p>}
            <p className={`mt-0.5 text-[14px] text-white whitespace-pre-line ${open ? "" : "line-clamp-3"}`} lang={s.language ?? undefined}>{s.answer}</p>
            <div className="mt-1.5 flex flex-wrap items-center gap-1">
              <button type="button" className={SMALL_BTN} onClick={() => setExpanded(open ? null : s.id)}>
                <Icon name={open ? "expand_less" : "expand_more"} className="text-[16px]" />{open ? "Less" : "More"}
              </button>
              <button type="button" className={SMALL_BTN} onClick={() => { void navigator.clipboard?.writeText(s.answer).then(() => { setCopied(s.id); window.setTimeout(() => setCopied(null), 1400); }).catch(() => undefined); }}>
                <Icon name={copied === s.id ? "check" : "content_copy"} className="text-[15px]" />{copied === s.id ? "Copied" : "Copy"}
              </button>
              <button type="button" className={SMALL_BTN} onClick={() => void remove(s.id)}>
                <Icon name="delete" className="text-[15px]" />Remove
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function MyChecklistPanel({ token, open }: { token: string; open: boolean }) {
  const [data, setData] = useState<MyChecklist | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  const load = useCallback(async (type?: string, category?: string) => {
    try {
      setData(await getMyChecklist(token, type, category));
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't load your checklist.");
    }
  }, [token]);

  useEffect(() => { if (open) void load(); }, [open, load]);

  const persist = async (next: MyChecklist) => {
    setData(next);
    try { await saveMyChecklist(token, next.admission_type, next.category, next.done); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Couldn't save your ticks."); }
  };

  const toggle = (item: string) => {
    if (!data) return;
    const done = data.done.includes(item) ? data.done.filter((d) => d !== item) : [...data.done, item];
    void persist({ ...data, done });
  };

  const change = async (type: string, category: string) => {
    if (!data) return;
    await load(type, category);
    // remember the new choice (ticks of items that are still on the list are kept by the backend)
    try { await saveMyChecklist(token, type, category, data.done); } catch { /* shown on next load */ }
  };

  if (!data) {
    return <div className="flex-1 px-4 pt-3"><Err text={error} />{!error && <p className="py-2 text-[14px] text-white/60">Loading…</p>}</div>;
  }

  const all = [...data.documents, ...data.steps];
  const doneCount = all.filter((i) => data.done.includes(i)).length;
  const pct = all.length ? Math.round((doneCount / all.length) * 100) : 0;

  const Item = ({ text }: { text: string }) => {
    const checked = data.done.includes(text);
    return (
      <label className="flex items-start gap-2.5 py-1.5 cursor-pointer select-none">
        <input type="checkbox" checked={checked} onChange={() => toggle(text)} className="mt-0.5 w-[18px] h-[18px] rounded accent-[#c2cc99] flex-shrink-0" />
        <span className={`text-[14px] leading-snug ${checked ? "text-white/50 line-through" : "text-white/90"}`}>{text}</span>
      </label>
    );
  };

  return (
    <div className="flex-1 overflow-y-auto px-4 pt-3 pb-4 flex flex-col gap-3">
      <Err text={error} />
      <div className="grid grid-cols-2 gap-2">
        <select value={data.admission_type} onChange={(e) => void change(e.target.value, data.category)} className="h-9 px-2 rounded-lg text-[13px] text-white" style={BOX} aria-label="How you are joining">
          {Object.entries(data.admission_types).map(([v, label]) => <option key={v} value={v} className="text-black" title={label}>{v === "Lateral" ? "Lateral (DCET)" : v === "MBA" ? "MBA (PGCET)" : v}</option>)}
        </select>
        <select value={data.category} onChange={(e) => void change(data.admission_type, e.target.value)} className="h-9 px-2 rounded-lg text-[13px] text-white" style={BOX} aria-label="Category">
          {data.categories.map((c) => <option key={c} value={c} className="text-black">{c}</option>)}
        </select>
      </div>
      <div>
        <div className="flex justify-between text-[12.5px] text-white/65"><span>{doneCount} of {all.length} done</span><span>{pct}%</span></div>
        <div className="mt-1 h-2 rounded-full bg-white/10 overflow-hidden"><div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: "#c2cc99" }} /></div>
      </div>
      <div className="rounded-xl px-3.5 py-2.5" style={BOX}>
        <p className="text-[12px] font-semibold uppercase tracking-[0.08em] text-white/50">Documents to bring</p>
        {data.documents.map((d) => <Item key={d} text={d} />)}
      </div>
      <div className="rounded-xl px-3.5 py-2.5" style={BOX}>
        <p className="text-[12px] font-semibold uppercase tracking-[0.08em] text-white/50">Next steps</p>
        {data.steps.map((d) => <Item key={d} text={d} />)}
      </div>
      <button
        type="button"
        disabled={downloading}
        onClick={() => { setDownloading(true); void downloadChecklist(data.admission_type, data.category).catch(() => setError("Couldn't download the PDF.")).finally(() => setDownloading(false)); }}
        className="h-10 rounded-xl flex items-center justify-center gap-2 text-[14px] font-semibold disabled:opacity-60"
        style={{ background: "#c2cc99", color: "#1d2214" }}
      >
        <Icon name="download" className="text-[18px]" />{downloading ? "Preparing…" : "Download as PDF"}
      </button>
      <EmailMeButton kind="checklist" label="Email me this checklist (with PDF)" className="h-10 rounded-xl flex items-center justify-center gap-2 text-[14px] text-white hover:bg-white/10 disabled:opacity-70" style={BOX} />
      <p className="text-[12px] text-white/50">{data.note}</p>
    </div>
  );
}

// ── My profile (2026-11-20) ──────────────────────────────────────────────────
const BRANCH_LABELS: Record<string, string> = {
  "CSE": "CSE", "CSE-AIML": "AI & ML", "CSE-DS": "Data Science", "CSE-CyberSecurity": "Cyber Security",
  "CS-BusinessSystems": "Business Systems", "ECE": "ECE", "Civil": "Civil", "Mechanical": "Mechanical",
};
const EXAM_LABELS: Record<string, string> = { KCET: "KCET", COMEDK: "COMEDK", Management: "Management quota", Lateral: "Lateral entry (DCET)", MBA: "MBA (PGCET)" };

export function ProfilePanel({ token, open }: { token: string; open: boolean }) {
  const [p, setP] = useState<MyProfile | null>(null);
  const [rankText, setRankText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!open) return;
    getMyProfile(token)
      .then((x) => { setP(x); setRankText(x.rank ? String(x.rank) : ""); })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load your profile."));
  }, [open, token]);

  if (!p) return <div className="flex-1 px-4 pt-3"><Err text={error} />{!error && <p className="py-2 text-[14px] text-white/60">Loading…</p>}</div>;
  const opts = p.options ?? { exams: EXAM_LABELS, categories: ["General", "SC", "ST", "OBC"], branches: Object.keys(BRANCH_LABELS) };
  const rankExam = p.exam === "KCET" || p.exam === "COMEDK";

  const save = async () => {
    const digits = rankText.replace(/\D/g, "");
    const rank = digits ? Number(digits) : null;
    if (rank !== null && (rank < 1 || rank > 500000)) { setError("Please enter a rank between 1 and 5,00,000."); return; }
    setBusy(true); setError(null); setSaved(false);
    try {
      const next = await saveMyProfile(token, { exam: p.exam, rank: rankExam ? rank : null, category: p.category, branches: p.branches });
      setP({ ...next, options: p.options });
      setRankText(next.rank ? String(next.rank) : "");
      setSaved(true);
      window.setTimeout(() => setSaved(false), 2500);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't save your profile.");
    } finally { setBusy(false); }
  };

  const toggleBranch = (b: string) =>
    setP({ ...p, branches: p.branches.includes(b) ? p.branches.filter((x) => x !== b) : [...p.branches, b] });

  return (
    <div className="flex-1 overflow-y-auto px-4 pt-3 pb-4 flex flex-col gap-3.5">
      <p className="text-[13px] text-white/65">Eva uses this to personalise answers: ask “Which branch can I get?” and she uses your rank. What you say in a question always comes first.</p>
      <Err text={error} />
      <label className="flex flex-col gap-1">
        <span className="text-[12px] font-semibold uppercase tracking-[0.08em] text-white/50">How are you joining?</span>
        <select value={p.exam ?? ""} onChange={(e) => setP({ ...p, exam: e.target.value || null })} className="h-10 px-2 rounded-lg text-[14px] text-white" style={BOX}>
          <option value="" className="text-black">Not decided yet</option>
          {Object.keys(opts.exams).map((v) => <option key={v} value={v} className="text-black">{EXAM_LABELS[v] ?? v}</option>)}
        </select>
      </label>
      {rankExam && (
        <label className="flex flex-col gap-1">
          <span className="text-[12px] font-semibold uppercase tracking-[0.08em] text-white/50">My {p.exam} rank</span>
          <input value={rankText} onChange={(e) => setRankText(e.target.value)} inputMode="numeric" placeholder="e.g. 12000" maxLength={8}
            className="h-10 px-3 rounded-lg text-[14px] text-white placeholder:text-white/40 outline-none focus:ring-2 focus:ring-white/30" style={BOX} />
        </label>
      )}
      <label className="flex flex-col gap-1">
        <span className="text-[12px] font-semibold uppercase tracking-[0.08em] text-white/50">Category</span>
        <select value={p.category ?? ""} onChange={(e) => setP({ ...p, category: e.target.value || null })} className="h-10 px-2 rounded-lg text-[14px] text-white" style={BOX}>
          <option value="" className="text-black">Prefer not to say</option>
          {opts.categories.map((c) => <option key={c} value={c} className="text-black">{c}</option>)}
        </select>
      </label>
      <div className="flex flex-col gap-1.5">
        <span className="text-[12px] font-semibold uppercase tracking-[0.08em] text-white/50">Branches I'm interested in</span>
        <div className="flex flex-wrap gap-1.5">
          {opts.branches.map((b) => {
            const on = p.branches.includes(b);
            return (
              <button key={b} type="button" onClick={() => toggleBranch(b)} aria-pressed={on}
                className="h-8 px-3 rounded-full text-[13px] transition-colors"
                style={on ? { background: "rgba(194, 204, 153, 0.9)", color: "#1d2214" } : { ...BOX, color: "rgba(255,255,255,0.85)" }}>
                {BRANCH_LABELS[b] ?? b}
              </button>
            );
          })}
        </div>
      </div>
      <button type="button" onClick={() => void save()} disabled={busy} className="h-10 rounded-xl flex items-center justify-center gap-2 text-[14.5px] font-semibold disabled:opacity-60" style={{ background: "#c2cc99", color: "#1d2214" }}>
        <Icon name={saved ? "check" : "save"} className="text-[18px]" />{busy ? "Saving…" : saved ? "Saved" : "Save my profile"}
      </button>
      <p className="text-[12px] text-white/50">Only you can see this. Your checklist also starts with your exam and category.</p>
    </div>
  );
}
