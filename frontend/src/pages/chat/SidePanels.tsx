import type { CSSProperties } from "react";
import { Icon } from "../../components/Icon";
import {
  RESPONSE_OPTIONS,
  SPEECH_OPTIONS,
  type ResponseLanguage,
  type SpeechLanguage,
} from "../../context/LanguageContext";
import type { QueryContext, Understanding } from "../../lib/types";

export const panelStyle: CSSProperties = {
  background: "rgba(14, 18, 26, 0.25)",
  backdropFilter: "blur(24px)",
  WebkitBackdropFilter: "blur(24px)",
  border: "1px solid rgba(255, 255, 255, 0.22)",
  textShadow: "rgba(0, 0, 0, 0.7) 0px 1px 3px",
};

const inputClass = "bg-black/40 border border-white/20 rounded-DEFAULT px-3 py-1.5 font-body-sm text-body-sm text-white placeholder:text-white/40 outline-none focus:border-secondary w-full min-w-0";

export interface ContextFields { rank: string; category: string; branch: string }

export function toQueryContext(f: ContextFields): QueryContext | null {
  const rank = f.rank.trim();
  const ctx: QueryContext = {
    rank: /^\d+$/.test(rank) ? Number(rank) : null,
    category: f.category.trim() || null,
    branch: f.branch.trim() || null,
  };
  return Object.values(ctx).some((v) => v !== null) ? ctx : null;
}

export function QueryContextCard({ value, onChange }: { value: ContextFields; onChange: (v: ContextFields) => void }) {
  const field = (key: keyof ContextFields) => ({
    value: value[key],
    onChange: (e: React.ChangeEvent<HTMLInputElement>) => onChange({ ...value, [key]: e.target.value }),
  });
  return (
    <div className="rounded-lg p-space-lg shadow-[0_12px_36px_rgba(0,0,0,0.6)] relative overflow-hidden flex flex-col gap-space-sm" style={panelStyle}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Icon name="tune" className="text-[20px] text-secondary font-bold" />
          <span className="font-title-md text-title-md text-white font-bold">Your Query Context</span>
        </div>
        <span className="font-label-sm text-label-sm px-2 py-0.5 rounded-full bg-white/15 text-white/90 border border-white/20 font-medium">Optional</span>
      </div>
      <p className="font-body-sm text-body-sm text-white/80">Set filters to receive personalized fee and cutoff insights:</p>
      <div className="grid grid-cols-1 gap-2 mt-1">
        <label className="flex flex-col gap-1">
          <span className="font-label-sm text-label-sm text-white/90 font-medium">Rank (KCET / COMEDK)</span>
          <input className={inputClass} inputMode="numeric" placeholder="e.g. 25000" {...field("rank")} />
        </label>
        <div className="grid grid-cols-2 gap-2">
          <label className="flex flex-col gap-1">
            <span className="font-label-sm text-label-sm text-white/90 font-medium">Category</span>
            <input className={inputClass} placeholder="e.g. GM" {...field("category")} />
          </label>
          <label className="flex flex-col gap-1">
            <span className="font-label-sm text-label-sm text-white/90 font-medium">Branch</span>
            <input className={inputClass} placeholder="e.g. CSE" {...field("branch")} />
          </label>
        </div>
      </div>
    </div>
  );
}

const pretty = (v?: string) => (v ?? "").replace(/_/g, " ");

