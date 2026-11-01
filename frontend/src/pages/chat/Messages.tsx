import { useEffect, useRef, useState } from "react";
import { Icon } from "../../components/Icon";
import { audioSource } from "../../lib/audio";
import { ApiError, downloadChecklist } from "../../lib/api";
import type { CollegeOverview, DocumentLink, OverviewSection, QueryResponse, TableData } from "../../lib/types";
import type { ChatMessage } from "./useChat";
import { EvaAvatar } from "../../components/EvaAvatar";

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
          className={`px-5 py-2.5 rounded-[20px] text-white text-[15.5px] md:text-[16.5px] leading-snug break-words ${m.pending ? "italic text-white/75" : ""}`}
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
      <span className="w-9 h-9 flex-shrink-0 rounded-full flex items-center justify-center" style={{ background: "#29301d", border: "1px solid #53553e", boxShadow: "0 6px 18px rgba(0,0,0,0.35)" }}>
        <Icon name="person" className="text-[20px] text-white" filled />
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

// ---- "College at a glance" card (2026-10-15) ----
// Shown for "tell me everything" questions: every topic as a tile, a few headline
// numbers on top, and the full brochure as a PDF download.
const HIGHLIGHTS: { section: string; label: string; caption: string }[] = [
  { section: "placements", label: "Highest package", caption: "Highest package" },
  { section: "placements", label: "Average package", caption: "Average package" },
  { section: "placements", label: "Total offers", caption: "Placement offers" },
  { section: "about", label: "Established", caption: "Established" },
];
const TILE_ITEMS = 4;

function OverviewTile({ section }: { section: OverviewSection }) {
  const [open, setOpen] = useState(false);
  const items = open ? section.items : section.items.slice(0, TILE_ITEMS);
  const hidden = section.items.length - TILE_ITEMS;
  return (
    <div className="rounded-[20px] p-4 flex flex-col" style={{ background: "rgba(14, 14, 11, 0.42)", border: "1px solid rgba(237, 243, 181, 0.16)" }}>
      <div className="flex items-center gap-2.5">
        <span className="w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0" style={{ background: "rgba(194, 204, 153, 0.16)", border: "1px solid rgba(194, 204, 153, 0.35)" }}>
          <Icon name={section.icon} className="text-[19px]" style={{ color: SAGE_TINT }} filled />
        </span>
        <div className="text-white text-[21px] leading-tight" style={{ fontFamily: '"Cormorant Garamond", Georgia, serif', fontWeight: 600 }}>{section.title}</div>
      </div>
      <dl className="mt-3 flex flex-col gap-2">
        {items.map((it) => (
          <div key={it.label} className="grid grid-cols-[minmax(92px,38%)_1fr] gap-3 text-[14px] leading-snug">
            <dt className="text-white/55">{it.label}</dt>
            <dd className="text-white/92 break-words">{it.value}</dd>
          </div>
        ))}
      </dl>
      {section.note && open && <p className="mt-2 text-[12.5px] italic text-white/45">{section.note}</p>}
      {hidden > 0 && (
        <button type="button" onClick={() => setOpen((o) => !o)} className="mt-3 self-start text-[13.5px] font-medium underline underline-offset-4 decoration-[#c2cc99]/70 hover:text-white" style={{ color: SAGE_TINT }}>
          {open ? "Show less" : `Show ${hidden} more`}
        </button>
      )}
    </div>
  );
}

// 2026-10-29: PDF buttons under a reply — e.g. the bus-route PDF straight from
// the college website, or our brochure when no branch was named.
// 2026-10-31: personal document checklist (the backend's POST /api/checklist was
// ready but had no button). Offered under admission / documents replies.
const CHECKLIST_TYPES: [string, string][] = [
  ["KCET", "KCET"], ["COMEDK", "COMEDK"], ["Management", "Management quota"],
  ["Lateral", "Lateral entry (DCET)"], ["MBA", "MBA (PGCET)"],
];
const CHECKLIST_CATEGORIES = ["General", "SC", "ST", "OBC"];

