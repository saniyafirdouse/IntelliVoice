import { useMemo, useRef, useState, type CSSProperties } from "react";
import { Icon } from "../components/Icon";
import { PageShell } from "../components/PageShell";
import { EvaAvatar } from "../components/EvaAvatar";
import { useLanguage } from "../context/LanguageContext";
import { FAQ_CATEGORIES, HOW_IT_WORKS, RELIABILITY, STATIC_ANSWERS } from "../data/faq";
import { askQuestion } from "../lib/api";
import { ContactDialog } from "./chat/ContactDialog";
import type { DocumentLink } from "../lib/types";

const glassPanel: CSSProperties = {
  background: "rgba(14, 18, 30, 0.24)",
  border: "1px solid rgba(255, 255, 255, 0.16)",
  backdropFilter: "blur(20px)",
  WebkitBackdropFilter: "blur(20px)",
  boxShadow: "rgba(0, 0, 0, 0.25) 0px 8px 32px, rgba(255, 255, 255, 0.2) 0px 1px 0px inset",
};
const primaryButton: CSSProperties = {
  background: "linear-gradient(135deg, rgba(126, 130, 194, 0.85), rgba(191, 194, 255, 0.75))",
  border: "1px solid rgba(255, 255, 255, 0.55)",
  boxShadow: "rgba(126, 130, 194, 0.55) 0px 0px 24px",
  color: "rgb(255, 255, 255)",
};

// 2026-11-01: an opened question shows Eva's real answer right here (text only — no voice,
// so no Sarvam credits), from the same database as the chat. Before, it only linked to the chat.
type Answer = { status: "loading" | "done" | "error"; text?: string; docs?: DocumentLink[] };

