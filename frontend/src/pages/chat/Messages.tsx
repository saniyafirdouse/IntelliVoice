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

function UserBubble({ m }: { m: Extract<ChatMessage, { kind: "user" }> }) {
  return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex flex-wrap justify-end items-center gap-2 text-white/70 font-label-sm text-label-sm">
        <Icon name={m.voice ? "mic" : "keyboard"} className="text-[14px]" />
        <span>You{m.voice ? " (voice)" : ""}</span>
        {m.langLabel && <span>· {m.langLabel}</span>}
        <span>{time(m.at)}</span>
      </div>
      <div
        className={`max-w-[85%] px-4 py-3 rounded-2xl rounded-tr-md text-white font-body-lg text-body-lg break-words ${m.pending ? "italic text-white/80" : ""}`}
        style={{ background: "rgba(88, 92, 176, 0.55)", border: "1px solid rgba(255,255,255,0.25)" }}
      >
        {m.text}
      </div>
    </div>
  );
}

function ReplyTable({ data }: { data: TableData }) {
  if (!Array.isArray(data.columns) || !Array.isArray(data.rows) || data.rows.length === 0) return null;
  return (
    <div className="mt-3 overflow-x-auto rounded-xl border border-white/15 bg-black/30">
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
      className="px-3 py-1.5 rounded-full text-white font-label-md text-label-md font-semibold flex items-center gap-1.5 disabled:opacity-60"
      style={{ background: "rgb(88, 92, 176)", border: "1px solid rgba(255,255,255,0.35)" }}
    >
      <Icon name={playing ? "pause" : "play_arrow"} className="text-[18px]" />
      <span>{failed ? "Audio unavailable" : playing ? "Playing…" : duration ? `Play (${duration.toFixed(1)}s)` : "Play"}</span>
    </button>
  );
}

function BotBubble({ m, control, isLatest }: { m: Extract<ChatMessage, { kind: "bot" }>; control: AudioControl; isLatest: boolean }) {
  const { res } = m;
  const r = res.response ?? {};
  // the reply's own language/script if the backend says so, else the detected question language
  const lang = r.language || (res.language?.primary as string) || "";
  const mode = res.understanding?.response_mode;
  const canRomanize = (lang === "kn" || lang === "hi") && !!r.text_romanized;
  const [roman, setRoman] = useState(false);
  const escalate = mode === "escalation" || !!res.escalation?.needed;
  const contact = res.escalation?.contact;

  return (
    <div className="flex flex-col items-start gap-1">
      <div className="flex flex-wrap items-center gap-2 text-white/70 font-label-sm text-label-sm">
        <span className="w-5 h-5 rounded-full flex items-center justify-center bg-secondary-container text-white"><Icon name="support_agent" className="text-[13px]" /></span>
        <span>IntelliVoice</span>
        {LANG_NAMES[lang] && <span>· {LANG_NAMES[lang]}</span>}
        <span>{time(m.at)}</span>
        {res.demo && <span className="px-2 py-0.5 rounded-full bg-amber-400/25 border border-amber-200/40 text-amber-100">Demo mode · sample reply</span>}
      </div>
      <div
        className="w-full max-w-[92%] px-4 py-3 rounded-2xl rounded-tl-md text-white"
        style={{ background: "rgba(18, 20, 28, 0.55)", border: `1px solid ${mode === "reassurance" ? "rgba(167, 243, 208, 0.45)" : "rgba(191,194,255,0.3)"}` }}
      >
        <p className="font-body-lg text-body-lg whitespace-pre-line break-words" lang={lang || "en"}>
          {canRomanize && roman ? r.text_romanized : r.text}
        </p>
        {res.data && <ReplyTable data={res.data} />}
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <ReplyAudio res={res} control={control} isLatest={isLatest} />
          {res.audio?.voice && <span className="font-label-sm text-label-sm text-white/60">Voice: {res.audio.voice}</span>}
          {canRomanize && (
            <button type="button" onClick={() => setRoman((x) => !x)} className="px-3 py-1 rounded-full text-white font-label-md text-label-md border border-white/30 bg-white/10 hover:bg-white/20">
              {roman ? (lang === "hi" ? "Show in हिंदी" : "Show in ಕನ್ನಡ") : "Show in English letters"}
            </button>
          )}
        </div>
        {res.source && (
          <p className="mt-2 font-label-sm text-label-sm text-white/60 flex items-center gap-1">
            <Icon name="database" className="text-[14px]" />Source: {res.source}
          </p>
        )}
      </div>
      {escalate && (
        <div className="w-full max-w-[92%] mt-2 px-4 py-3 rounded-2xl text-white flex items-start gap-3" style={{ background: "rgba(88, 92, 176, 0.3)", border: "1px solid rgba(191,194,255,0.45)" }}>
          <Icon name="support_agent" className="text-[24px] text-secondary" />
          <div className="flex flex-col gap-1">
            <span className="font-title-md text-title-md font-bold">Need help from the admissions office?</span>
            <span className="font-body-md text-body-md text-white/85">{res.escalation?.message || "The SVIT admissions team can help with this question."}</span>
            {contact?.phone && <a className="font-body-md text-body-md text-secondary underline" href={`tel:${contact.phone}`}>{contact.phone}</a>}
            {contact?.email && <a className="font-body-md text-body-md text-secondary underline" href={`mailto:${contact.email}`}>{contact.email}</a>}
          </div>
        </div>
      )}
    </div>
  );
}

function ErrorBubble({ m, onRetry }: { m: Extract<ChatMessage, { kind: "error" }>; onRetry: (id: string) => void }) {
  return (
    <div className="flex flex-col items-start gap-2" role="alert">
      <div className="max-w-[90%] px-4 py-3 rounded-2xl text-white font-body-md text-body-md flex items-start gap-2" style={{ background: "rgba(147, 0, 10, 0.35)", border: "1px solid rgba(255, 180, 171, 0.45)" }}>
        <Icon name="error" className="text-[20px]" /><span>{m.text}</span>
      </div>
      {m.retry && (
        <button type="button" onClick={() => onRetry(m.id)} className="px-3 py-1 rounded-full text-white font-label-md text-label-md border border-white/30 bg-white/10 hover:bg-white/20 flex items-center gap-1">
          <Icon name="refresh" className="text-[16px]" />Try again
        </button>
      )}
    </div>
  );
}

export function MessageList({ messages, busy, control, onRetry }: {
  messages: ChatMessage[];
  busy: boolean;
  control: AudioControl;
  onRetry: (id: string) => void;
}) {
  const lastBotId = [...messages].reverse().find((m) => m.kind === "bot")?.id;
  return (
    <>
      {messages.map((m) =>
        m.kind === "user" ? <UserBubble key={m.id} m={m} />
          : m.kind === "bot" ? <BotBubble key={m.id} m={m} control={control} isLatest={m.id === lastBotId} />
            : <ErrorBubble key={m.id} m={m} onRetry={onRetry} />)}
      {busy && (
        <div className="flex items-center gap-2 text-white/80 font-body-md text-body-md">
          <Icon name="progress_activity" className="text-[20px] text-secondary animate-spin" style={{ animationDuration: "1.4s" }} />
          <span>IntelliVoice is thinking…</span>
        </div>
      )}
    </>
  );
}
