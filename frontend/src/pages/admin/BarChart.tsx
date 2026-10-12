// Charts for the admin dashboard, drawn with plain HTML/SVG (no chart library needed).
//
// Colours: one soft palette that suits the purple glass + sunset campus photo. It was
// checked for colour-blind separation and contrast on the dark glass, and every chart
// also writes its labels and numbers in text, so colour is never the only clue.
// Hovering or focusing any bar / slice shows its exact value.

import { useState, type ReactNode } from "react";
import { Icon } from "../../components/Icon";

/** The dashboard palette (use these by name, so a thing keeps its colour everywhere). */
export const VIZ = {
  periwinkle: "#8488e8",
  coral: "#ce7b5c",
  teal: "#29aa96",
  amber: "#b68d27",
  rose: "#cb739d",
  sky: "#549ad4",
  sage: "#79a25b",
  lilac: "#a57fd1",
  muted: "#7c7a96",
} as const;

/** Fixed order for lists of different things (topics etc.). */
export const SERIES = [VIZ.periwinkle, VIZ.coral, VIZ.teal, VIZ.amber, VIZ.rose, VIZ.sky, VIZ.sage, VIZ.lilac];

export interface BarDatum { key: string; label: string; value: number; tooltip?: string; color?: string; icon?: string; help?: string }

const fmt = (n: number) => n.toLocaleString("en-IN");
const pctOf = (n: number, total: number) => (total ? Math.round((n / total) * 100) : 0);
/** Bar fill: the colour, slightly lighter at the top so it reads as glass, not a flat block. */
const barFill = (c: string) => `linear-gradient(to top, ${c}d9, ${c})`;

const TOOLTIP = "absolute z-10 whitespace-nowrap rounded px-2.5 py-1.5 bg-black/75 backdrop-blur-md border border-white/20 font-body-sm text-body-sm text-white shadow-lg pointer-events-none";

/**
 * Vertical bars: good for time (days, hours).
 * - `markPeak` labels the highest bar and gives it the accent colour.
 * - `showAverage` draws a dashed average line.
 * - `heat` shades each bar by its size (light = few, strong = many) in one colour.
 */
