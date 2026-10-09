import { useState, type FormEvent } from "react";
import { Icon } from "../../components/Icon";

const IDLE_BARS = [0.38, 0.85, 1, 0.6, 0.3];
const BAR_TONES = ["bg-secondary", "bg-secondary-fixed", "bg-secondary", "bg-secondary-fixed-dim", "bg-secondary"];

interface Props {
  languageSummary: string;
  recording: boolean;
  levels: number[];
  busy: boolean;
  status: { text: string; icon: string };
  onMic: () => void;
  onSend: (text: string) => void;
}

/** Status strip + big mic button + text input at the bottom of the chat card. */
export function MicDock({ languageSummary, recording, levels, busy, status, onMic, onSend }: Props) {
  const [text, setText] = useState("");

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const t = text.trim();
    if (!t || busy) return;
    setText("");
    onSend(t);
  };

  return (
    <>
      <div
        className="w-full rounded-3xl px-space-lg py-2.5 flex flex-wrap items-center justify-between gap-space-sm shadow-[0_8px_32px_rgba(0,0,0,0.5)]"
        style={{ background: "linear-gradient(90deg, rgba(24, 18, 48, 0.3), rgba(20, 24, 44, 0.28))", backdropFilter: "blur(20px)", border: "1px solid rgba(191, 194, 255, 0.3)", boxShadow: "rgba(0, 0, 0, 0.35) 0px 8px 24px, rgba(168, 85, 247, 0.12) 0px 0px 16px" }}
      >
        <div className="flex items-center gap-space-sm min-w-0" aria-live="polite">
          <Icon name={status.icon} className={`text-[20px] text-secondary flex-shrink-0 font-bold ${status.icon === "progress_activity" ? "animate-spin" : ""}`} />
          <div className="flex items-center gap-2 truncate">
            <span className="font-label-sm text-label-sm text-secondary uppercase font-bold tracking-wider">Status:</span>
            <span className="font-body-md text-body-md text-white font-medium italic truncate">{status.text}</span>
          </div>
        </div>
        <div className="flex items-center gap-space-sm min-w-0">
          <span className="px-2.5 py-0.5 rounded-2xl text-white font-label-sm text-label-sm font-bold flex items-center gap-1 shadow-sm" style={{ backgroundColor: "rgb(88, 92, 176)", border: "1px solid rgba(255, 255, 255, 0.3)" }}>
            <Icon name="graphic_eq" className="text-[14px] font-bold" />
            Sarvam AI Bulbul: Ritu (English) · Simran (Hindi) · Rupa (Kannada)
          </span>
        </div>
      </div>

      <div
        className="w-full p-space-md rounded-2xl shadow-[0_16px_48px_rgba(0,0,0,0.6)] flex flex-col md:flex-row items-center justify-between gap-space-lg"
        style={{ background: "linear-gradient(135deg, rgba(22, 16, 44, 0.32), rgba(30, 24, 58, 0.28))", backdropFilter: "blur(24px)", border: "1px solid rgba(191, 194, 255, 0.32)", boxShadow: "rgba(0, 0, 0, 0.45) 0px 16px 48px, rgba(124, 58, 237, 0.15) 0px 0px 32px" }}
      >
        <div className={`flex items-end gap-1.5 h-10 px-space-sm flex-shrink-0 transition-opacity ${recording ? "" : "opacity-30"}`} title="Microphone level" aria-hidden="true">
          {IDLE_BARS.map((idle, i) => (
            <div
              key={i}
              className={`w-1.5 rounded-full ${BAR_TONES[i]} transition-[height] duration-75`}
              style={{ height: `${Math.round((recording ? Math.max(0.15, Math.min(1, (levels[i] ?? 0) * 1.6)) : idle) * 100)}%` }}
            />
          ))}
        </div>

        <div className="flex flex-col items-center gap-space-xs flex-1 text-center">
          <div className="relative flex items-center justify-center">
            <div className={`absolute w-24 h-24 rounded-full bg-secondary/20 pointer-events-none ${recording ? "animate-ping" : ""}`} />
            <div className="absolute w-20 h-20 rounded-full bg-secondary/40 blur-md pointer-events-none" />
            <button
              type="button"
              onClick={onMic}
              disabled={busy && !recording}
              aria-label={recording ? "Stop recording and send" : "Tap to speak your question"}
              aria-pressed={recording}
              className={`relative z-10 w-[72px] h-[72px] rounded-full text-white flex items-center justify-center hover:scale-105 active:scale-95 transition-all duration-200 disabled:opacity-60 ${recording ? "scale-110" : ""}`}
              style={{
                background: recording ? "linear-gradient(135deg, rgb(220, 38, 38), rgb(185, 28, 28))" : "linear-gradient(135deg, rgb(109, 40, 217), rgb(79, 70, 229))",
                boxShadow: "rgba(124, 58, 237, 0.8) 0px 0px 40px, rgba(255, 255, 255, 0.4) 0px 0px 15px",
                border: "2.5px solid rgba(255, 255, 255, 0.6)",
              }}
            >
              <Icon name={recording ? "stop" : "mic"} className="text-[36px] font-bold" filled />
            </button>
          </div>
          <div className="flex flex-col items-center">
            <span className="font-title-md text-title-md text-white font-bold">{recording ? "Listening… tap again to send" : "Tap to speak"}</span>
            <span className="font-label-sm text-label-sm text-white/90 font-medium hidden sm:flex items-center gap-1">
              or hold <kbd className="px-1.5 py-0.5 rounded bg-black/60 font-mono text-[10px] text-secondary border border-white/20 font-bold">SPACEBAR</kbd> to stream Kannada, Hindi or English
            </span>
            <button
              type="button"
              title="Change language"
              onClick={() => {
                const el = document.getElementById("speech-lang");
                el?.scrollIntoView({ behavior: "smooth", block: "center" });
                el?.focus({ preventScroll: true });
              }}
              className="mt-1 px-2.5 py-0.5 rounded-full font-label-sm text-label-sm text-secondary font-semibold flex items-center gap-1 hover:bg-white/10 underline-offset-2 hover:underline"
            >
              <Icon name="translate" className="text-[14px]" />
              {languageSummary}
              <Icon name="edit" className="text-[13px]" />
            </button>
          </div>
        </div>

        <form onSubmit={submit} className="w-full md:w-80 flex items-center gap-space-xs bg-black/50 border border-white/25 px-space-md py-2 rounded-full focus-within:ring-2 focus-within:ring-secondary/60 transition-all">
          <input
            value={text}
            onChange={(e) => setText(e.target.value)}
            maxLength={500}
            disabled={busy}
            aria-label="Type your question"
            placeholder="Type query in any language..."
            className="bg-transparent border-none outline-none font-body-sm text-body-sm text-white placeholder:text-white/60 font-medium w-full min-w-0"
          />
          <div className="flex items-center gap-1 flex-shrink-0">
            <span className="px-1.5 py-0.5 rounded bg-white/20 font-mono text-[10px] text-white font-bold hidden lg:inline">↵</span>
            <button type="submit" disabled={busy || !text.trim()} aria-label="Send message" className="w-8 h-8 rounded-full text-white flex items-center justify-center hover:scale-105 active:scale-95 transition-all disabled:opacity-60" style={{ backgroundColor: "rgb(88, 92, 176)", border: "1px solid rgba(255, 255, 255, 0.35)" }}>
              <Icon name="arrow_upward" className="text-[18px] font-bold" />
            </button>
          </div>
        </form>
      </div>
    </>
  );
}
