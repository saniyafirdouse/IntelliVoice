// Admin "System health" (2026-11-01): is IntelliVoice working right now?
// Service status (green / red), time per step over the last questions, and recent
// problems. Refreshes every 10 seconds. Reads the question logs only, so looking
// at this page never uses Groq or Sarvam credits.
import { useCallback, useEffect, useState } from "react";
import { Icon } from "../../components/Icon";
import { useAuth } from "../../context/AuthContext";
import { ApiError } from "../../lib/api";
import { adminApi, formatWhen, type HealthService, type SystemHealth } from "../../lib/adminApi";
import { Button, Card, Loading, Notice, PageTitle, StatTile } from "./AdminUi";

const GOOD = "#5fd3a5", BAD = "#ff8a80", UNKNOWN = "#b8b8c8", WARN = "#f5c26b";

const secs = (ms: number | null | undefined) => (ms == null ? "—" : `${(ms / 1000).toFixed(1)} s`);

function ServiceCard({ name, icon, service }: { name: string; icon: string; service: HealthService }) {
  const color = service.ok === true ? GOOD : service.ok === false ? BAD : UNKNOWN;
  const word = service.ok === true ? "Working" : service.ok === false ? "Problem" : "No data yet";
  return (
    <div className="rounded-lg p-space-md flex gap-3 items-start" style={{ background: "rgba(18, 16, 30, 0.55)", border: `1px solid ${color}66` }}>
      <span className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0" style={{ background: `${color}22`, border: `1px solid ${color}88` }}>
        <Icon name={icon} className="text-[22px]" style={{ color }} />
      </span>
      <div className="min-w-0">
        <p className="text-white font-semibold flex items-center gap-2">
          {name}
          <span className="inline-flex items-center gap-1 text-[12px] font-semibold px-2 py-0.5 rounded-full" style={{ background: `${color}22`, color }}>
            <span className="w-1.5 h-1.5 rounded-full" style={{ background: color }} />{word}
          </span>
        </p>
        <p className="mt-1 text-[13px] text-white/80 break-words">{service.detail}</p>
      </div>
    </div>
  );
}

