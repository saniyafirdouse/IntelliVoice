// Voice Chat start screen (2026-10-14) — follows the reference design San picked:
// "Hello! How can I help you today?" + three cards (type / hands-free / press to speak),
// "Try asking" chips and a "Talk to a Human Officer" card. Colours are sampled from the
// reference image; headings use Cormorant Garamond, everything else Inter.

import { useEffect, useRef, useState, type FormEvent, type PointerEvent as ReactPointerEvent } from "react";
import { Icon } from "../../components/Icon";
import { LanguageMenu } from "../../components/SiteHeader";

// ---- palette (sampled from the reference) ----
const C = {
  sage: "#9db87c",          // "New" badge, hands-free accents
  sageBright: "#b9cf94",    // hands-free border highlight
  sageDeep: "#333d2a",      // hands-free icon circle
  peach: "#dcaa93",         // press-to-speak ring / border
  peachSoft: "#d7c2a7",     // warm end of the wave lines
  gold: "#f6e5ad",          // "Try asking" sparkle
  text: "#ffffff",
  textSoft: "rgba(255, 255, 255, 0.78)",
};

export const TRY_ASKING = [
  "CSE fees for KCET?",
  "Hostel facilities for girls?",
  "COMEDK cutoff for ISE?",
  "Placement record 2024?",
];

const serif = { fontFamily: '"Cormorant Garamond", "Noto Sans Kannada", "Noto Sans Devanagari", Georgia, serif' };

// ---------------------------------------------------------------- heading
export function ChatHeading() {
  return (
    <div className="flex flex-col items-center text-center px-4">
      <p className="text-[11px] sm:text-[12px] font-medium tracking-[0.34em] uppercase text-white/85" style={{ textShadow: "0 1px 6px rgba(0,0,0,0.6)" }}>
        Your AI assistant for SVIT admissions
      </p>
      <h1
        className="mt-4 text-white font-medium leading-[1.08]"
        style={{ ...serif, fontSize: "clamp(34px, 3.55vw, 54px)", letterSpacing: "0.003em", textShadow: "0 2px 18px rgba(0,0,0,0.45)" }}
      >
        Hello! How can I help you today?
      </h1>
      <p className="mt-3 text-[15px] sm:text-[17px] text-white/92" style={{ textShadow: "0 1px 6px rgba(0,0,0,0.6)" }}>
        Ask about admissions, fees, cutoffs, placements, hostels and more.
      </p>
    </div>
  );
}

// ---------------------------------------------------------------- human officer card
export function HumanOfficerCard({ onClick, disabled }: { onClick: () => void; disabled: boolean }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="group w-full sm:w-[312px] flex items-center gap-3.5 pl-3 pr-5 py-3 rounded-[22px] text-left transition-all hover:brightness-110 disabled:opacity-60"
      style={{ background: "linear-gradient(135deg, rgba(65, 42, 26, 0.72), rgba(36, 26, 22, 0.66))", border: "1.5px solid rgba(246, 240, 189, 0.85)", backdropFilter: "blur(14px)", WebkitBackdropFilter: "blur(14px)", boxShadow: "0 0 0 1px rgba(246, 240, 189, 0.12), 0 0 26px rgba(246, 240, 189, 0.28), 0 10px 30px rgba(0,0,0,0.3)" }}
    >
      <span className="w-11 h-11 rounded-full flex items-center justify-center flex-shrink-0" style={{ background: "#202023" }}>
        <Icon name="headset_mic" className="text-[22px] text-white" />
      </span>
      <span className="flex flex-col min-w-0 flex-1">
        <span className="text-[15px] font-semibold text-white leading-tight">Talk to a Human Officer</span>
        <span className="text-[12px] text-white/60 leading-tight mt-1 whitespace-nowrap">Get help from our admission team</span>
      </span>
      <Icon name="arrow_forward" className="text-[20px] text-white/90 group-hover:translate-x-0.5 transition-transform" />
    </button>
  );
}

