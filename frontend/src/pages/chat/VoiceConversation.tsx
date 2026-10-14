// Full-screen hands-free conversation view (2026-10-13).
// Glowing ribbon "orb" in the site's lavender / violet, drawn on a canvas over the
// voice background image (public/assets/voice-bg.jpg). The orb emits a soft bloom:
// it breathes when idle, follows your voice while listening, swirls while
// thinking and pulses with IntelliVoice's voice while speaking.

import { useEffect, useRef, useState, type MutableRefObject } from "react";
import { Icon } from "../../components/Icon";
import type { ConversationPhase } from "./useVoiceConversation";

interface Props {
  phase: ConversationPhase;
  levelRef: MutableRefObject<number>;
  error: string | null;
  lastQuestion: string;
  lastReply: string;
  startedAt: number | null;
  turns: number;
  languageSummary: string;
  onTap: () => void;
  onEnd: () => void;
}

const LABELS: Record<ConversationPhase, { title: string; hint: string }> = {
  off: { title: "", hint: "" },
  starting: { title: "Starting…", hint: "Allow the microphone if your browser asks." },
  listening: { title: "Listening…", hint: "Speak in English, ಕನ್ನಡ or हिंदी. Pause when you're done." },
  thinking: { title: "Thinking…", hint: "Finding the answer in the SVIT admissions database." },
  speaking: { title: "Speaking…", hint: "Just start talking to interrupt — or tap the orb." },
  error: { title: "Something went wrong", hint: "" },
};

// Ribbon colours: the site's lavender / periwinkle / violet.
const RIBBONS = [
  { color: [191, 194, 255], width: 1.6, alpha: 0.85, speed: 0.35, lobes: [3, 5], phase: 0 },
  { color: [167, 139, 250], width: 1.3, alpha: 0.7, speed: -0.28, lobes: [4, 2], phase: 1.7 },
  { color: [132, 136, 232], width: 1.2, alpha: 0.65, speed: 0.22, lobes: [2, 6], phase: 3.1 },
  { color: [216, 180, 254], width: 1.0, alpha: 0.55, speed: -0.4, lobes: [5, 3], phase: 4.4 },
];
const STRANDS = 7;   // thin lines per ribbon -> the silky look

