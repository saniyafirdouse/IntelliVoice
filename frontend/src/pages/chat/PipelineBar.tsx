import { Fragment, type CSSProperties } from "react";
import { Icon } from "../../components/Icon";
import { STAGES, type Stage, type StageState } from "./useChat";

const LABELS: Record<Stage, string> = {
  speech: "Speech (Whisper)",
  language: "1. Language",
  understanding: "2. Understanding",
  knowledge: "3. Knowledge",
  memory: "4. Memory",
  response: "5. Response",
  voice: "Voice (Sarvam)",
};

const STYLE: Record<StageState, { chip: CSSProperties; dot: string; pulse: boolean }> = {
  idle: { chip: { background: "rgba(255,255,255,0.12)" }, dot: "bg-white/50", pulse: false },
  active: { chip: { background: "rgb(126, 130, 194)" }, dot: "bg-white", pulse: true },
  done: { chip: { background: "rgb(88, 92, 176)" }, dot: "bg-emerald-300", pulse: false },
  skipped: { chip: { background: "rgba(255,255,255,0.06)", opacity: 0.45 }, dot: "bg-white/30", pulse: false },
};

export function PipelineBar({ stages, elapsed }: { stages: Record<Stage, StageState>; elapsed: string }) {
  return (
    <div
      className="w-full flex flex-wrap items-center justify-between gap-space-md px-space-lg py-space-sm rounded-[2rem] sm:rounded-full shadow-[0_8px_32px_rgba(0,0,0,0.5)]"
      style={{ background: "rgba(18, 20, 20, 0.32)", backdropFilter: "blur(20px)", WebkitBackdropFilter: "blur(20px)", border: "1px solid rgba(255, 255, 255, 0.25)", textShadow: "rgba(0, 0, 0, 0.8) 0px 1px 3px" }}
    >
      <div className="flex items-center gap-space-sm flex-wrap">
        <span className="flex h-2.5 w-2.5 relative">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-secondary opacity-75" />
          <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-secondary" />
        </span>
        <span className="font-label-sm text-label-sm text-white/90 font-bold uppercase tracking-wider mr-1">6-Engine Pipeline:</span>
        <ol className="flex items-center gap-1.5 flex-wrap text-white font-label-sm text-label-sm" aria-label="Pipeline progress">
          {STAGES.map((s, i) => {
            const look = STYLE[stages[s]];
            return (
              <Fragment key={s}>
                {i > 0 && <span className="text-white/50" aria-hidden="true">→</span>}
                <li
                  data-stage={s}
                  data-state={stages[s]}
                  className={`px-2 py-0.5 rounded-full text-white font-semibold border border-white/20 flex items-center gap-1 transition-all duration-300 ${look.pulse ? "animate-pulse" : ""}`}
                  style={look.chip}
                >
                  <span className={`w-1.5 h-1.5 rounded-full ${look.dot}`} />
                  {LABELS[s]}
                </li>
              </Fragment>
            );
          })}
        </ol>
      </div>
      <div className="flex flex-wrap items-center gap-space-sm sm:gap-space-md">
        <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-black/40 backdrop-blur-md border border-white/20">
          <Icon name="database" className="text-[16px] text-secondary font-bold" />
          <span className="font-label-sm text-label-sm text-white font-medium">Source: SVIT Admissions Database</span>
        </div>
        <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-black/40 border border-white/20">
          <Icon name="schedule" className="text-[16px] text-secondary font-bold" />
          <span className="font-label-sm text-label-sm text-white font-semibold">Session Active: {elapsed}</span>
        </div>
      </div>
    </div>
  );
}