// ---------------------------------------------------------------- decorative waves
/** The sweeping silk waves of the hands-free card (sage from the bottom-left, peach rising to the top-right). */
function HandsFreeWaves() {
  const n = 22;
  const lines = Array.from({ length: n }, (_, i) => i / (n - 1));
  return (
    <svg viewBox="0 0 440 180" preserveAspectRatio="none" className="absolute inset-0 w-full h-full pointer-events-none" aria-hidden="true">
      <defs>
        <linearGradient id="ivHfSage" x1="0" x2="1" y1="0" y2="0">
          <stop offset="0" stopColor="#a6c27f" stopOpacity="0.9" />
          <stop offset="0.45" stopColor="#8fab6c" stopOpacity="0.55" />
          <stop offset="0.75" stopColor="#8fab6c" stopOpacity="0" />
        </linearGradient>
        <linearGradient id="ivHfPeach" x1="0" x2="1" y1="0" y2="0">
          <stop offset="0.35" stopColor="#c9b38f" stopOpacity="0" />
          <stop offset="0.7" stopColor="#d7c2a7" stopOpacity="0.55" />
          <stop offset="1" stopColor="#e8d3b4" stopOpacity="0.95" />
        </linearGradient>
      </defs>
      <g fill="none" strokeWidth="0.7" className="iv-wave-drift">
        {lines.map((k, i) => (
          <path key={`s${i}`} stroke="url(#ivHfSage)"
            d={`M -10 ${178 - k * 30} C 40 ${150 - k * 52} 95 ${118 - k * 36} 150 ${140 - k * 18} S 250 ${182 - k * 6} 300 ${184}`} />
        ))}
        {lines.map((k, i) => (
          <path key={`p${i}`} stroke="url(#ivHfPeach)"
            d={`M 170 ${184} C 260 ${180 - k * 8} 300 ${170 - k * 30} 350 ${132 - k * 38} S 420 ${62 - k * 30} 452 ${54 - k * 26}`} />
        ))}
      </g>
    </svg>
  );
}

/** Small waveform bars either side of the hands-free icon. */
function WaveBars({ flip = false }: { flip?: boolean }) {
  const h = [3, 6, 4, 9, 5, 12, 7, 15, 9, 6, 13, 8, 18, 10, 6, 11, 5, 8, 4, 6, 3];
  const bars = flip ? [...h].reverse() : h;
  return (
    <span className="hidden sm:flex items-center gap-[3px] h-5" aria-hidden="true">
      {bars.map((v, i) => (
        <span key={i} className="w-[1.5px] rounded-full" style={{ height: `${v}px`, background: `rgba(185, 207, 148, ${0.35 + (flip ? i : bars.length - i) / bars.length * 0.55})` }} />
      ))}
    </span>
  );
}

const CARD_BASE = "relative overflow-hidden rounded-[24px] transition-all duration-200";
const glassBlur = { backdropFilter: "blur(16px)", WebkitBackdropFilter: "blur(16px)" };