function Orb({ phase, levelRef, onTap }: { phase: ConversationPhase; levelRef: MutableRefObject<number>; onTap: () => void }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const phaseRef = useRef(phase);
  phaseRef.current = phase;

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;
    const reduced = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    let raf = 0;
    let smooth = 0;
    let swirl = 0;
    const start = performance.now();

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const { width, height } = canvas.getBoundingClientRect();
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    window.addEventListener("resize", resize);

    const draw = (now: number) => {
      const t = ((now - start) / 1000) * (reduced ? 0.3 : 1.45);   // a bit livelier than before
      const p = phaseRef.current;
      const target = p === "listening" || p === "speaking" ? levelRef.current : 0;
      smooth += (target - smooth) * 0.18;
      swirl += (p === "thinking" ? 0.04 : 0.011) * (reduced ? 0.3 : 1);

      const { width, height } = canvas.getBoundingClientRect();
      const cx = width / 2, cy = height / 2;
      const base = Math.min(width, height) * 0.25;
      ctx.clearRect(0, 0, width, height);

      // soft glow behind the ribbons
      const glow = ctx.createRadialGradient(cx, cy, base * 0.2, cx, cy, base * 1.9);
      const g = 0.18 + smooth * 0.35 + (p === "thinking" ? 0.08 * (1 + Math.sin(t * 3)) : 0);
      glow.addColorStop(0, `rgba(124, 58, 237, ${g})`);
      glow.addColorStop(0.55, `rgba(88, 92, 176, ${g * 0.45})`);
      glow.addColorStop(1, "rgba(0, 0, 0, 0)");
      ctx.fillStyle = glow;
      ctx.fillRect(0, 0, width, height);

      ctx.globalCompositeOperation = "lighter";
      // light it emits: a soft lavender bloom around the ring that brightens with the voice
      const bloomA = 0.16 + smooth * 0.34 + 0.04 * Math.sin(t * 1.6) + (p === "thinking" ? 0.06 * (1 + Math.sin(t * 3)) : 0);
      const bloom = ctx.createRadialGradient(cx, cy, base * 0.75, cx, cy, base * 2.0);
      bloom.addColorStop(0, `rgba(196, 181, 253, ${bloomA})`);
      bloom.addColorStop(0.35, `rgba(167, 139, 250, ${bloomA * 0.45})`);
      bloom.addColorStop(1, "rgba(124, 58, 237, 0)");
      ctx.fillStyle = bloom;
      ctx.fillRect(0, 0, width, height);
      // glowing rim under the ribbons
      ctx.beginPath();
      ctx.arc(cx, cy, base, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(167, 139, 250, ${0.22 + smooth * 0.3})`;
      ctx.lineWidth = base * 0.14;
      ctx.shadowColor = "rgba(196, 181, 253, 1)";
      ctx.shadowBlur = 40 + smooth * 40;
      ctx.stroke();
      ctx.shadowBlur = 0;

      // round when quiet, but always gently alive; swells and ripples with the voice
      const breath = 1 + 0.035 * Math.sin(t * 1.3) + smooth * 0.13;   // grows with the voice
      const amp = 0.035 + 0.015 * (1 + Math.sin(t * 1.7)) + smooth * 0.17 + (p === "thinking" ? 0.04 : 0);   // ripples, but stays round
      for (const r of RIBBONS) {
        for (let s = 0; s < STRANDS; s++) {
          const offset = (s - (STRANDS - 1) / 2) / STRANDS;
          ctx.beginPath();
          for (let i = 0; i <= 160; i++) {
            const a = (i / 160) * Math.PI * 2;
            const wobble =
              Math.sin(a * r.lobes[0] + t * r.speed * 2 + r.phase + swirl * 3 + offset * 0.9) * amp +
              Math.sin(a * r.lobes[1] - t * r.speed * 1.4 + r.phase * 0.5 + offset * 0.6) * amp * 0.55;
            const rad = base * breath * (1 + wobble + offset * 0.08);
            const x = cx + Math.cos(a + swirl) * rad;
            const y = cy + Math.sin(a + swirl) * rad;
            if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
          }
          const alpha = r.alpha * (1 - Math.abs(offset) * 1.4) * (0.7 + smooth * 0.6);
          ctx.strokeStyle = `rgba(${r.color[0]}, ${r.color[1]}, ${r.color[2]}, ${Math.max(0.05, alpha)})`;
          ctx.lineWidth = r.width;
          ctx.shadowColor = `rgba(${r.color[0]}, ${r.color[1]}, ${r.color[2]}, 0.9)`;
          ctx.shadowBlur = 14 + smooth * 24;
          ctx.stroke();
        }
      }
      ctx.globalCompositeOperation = "source-over";
      ctx.shadowBlur = 0;
      raf = requestAnimationFrame(draw);
    };
    raf = requestAnimationFrame(draw);
    return () => { cancelAnimationFrame(raf); window.removeEventListener("resize", resize); };
  }, [levelRef]);

  return (
    <button
      type="button"
      onClick={onTap}
      aria-label={phase === "speaking" ? "Interrupt" : phase === "listening" ? "Send now" : "Voice orb"}
      className="relative w-[min(92vw,54dvh,560px)] aspect-square rounded-full focus:outline-none focus-visible:ring-2 focus-visible:ring-secondary"
    >
      <canvas ref={canvasRef} className="absolute inset-0 w-full h-full" aria-hidden="true" />
    </button>
  );
}

function useClock(startedAt: number | null) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    if (!startedAt) return;
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [startedAt]);
  if (!startedAt) return "00:00:00";
  const s = Math.max(0, Math.floor((now - startedAt) / 1000));
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(Math.floor(s / 3600))}:${pad(Math.floor((s % 3600) / 60))}:${pad(s % 60)}`;
}

export function VoiceConversation({ phase, levelRef, error, lastQuestion, lastReply, startedAt, turns, languageSummary, onTap, onEnd }: Props) {
  const clock = useClock(startedAt);
  const label = LABELS[phase];

  // Esc ends the conversation.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onEnd(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onEnd]);

  if (phase === "off") return null;

  const caption = phase === "speaking" || (phase === "listening" && lastReply) ? lastReply : "";
  const showQuestion = !!lastQuestion && (phase === "thinking" || phase === "speaking");

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Voice conversation with IntelliVoice"
      className="fixed inset-0 z-[60] flex flex-col items-center justify-between text-white overflow-hidden"
      style={{ background: "#12111c" }}
    >
      {/* Background image with a slow camera-like drift + a faint moving shimmer (2026-10-13). */}
      <style>{`
        @keyframes iv-bg-drift { 0% { transform: scale(1.06) translate(-1.6%, -1.1%); } 100% { transform: scale(1.14) translate(1.6%, 1.1%); } }
        @keyframes iv-bg-shimmer { 0% { opacity: 0.35; transform: translate(-6%, 2%); } 50% { opacity: 0.75; } 100% { opacity: 0.35; transform: translate(6%, -2%); } }
        @media (prefers-reduced-motion: reduce) { .iv-bg-drift, .iv-bg-shimmer { animation: none !important; } }
      `}</style>
      <div className="absolute inset-0 -z-10 pointer-events-none" aria-hidden="true">
        <div
          className="iv-bg-drift absolute inset-0 bg-cover bg-center"
          style={{ backgroundImage: 'url("/assets/voice-bg.jpg")', animation: "iv-bg-drift 38s ease-in-out infinite alternate", willChange: "transform" }}
        />
        <div
          className="iv-bg-shimmer absolute -inset-[10%]"
          style={{ background: "radial-gradient(40% 30% at 30% 40%, rgba(167, 139, 250, 0.16), transparent 70%), radial-gradient(35% 28% at 72% 58%, rgba(216, 180, 254, 0.12), transparent 70%)", animation: "iv-bg-shimmer 16s ease-in-out infinite alternate", willChange: "transform, opacity" }}
        />
        <div className="absolute inset-0" style={{ background: "rgba(10, 10, 20, 0.18)" }} />
      </div>
      {/* top bar */}
      <div className="w-full max-w-3xl flex items-center justify-between px-6 pt-6">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/10 border border-white/20 font-label-md text-label-md" style={{ textShadow: "rgba(0,0,0,0.7) 0 1px 3px" }}>
          <span className="relative flex w-2.5 h-2.5">
            <span className={`absolute inset-0 rounded-full bg-secondary ${phase === "listening" ? "animate-ping" : ""}`} />
            <span className="relative w-2.5 h-2.5 rounded-full bg-secondary" />
          </span>
          IntelliVoice · Voice conversation
        </div>
        <div className="flex items-center gap-3">
          {turns > 0 && (
            <span className="hidden sm:flex items-center gap-1 px-3 py-1.5 rounded-full bg-white/10 border border-white/20 font-label-md text-label-md text-white/85">
              <Icon name="forum" className="text-[16px]" />
              {turns} {turns === 1 ? "question" : "questions"} saved to chat
            </span>
          )}
          <span className="font-label-md text-label-md text-secondary tabular-nums" aria-label="Conversation time">{clock}</span>
        </div>
      </div>

      {/* orb + captions */}
      <div className="flex flex-col items-center gap-4 px-6 w-full max-w-3xl">
        <Orb phase={phase} levelRef={levelRef} onTap={onTap} />
        <div className="flex flex-col items-center gap-2 text-center min-h-[150px]" aria-live="polite" style={{ textShadow: "rgba(0,0,0,0.75) 0 1px 4px" }}>
          <p className="font-headline-md text-headline-md font-bold">{error ? "Sorry…" : label.title}</p>
          <p className="font-body-md text-body-md text-white/75">{error || label.hint}</p>
          {showQuestion && (
            <p className="mt-2 font-body-md text-body-md text-secondary max-w-xl line-clamp-2">“{lastQuestion}”</p>
          )}
          {caption && (
            <p className="mt-1 font-title-md text-title-md text-white/95 max-w-2xl line-clamp-3 leading-relaxed">{caption}</p>
          )}
        </div>
      </div>

      {/* controls */}
      <div className="w-full max-w-md flex items-center justify-between px-8 pb-10">
        <span className="w-12 h-12 rounded-full flex items-center justify-center bg-white/10 border border-white/20" title={languageSummary} aria-label={languageSummary}>
          <Icon name="translate" className="text-[22px]" />
        </span>
        <button
          type="button"
          onClick={onTap}
          disabled={phase !== "speaking" && phase !== "listening"}
          aria-label={phase === "speaking" ? "Interrupt and ask" : "Send what I said now"}
          className="w-[76px] h-[76px] rounded-full flex items-center justify-center transition-transform hover:scale-105 active:scale-95 disabled:opacity-60"
          style={{ background: "linear-gradient(135deg, rgb(109, 40, 217), rgb(79, 70, 229))", border: "2.5px solid rgba(255,255,255,0.6)", boxShadow: "rgba(124, 58, 237, 0.8) 0 0 40px, rgba(255,255,255,0.35) 0 0 14px" }}
        >
          <Icon name={phase === "speaking" ? "stop" : phase === "thinking" ? "progress_activity" : "mic"} className={`text-[32px] ${phase === "thinking" ? "animate-spin" : ""}`} />
        </button>
        <button
          type="button"
          onClick={onEnd}
          aria-label="End conversation"
          className="w-12 h-12 rounded-full flex items-center justify-center bg-red-500/25 border border-red-300/50 hover:bg-red-500/40 transition-colors"
        >
          <Icon name="close" className="text-[24px]" />
        </button>
      </div>
    </div>
  );
}