export default function AdminHealthPage() {
  const { token } = useAuth();
  const [data, setData] = useState<SystemHealth | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!token) return;
    try {
      setData(await adminApi.health(token));
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't reach the backend — it may be stopped.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void load();
    const id = window.setInterval(() => void load(), 10_000);
    return () => window.clearInterval(id);
  }, [load]);

  const [switching, setSwitching] = useState(false);
  const togglePhones = async () => {
    if (!token || !data) return;
    setSwitching(true);
    try {
      await adminApi.setPhoneAccess(token, !data.phones.paused);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't change phone access.");
    } finally {
      setSwitching(false);
    }
  };

  const steps = data?.speed.steps.filter((s) => s.count > 0) ?? [];
  const maxMs = Math.max(1, ...steps.map((s) => s.p90_ms ?? s.avg_ms ?? 0));

  return (
    <div className="flex flex-col gap-space-lg">
      <PageTitle
        title="System health"
        subtitle={data ? `Is everything working right now? Updates every 10 seconds · last check ${formatWhen(data.checked_at)}` : "Is everything working right now? Updates every 10 seconds."}
        actions={<Button icon="refresh" onClick={() => void load()}>Check now</Button>}
      />
      {error && <Notice kind="error">{error}</Notice>}
      {loading && !data && <Loading label="Checking the services…" />}

      {data && (
        <>
          <Card title="Services" icon="hub" subtitle="Green = working. Red = needs attention.">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-space-md">
              <ServiceCard name="Backend" icon="dns" service={data.services.backend} />
              <ServiceCard name="Database (MongoDB)" icon="database" service={data.services.database} />
              <ServiceCard name="Answers (Groq)" icon="psychology" service={data.services.groq} />
              <ServiceCard name="Voice (Sarvam)" icon="record_voice_over" service={data.services.sarvam} />
            </div>
          </Card>

          {/* 2026-11-01: visitors on their own phones (through the Cloudflare tunnel) */}
          <Card title="Visitor phones" icon="smartphone" subtitle="Phones that opened Eva through the expo QR code. The stall laptop is never paused or limited.">
            <div className="flex flex-wrap items-center justify-between gap-space-md">
              <div className="flex flex-col gap-1">
                <p className="text-white font-semibold flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full" style={{ background: data.phones.paused ? BAD : GOOD }} />
                  {data.phones.paused ? "Paused — phones see \"please use the laptop at the stall\"" : "Open to visitors"}
                </p>
                <p className="text-[13px] text-white/75">
                  {data.phones.questions_last_hour} of {data.phones.hourly_cap} phone questions used this hour · each phone: 10 questions per 5 minutes
                </p>
                <span className="block h-1.5 w-64 max-w-full rounded-full bg-white/10 overflow-hidden">
                  <span className="block h-full rounded-full" style={{ width: `${Math.min(100, (data.phones.questions_last_hour / Math.max(1, data.phones.hourly_cap)) * 100)}%`, background: data.phones.questions_last_hour >= data.phones.hourly_cap ? BAD : WARN }} />
                </span>
              </div>
              <Button kind={data.phones.paused ? "success" : "danger"} icon={data.phones.paused ? "play_arrow" : "pause"} busy={switching} onClick={() => void togglePhones()}>
                {data.phones.paused ? "Resume phone access" : "Pause phone access"}
              </Button>
            </div>
          </Card>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-space-md">
            <StatTile label="Questions (last hour)" value={String(data.last_hour.questions)} icon="forum" />
            <StatTile label="Failed replies" value={String(data.last_hour.failed_replies)} icon="error" tone={data.last_hour.failed_replies ? BAD : GOOD} />
            <StatTile label="Voice failed" value={String(data.last_hour.voice_failed)} icon="volume_off" tone={data.last_hour.voice_failed ? WARN : GOOD} hint="reply shown, not spoken" />
            <StatTile label={'"Couldn\'t hear you"'} value={String(data.last_hour.could_not_hear)} icon="hearing_disabled" tone={WARN} hint="noise / unclear speech" />
          </div>

          <Card title="Time per step" icon="timer" subtitle={data.speed.questions ? `Last ${data.speed.questions} questions · whole reply: average ${secs(data.speed.avg_total_ms)}, 9 in 10 within ${secs(data.speed.p90_total_ms)}` : "No timed questions yet — ask Eva something."}>
            {steps.length === 0 ? (
              <p className="text-white/75">Times appear here after the first questions.</p>
            ) : (
              <div className="flex flex-col gap-3">
                {steps.map((s) => (
                  <div key={s.label} className="grid grid-cols-[minmax(0,170px)_1fr_auto] items-center gap-3">
                    <span className="text-[13.5px] text-white/90 truncate" title={s.label}>{s.label}</span>
                    <span className="relative h-3 rounded-full bg-white/10 overflow-hidden" title={`average ${secs(s.avg_ms)} · 9 in 10 within ${secs(s.p90_ms)}`}>
                      <span className="absolute inset-y-0 left-0 rounded-full" style={{ width: `${((s.p90_ms ?? 0) / maxMs) * 100}%`, background: "rgba(191, 194, 255, 0.35)" }} />
                      <span className="absolute inset-y-0 left-0 rounded-full" style={{ width: `${((s.avg_ms ?? 0) / maxMs) * 100}%`, background: "#bfc2ff" }} />
                    </span>
                    <span className="text-[13px] text-white tabular-nums whitespace-nowrap">{secs(s.avg_ms)} <span className="text-white/55">· {secs(s.p90_ms)}</span></span>
                  </div>
                ))}
                <p className="text-[12px] text-white/60">Dark bar = average time; light bar = 9 out of 10 questions are faster than this. Kannada steps only appear for Kannada replies.</p>
              </div>
            )}
          </Card>

          <Card title="Recent problems" icon="report" subtitle="Since the backend started (key switches, failed replies, failed voice).">
            {data.problems.length === 0 ? (
              <p className="text-white/80 flex items-center gap-2"><Icon name="check_circle" className="text-[20px]" style={{ color: GOOD }} />No problems recorded.</p>
            ) : (
              <ul className="flex flex-col gap-2 list-none p-0 m-0">
                {data.problems.map((p, i) => (
                  <li key={`${p.at}-${i}`} className="rounded-DEFAULT px-3 py-2 flex flex-wrap items-baseline gap-x-3 gap-y-1" style={{ background: "rgba(255,255,255,0.06)" }}>
                    <span className="text-[12px] text-white/60 tabular-nums">{formatWhen(p.at)}</span>
                    <span className="text-[12px] font-semibold px-2 py-0.5 rounded-full" style={{ background: `${BAD}22`, color: BAD }}>{p.source}</span>
                    <span className="text-[13.5px] text-white/90 break-words">{p.detail}</span>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