// ---------------------------------------------------------------- 1. type your question
function TypeCard({ onSend, busy }: { onSend: (q: string) => void; busy: boolean }) {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  useEffect(() => { if (open) inputRef.current?.focus(); }, [open]);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const t = text.trim();
    if (!t || busy) return;
    onSend(t);
    setText("");
  };

  return (
    <div
      className={`${CARD_BASE} min-h-[150px] p-5 flex flex-col justify-between hover:brightness-110`}
      style={{ background: "linear-gradient(180deg, rgba(62, 56, 54, 0.62), rgba(40, 38, 42, 0.66))", border: "1px solid rgba(255, 255, 255, 0.16)", boxShadow: "0 14px 36px rgba(0,0,0,0.35)", ...glassBlur }}
    >
      <span className="w-[52px] h-[52px] rounded-full flex items-center justify-center" style={{ background: "rgba(255, 255, 255, 0.1)", border: "1px solid rgba(255, 255, 255, 0.28)" }}>
        <Icon name="keyboard" className="text-[26px] text-white" />
      </span>
      {open ? (
        <form onSubmit={submit} className="mt-3 flex items-center gap-2">
          <input
            ref={inputRef}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Escape") setOpen(false); }}
            maxLength={500}
            disabled={busy}
            aria-label="Type your question"
            placeholder="Type your question…"
            className="flex-1 min-w-0 h-11 px-4 rounded-full bg-black/30 border border-white/25 text-[14px] text-white placeholder:text-white/50 outline-none focus:border-white/55"
          />
          <button type="submit" disabled={busy || !text.trim()} aria-label="Send" className="w-11 h-11 flex-shrink-0 rounded-full flex items-center justify-center border border-white/45 text-white hover:bg-white/10 disabled:opacity-50">
            <Icon name="arrow_forward" className="text-[22px]" />
          </button>
        </form>
      ) : (
        <button type="button" onClick={() => setOpen(true)} className="mt-3 flex items-center justify-between gap-3 text-left group" aria-label="Type your question">
          <span className="flex flex-col">
            <span className="text-[16px] font-semibold text-white">Type your question</span>
            <span className="text-[12.5px] text-white/72 mt-0.5">Ask in English, <span lang="kn">ಕನ್ನಡ</span> or <span lang="hi">हिंदी</span></span>
          </span>
          <span className="w-11 h-11 flex-shrink-0 rounded-full flex items-center justify-center border border-white/45 text-white group-hover:bg-white/10 transition-colors">
            <Icon name="arrow_forward" className="text-[22px]" />
          </span>
        </button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------- 2. hands-free (highlighted)
function HandsFreeCard({ onStart, disabled }: { onStart: () => void; disabled: boolean }) {
  return (
    <div className="relative">
      {/* soft green glow behind the card so it stands out (the "eye-catching" one) */}
      <div className="iv-hf-glow absolute -inset-4 rounded-[36px] pointer-events-none" aria-hidden="true"
           style={{ background: "radial-gradient(60% 70% at 50% 55%, rgba(157, 184, 124, 0.38), rgba(157, 184, 124, 0.08) 60%, transparent 75%)", filter: "blur(10px)" }} />
      <button
        type="button"
        onClick={onStart}
        disabled={disabled}
        className={`${CARD_BASE} w-full min-h-[176px] px-6 pt-4 pb-6 flex flex-col items-center justify-start text-center hover:-translate-y-0.5 disabled:opacity-60`}
        style={{
          background: "linear-gradient(180deg, rgba(52, 52, 34, 0.9) 0%, rgba(32, 38, 26, 0.92) 55%, rgba(30, 38, 27, 0.94) 100%)",
          border: `1.5px solid ${C.sageBright}`,
          boxShadow: `0 0 0 1px rgba(185, 207, 148, 0.18), 0 0 34px rgba(157, 184, 124, 0.38), 0 18px 44px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.08)`,
          ...glassBlur,
        }}
        aria-label="Start hands-free voice chat"
      >
        <HandsFreeWaves />
        <span className="relative flex items-center gap-3">
          <WaveBars />
          <span className="w-[52px] h-[52px] rounded-full flex items-center justify-center" style={{ background: C.sageDeep, border: `1.5px solid ${C.sage}`, boxShadow: "0 0 18px rgba(157, 184, 124, 0.45)" }}>
            <Icon name="graphic_eq" className="text-[26px] text-white" />
          </span>
          <WaveBars flip />
        </span>
        <span className="relative mt-3 flex items-center gap-2">
          <span className="text-[16.5px] font-semibold text-white">Hands-free Voice Chat</span>
          <span className="px-2.5 py-0.5 rounded-full text-[12px] font-semibold" style={{ background: C.sage, color: "#1f2a14" }}>New</span>
        </span>
        <span className="relative mt-1.5 text-[12.5px] text-white/82">Just speak naturally. No buttons needed.</span>
      </button>
    </div>
  );
}

// ---------------------------------------------------------------- 3. press to speak
function SpeakCard({ recording, levels, busy, onStart, onStop }: {
  recording: boolean; levels: number[]; busy: boolean; onStart: () => void; onStop: () => void;
}) {
  // Hold to talk; a quick tap also works (tap once to start, tap again to send).
  const pressRef = useRef<{ at: number; started: boolean }>({ at: 0, started: false });
  const down = (e: ReactPointerEvent) => {
    if (e.button !== 0) return;
    (e.currentTarget as HTMLElement).setPointerCapture?.(e.pointerId);
    if (recording) { pressRef.current = { at: 0, started: false }; onStop(); return; }
    if (busy) return;
    pressRef.current = { at: performance.now(), started: true };
    onStart();
  };
  const up = () => {
    const p = pressRef.current;
    if (p.started && performance.now() - p.at > 350) onStop();   // held -> release sends
    pressRef.current = { at: 0, started: false };
  };
  const level = recording ? Math.min(1, Math.max(...levels, 0) * 1.6) : 0;

  return (
    <button
      type="button"
      onPointerDown={down}
      onPointerUp={up}
      onPointerCancel={up}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); if (recording) onStop(); else if (!busy) onStart(); } }}
      disabled={busy && !recording}
      aria-pressed={recording}
      aria-label={recording ? "Release or tap to send" : "Press and hold to speak"}
      className={`${CARD_BASE} w-full min-h-[150px] p-5 flex flex-col items-center justify-center text-center select-none touch-none hover:brightness-110 disabled:opacity-60`}
      style={{ background: "linear-gradient(180deg, rgba(42, 34, 27, 0.74), rgba(52, 39, 31, 0.78))", border: `1px solid rgba(220, 170, 147, ${recording ? 0.9 : 0.5})`, boxShadow: recording ? "0 0 30px rgba(220, 170, 147, 0.35), 0 14px 36px rgba(0,0,0,0.35)" : "0 14px 36px rgba(0,0,0,0.35)", ...glassBlur }}
    >
      <svg viewBox="0 0 300 160" preserveAspectRatio="none" className="absolute inset-0 w-full h-full pointer-events-none" aria-hidden="true">
        <g fill="none" stroke="#dcaa93" strokeWidth="0.6" className="iv-wave-drift">
          {Array.from({ length: 9 }, (_, i) => (
            <path key={`t${i}`} strokeOpacity={0.12 + i * 0.03} d={`M 190 ${-4 + i * 3} C 240 ${10 + i * 6} 270 ${30 + i * 5} 306 ${70 + i * 6}`} />
          ))}
          {Array.from({ length: 9 }, (_, i) => (
            <path key={`b${i}`} strokeOpacity={0.12 + i * 0.03} d={`M -6 ${86 + i * 6} C 30 ${110 + i * 5} 60 ${140 + i * 3} 110 ${166 - i}`} />
          ))}
        </g>
      </svg>
      <span className="relative flex items-center justify-center">
        <span className={`absolute rounded-full ${recording ? "animate-ping" : ""}`} style={{ width: 84, height: 84, background: "rgba(220, 170, 147, 0.18)" }} />
        <span
          className="relative w-[74px] h-[74px] rounded-full flex items-center justify-center transition-transform"
          style={{ background: "rgba(74, 55, 43, 0.92)", border: `2px solid ${C.peach}`, boxShadow: `0 0 ${18 + level * 26}px rgba(220, 170, 147, ${0.35 + level * 0.4})`, transform: `scale(${1 + level * 0.08})` }}
        >
          <Icon name={recording ? "stop" : "mic"} className="text-[38px] text-white" filled />
        </span>
      </span>
      <span className="relative mt-3 text-[16px] font-semibold text-white">{recording ? "Listening…" : "Press to speak"}</span>
      <span className="relative mt-0.5 text-[12.5px] text-white/72">{recording ? "Release (or tap) to send" : "Hold to record, release to send"}</span>
    </button>
  );
}