export function ColumnChart({ data, height = 160, unit = "questions", labelEvery = 1, ariaLabel, color = VIZ.periwinkle, peakColor, markPeak = false, showAverage = false, heat = false }: {
  data: BarDatum[]; height?: number; unit?: string; labelEvery?: number; ariaLabel: string;
  color?: string; peakColor?: string; markPeak?: boolean; showAverage?: boolean; heat?: boolean;
}) {
  const [hover, setHover] = useState<number | null>(null);
  const max = Math.max(1, ...data.map((d) => d.value));
  const ticks = niceTicks(max);
  const top = ticks[ticks.length - 1];
  const peakIndex = data.reduce((best, d, i) => (d.value > data[best].value ? i : best), 0);
  const avg = data.length ? data.reduce((s, d) => s + d.value, 0) / data.length : 0;

  return (
    <figure className="flex flex-col gap-2" aria-label={ariaLabel}>
      <div className="relative flex gap-2" style={{ height }}>
        {/* y axis labels + recessive grid */}
        <div className="flex flex-col justify-between text-right font-body-sm text-[11px] text-white/65 tabular-nums w-8 flex-shrink-0">
          {[...ticks].reverse().map((t) => <span key={t} className="leading-none">{t}</span>)}
        </div>
        <div className="relative flex-1 min-w-0">
          {ticks.map((t) => (
            <div key={t} className="absolute left-0 right-0 border-t border-white/10" style={{ bottom: `${(t / top) * 100}%` }} />
          ))}
          <div className="absolute inset-0 flex items-end gap-[3px]">
            {data.map((d, i) => {
              const pct = (d.value / top) * 100;
              const on = hover === i;
              const isPeak = markPeak && i === peakIndex && d.value > 0;
              const strength = heat ? 0.3 + 0.7 * (d.value / max) : 1;
              const c = isPeak && peakColor ? peakColor : d.color ?? color;
              return (
                <button
                  key={d.key}
                  type="button"
                  className="relative flex-1 h-full flex items-end focus:outline-none"
                  onMouseEnter={() => setHover(i)}
                  onMouseLeave={() => setHover(null)}
                  onFocus={() => setHover(i)}
                  onBlur={() => setHover(null)}
                  aria-label={`${d.tooltip ?? d.label}: ${d.value} ${unit}`}
                >
                  <span
                    className="w-full rounded-t-[4px] transition-all"
                    style={{
                      height: `${pct}%`,
                      minHeight: d.value > 0 ? 3 : 0,
                      background: barFill(c),
                      opacity: (hover === null || on ? 1 : 0.55) * strength,
                      boxShadow: on || isPeak ? `0 0 18px ${c}66` : undefined,
                    }}
                  />
                  {isPeak && !on && (
                    <span className="absolute left-1/2 -translate-x-1/2 mb-1 whitespace-nowrap font-label-md text-label-md text-white font-bold tabular-nums" style={{ bottom: `${pct}%` }}>
                      {fmt(d.value)} <span className="font-normal text-white/75">peak</span>
                    </span>
                  )}
                  {on && (
                    <span className={`${TOOLTIP} mb-1 left-1/2 -translate-x-1/2`} style={{ bottom: `${pct}%` }}>
                      <strong className="tabular-nums">{fmt(d.value)}</strong> {unit}
                      <span className="block text-white/70">{d.tooltip ?? d.label}</span>
                    </span>
                  )}
                </button>
              );
            })}
          </div>
          {showAverage && avg > 0 && (
            <div className="absolute left-0 right-0 border-t border-dashed border-white/60 pointer-events-none" style={{ bottom: `${(avg / top) * 100}%` }} aria-hidden="true" />
          )}
        </div>
      </div>
      {/* x axis labels */}
      <div className="flex gap-2">
        <div className="w-8 flex-shrink-0" />
        <div className="flex-1 min-w-0 flex gap-[3px] font-body-sm text-[11px] text-white/70">
          {data.map((d, i) => (
            <span key={d.key} className="flex-1 relative h-4">
              {i % labelEvery === 0 && <span className="absolute left-1/2 -translate-x-1/2 whitespace-nowrap">{d.label}</span>}
            </span>
          ))}
        </div>
      </div>
      {showAverage && avg > 0 && (
        <p className="flex items-center gap-2 pl-10 font-body-sm text-body-sm text-white/80">
          <span className="inline-block w-6 border-t border-dashed border-white/70" aria-hidden="true" />
          Average: <strong className="text-white tabular-nums">{Math.round(avg)}</strong> {unit} a day
        </p>
      )}
    </figure>
  );
}

/** Horizontal bars: good for ranked categories. Each row has its own colour dot + bar; numbers are written out. */
export function RankedBars({ data, unit = "questions", total }: { data: BarDatum[]; unit?: string; total?: number }) {
  const max = Math.max(1, ...data.map((d) => d.value));
  return (
    <ul className="flex flex-col gap-3">
      {data.map((d, i) => {
        const c = d.color ?? SERIES[i] ?? VIZ.muted;
        return (
          <li key={d.key} className="flex flex-col gap-1.5" title={`${d.label}: ${d.value} ${unit}`}>
            <div className="flex items-baseline justify-between gap-2 font-body-md text-body-md">
              <span className="text-white/90 truncate flex items-center gap-2">
                <span className="inline-block w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: c }} aria-hidden="true" />
                {d.label}
              </span>
              <span className="text-white tabular-nums font-semibold flex-shrink-0">
                {fmt(d.value)}
                {total ? <span className="text-white/70 font-normal"> · {pctOf(d.value, total)}%</span> : null}
              </span>
            </div>
            <div className="h-2.5 rounded-full bg-white/10 overflow-hidden">
              <div className="h-full rounded-full" style={{ width: `${(d.value / max) * 100}%`, background: `linear-gradient(to right, ${c}b3, ${c})`, minWidth: d.value > 0 ? 6 : 0 }} />
            </div>
          </li>
        );
      })}
    </ul>
  );
}