function FaqItem({ question, open, onToggle, answer }: { question: string; open: boolean; onToggle: () => void; answer?: Answer }) {
  return (
    <div className="faq-card rounded-2xl bg-surface-container-lowest/55 backdrop-blur-xl shadow-[0_8px_32px_rgba(0,0,0,0.3)] overflow-hidden transition-all">
      <button
        type="button"
        aria-expanded={open}
        onClick={onToggle}
        className="faq-toggle w-full px-space-lg py-space-md flex items-center justify-between text-left gap-space-md hover:bg-surface-container-high/30 transition-colors"
      >
        <span className="font-title-md text-title-md text-on-surface">{question}</span>
        <Icon name="expand_more" className="text-secondary transition-transform duration-300 icon-arrow" style={{ transform: open ? "rotate(180deg)" : "rotate(0deg)" }} />
      </button>
      {open && (
        <div className="faq-content px-space-lg pb-space-lg pt-1">
          <div className="p-space-md rounded-xl bg-surface-container-high/40 flex gap-3" aria-live="polite">
            <EvaAvatar size={36} />
            <div className="flex-1 min-w-0">
              <p className="text-[13px] font-semibold text-white/75">Eva</p>
              {(!answer || answer.status === "loading") && (
                <p className="mt-1 text-white/70 flex items-center gap-2">
                  <Icon name="progress_activity" className="text-[18px] animate-spin" />
                  Finding the answer in the SVIT admissions database…
                </p>
              )}
              {answer?.status === "error" && (
                <p className="mt-1 text-white/80">Sorry, I couldn't get the answer right now. Please ask me in Voice Chat.</p>
              )}
              {answer?.status === "done" && (
                <>
                  <p className="mt-1 text-[15.5px] leading-[1.55] text-white whitespace-pre-line break-words">{answer.text}</p>
                  {!!answer.docs?.length && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {answer.docs.filter((d) => d?.url).map((d) => (
                        <a key={d.url} href={d.url} {...(d.download ? { download: true } : { target: "_blank", rel: "noopener noreferrer" })}
                          className="h-9 pl-3 pr-4 rounded-full flex items-center gap-1.5 text-[13.5px] font-semibold"
                          style={{ background: "#e8d3a3", color: "#2d1f45" }}>
                          <Icon name={d.download ? "download" : "picture_as_pdf"} className="text-[18px]" />
                          {d.title || "Open PDF"}
                        </a>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function FaqPage() {
  const [category, setCategory] = useState("all");
  const [search, setSearch] = useState("");
  const [openItems, setOpenItems] = useState<Set<string>>(new Set());
  const [contactOpen, setContactOpen] = useState(false);
  const { responseLanguage } = useLanguage();
  const [answers, setAnswers] = useState<Record<string, Answer>>({});
  const asked = useRef<Set<string>>(new Set());
  const queue = useRef<Promise<void>>(Promise.resolve());   // one question at a time (free Groq limits)
  const sessionId = useRef(`faq-${Math.random().toString(36).slice(2, 10)}`);
  const counter = useRef(0);

  const ensureAnswer = (q: string) => {
    if (asked.current.has(q)) return;
    asked.current.add(q);
    if (STATIC_ANSWERS[q]) { setAnswers((a) => ({ ...a, [q]: { status: "done", text: STATIC_ANSWERS[q] } })); return; }
    setAnswers((a) => ({ ...a, [q]: { status: "loading" } }));
    counter.current += 1;
    const sid = `${sessionId.current}-${counter.current}`;   // each question its own short session (no carry-over)
    queue.current = queue.current.then(async () => {
      try {
        const res = await askQuestion({ sessionId: sid, text: q, responseLanguage, includeAudio: false });
        const text = res.response?.text?.trim();
        setAnswers((a) => ({ ...a, [q]: text ? { status: "done", text, docs: res.documents ?? [] } : { status: "error" } }));
      } catch {
        asked.current.delete(q);                      // closing and opening it tries again
        setAnswers((a) => ({ ...a, [q]: { status: "error" } }));
      }
    });
  };

  const visible = useMemo(() => {
    const q = search.trim().toLowerCase();
    return FAQ_CATEGORIES
      .filter((c) => category === "all" || c.id === category)
      .map((c) => ({
        ...c,
        questions: q ? c.questions.filter((x) => x.toLowerCase().includes(q) || c.title.toLowerCase().includes(q)) : c.questions,
      }))
      .filter((c) => c.questions.length > 0);
  }, [category, search]);

  const toggle = (q: string) =>
    setOpenItems((prev) => {
      const next = new Set(prev);
      if (next.has(q)) next.delete(q); else { next.add(q); ensureAnswer(q); }
      return next;
    });

  // 2026-11-01: a typed question that isn't in the list is answered right here too (no jump to the chat)
  const [custom, setCustom] = useState<string | null>(null);
  const askTyped = () => { const q = search.trim(); if (q) { setCustom(q); ensureAnswer(q); } };

  return (
    <PageShell
      scope="pg-faq"
      variant="app"
      title="Help & FAQ"
      className="font-body-md text-on-surface antialiased selection:bg-secondary-container selection:text-on-secondary-container"
    >
      <main className="w-full pt-20 min-h-screen relative">
        <div className="flex flex-col w-full relative">
          <div className="fixed inset-0 pointer-events-none z-0" aria-hidden="true">
            <div className="absolute inset-0 bg-cover bg-center" style={{ backgroundImage: 'url("/assets/campus-front.jpg")' }} />{/* 2026-11-01: same SVIT front entrance as the Home page (was the night photo) */}
            <div className="absolute inset-0 bg-black/45" />
          </div>

          <div className="relative z-10 w-full px-margin-mobile lg:px-margin max-w-7xl mx-auto flex flex-col gap-space-2xl pb-space-2xl">
            {/* ---------- Title + search ---------- */}
            <div className="flex flex-col items-center text-center pt-space-xl gap-space-md max-w-4xl mx-auto w-full">
              <div className="inline-flex max-w-full items-center gap-2 px-4 py-1.5 rounded-full backdrop-blur-md" style={{ background: "rgba(20, 24, 38, 0.75)", border: "1px solid rgba(255, 255, 255, 0.32)", backdropFilter: "blur(20px)", boxShadow: "rgba(0, 0, 0, 0.4) 0px 4px 20px" }}>
                <span className="w-2 h-2 rounded-full bg-secondary animate-ping" />
                <span className="font-label-sm text-label-sm text-secondary tracking-widest uppercase font-semibold text-center">
                  SVIT IntelliVoice Knowledge Base &amp; Admission Dispatch
                </span>
              </div>
              <div className="w-full max-w-3xl mx-auto rounded-3xl flex flex-col items-center text-center gap-space-sm p-6 sm:p-10" style={{ background: "rgba(14, 18, 30, 0.25)", backdropFilter: "blur(20px)", border: "1px solid rgba(255, 255, 255, 0.16)", boxShadow: "rgba(0, 0, 0, 0.3) 0px 16px 40px, rgba(255, 255, 255, 0.2) 0px 1px 0px inset" }}>
                <h1 className="font-display text-headline-lg-mobile md:text-display tracking-tight font-bold m-0" style={{ color: "#ffffff", textShadow: "0 2px 12px rgba(0, 0, 0, 0.8), 0 1px 4px rgba(0, 0, 0, 0.9)" }}>
                  How can we help you today?
                </h1>
                <p className="font-body-lg text-body-lg max-w-2xl leading-relaxed font-medium m-0" style={{ color: "#e2e8f0", textShadow: "0 1px 6px rgba(0, 0, 0, 0.8)" }}>
                  Open any question to see Eva’s answer from the SVIT admissions database: admissions, branches, fees, hostel, transport and placements.
                </p>
              </div>

              <form
                className="w-full mt-space-md"
                role="search"
                onSubmit={(e) => { e.preventDefault(); askTyped(); }}
              >
                <div className="relative flex items-center w-full rounded-full p-2 pl-4 sm:pl-6 transition-all focus-within:border-white/30" style={{ background: "rgba(14, 18, 30, 0.28)", border: "1px solid rgba(255, 255, 255, 0.18)", backdropFilter: "blur(20px)", boxShadow: "rgba(0, 0, 0, 0.3) 0px 16px 40px, rgba(255, 255, 255, 0.22) 0px 1px 0px inset" }}>
                  <Icon name="search" className="text-secondary text-[26px] mr-3" />
                  <input
                    id="faq-search-input"
                    type="text"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    aria-label="Search questions or ask IntelliVoice"
                    placeholder="Ask anything (e.g. 'What is the CET cutoff for CSE?', 'Hostel fee structure', 'ComedK Code')..."
                    className="w-full min-w-0 bg-transparent text-on-surface placeholder:text-on-surface-variant/60 font-body-md text-body-md focus:outline-none"
                  />
                  <button type="submit" className="flex-shrink-0 flex items-center gap-2 px-4 sm:px-5 py-3 rounded-full shadow-lg hover:opacity-95 active:scale-95 transition-all" style={primaryButton}>
                    <Icon name="auto_awesome" className="text-[20px]" filled />
                    <span className="font-label-lg text-label-lg font-semibold tracking-wide hidden sm:inline">Ask Eva</span>
                  </button>
                </div>
              </form>

              <div className="w-full py-2" role="tablist" aria-label="FAQ topics">
                <div className="flex flex-wrap items-center justify-center gap-2">
                  {[{ id: "all", pill: "All Topics" }, ...FAQ_CATEGORIES].map((c) => {
                    const on = category === c.id;
                    return (
                      <button
                        key={c.id}
                        type="button"
                        role="tab"
                        aria-selected={on}
                        onClick={() => setCategory(c.id)}
                        className={`cat-pill px-4 py-2 rounded-full font-label-md text-label-md transition-all ${on ? "active text-white" : "text-on-surface-variant hover:text-white"}`}
                      >
                        {c.pill}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* ---------- How it works ---------- */}
            <section className="flex flex-col gap-space-lg">
              <div className="flex flex-col gap-1 p-4 sm:px-6 sm:py-4 rounded-2xl" style={glassPanel}>
                <span className="font-label-sm text-label-sm uppercase text-secondary tracking-widest">Acoustic Assistant Workflow</span>
                <h2 className="font-headline-md text-headline-md text-on-surface">How IntelliVoice Operates in 4 Simple Steps</h2>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-space-md">
                {HOW_IT_WORKS.map((s) => (
                  <div key={s.n} className="flex flex-col justify-between p-space-lg rounded-2xl bg-surface-container-lowest/50 backdrop-blur-xl shadow-[0_8px_32px_rgba(0,0,0,0.35)] hover:-translate-y-1 transition-all duration-300 group">
                    <div className="flex flex-col gap-space-md">
                      <div className="flex items-center justify-between">
                        <span className="font-display text-headline-md text-secondary font-bold">{s.n}</span>
                        <div className="w-10 h-10 rounded-full bg-secondary-container/50 flex items-center justify-center text-secondary group-hover:scale-110 transition-transform">
                          <Icon name={s.icon} className="text-[20px]" />
                        </div>
                      </div>
                      <h3 className="font-title-lg text-title-lg text-on-surface">{s.title}</h3>
                      <p className="font-body-sm text-body-sm text-on-surface-variant">{s.body}</p>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            {/* ---------- Questions ---------- */}
            <section className="flex flex-col gap-space-xl">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-space-sm p-4 sm:px-6 sm:py-4 rounded-2xl" style={glassPanel}>
                <div className="flex flex-col gap-1">
                  <span className="font-label-sm text-label-sm uppercase text-secondary tracking-widest">Institutional Directory</span>
                  <h2 className="font-headline-md text-headline-md text-on-surface">Frequently Answered Queries</h2>
                </div>
                <div className="hidden sm:flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => { const all = FAQ_CATEGORIES.flatMap((c) => c.questions); all.forEach(ensureAnswer); setOpenItems(new Set(all)); }}
                    className="px-3 py-1.5 rounded-full font-label-sm text-label-sm text-white transition-colors"
                    style={{ background: "rgba(126, 130, 194, 0.85)", boxShadow: "rgba(191, 194, 255, 0.6) 0px 0px 16px", border: "1px solid rgba(255, 255, 255, 0.6)" }}
                  >
                    Expand All
                  </button>
                  <button
                    type="button"
                    onClick={() => setOpenItems(new Set())}
                    className="px-3 py-1.5 rounded-full bg-surface-container-high/60 hover:bg-surface-container-high font-label-sm text-label-sm text-on-surface-variant transition-colors"
                  >
                    Collapse All
                  </button>
                </div>
              </div>

              <div className="flex flex-col gap-space-lg">
                {custom && (
                  <div className="flex flex-col gap-space-sm">
                    <div className="flex items-center gap-2.5 px-2">
                      <Icon name="auto_awesome" className="text-secondary text-[20px]" />
                      <h3 className="font-title-lg text-title-lg text-on-surface">Your question</h3>
                    </div>
                    <FaqItem question={custom} open onToggle={() => setCustom(null)} answer={answers[custom]} />
                  </div>
                )}
                {visible.length === 0 && !custom && (
                  <div className="faq-card rounded-2xl p-space-lg">
                    <p className="text-on-surface font-medium">No listed question matches “{search}”. Press <strong>Ask Eva</strong> and she will answer it here.</p>
                  </div>
                )}
                {visible.map((c) => (
                  <div key={c.id} className="faq-group flex flex-col gap-space-sm">
                    <div className="flex items-center gap-2.5 px-2">
                      <Icon name={c.icon} className="text-secondary text-[20px]" />
                      <h3 className="font-title-lg text-title-lg text-on-surface">{c.title}</h3>
                    </div>
                    {c.questions.map((q) => (
                      <FaqItem key={q} question={q} open={openItems.has(q)} onToggle={() => toggle(q)} answer={answers[q]} />
                    ))}
                  </div>
                ))}
              </div>
            </section>

            {/* ---------- Reliability ---------- */}
            <section className="flex flex-col gap-space-md">
              <div className="flex items-center gap-2.5 p-3 px-5 rounded-2xl w-fit" style={glassPanel}>
                <Icon name="verified_user" className="text-secondary" />
                <h2 className="font-headline-sm text-headline-sm text-on-surface">How IntelliVoice Keeps Answers Reliable</h2>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-space-md">
                {RELIABILITY.map((r) => (
                  <div key={r.title} className="p-space-lg rounded-2xl bg-surface-container-lowest/50 backdrop-blur-xl shadow-[0_8px_32px_rgba(0,0,0,0.35)] flex flex-col gap-space-sm hover:bg-surface-container-low/60 transition-colors">
                    <div className="w-8 h-8 rounded-full bg-secondary-container/60 flex items-center justify-center text-secondary">
                      <Icon name={r.icon} className="text-[18px]" />
                    </div>
                    <span className="font-title-md text-title-md text-on-surface">{r.title}</span>
                    <p className="font-body-sm text-body-sm text-on-surface-variant">{r.body}</p>
                  </div>
                ))}
              </div>
            </section>

            {/* ---------- Call to action ---------- */}
            <section className="rounded-3xl p-space-xl md:p-space-2xl flex flex-col md:flex-row items-center justify-between gap-space-xl relative overflow-hidden" style={{ background: "rgba(14, 18, 30, 0.26)", border: "1px solid rgba(255, 255, 255, 0.18)", backdropFilter: "blur(24px)", boxShadow: "rgba(0, 0, 0, 0.35) 0px 20px 50px, rgba(255, 255, 255, 0.25) 0px 1px 0px inset" }}>
              <div className="absolute -right-20 -bottom-20 w-80 h-80 rounded-full bg-secondary-container/30 blur-3xl pointer-events-none" />
              <div className="flex flex-col gap-space-xs text-center md:text-left z-10 max-w-xl">
                <span className="font-label-sm text-label-sm uppercase text-secondary font-semibold tracking-wider">Unresolved Inquiry?</span>
                <h2 className="font-headline-md text-headline-md text-on-surface">Still have a question? Ask Eva above, or reach the SVIT admission office</h2>
                <p className="font-body-md text-body-md text-on-surface-variant">
                  Type any question in the box at the top and Eva answers it on this page, or contact the admission office for personal cases.
                </p>
              </div>
              <div className="flex flex-wrap items-center justify-center gap-space-md z-10 flex-shrink-0">
                <button type="button" onClick={() => setContactOpen(true)} className="px-6 py-3.5 rounded-full font-title-md text-title-md flex items-center gap-2 hover:scale-105 active:scale-95 transition-all" style={primaryButton}>
                  <Icon name="contact_support" className="text-[20px]" />
                  <span>Contact the admission office</span>
                </button>
              </div>
            </section>
          </div>
        </div>
      </main>
      <ContactDialog open={contactOpen} onClose={() => setContactOpen(false)} />
    </PageShell>
  );
}