// ---------------------------------------------------------------- the row of cards
export function ActionCards(props: {
  busy: boolean;
  recording: boolean;
  levels: number[];
  onSend: (q: string) => void;
  onHandsFree: () => void;
  onStartRecording: () => void;
  onStopRecording: () => void;
}) {
  return (
    <div className="w-full max-w-[1080px] mx-auto grid grid-cols-1 md:grid-cols-[1fr_1.45fr_1fr] items-center gap-5 md:gap-5">
      <div className="order-3 md:order-none"><TypeCard onSend={props.onSend} busy={props.busy} /></div>
      <div className="order-1 md:order-none"><HandsFreeCard onStart={props.onHandsFree} disabled={props.busy || props.recording} /></div>
      <div className="order-2 md:order-none">
        <SpeakCard recording={props.recording} levels={props.levels} busy={props.busy} onStart={props.onStartRecording} onStop={props.onStopRecording} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- try asking
export function TryAsking({ onAsk, disabled }: { onAsk: (q: string) => void; disabled: boolean }) {
  return (
    <div className="flex flex-col items-center gap-3.5 px-4">
      <span className="flex items-center gap-2 text-[15px] font-semibold text-white" style={{ textShadow: "0 1px 6px rgba(0,0,0,0.6)" }}>
        <Icon name="lightbulb" className="text-[20px]" style={{ color: C.gold }} filled />
        Try asking
      </span>
      <div className="flex flex-wrap items-center justify-center gap-3">
        {TRY_ASKING.map((q) => (
          <button
            key={q}
            type="button"
            disabled={disabled}
            onClick={() => onAsk(q)}
            className="group h-11 pl-5 pr-4 rounded-full flex items-center gap-2.5 text-[14px] text-white transition-all hover:brightness-125 disabled:opacity-60"
            style={{ background: "rgba(62, 50, 44, 0.55)", border: "1px solid rgba(255, 255, 255, 0.26)", ...glassBlur }}
          >
            {q}
            <Icon name="arrow_forward" className="text-[18px] group-hover:translate-x-0.5 transition-transform" />
          </button>
        ))}
      </div>
    </div>
  );
}

/** CSS used by the cards (slow wave drift, breathing glow). Respects reduced motion. */
export const CHAT_HOME_CSS = `
@keyframes iv-wave-drift { 0%, 100% { transform: translateX(0); } 50% { transform: translateX(-10px); } }
@keyframes iv-hf-glow { 0%, 100% { opacity: 0.75; transform: scale(0.98); } 50% { opacity: 1; transform: scale(1.02); } }
.iv-wave-drift { animation: iv-wave-drift 9s ease-in-out infinite; }
.iv-hf-glow { animation: iv-hf-glow 4.5s ease-in-out infinite; }
@keyframes iv-blob { 0%, 100% { transform: scale(1) rotate(0deg); } 50% { transform: scale(1.04) rotate(-2deg); } }
@keyframes iv-dot-pulse { 0%, 100% { opacity: 0.6; } 50% { opacity: 1; } }
.iv-blob { animation: iv-blob 6s ease-in-out infinite; transform-origin: 50% 50%; }
.iv-dot-pulse { animation: iv-dot-pulse 3s ease-in-out infinite; }
@media (prefers-reduced-motion: reduce) { .iv-wave-drift, .iv-hf-glow, .iv-blob, .iv-dot-pulse { animation: none; } }
`;

// ================================================================ conversation mode (2026-10-14, second reference)

/** Thin glowing line with light dots drifting across the background. */
export function DecorLine() {
  return (
    <svg viewBox="0 0 1600 900" preserveAspectRatio="none" className="fixed inset-0 w-full h-full pointer-events-none z-0" aria-hidden="true">
      <defs>
        <radialGradient id="ivDot"><stop offset="0" stopColor="#ffffd1" stopOpacity="1" /><stop offset="1" stopColor="#ffffd1" stopOpacity="0" /></radialGradient>
      </defs>
      <path d="M -20 640 C 90 560 180 500 210 515 S 300 600 420 640 S 640 590 760 620 S 980 640 1050 660 S 1240 560 1320 520 S 1500 640 1620 720"
            fill="none" stroke="rgba(255, 250, 220, 0.55)" strokeWidth="1.1" />
      {[[210, 515], [1050, 660], [1470, 610]].map(([x, y], i) => (
        <g key={i} className="iv-dot-pulse" style={{ animationDelay: `${i * 0.9}s` }}>
          <circle cx={x} cy={y} r="12" fill="url(#ivDot)" opacity="0.55" />
          <circle cx={x} cy={y} r="3.2" fill="#ffffd1" />
        </g>
      ))}
    </svg>
  );
}

/** Green blob + "Switch to hands-free voice chat" (right side while chatting). */
export function HandsFreeSide({ onStart, disabled, compact = false }: { onStart: () => void; disabled: boolean; compact?: boolean }) {
  return (
    <div className="flex flex-col items-center gap-0">
      {!compact && (
        <button type="button" onClick={onStart} disabled={disabled} aria-label="Start hands-free voice chat" className="relative w-[260px] h-[150px] disabled:opacity-60 group">
          <svg viewBox="0 0 260 150" className="iv-blob absolute inset-0 w-full h-full overflow-visible" aria-hidden="true">
            <defs>
              <radialGradient id="ivBlobFill" cx="50%" cy="40%" r="70%">
                <stop offset="0" stopColor="#5b6238" />
                <stop offset="0.55" stopColor="#3e4123" />
                <stop offset="1" stopColor="#2a2f1a" />
              </radialGradient>
              <filter id="ivBlobGlow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="9" /></filter>
            </defs>
            <path d="M70 30 C 84 8 120 2 146 12 C 170 20 186 8 210 22 C 238 38 250 66 240 92 C 232 116 214 132 186 138 C 156 145 132 132 104 140 C 72 149 34 140 18 116 C 2 92 14 70 32 58 C 48 48 56 44 70 30 Z" fill="rgba(157, 184, 124, 0.45)" filter="url(#ivBlobGlow)" />
            <path d="M70 30 C 84 8 120 2 146 12 C 170 20 186 8 210 22 C 238 38 250 66 240 92 C 232 116 214 132 186 138 C 156 145 132 132 104 140 C 72 149 34 140 18 116 C 2 92 14 70 32 58 C 48 48 56 44 70 30 Z" fill="url(#ivBlobFill)" stroke="#c9b683" strokeOpacity="0.75" strokeWidth="1.3" />
            <path d="M82 34 C 104 18 140 18 160 26 C 184 34 210 30 226 52" fill="none" stroke="rgba(255, 255, 240, 0.28)" strokeWidth="1" />
          </svg>
          <span className="absolute inset-0 flex items-center justify-center">
            <Icon name="graphic_eq" className="text-[42px] text-white group-hover:scale-110 transition-transform" />
          </span>
        </button>
      )}
      <button
        type="button"
        onClick={onStart}
        disabled={disabled}
        className="-mt-2 relative h-[58px] px-7 rounded-full flex items-center gap-3 text-[15.5px] text-white whitespace-nowrap transition-all hover:brightness-125 disabled:opacity-60"
        style={{ background: "rgba(32, 41, 23, 0.88)", border: "1px solid rgba(107, 111, 78, 0.9)", boxShadow: "0 10px 26px rgba(0,0,0,0.35)", backdropFilter: "blur(14px)", WebkitBackdropFilter: "blur(14px)" }}
      >
        <Icon name="mic" className="text-[24px]" />
        Switch to hands-free voice chat
      </button>
    </div>
  );
}

/** Bottom bar: press-to-speak mic, question box, language, send. */
export function Composer({ busy, recording, onSend, onStartRecording, onStopRecording }: {
  busy: boolean; recording: boolean; onSend: (q: string) => void; onStartRecording: () => void; onStopRecording: () => void;
}) {
  const [text, setText] = useState("");
  const pressRef = useRef<{ at: number; started: boolean }>({ at: 0, started: false });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    const t = text.trim();
    if (!t || busy) return;
    setText("");
    onSend(t);
  };
  // mic: hold to talk, or tap once to start and tap again to send
  const down = (e: ReactPointerEvent) => {
    if (e.button !== 0) return;
    (e.currentTarget as HTMLElement).setPointerCapture?.(e.pointerId);
    if (recording) { pressRef.current = { at: 0, started: false }; onStopRecording(); return; }
    if (busy) return;
    pressRef.current = { at: performance.now(), started: true };
    onStartRecording();
  };
  const up = () => {
    const p = pressRef.current;
    if (p.started && performance.now() - p.at > 350) onStopRecording();
    pressRef.current = { at: 0, started: false };
  };
  return (
    <form
      onSubmit={submit}
      className="w-full flex items-center gap-2 sm:gap-3 h-[76px] md:h-[88px] pl-3 md:pl-4 pr-3 rounded-[30px]"
      style={{ background: "linear-gradient(180deg, rgba(44, 42, 37, 0.82), rgba(30, 29, 26, 0.86))", border: `1.5px solid rgba(191, 152, 111, ${recording ? 0.95 : 0.7})`, boxShadow: recording ? "0 0 28px rgba(220, 170, 147, 0.35), 0 16px 40px rgba(0,0,0,0.4)" : "0 16px 40px rgba(0,0,0,0.4)", backdropFilter: "blur(18px)", WebkitBackdropFilter: "blur(18px)" }}
    >
      <button
        type="button"
        onPointerDown={down}
        onPointerUp={up}
        onPointerCancel={up}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); if (recording) onStopRecording(); else if (!busy) onStartRecording(); } }}
        disabled={busy && !recording}
        aria-pressed={recording}
        aria-label={recording ? "Release or tap to send" : "Press and hold to speak"}
        title="Hold to speak (or tap to start / stop)"
        className={`relative w-12 h-12 md:w-14 md:h-14 flex-shrink-0 rounded-full flex items-center justify-center text-white select-none touch-none transition-colors ${recording ? "" : "hover:bg-white/10"} disabled:opacity-50`}
        style={recording ? { background: "rgba(74, 55, 43, 0.95)", border: "2px solid #dcaa93", boxShadow: "0 0 18px rgba(220, 170, 147, 0.6)" } : undefined}
      >
        {recording && <span className="absolute inset-0 rounded-full animate-ping" style={{ background: "rgba(220, 170, 147, 0.25)" }} />}
        <Icon name={recording ? "stop" : "mic"} className="relative text-[28px]" />
      </button>
      <input
        value={text}
        onChange={(e) => setText(e.target.value)}
        maxLength={500}
        disabled={busy}
        aria-label="Type your question"
        placeholder={recording ? "Listening… release (or tap the mic) to send" : "Ask a follow-up question..."}
        className="flex-1 min-w-0 bg-transparent border-none outline-none text-[16px] md:text-[18px] text-white placeholder:text-white/55"
      />
      <LanguageMenu up className="hidden sm:block flex-shrink-0" />
      <button
        type="submit"
        disabled={busy || !text.trim()}
        aria-label="Send"
        className="w-14 h-14 md:w-[66px] md:h-[66px] flex-shrink-0 rounded-full flex items-center justify-center transition-all hover:brightness-110 active:scale-95 disabled:opacity-70"
        style={{ background: "#9eb07c", boxShadow: "0 0 0 1px rgba(255,255,255,0.15), 0 8px 22px rgba(158, 176, 124, 0.35)" }}
      >
        <Icon name="send" className="text-[26px]" style={{ color: "#2c3520", transform: "rotate(-30deg) translateX(1px)" }} />
      </button>
    </form>
  );
}
