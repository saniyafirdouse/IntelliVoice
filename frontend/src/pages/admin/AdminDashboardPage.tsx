import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Icon } from "../../components/Icon";
import { useAuth } from "../../context/AuthContext";
import { ApiError } from "../../lib/api";
import { adminApi, prettyIntent, type Dashboard } from "../../lib/adminApi";
import { Button, Card, EmptyState, Loading, Notice, PageTitle, PeriodPicker, StatTile } from "./AdminUi";
import { ColumnChart, DonutChart, RankedBars, SplitBar, VIZ } from "./BarChart";

// Each thing keeps the same colour wherever it appears.
const STATUS_ROWS = [
  { key: "answered", label: "Answered", icon: "check_circle", color: VIZ.teal, help: "From the college data" },
  { key: "no_data", label: "No data yet", icon: "database", color: VIZ.amber, help: "Understood, data missing" },
  { key: "out_of_scope", label: "Out of scope", icon: "do_not_disturb_on", color: VIZ.sky, help: "Not about admissions" },
  { key: "error", label: "Technical error", icon: "error", color: VIZ.coral, help: "Failed on the server" },
] as const;

const LANGUAGE_COLORS: Record<string, string> = { kn: VIZ.periwinkle, en: VIZ.teal, hi: VIZ.coral };
const MOOD_COLORS: Record<string, string> = { neutral: VIZ.sky, worried: VIZ.amber, confused: VIZ.lilac, frustrated: VIZ.coral, happy: VIZ.sage, positive: VIZ.sage };

export default function AdminDashboardPage() {
  const { token } = useAuth();
  const [days, setDays] = useState(7);
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      setData(await adminApi.dashboard(token, days));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't load the dashboard.");
    } finally {
      setLoading(false);
    }
  }, [token, days]);

  useEffect(() => { void load(); }, [load]);

  return (
    <>
      <PageTitle
        title="Dashboard"
        subtitle="What parents and students are asking IntelliVoice, and how well it answers."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <PeriodPicker days={days} onChange={setDays} />
            <Button icon="refresh" onClick={() => void load()} busy={loading} aria-label="Refresh">Refresh</Button>
          </div>
        }
      />

      {error && <Notice kind="error">{error}</Notice>}
      {loading && !data && <Loading label="Loading dashboard…" />}

      {data && data.total_queries === 0 && (
        <Card>
          <EmptyState icon="query_stats" title={`No questions in the last ${days === 1 ? "day" : `${days} days`}`}>
            As soon as parents start asking questions on the Voice Chat page, the numbers and charts appear here.
          </EmptyState>
        </Card>
      )}

      {data && data.total_queries > 0 && <DashboardBody data={data} />}
    </>
  );
}