export function UnderstandingPanel({ data, busy }: { data: Understanding | null; busy: boolean }) {
  const entities = Object.entries(data?.entities ?? {}).filter(
    ([, v]) => v !== null && v !== "" && !(Array.isArray(v) && v.length === 0),
  );
  return (
    <div className="rounded-lg p-space-lg shadow-[0_12px_36px_rgba(0,0,0,0.6)] flex flex-col gap-space-sm" style={panelStyle} aria-live="polite">
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-1.5">
          <Icon name="psychology" className="text-[18px] text-secondary font-bold" />
          <span className="font-title-md text-title-md text-white font-bold">Engine 2: Understanding</span>
        </div>
        <span className="px-2.5 py-0.5 rounded-full bg-white/10 text-white/80 font-label-sm text-label-sm font-medium border border-white/15">
          {busy ? "Working…" : data ? "Done" : "Idle"}
        </span>
      </div>

      {!data ? (
        <div className="p-4 rounded-DEFAULT bg-black/40 border border-white/15 flex flex-col items-center justify-center text-center gap-2 py-6">
          <Icon name="hourglass_empty" className="text-[32px] text-secondary/60 animate-pulse" />
          <span className="font-title-md text-title-md text-white font-bold">Waiting for your question…</span>
          <p className="font-body-sm text-body-sm text-white/70 max-w-[220px]">Intent, entity detection &amp; emotion will appear here after your first query.</p>
        </div>
      ) : (
        <div className="p-4 rounded-DEFAULT bg-black/40 border border-white/15 flex flex-col gap-3 text-left">
          <div className="flex flex-col gap-0.5">
            <div className="flex items-center justify-between gap-2">
              <span className="font-label-sm text-label-sm text-white/70">Detected intent</span>
              {typeof data.confidence === "number" && (
                <span className="font-label-sm text-label-sm text-secondary font-semibold">{Math.round(data.confidence * 100)}% confidence</span>
              )}
            </div>
            <span className="font-title-md text-title-md text-white font-bold break-words">{data.intent || "—"}</span>
          </div>
          <div className="flex flex-col gap-1">
            <span className="font-label-sm text-label-sm text-white/70">Extracted entities</span>
            <div className="flex flex-wrap gap-1.5">
              {entities.length ? entities.map(([k, v]) => (
                <span key={k} className="px-2 py-0.5 rounded-full bg-white/10 border border-white/20 text-white font-label-sm text-label-sm">
                  {pretty(k)}: {Array.isArray(v) ? v.join(", ") : String(v)}
                </span>
              )) : <span className="font-body-sm text-body-sm text-white/60">None</span>}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div className="p-2 rounded-lg bg-black/30 border border-white/10">
              <div className="font-label-sm text-label-sm text-white/60">Emotion</div>
              <div className="font-body-md text-body-md text-white font-semibold">{pretty(data.emotion) || "—"}</div>
            </div>
            <div className="p-2 rounded-lg bg-black/30 border border-white/10">
              <div className="font-label-sm text-label-sm text-white/60">Response mode</div>
              <div className="font-body-md text-body-md text-white font-semibold">{pretty(data.response_mode) || "—"}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export const ONE_TAP = ["Fee structure for CSE?", "KCET Round 2 Cutoff for ISE?", "Hostel facilities & mess?", "Placement record for ISE?"];
export const HUMAN_REQUEST = "I want to talk to someone from the SVIT admissions office.";

export function OneTapPanel({ onAsk, disabled }: { onAsk: (q: string) => void; disabled: boolean }) {
  return (
    <>
      <div className="rounded-lg p-space-lg shadow-[0_12px_36px_rgba(0,0,0,0.6)] flex flex-col gap-space-sm" style={panelStyle}>
        <div className="flex items-center gap-space-xs mb-1">
          <Icon name="bolt" className="text-[18px] text-secondary font-bold" />
          <span className="font-title-md text-title-md text-white font-bold">One-Tap Inquiries</span>
        </div>
        <p className="font-body-sm text-body-sm text-white/90 font-medium">Direct queries matching verified admission intents:</p>
        <div className="flex flex-col gap-2 mt-1">
          {ONE_TAP.map((q) => (
            <button
              key={q}
              type="button"
              disabled={disabled}
              onClick={() => onAsk(q)}
              className="w-full text-left px-4 py-2.5 rounded-full text-white font-body-sm text-body-sm font-semibold transition-all flex items-center justify-between group shadow-sm disabled:opacity-60"
              style={{ backgroundColor: "rgb(88, 92, 176)", border: "1px solid rgba(255, 255, 255, 0.35)", textShadow: "rgba(0, 0, 0, 0.6) 0px 1px 2px" }}
            >
              <span className="text-white">{q}</span>
              <Icon name="north_east" className="text-[18px] text-white group-hover:translate-x-0.5 transition-all font-bold" />
            </button>
          ))}
        </div>
      </div>
      <button
        type="button"
        disabled={disabled}
        onClick={() => onAsk(HUMAN_REQUEST)}
        className="w-full py-3.5 px-space-md rounded-full text-white font-title-md text-title-md font-bold transition-all shadow-[0_8px_28px_rgba(0,0,0,0.5)] flex items-center justify-center gap-space-sm group disabled:opacity-60"
        style={{ backgroundColor: "rgb(84, 88, 171)", color: "rgb(255, 255, 255)", border: "1px solid rgba(255, 255, 255, 0.35)", textShadow: "rgba(0, 0, 0, 0.8) 0px 1px 3px" }}
      >
        <Icon name="support_agent" className="text-[20px] text-white font-bold" />
        <span className="text-white">Talk to Human Officer</span>
      </button>
    </>
  );
}

// ---------- language choice ----------

const selectClass =
  "w-full min-w-0 appearance-none bg-black/40 border border-white/20 rounded-DEFAULT pl-3 pr-8 py-1.5 font-body-sm text-body-sm text-white outline-none focus:border-secondary cursor-pointer";

function Select<T extends string>({ id, label, icon, value, options, onChange }: {
  id: string; label: string; icon: string; value: T;
  options: { value: T; label: string }[]; onChange: (v: T) => void;
}) {
  return (
    <label htmlFor={id} className="flex flex-col gap-1">
      <span className="font-label-sm text-label-sm text-white/90 font-medium flex items-center gap-1">
        <Icon name={icon} className="text-[14px] text-secondary" />
        {label}
      </span>
      <span className="relative">
        <select id={id} value={value} onChange={(e) => onChange(e.target.value as T)} className={selectClass} style={{ backgroundImage: "none" }}>
          {options.map((o) => (
            <option key={o.value} value={o.value} style={{ background: "#1e2020", color: "#fff" }}>{o.label}</option>
          ))}
        </select>
        <Icon name="expand_more" className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-[18px] text-white/70" />
      </span>
    </label>
  );
}

export function LanguageCard({ speech, response, onSpeech, onResponse }: {
  speech: SpeechLanguage; response: ResponseLanguage;
  onSpeech: (v: SpeechLanguage) => void; onResponse: (v: ResponseLanguage) => void;
}) {
  return (
    <div className="rounded-lg p-space-lg shadow-[0_12px_36px_rgba(0,0,0,0.6)] flex flex-col gap-space-sm" style={panelStyle}>
      <div className="flex items-center gap-2">
        <Icon name="translate" className="text-[20px] text-secondary font-bold" />
        <span className="font-title-md text-title-md text-white font-bold">Language</span>
      </div>
      <Select id="speech-lang" label="I will speak in" icon="mic" value={speech} options={SPEECH_OPTIONS} onChange={onSpeech} />
      <Select id="reply-lang" label="Reply to me in" icon="volume_up" value={response} options={RESPONSE_OPTIONS} onChange={onResponse} />
      <p className="font-body-sm text-body-sm text-white/70">
        “English letters” writes Kannada or Hindi in the English alphabet, e.g. <i>“CSE fees eshtu?”</i>
      </p>
    </div>
  );
}