/**
 * Donut chart with a legend beside it. The centre shows the total, or the slice you hover.
 * Good for "parts of a whole" with a few parts (2–5).
 */
export function DonutChart({ data, centerLabel, unit = "questions", size = 168, legendExtra, stacked = false }: {
  data: BarDatum[]; centerLabel: string; unit?: string; size?: number; legendExtra?: ReactNode;
  /** donut on top with a 2-column legend underneath (for narrow cards) */
  stacked?: boolean;
}) {
  const [hover, setHover] = useState<number | null>(null);
  const total = data.reduce((s, d) => s + d.value, 0);
  const stroke = 22;
  const r = (size - stroke) / 2 - 4;
  const C = 2 * Math.PI * r;
  const gap = data.filter((d) => d.value > 0).length > 1 ? 3 : 0; // small gap between slices
  let offset = 0;
  const shown = hover !== null ? data[hover] : null;

  return (
    <figure className={`flex flex-col items-center gap-space-lg ${stacked ? "" : "sm:flex-row"}`} aria-label={`${centerLabel}: ${data.map((d) => `${d.label} ${d.value}`).join(", ")}`}>
      <div className="relative flex-shrink-0" style={{ width: size, height: size }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90">
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth={stroke} />
          {data.map((d, i) => {
            const c = d.color ?? SERIES[i];
            const len = total ? (d.value / total) * C : 0;
            const seg = Math.max(0, len - gap);
            const el = len > 0 && (
              <circle
                key={d.key}
                cx={size / 2}
                cy={size / 2}
                r={r}
                fill="none"
                stroke={c}
                strokeWidth={hover === i ? stroke + 6 : stroke}
                strokeDasharray={`${seg} ${C - seg}`}
                strokeDashoffset={-offset}
                style={{ transition: "stroke-width 150ms, opacity 150ms", opacity: hover === null || hover === i ? 1 : 0.4, cursor: "pointer", filter: hover === i ? `drop-shadow(0 0 8px ${c}aa)` : undefined }}
                onMouseEnter={() => setHover(i)}
                onMouseLeave={() => setHover(null)}
              />
            );
            offset += len;
            return el;
          })}
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center pointer-events-none px-6">
          <span className="font-headline-md text-headline-md text-white font-bold tabular-nums leading-none">
            {shown ? `${pctOf(shown.value, total)}%` : fmt(total)}
          </span>
          <span className="mt-1 font-body-sm text-body-sm text-white/75 leading-tight">{shown ? shown.label : centerLabel}</span>
        </div>
      </div>

      <ul className={`flex-1 min-w-0 w-full ${stacked ? "grid grid-cols-2 gap-1" : "flex flex-col gap-2"}`}>
        {data.map((d, i) => {
          const c = d.color ?? SERIES[i];
          if (stacked) return (
            <li key={d.key}>
              <button
                type="button"
                title={d.help}
                className={`w-full flex items-start gap-2 rounded px-2 py-1.5 text-left transition-colors ${hover === i ? "bg-white/10" : ""}`}
                onMouseEnter={() => setHover(i)}
                onMouseLeave={() => setHover(null)}
                onFocus={() => setHover(i)}
                onBlur={() => setHover(null)}
                aria-label={`${d.label}: ${d.value} ${unit}, ${pctOf(d.value, total)}%`}
              >
                {d.icon
                  ? <Icon name={d.icon} filled className="text-[20px] flex-shrink-0 mt-px" style={{ color: c }} />
                  : <span className="w-3 h-3 mt-1 rounded-full flex-shrink-0" style={{ background: c }} aria-hidden="true" />}
                <span className="min-w-0 flex flex-col">
                  <span className="font-label-lg text-label-lg text-white truncate">{d.label}</span>
                  <span className="font-title-md text-title-md text-white font-bold tabular-nums">
                    {fmt(d.value)} <span className="font-body-sm text-body-sm text-white/70 font-normal">· {pctOf(d.value, total)}%</span>
                  </span>
                </span>
              </button>
            </li>
          );
          return (
            <li key={d.key}>
              <button
                type="button"
                className={`w-full flex items-center gap-2.5 rounded px-2 py-1.5 text-left transition-colors ${hover === i ? "bg-white/10" : ""}`}
                onMouseEnter={() => setHover(i)}
                onMouseLeave={() => setHover(null)}
                onFocus={() => setHover(i)}
                onBlur={() => setHover(null)}
                aria-label={`${d.label}: ${d.value} ${unit}, ${pctOf(d.value, total)}%`}
              >
                {d.icon
                  ? <Icon name={d.icon} filled className="text-[20px] flex-shrink-0" style={{ color: c }} />
                  : <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ background: c }} aria-hidden="true" />}
                <span className="flex-1 min-w-0 flex flex-col">
                  <span className="font-label-lg text-label-lg text-white">{d.label}</span>
                  {d.help && <span className="font-body-sm text-body-sm text-white/65 truncate">{d.help}</span>}
                </span>
                <span className="font-title-md text-title-md text-white tabular-nums flex-shrink-0">
                  {fmt(d.value)} <span className="font-body-sm text-body-sm text-white/65">· {pctOf(d.value, total)}%</span>
                </span>
              </button>
            </li>
          );
        })}
        {legendExtra}
      </ul>
    </figure>
  );
}