function ChecklistButton({ res }: { res: QueryResponse }) {
  const ents = res.understanding?.entities ?? {};
  const guess = ents.quota === "Management" ? "Management" : ents.exam === "COMEDK" ? "COMEDK" : ents.exam === "DCET" ? "Lateral"
    : ents.exam === "PGCET" ? "MBA" : "KCET";
  const [open, setOpen] = useState(false);
  const [type, setType] = useState(guess);
  const [category, setCategory] = useState("General");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const get = async () => {
    setBusy(true); setError(null);
    try { await downloadChecklist(type, category, name); setOpen(false); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Couldn't make the checklist. Please try again."); }
    finally { setBusy(false); }
  };
  const field = "h-10 rounded-full px-3 text-[14px] text-white bg-black/35 border border-white/20 outline-none focus:border-white/50";
  if (!open) {
    return (
      <button type="button" onClick={() => setOpen(true)}
        className="mt-3 h-11 pl-4 pr-5 rounded-full flex items-center gap-2 text-[14.5px] font-semibold text-white transition-all hover:bg-white/10"
        style={{ border: "1px solid rgba(194, 204, 153, 0.55)" }}>
        <Icon name="checklist" className="text-[20px]" style={{ color: "#c2cc99" }} />
        Get my document checklist (PDF)
      </button>
    );
  }
  return (
    <div className="mt-3 rounded-2xl p-3 flex flex-wrap items-center gap-2" style={{ background: "rgba(10, 10, 8, 0.4)", border: "1px solid rgba(255,255,255,0.12)" }}>
      <select aria-label="How you are applying" value={type} onChange={(e) => setType(e.target.value)} className={field}>
        {CHECKLIST_TYPES.map(([v, l]) => <option key={v} value={v} className="text-black">{l}</option>)}
      </select>
      <select aria-label="Category" value={category} onChange={(e) => setCategory(e.target.value)} className={field}>
        {CHECKLIST_CATEGORIES.map((c) => <option key={c} value={c} className="text-black">{c}</option>)}
      </select>
      <input aria-label="Student name (optional)" placeholder="Student name (optional)" value={name} maxLength={80}
        onChange={(e) => setName(e.target.value)} className={`${field} w-48`} />
      <button type="button" onClick={() => void get()} disabled={busy}
        className="h-10 px-4 rounded-full flex items-center gap-1.5 text-[14px] font-semibold disabled:opacity-60"
        style={{ background: "#c2cc99", color: "#1d2214" }}>
        <Icon name={busy ? "progress_activity" : "download"} className={`text-[18px] ${busy ? "animate-spin" : ""}`} />
        Download
      </button>
      <button type="button" onClick={() => setOpen(false)} aria-label="Close" className="w-10 h-10 rounded-full flex items-center justify-center text-white/70 hover:bg-white/10">
        <Icon name="close" className="text-[18px]" />
      </button>
      {error && <p className="w-full text-[13px] text-red-200">{error}</p>}
    </div>
  );
}

export function DocumentButtons({ docs }: { docs: DocumentLink[] }) {
  return (
    <div className="mt-4 flex flex-wrap gap-2.5">
      {docs.filter((d) => d?.url).map((d) => (
        <a
          key={d.url}
          href={d.url}
          {...(d.download ? { download: true } : { target: "_blank", rel: "noopener noreferrer" })}
          className="h-11 pl-4 pr-5 rounded-full flex items-center gap-2 text-[14.5px] font-semibold transition-all hover:brightness-105 active:scale-[0.98]"
          style={{ background: "#c2cc99", color: "#1d2214", boxShadow: "0 8px 20px rgba(194, 204, 153, 0.22)" }}
        >
          <Icon name={d.download ? "download" : "picture_as_pdf"} className="text-[20px]" />
          {d.title || "Open PDF"}
        </a>
      ))}
    </div>
  );
}

function OverviewCard({ overview }: { overview: CollegeOverview }) {
  const sections = (overview.sections ?? []).filter((s) => s.items?.length);
  if (!sections.length) return null;
  const find = (id: string, label: string) => sections.find((s) => s.id === id)?.items.find((i) => i.label === label)?.value;
  const highlights = HIGHLIGHTS
    .map((h) => {
      const v = find(h.section, h.label);
      // "2008 by Sri Sai Vidya Vikas..." -> "2008" (the tile has room for a short number only)
      return { ...h, value: h.label === "Established" ? v?.match(/\b(19|20)\d\d\b/)?.[0] : v };
    })
    .filter((h) => h.value);
  const brochure = overview.brochure_url || "/api/brochure";
  const name = (overview.title || "Sai Vidya Institute of Technology").replace(/\s+at a glance$/i, "");
  return (
    <div className="mt-4 rounded-[24px] p-4 md:p-5" style={{ background: "linear-gradient(160deg, rgba(194, 204, 153, 0.12), rgba(20, 20, 16, 0.35))", border: "1px solid rgba(194, 204, 153, 0.32)" }}>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-[11.5px] font-semibold uppercase tracking-[0.24em] text-white/55">College at a glance</p>
          <div className="mt-1 text-white text-[28px] md:text-[34px] leading-tight" style={{ fontFamily: '"Cormorant Garamond", Georgia, serif', fontWeight: 600 }}>{name}</div>
        </div>
        <a
          href={brochure}
          download
          className="h-11 pl-4 pr-5 rounded-full flex items-center gap-2 text-[14.5px] font-semibold transition-all hover:brightness-105 active:scale-[0.98]"
          style={{ background: "#c2cc99", color: "#1d2214", boxShadow: "0 8px 20px rgba(194, 204, 153, 0.22)" }}
        >
          <Icon name="download" className="text-[20px]" />
          Download brochure (PDF)
        </a>
      </div>

      {highlights.length > 0 && (
        <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-2.5">
          {highlights.map((h) => (
            <div key={h.caption} className="rounded-2xl px-3.5 py-3" style={{ background: "rgba(10, 10, 8, 0.4)", border: "1px solid rgba(255, 255, 255, 0.08)" }}>
              <div className="text-[24px] md:text-[26px] leading-none text-white" style={{ fontFamily: '"Cormorant Garamond", Georgia, serif', fontWeight: 600, color: SAGE_TINT }}>{h.value}</div>
              <div className="mt-1.5 text-[12.5px] text-white/60">{h.caption}</div>
            </div>
          ))}
        </div>
      )}

      <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3">
        {sections.map((s) => <OverviewTile key={s.id} section={s} />)}
      </div>
      <p className="mt-3 text-[12.5px] text-white/45">From the SVIT admissions database. Fees and cutoffs can change every year; please confirm with the admission office.</p>
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

const ACTION_BTN = "h-8 px-3 rounded-full flex items-center gap-1.5 text-[13px] text-white/92 transition-colors hover:bg-white/10 disabled:opacity-50";

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
  placementsBranch: { icon: "work", label: "Placements by branch", q: "What are the placement numbers for each branch at SVIT?" },
} satisfies Record<string, FollowUp>;
const FOLLOW_UPS: { match: RegExp; items: FollowUp[] }[] = [
  { match: /college_overview/i, items: [F.placementsBranch, F.feeStructure, F.scholarships] },   // "tell me everything"
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
          className="group h-10 pl-4 pr-4 rounded-full flex items-center gap-2.5 text-[14px] text-white transition-all hover:brightness-125 disabled:opacity-60"
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
        className="w-full max-w-[1100px] rounded-[22px] px-4 py-3 md:px-5 md:py-3.5 flex gap-3.5"
        style={{
          background: "linear-gradient(160deg, rgba(66, 53, 41, 0.72) 0%, rgba(34, 29, 24, 0.8) 45%, rgba(20, 20, 17, 0.84) 100%)",
          border: `1px solid ${mode === "reassurance" ? "rgba(167, 243, 208, 0.45)" : "rgba(167, 134, 95, 0.55)"}`,
          boxShadow: "0 18px 46px rgba(0,0,0,0.38), inset 0 1px 0 rgba(255, 230, 190, 0.12)",
          ...GLASS,
        }}
      >
        <EvaAvatar size={40} />
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <span className="text-[15.5px] font-semibold text-white">Eva <span className="font-normal" style={{ color: "#e8d3a3" }}>· IntelliVoice AI</span></span>
            <span className="text-[13px] text-white/55">{time(m.at)}</span>
            {LANG_NAMES[lang] && <span className="text-[12.5px] text-white/45">· {LANG_NAMES[lang]}</span>}
            {res.demo && <span className="px-2 py-0.5 rounded-full text-[11px] bg-amber-400/25 border border-amber-200/40 text-amber-100">Demo mode · sample reply</span>}
          </div>
          <p className="mt-1 text-[15.5px] md:text-[16.5px] leading-[1.5] text-white whitespace-pre-line break-words" lang={lang || "en"}>{shown}</p>
          {res.data && <ReplyTable data={res.data} />}
          {res.overview && <OverviewCard overview={res.overview} />}
          {!res.overview && res.documents && res.documents.length > 0 && <DocumentButtons docs={res.documents} />}
          {res.checklist_available && <ChecklistButton res={res} />}

          <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
            <span className="h-8 pl-3 pr-4 rounded-full flex items-center gap-2 text-[13px] text-white/85" style={{ background: "rgba(39, 39, 30, 0.85)", border: "1px solid rgba(255, 255, 255, 0.1)" }}>
              <Icon name="database" className="text-[17px]" style={{ color: SAGE_TINT }} filled />
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
        <div className="w-full max-w-[1100px] mt-3 px-5 py-4 rounded-[24px] text-white flex items-start gap-3" style={{ background: "linear-gradient(135deg, rgba(65, 42, 26, 0.75), rgba(36, 26, 20, 0.8))", border: "1.5px solid rgba(246, 240, 189, 0.75)", boxShadow: "0 0 22px rgba(246, 240, 189, 0.22)", ...GLASS }}>
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
          <EvaAvatar size={32} />
          <span className="flex gap-1" aria-hidden="true">
            <span className="w-1.5 h-1.5 rounded-full animate-bounce" style={{ background: "#c9dc9b", animationDelay: "0ms" }} />
            <span className="w-1.5 h-1.5 rounded-full animate-bounce" style={{ background: "#c9dc9b", animationDelay: "150ms" }} />
            <span className="w-1.5 h-1.5 rounded-full animate-bounce" style={{ background: "#c9dc9b", animationDelay: "300ms" }} />
          </span>
          <span>Eva is thinking…</span>
        </div>
      )}
    </>
  );
}