function DashboardBody({ data }: { data: Dashboard }) {
  const total = data.total_queries;
  const unanswered = data.status.no_data + data.status.out_of_scope;
  const voice = data.input_types.audio ?? 0;
  const daily = data.daily_queries.map((d) => {
    const date = new Date(`${d.date}T00:00:00`);
    return {
      key: d.date,
      label: data.days > 14 ? String(date.getDate()) : date.toLocaleDateString("en-IN", { day: "numeric", month: "short" }),
      tooltip: date.toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long" }),
      value: d.count,
    };
  });
  const hours = data.busiest_hours.map((h) => ({
    key: String(h.hour),
    label: h.hour % 12 === 0 ? (h.hour === 0 ? "12a" : "12p") : String(h.hour % 12),
    tooltip: `${formatHour(h.hour)} – ${formatHour((h.hour + 1) % 24)}`,
    value: h.count,
  }));
  const peak = data.busiest_hours.reduce((a, b) => (b.count > a.count ? b : a), data.busiest_hours[0]);

  return (
    <>
      {/* headline numbers */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-space-md">
        <StatTile icon="forum" tone={VIZ.periwinkle} label="Questions asked" value={total.toLocaleString("en-IN")} hint={`${data.unique_sessions.toLocaleString("en-IN")} conversations`} />
        <StatTile icon="task_alt" tone={VIZ.teal} label="Answered" value={`${data.answered_rate}%`} progress={data.answered_rate} hint={`${data.status.answered.toLocaleString("en-IN")} of ${total.toLocaleString("en-IN")}`} />
        <StatTile icon="help_center" tone={VIZ.amber} label="Couldn't answer" value={unanswered.toLocaleString("en-IN")} hint={unanswered ? "See the Unanswered page" : "Nothing missing"} />
        <StatTile
          icon="timer"
          tone={VIZ.sky}
          label="Avg. answer time"
          value={data.avg_response_time_ms ? `${(data.avg_response_time_ms / 1000).toFixed(1)} s` : "—"}
          hint={`${data.escalations} sent to admissions office`}
        />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-5 gap-space-lg">
        <Card title="Questions per day" icon="calendar_month" className="xl:col-span-3" subtitle={`Last ${data.days === 1 ? "day" : `${data.days} days`}`}>
          <ColumnChart data={daily} height={260} ariaLabel="Questions per day" color={VIZ.periwinkle} peakColor={VIZ.lilac} markPeak showAverage labelEvery={data.days > 31 ? 7 : data.days > 14 ? 3 : 1} />
        </Card>

        <Card title="How questions were handled" icon="fact_check" className="xl:col-span-2">
          <DonutChart
            centerLabel="questions"
            size={156}
            stacked
            data={STATUS_ROWS.map((s) => ({ key: s.key, label: s.label, value: data.status[s.key], color: s.color, icon: s.icon, help: s.help }))}
          />
          {unanswered > 0 && (
            <Link to="/admin/unanswered" className="inline-flex items-center gap-1 font-label-lg text-label-lg text-secondary hover:underline self-start">
              See what&apos;s missing <Icon name="arrow_forward" className="text-[18px]" />
            </Link>
          )}
        </Card>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-space-lg">
        <Card title="Most-asked topics" icon="leaderboard" subtitle="Top 10 topics parents asked about">
          {data.top_intents.length ? (
            <RankedBars total={total} data={data.top_intents.map((t) => ({ key: t.intent, label: prettyIntent(t.intent), value: t.count }))} />
          ) : <p className="text-white/65">No topics yet.</p>}
        </Card>

        <div className="flex flex-col gap-space-lg">
          <Card title="Languages" icon="translate" subtitle={`${data.code_switched_percent}% of questions mixed two languages`}>
            <DonutChart
              centerLabel="questions"
              size={140}
              data={data.languages.map((l) => ({ key: l.code, label: l.language, value: l.count, color: LANGUAGE_COLORS[l.code] ?? VIZ.amber }))}
            />
          </Card>
          <Card title="Voice or typed" icon="mic" subtitle="How people asked their question">
            <SplitBar
              data={[
                { key: "audio", label: "Spoken", value: voice, color: VIZ.rose, icon: "mic" },
                { key: "text", label: "Typed", value: data.input_types.text ?? 0, color: VIZ.sky, icon: "keyboard" },
              ]}
            />
          </Card>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-5 gap-space-lg">
        <Card title="Busiest hours" icon="schedule" className="xl:col-span-3" subtitle={peak && peak.count > 0 ? `Peak: ${formatHour(peak.hour)} – ${formatHour((peak.hour + 1) % 24)} (Indian time) · stronger colour = busier` : "Indian time"}>
          <ColumnChart data={hours} ariaLabel="Questions by hour of day" labelEvery={hours.length > 12 ? 3 : 1} height={170} color={VIZ.coral} heat markPeak />
        </Card>
        <Card title="How parents felt" icon="mood" className="xl:col-span-2" subtitle="Emotion detected in the question">
          <RankedBars total={total} data={data.emotions.map((e) => ({ key: e.emotion, label: capitalise(e.emotion), value: e.count, color: MOOD_COLORS[e.emotion] ?? VIZ.muted }))} />
        </Card>
      </div>
    </>
  );
}

function formatHour(h: number) {
  const suffix = h < 12 ? "am" : "pm";
  const hr = h % 12 === 0 ? 12 : h % 12;
  return `${hr} ${suffix}`;
}

function capitalise(s: string) {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : s;
}