/** One bar split into parts (e.g. voice vs typed), with the parts named underneath. */
export function SplitBar({ data, unit = "questions" }: { data: BarDatum[]; unit?: string }) {
  const total = data.reduce((s, d) => s + d.value, 0);
  return (
    <div className="flex flex-col gap-3">
      <div className="flex h-4 rounded-full overflow-hidden gap-[3px] bg-white/5" role="img" aria-label={data.map((d) => `${d.label} ${pctOf(d.value, total)}%`).join(", ")}>
        {data.map((d, i) => d.value > 0 && (
          <div key={d.key} title={`${d.label}: ${fmt(d.value)} ${unit}`} className="h-full first:rounded-l-full last:rounded-r-full" style={{ width: `${(d.value / (total || 1)) * 100}%`, background: barFill(d.color ?? SERIES[i]) }} />
        ))}
      </div>
      <div className="flex flex-wrap justify-between gap-x-space-lg gap-y-2">
        {data.map((d, i) => (
          <div key={d.key} className="flex items-center gap-2">
            {d.icon
              ? <Icon name={d.icon} filled className="text-[20px]" style={{ color: d.color ?? SERIES[i] }} />
              : <span className="w-3 h-3 rounded-full" style={{ background: d.color ?? SERIES[i] }} aria-hidden="true" />}
            <span className="font-label-lg text-label-lg text-white">{d.label}</span>
            <span className="font-title-md text-title-md text-white font-bold tabular-nums">{pctOf(d.value, total)}%</span>
            <span className="font-body-sm text-body-sm text-white/65 tabular-nums">({fmt(d.value)})</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function niceTicks(max: number): number[] {
  if (max <= 4) return [0, 1, 2, 3, 4].slice(0, Math.max(2, max + 1));
  const raw = max / 4;
  const pow = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 5, 10].map((m) => m * pow).find((s) => s >= raw) ?? raw;
  const out: number[] = [];
  for (let v = 0; v <= max + step - 1e-9; v += step) out.push(Math.round(v));
  return out;
}
