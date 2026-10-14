import { useEffect, useRef, useState } from "react";
import { Icon } from "../../components/Icon";
import { audioSource } from "../../lib/audio";
import type { QueryResponse, TableData } from "../../lib/types";
import type { ChatMessage } from "./useChat";

const LANG_NAMES: Record<string, string> = {
  en: "English", hi: "Hindi", kn: "Kannada",
  "kn-Latn": "Kannada (English letters)", "hi-Latn": "Hindi (English letters)",
};
const time = (d: Date) => d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

export const WELCOME_CHIPS = [
  "Fee structure for CSE?",
  "KCET Round 2 Cutoff for ISE?",
  "Hostel facilities & mess options?",
  "Placement record for 2024?",
  "COMEDK seat matrix & eligibility?",
];

export function Welcome({ onAsk, disabled }: { onAsk: (q: string) => void; disabled: boolean }) {
  return (
    <div className="flex flex-col items-center justify-center text-center py-space-xl px-space-md gap-space-lg my-auto">
      <div className="w-16 h-16 rounded-full flex items-center justify-center text-secondary shadow-[0_0_24px_rgba(191,194,255,0.35)]" style={{ background: "rgba(88, 92, 176, 0.35)", border: "1.5px solid rgba(255, 255, 255, 0.4)" }}>
        <Icon name="support_agent" className="text-[36px] text-white font-bold" />
      </div>
      <div className="flex flex-col items-center gap-2 max-w-2xl">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-secondary-container/60 border border-white/20 text-white font-label-sm text-label-sm font-semibold">
          <span className="w-2 h-2 rounded-full bg-secondary animate-pulse" />
          <span>SVIT Multilingual AI Admission Desk</span>
        </div>
        <h2 className="font-headline-sm md:font-headline-md text-title-lg md:text-[28px] text-white font-bold tracking-tight leading-snug">
          Ask me anything about SVIT admissions in English,{" "}
          <span style={{ fontFamily: '"Noto Sans Kannada", sans-serif' }}>ಕನ್ನಡ</span> or{" "}
          <span style={{ fontFamily: '"Noto Sans Devanagari", sans-serif' }}>हिंदी</span>
        </h2>
        <p className="font-title-md text-title-md text-secondary font-semibold">
          <span style={{ fontFamily: '"Noto Sans Kannada", sans-serif' }}>ನಮಸ್ಕಾರ! ಸಾಯಿ ವಿದ್ಯಾ ಪ್ರವೇಶಾತಿ ಮಾಹಿತಿ</span>
          {" • "}
          <span style={{ fontFamily: '"Noto Sans Devanagari", sans-serif' }}>नमस्ते! साई विद्या प्रवेश पूछताछ</span>
        </p>
        <p className="font-body-md text-body-md text-white/90 max-w-xl leading-relaxed">
          Ask by voice or text. Answers come from the SVIT admissions database through the six-engine pipeline.
        </p>
      </div>
      <div className="w-full max-w-2xl flex flex-col items-center gap-2.5 pt-2">
        <span className="font-label-sm text-label-sm text-white/80 font-bold uppercase tracking-wider flex items-center gap-1.5">
          <Icon name="bolt" className="text-[16px] text-secondary font-bold" />
          Popular Admissions Inquiries
        </span>
        <div className="flex flex-wrap items-center justify-center gap-2">
          {WELCOME_CHIPS.map((q) => (
            <button
              key={q}
              type="button"
              disabled={disabled}
              onClick={() => onAsk(q)}
              className="px-4 py-2 rounded-full text-white font-body-sm text-body-sm font-semibold transition-all hover:scale-105 active:scale-95 shadow-sm flex items-center gap-1.5 group disabled:opacity-60"
              style={{ backgroundColor: "rgba(88, 92, 176, 0.85)", border: "1px solid rgba(255, 255, 255, 0.35)", textShadow: "rgba(0, 0, 0, 0.6) 0px 1px 2px" }}
            >
              <span>{q}</span>
              <Icon name="north_east" className="text-[16px] group-hover:translate-x-0.5 transition-transform" />
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}


// ---- look (2026-10-14, from the conversation reference) ----
const SAGE_TINT = "#edf3b5";      // pale yellow-green icons
const GLASS = { backdropFilter: "blur(16px)", WebkitBackdropFilter: "blur(16px)" } as const;

function UserBubble({ m }: { m: Extract<ChatMessage, { kind: "user" }> }) {
  return (
    <div className="flex items-start justify-end gap-3">
      <div className="flex flex-col items-end max-w-[78%]">
        <div
          className={`px-6 py-3.5 rounded-[26px] text-white text-[17px] md:text-[19px] leading-snug break-words ${m.pending ? "italic text-white/75" : ""}`}
          style={{ background: "linear-gradient(135deg, rgba(55, 57, 44, 0.86), rgba(45, 46, 33, 0.86))", border: "1px solid rgba(135, 129, 104, 0.75)", boxShadow: "0 10px 30px rgba(0,0,0,0.3)", ...GLASS }}
        >
          {m.text}
          <span className="mt-1 flex items-center justify-end gap-1 text-[11.5px] text-white/55 not-italic">
            {m.langLabel && <span className="mr-1 hidden sm:inline">{m.langLabel} ·</span>}
            {m.voice && <Icon name="mic" className="text-[13px]" />}
            {time(m.at)}
            {!m.pending && <Icon name="done_all" className="text-[14px]" />}
          </span>
        </div>
      </div>
      <span className="w-12 h-12 md:w-14 md:h-14 flex-shrink-0 rounded-full flex items-center justify-center" style={{ background: "#29301d", border: "1px solid #53553e", boxShadow: "0 6px 18px rgba(0,0,0,0.35)" }}>
        <Icon name="person" className="text-[26px] text-white" filled />
      </span>
    </div>
  );
}

function ReplyTable({ data }: { data: TableData }) {
  if (!Array.isArray(data.columns) || !Array.isArray(data.rows) || data.rows.length === 0) return null;
  return (
    <div className="mt-3 overflow-x-auto rounded-2xl border border-white/12 bg-black/25">
      {data.title && <div className="px-3 pt-2 font-title-md text-title-md text-white">{data.title}</div>}
      <table className="w-full min-w-[320px]">
        <thead>
          <tr>{data.columns.map((c) => <th key={c} className="px-3 py-2 text-left font-label-md text-label-md text-white/80 uppercase tracking-wide">{c}</th>)}</tr>
        </thead>
        <tbody>
          {data.rows.map((row, i) => (
            <tr key={i} className="border-t border-white/10">
              {row.map((cell, j) => <td key={j} className="px-3 py-2 font-body-md text-body-md text-white">{String(cell)}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}


interface AudioControl {
  autoplay: boolean;
  /** makes sure only one reply plays at a time */
  claim: (audio: HTMLAudioElement) => void;
}

function ReplyAudio({ res, control, isLatest }: { res: QueryResponse; control: AudioControl; isLatest: boolean }) {
  const hasAudio = !!(res.audio && (res.audio.base64 || res.audio.url));
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const autoplayed = useRef(false);
  const [playing, setPlaying] = useState(false);
  const [duration, setDuration] = useState<number | null>(null);
  const [failed, setFailed] = useState(false);

  // latest props for the effect below, without re-running it
  const live = useRef({ control, isLatest });
  live.current = { control, isLatest };

  const play = () => {
    const a = audioRef.current;
    if (!a) return;
    live.current.control.claim(a);
    a.currentTime = 0;
    a.play().catch(() => undefined); // the browser may block autoplay; the button still works
  };

  useEffect(() => {
    const source = audioSource(res.audio);
    if (!source) return;
    const audio = new Audio(source.src);
    audioRef.current = audio;
    const onMeta = () => setDuration(Number.isFinite(audio.duration) ? audio.duration : null);
    const onPlay = () => setPlaying(true);
    const onStop = () => setPlaying(false);
    const onError = () => setFailed(true);
    audio.addEventListener("loadedmetadata", onMeta);
    audio.addEventListener("play", onPlay);
    audio.addEventListener("pause", onStop);
    audio.addEventListener("ended", onStop);
    audio.addEventListener("error", onError);

    if (live.current.isLatest && live.current.control.autoplay && !autoplayed.current) {
      autoplayed.current = true;
      play();
    }
    return () => {
      autoplayed.current = false;
      audio.pause();
      audio.removeEventListener("loadedmetadata", onMeta);
      audio.removeEventListener("play", onPlay);
      audio.removeEventListener("pause", onStop);
      audio.removeEventListener("ended", onStop);
      audio.removeEventListener("error", onError);
      audioRef.current = null;
      audio.removeAttribute("src"); // stop loading before the URL is released
      audio.load();
      source.revoke();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [res.audio]);


  if (!hasAudio) return null;
  return (
    <button
      type="button"
      disabled={failed}
      onClick={() => (playing ? audioRef.current?.pause() : play())}
      className={ACTION_BTN}
      title={duration ? `${duration.toFixed(1)} s` : undefined}
    >
      <Icon name={playing ? "pause_circle" : "play_circle"} className="text-[22px]" />
      <span>{failed ? "Audio unavailable" : playing ? "Playing…" : "Listen"}</span>
    </button>
  );
}

const ACTION_BTN = "h-10 px-3.5 rounded-full flex items-center gap-2 text-[14.5px] text-white/92 transition-colors hover:bg-white/10 disabled:opacity-50";

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    void navigator.clipboard?.writeText(text).then(() => { setCopied(true); window.setTimeout(() => setCopied(false), 1500); }).catch(() => undefined);
  };
  return (
    <button type="button" onClick={copy} className={ACTION_BTN}>
      <Icon name={copied ? "check" : "content_copy"} className="text-[20px]" />
      <span>{copied ? "Copied" : "Copy"}</span>
    </button>
  );
}

/** 👍 / 👎 — shows the choice (saved on this screen only for now). */
function Feedback() {
  const [vote, setVote] = useState<"up" | "down" | null>(null);
  return (
    <span className="flex items-center gap-1">
      <button type="button" aria-label="Helpful" aria-pressed={vote === "up"} onClick={() => setVote(vote === "up" ? null : "up")} className="w-10 h-10 rounded-full flex items-center justify-center text-white/90 hover:bg-white/10 transition-colors">
        <Icon name="thumb_up" className="text-[21px]" filled={vote === "up"} style={vote === "up" ? { color: SAGE_TINT } : undefined} />
      </button>
      <button type="button" aria-label="Not helpful" aria-pressed={vote === "down"} onClick={() => setVote(vote === "down" ? null : "down")} className="w-10 h-10 rounded-full flex items-center justify-center text-white/90 hover:bg-white/10 transition-colors">
        <Icon name="thumb_down" className="text-[21px]" filled={vote === "down"} style={vote === "down" ? { color: "#f3c6a8" } : undefined} />
      </button>
    </span>
  );
}

// ---- related next questions (shown under the latest answer) ----
type FollowUp = { icon: string; label: string; q: string };
const F = {
  hostelFees: { icon: "school", label: "Hostel fees", q: "What are the hostel fees at SVIT?" },
  kcetCutoff: { icon: "description", label: "KCET cutoff", q: "What is the KCET cutoff for CSE at SVIT?" },
  scholarships: { icon: "star", label: "Scholarships", q: "What scholarships are available at SVIT?" },
  feeStructure: { icon: "payments", label: "Fee structure", q: "What is the fee structure for CSE through KCET?" },
  comedk: { icon: "description", label: "COMEDK cutoff", q: "What is the COMEDK cutoff for CSE at SVIT?" },
  documents: { icon: "folder_open", label: "Documents needed", q: "Which documents are needed for admission?" },
  mess: { icon: "restaurant", label: "Mess & food", q: "What are the mess and food facilities in the hostel?" },
  transport: { icon: "directions_bus", label: "Bus routes", q: "What transport and bus routes does SVIT have?" },
  recruiters: { icon: "work", label: "Top recruiters", q: "Which companies come to SVIT for placements?" },
  packages: { icon: "trending_up", label: "Average package", q: "What is the average placement package at SVIT?" },
  process: { icon: "checklist", label: "Admission process", q: "What is the admission process at SVIT?" },
} satisfies Record<string, FollowUp>;
const FOLLOW_UPS: { match: RegExp; items: FollowUp[] }[] = [
  { match: /fee|payment|refund/i, items: [F.hostelFees, F.kcetCutoff, F.scholarships] },
  { match: /cutoff|rank|seat/i, items: [F.feeStructure, F.comedk, F.documents] },
  { match: /hostel|mess|campus/i, items: [F.hostelFees, F.mess, F.transport] },
  { match: /placement|recruit|package|intern/i, items: [F.recruiters, F.packages, F.feeStructure] },
  { match: /scholar/i, items: [F.feeStructure, F.documents, F.process] },
  { match: /transport|bus/i, items: [F.transport, F.hostelFees, F.feeStructure] },
  { match: /document|admission|process|eligib/i, items: [F.process, F.documents, F.feeStructure] },
];
function followUpsFor(res: QueryResponse): FollowUp[] {
  const key = [res.understanding?.intent, res.memory?.topic, res.transcript].filter(Boolean).join(" ");
  return (FOLLOW_UPS.find((r) => r.match.test(key))?.items) ?? [F.hostelFees, F.kcetCutoff, F.scholarships];
}

function FollowUps({ res, onAsk, disabled }: { res: QueryResponse; onAsk: (q: string) => void; disabled: boolean }) {
  return (
    <div className="mt-4 flex flex-wrap gap-3 md:pl-1">
      {followUpsFor(res).map((f) => (
        <button
          key={f.label}
          type="button"
          disabled={disabled}
          onClick={() => onAsk(f.q)}
          className="group h-[52px] pl-5 pr-5 rounded-full flex items-center gap-3 text-[15.5px] text-white transition-all hover:brightness-125 disabled:opacity-60"
          style={{ background: "linear-gradient(180deg, rgba(34, 30, 24, 0.78), rgba(16, 16, 12, 0.82))", border: "1px solid rgba(135, 107, 82, 0.7)", boxShadow: "0 8px 22px rgba(0,0,0,0.3)", ...GLASS }}
        >
          <Icon name={f.icon} className="text-[22px]" style={{ color: SAGE_TINT }} filled />
          <span className="mr-3">{f.label}</span>
          <Icon name="arrow_forward" className="text-[20px] group-hover:translate-x-0.5 transition-transform" />
        </button>
      ))}
    </div>
  );
}

function BotBubble({ m, control, isLatest, onAsk, busy }: { m: Extract<ChatMessage, { kind: "bot" }>; control: AudioControl; isLatest: boolean; onAsk: (q: string) => void; busy: boolean }) {
  const { res } = m;
  const r = res.response ?? {};
  // the reply's own language/script if the backend says so, else the detected question language
  const lang = r.language || (res.language?.primary as string) || "";
  const mode = res.understanding?.response_mode;
  const canRomanize = (lang === "kn" || lang === "hi") && !!r.text_romanized;
  const [roman, setRoman] = useState(false);
  const escalate = mode === "escalation" || !!res.escalation?.needed;
  const contact = res.escalation?.contact;
  const shown = (canRomanize && roman ? r.text_romanized : r.text) ?? "";

  return (
    <div className="flex flex-col items-start">
      <div
        className="w-full max-w-[950px] rounded-[28px] p-5 md:p-6 flex gap-4"
        style={{
          background: "linear-gradient(160deg, rgba(66, 53, 41, 0.72) 0%, rgba(34, 29, 24, 0.8) 45%, rgba(20, 20, 17, 0.84) 100%)",
          border: `1px solid ${mode === "reassurance" ? "rgba(167, 243, 208, 0.45)" : "rgba(167, 134, 95, 0.55)"}`,
          boxShadow: "0 18px 46px rgba(0,0,0,0.38), inset 0 1px 0 rgba(255, 230, 190, 0.12)",
          ...GLASS,
        }}
      >
        <img src="/assets/svit-logo.png" alt="" className="w-12 h-12 md:w-[60px] md:h-[60px] rounded-full flex-shrink-0 object-contain bg-white/90 p-0.5" style={{ boxShadow: "0 0 0 2px rgba(255,255,255,0.2), 0 6px 16px rgba(0,0,0,0.35)" }} />
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <span className="text-[15.5px] font-semibold text-white">IntelliVoice <span style={{ color: "#c9dc9b" }}>AI</span></span>
            <span className="text-[13px] text-white/55">{time(m.at)}</span>
            {LANG_NAMES[lang] && <span className="text-[12.5px] text-white/45">· {LANG_NAMES[lang]}</span>}
            {res.demo && <span className="px-2 py-0.5 rounded-full text-[11px] bg-amber-400/25 border border-amber-200/40 text-amber-100">Demo mode · sample reply</span>}
          </div>
          <p className="mt-2 text-[17px] md:text-[19px] leading-[1.55] text-white whitespace-pre-line break-words" lang={lang || "en"}>{shown}</p>
          {res.data && <ReplyTable data={res.data} />}

          <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
            <span className="h-11 pl-3.5 pr-5 rounded-full flex items-center gap-2.5 text-[14.5px] text-white/92" style={{ background: "rgba(39, 39, 30, 0.85)", border: "1px solid rgba(255, 255, 255, 0.1)" }}>
              <Icon name="database" className="text-[21px]" style={{ color: SAGE_TINT }} filled />
              {res.source || "SVIT Admissions Database"}
            </span>
            <span className="flex flex-wrap items-center gap-1">
              <span className="rounded-full" style={{ background: "rgba(20, 19, 16, 0.6)", border: "1px solid rgba(255,255,255,0.08)" }}>
                <ReplyAudio res={res} control={control} isLatest={isLatest} />
              </span>
              <CopyButton text={shown} />
              {canRomanize && (
                <button type="button" onClick={() => setRoman((x) => !x)} className={ACTION_BTN}>
                  <Icon name="translate" className="text-[20px]" />
                  <span>{roman ? (lang === "hi" ? "हिंदी" : "ಕನ್ನಡ") : "English letters"}</span>
                </button>
              )}
              <span className="w-px h-6 bg-white/20 mx-1.5" aria-hidden="true" />
              <Feedback />
            </span>
          </div>
        </div>
      </div>
      {escalate && (
        <div className="w-full max-w-[950px] mt-3 px-5 py-4 rounded-[24px] text-white flex items-start gap-3" style={{ background: "linear-gradient(135deg, rgba(65, 42, 26, 0.75), rgba(36, 26, 20, 0.8))", border: "1.5px solid rgba(246, 240, 189, 0.75)", boxShadow: "0 0 22px rgba(246, 240, 189, 0.22)", ...GLASS }}>
          <Icon name="headset_mic" className="text-[26px]" style={{ color: "#f6f0bd" }} />
          <div className="flex flex-col gap-1">
            <span className="text-[16px] font-semibold">Need help from the admissions office?</span>
            <span className="text-[14.5px] text-white/85">{res.escalation?.message || "The SVIT admissions team can help with this question."}</span>
            {contact?.phone && <a className="text-[14.5px] underline underline-offset-2" style={{ color: "#f6f0bd" }} href={`tel:${contact.phone}`}>{contact.phone}</a>}
            {contact?.email && <a className="text-[14.5px] underline underline-offset-2" style={{ color: "#f6f0bd" }} href={`mailto:${contact.email}`}>{contact.email}</a>}
          </div>
        </div>
      )}
      {isLatest && !escalate && <FollowUps res={res} onAsk={onAsk} disabled={busy} />}
    </div>
  );
}

function ErrorBubble({ m, onRetry }: { m: Extract<ChatMessage, { kind: "error" }>; onRetry: (id: string) => void }) {
  return (
    <div className="flex flex-col items-start gap-2" role="alert">
      <div className="max-w-[90%] px-5 py-3.5 rounded-[22px] text-white text-[15px] flex items-start gap-2" style={{ background: "rgba(110, 20, 20, 0.45)", border: "1px solid rgba(255, 180, 171, 0.45)", ...GLASS }}>
        <Icon name="error" className="text-[20px]" /><span>{m.text}</span>
      </div>
      {m.retry && (
        <button type="button" onClick={() => onRetry(m.id)} className="h-10 px-4 rounded-full text-white text-[14px] border border-white/30 bg-white/10 hover:bg-white/20 flex items-center gap-1.5">
          <Icon name="refresh" className="text-[18px]" />Try again
        </button>
      )}
    </div>
  );
}

export function MessageList({ messages, busy, control, onRetry, onAsk }: {
  messages: ChatMessage[];
  busy: boolean;
  control: AudioControl;
  onRetry: (id: string) => void;
  onAsk: (q: string) => void;
}) {
  const lastBotId = [...messages].reverse().find((m) => m.kind === "bot")?.id;
  const lastId = messages[messages.length - 1]?.id;
  return (
    <>
      {messages.map((m) =>
        m.kind === "user" ? <UserBubble key={m.id} m={m} />
          : m.kind === "bot" ? <BotBubble key={m.id} m={m} control={control} isLatest={m.id === lastBotId && m.id === lastId && !busy} onAsk={onAsk} busy={busy} />
            : <ErrorBubble key={m.id} m={m} onRetry={onRetry} />)}
      {busy && (
        <div className="self-start flex items-center gap-3 pl-2 pr-5 py-2 rounded-full text-white/85 text-[15px]" style={{ background: "rgba(20, 19, 16, 0.6)", border: "1px solid rgba(167, 134, 95, 0.4)", ...GLASS }}>
          <img src="/assets/svit-logo.png" alt="" className="w-8 h-8 rounded-full object-contain bg-white/90 p-0.5" />
          <span className="flex gap-1" aria-hidden="true">
            <span className="w-1.5 h-1.5 rounded-full animate-bounce" style={{ background: "#c9dc9b", animationDelay: "0ms" }} />
            <span className="w-1.5 h-1.5 rounded-full animate-bounce" style={{ background: "#c9dc9b", animationDelay: "150ms" }} />
            <span className="w-1.5 h-1.5 rounded-full animate-bounce" style={{ background: "#c9dc9b", animationDelay: "300ms" }} />
          </span>
          <span>IntelliVoice is thinking…</span>
        </div>
      )}
    </>
  );
}
