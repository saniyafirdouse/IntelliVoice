import type { CSSProperties } from "react";
import { CampusBackdrop } from "../components/CampusBackdrop";
import { FloatingMicButton } from "../components/FloatingMicButton";
import { Icon } from "../components/Icon";
import { PageShell } from "../components/PageShell";
import { useSectionBackground } from "../hooks/useSectionBackground";

// Frosted dark card style from the Stitch "About" design.
const card: CSSProperties = {
  background: "rgba(18, 22, 28, 0.55)",
  backdropFilter: "blur(16px)",
  WebkitBackdropFilter: "blur(16px)",
  border: "1px solid rgba(255, 255, 255, 0.25)",
  boxShadow: "rgba(0, 0, 0, 0.35) 0px 8px 32px",
};
const cardLarge: CSSProperties = { ...card, boxShadow: "rgba(0, 0, 0, 0.4) 0px 16px 40px" };
const softFill: CSSProperties = { background: "rgba(255, 255, 255, 0.12)" };
const chipFill: CSSProperties = { background: "rgba(255, 255, 255, 0.18)" };
const lavenderFill: CSSProperties = { background: "rgba(191, 194, 255, 0.35)" };

const PROBLEMS = [
  { icon: "call_end", title: "Long Waits During Counselling", body: "During KCET and COMEDK counselling rounds, phone lines and help desks get crowded with repetitive questions.", tag: "Repetitive Queries" },
  { icon: "translate", title: "Language Barriers", body: "Many students and parents are more comfortable in Kannada or Hindi, but most admission help is available only in English.", tag: "Multilingual Access" },
  { icon: "schedule", title: "Limited Support Hours", body: "Help is only available during office hours, leaving students without answers in the evenings and on weekends.", tag: "24/7 Availability" },
];

const ENGINES = [
  { n: "01", icon: "translate", title: "Language Detection", body: "Detects whether the user is speaking English, Kannada or Hindi, including code-mixed speech like Kanglish and Hinglish, using a fine-tuned MuRIL model.", tag: "Fine-tuned MuRIL Model" },
  { n: "02", icon: "psychology", title: "Query Understanding", body: "Identifies what the user is asking using a hybrid Sentence-Transformer and LLM classifier, extracts details like branch, quota, category and rank across 11 entity types, and detects the user's emotion.", tag: "Hybrid Classifier · 11 Entity Types" },
  { n: "03", icon: "database", title: "Knowledge Retrieval", body: "Fetches answers from the SVIT admissions database, which is the single source of truth for cutoffs, fees and seat details. This prevents the AI from inventing facts.", tag: "SVIT Database as Ground Truth" },
  { n: "04", icon: "history_toggle_off", title: "Contextual Memory", body: "Maintains session history and cross-turn entity retention across multi-turn counseling dialogues, ensuring applicant preferences persist seamlessly through follow-ups.", tag: "Cross-Turn Entity Retention" },
  { n: "05", icon: "tune", title: "Response Generation", body: "Phrases answers in a tone suited to the user's need, across five response modes: Informational, Reassurance, Comparison, Recommendation and Escalation.", tag: "5 Response Modes" },
  { n: "06", icon: "bar_chart", title: "Analytics", body: "Logs queries and system performance to help the admissions team understand what students ask most and improve the assistant over time.", tag: "Query Insights" },
];


const RECOGNITION = [
  { icon: "verified", label: "University Affiliation", value: "Visvesvaraya Technological University (VTU)" },
  { icon: "approval", label: "Statutory Recognition", value: "Approved by AICTE, New Delhi" },
  { icon: "grade", label: "Quality Accreditation", value: "NAAC 'A' Grade Accredited" },
];

function SectionIntro({ eyebrow, title, body }: { eyebrow: string; title: string; body: string }) {
  return (
    <div className="p-space-lg rounded-DEFAULT backdrop-blur-xl border border-white/30 mb-2" style={card}>
      <span className="uppercase tracking-widest text-mk-secondary font-bold glass-text-glow">{eyebrow}</span>
      <h2 className="font-mk-headline-lg text-white font-bold glass-text-glow">{title}</h2>
      <p className="font-mk-body-md text-slate-100 max-w-2xl font-medium glass-text-glow">{body}</p>
    </div>
  );
}

// 2026-11-01: "About SVIT" — the college itself, from the college website and the admissions
// database (verified facts in backend/engines/college_profile.py). Photos from public/assets.
const SVIT_PHOTOS = [
  { src: "/assets/campus-front.jpg", caption: "Main entrance" },
  { src: "/assets/campus-lobby-hall.jpg", caption: "Lobby" },
  { src: "/assets/campus-lawn.jpg", caption: "Campus lawn" },
  { src: "/assets/campus-building.jpg", caption: "Academic block" },
];
const SVIT_STATS = [
  { value: "2008", label: "Founded" },
  { value: "1,686", label: "Students (2026)" },
  { value: "402", label: "Placement offers (2026)" },
  { value: "33 LPA", label: "Highest package" },
  { value: "7.5 LPA", label: "Average package" },
  { value: "200+", label: "Companies visited" },
];
const SVIT_PROGRAMMES = [
  { name: "Computer Science & Engineering", note: "Intake 180" },
  { name: "CSE (AI & Machine Learning)", note: "Intake 120" },
  { name: "CSE (Data Science)", note: "Intake 120" },
  { name: "Electronics & Communication", note: "Intake 120" },
  { name: "CSE (Cyber Security)", note: "New from 2026-27" },
  { name: "CS (Business Systems)", note: "New from 2026-27" },
  { name: "Civil Engineering", note: "Intake 30" },
  { name: "Mechanical Engineering", note: "Intake 30" },
  { name: "MBA", note: "Through PGCET (code B269)" },
];
const SVIT_CAMPUS = [
  { icon: "apartment", title: "Hostels", body: "Separate on-campus hostels for boys and girls, vegetarian food, solar hot water and purified drinking water on every floor." },
  { icon: "directions_bus", title: "Transport", body: "8 college buses on routes across Bengaluru, with fixed morning pick-up times." },
  { icon: "local_library", title: "Library", body: "20,057 volumes, IEEE Xplore, ScienceDirect and Springer e-resources, and a fully automated digital library." },
  { icon: "sports_cricket", title: "Sports & clubs", body: "Cricket, basketball, volleyball, football, kabaddi, indoor games, a gym, NCC and NSS." },
  { icon: "science", title: "Laboratories", body: "Department labs for every branch and a Makers Space lab for projects." },
  { icon: "videocam", title: "Safe campus", body: "Green campus with CCTV in every classroom and strict hostel supervision." },
];
const SVIT_LEADERS = [
  { name: "Dr. Manjunath T N", role: "Principal" },
  { name: "Prof. M. R. Holla", role: "Mentor and guide" },
  { name: "Dr. Lakshminarayanachari K", role: "Vice Principal" },
  { name: "Dr. Vrinda Shetty", role: "Dean Academics" },
  { name: "Prof. R C Shanmukhaswamy", role: "Dean Administration" },
  { name: "Dr. T G Manjunatha", role: "Dean Student Affairs" },
];

function AboutSvit() {
  return (
    <section data-bg="bg-section-library" id="section-svit" className="flex flex-col gap-space-lg">
      <SectionIntro
        eyebrow="Our College"
        title="Sai Vidya Institute of Technology"
        body="Founded in 2008 by Sri Sai Vidya Vikas Shikshana Samithi with the motto “Learn to Lead”. Approved by AICTE, NAAC ‘A’ grade, affiliated to VTU, and autonomous for students joining from 2026."
      />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-space-md">
        {SVIT_PHOTOS.map((p) => (
          <figure key={p.src} className="relative rounded-lg overflow-hidden border border-white/30 shadow-2xl aspect-[4/3] m-0">
            <img src={p.src} alt={`SVIT ${p.caption.toLowerCase()}`} className="w-full h-full object-cover" loading="lazy" />
            <figcaption className="absolute left-0 right-0 bottom-0 px-3 py-2 text-white text-[13px] font-semibold" style={{ background: "linear-gradient(transparent, rgba(0,0,0,0.75))" }}>{p.caption}</figcaption>
          </figure>
        ))}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-space-md">
        {SVIT_STATS.map((s) => (
          <div key={s.label} className="p-space-md rounded-lg border border-white/30 backdrop-blur-2xl text-center" style={card}>
            <p className="text-white text-[26px] font-bold leading-tight glass-text-glow">{s.value}</p>
            <p className="text-slate-200 text-[13px] font-medium mt-1">{s.label}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-gutter items-stretch">
        <div className="lg:col-span-5 p-space-xl rounded-lg backdrop-blur-2xl shadow-2xl border border-white/30" style={cardLarge}>
          <h3 className="text-white font-bold glass-text-glow flex items-center gap-2"><Icon name="school" className="text-mk-secondary" />Programmes 2026-27</h3>
          <ul className="mt-space-md flex flex-col gap-2 list-none p-0 m-0">
            {SVIT_PROGRAMMES.map((p) => (
              <li key={p.name} className="flex items-center justify-between gap-3 px-3 py-2 rounded-DEFAULT border border-white/15" style={softFill}>
                <span className="text-white font-medium">{p.name}</span>
                <span className="text-mk-secondary text-[13px] font-semibold whitespace-nowrap">{p.note}</span>
              </li>
            ))}
          </ul>
          <p className="mt-space-md text-slate-200 text-[13px]">ISE has been merged into CSE for new admissions. Diploma holders can join the 2nd year of B.E. through DCET.</p>
        </div>
        <div className="lg:col-span-7 grid grid-cols-1 sm:grid-cols-2 gap-space-md">
          {SVIT_CAMPUS.map((c) => (
            <div key={c.title} className="p-space-lg rounded-lg border border-white/30 backdrop-blur-2xl shadow-2xl" style={card}>
              <div className="flex items-center gap-2.5">
                <span className="w-10 h-10 rounded-full flex items-center justify-center border border-white/30" style={lavenderFill}><Icon name={c.icon} className="text-white text-[22px]" /></span>
                <h3 className="text-white font-bold glass-text-glow">{c.title}</h3>
              </div>
              <p className="mt-2 text-slate-100 font-medium leading-relaxed">{c.body}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="p-space-xl rounded-lg backdrop-blur-2xl shadow-2xl border border-white/30" style={cardLarge}>
        <h3 className="text-white font-bold glass-text-glow flex items-center gap-2"><Icon name="groups" className="text-mk-secondary" />Leadership</h3>
        <div className="mt-space-md grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-space-md">
          {SVIT_LEADERS.map((l) => (
            <div key={l.name} className="px-4 py-3 rounded-DEFAULT border border-white/15" style={softFill}>
              <p className="text-white font-bold">{l.name}</p>
              <p className="text-mk-secondary text-[13px] font-semibold">{l.role}</p>
            </div>
          ))}
        </div>
        <p className="mt-space-md text-slate-300 text-[12.5px]">Source: saividya.ac.in and the SVIT admissions data, 2026. Ask Eva for the latest fees, cutoffs and seats.</p>
      </div>
    </section>
  );
}

export default function AboutPage() {
  const { ref, active } = useSectionBackground<HTMLElement>("bg-section-courtyard");

  return (
    <PageShell
      scope="pg-about"
      variant="marketing"
      title="About"
      className="antialiased selection:bg-[#7E82C2] selection:text-white relative"
      style={{ background: "linear-gradient(rgba(37, 14, 26, 0.96) 0%, rgba(48, 18, 36, 0.94) 50%, rgba(28, 11, 21, 0.98) 100%)" }}
      before={
        <>
          <CampusBackdrop
            active={active}
            images={{ "bg-section-quad": "/assets/campus-lobby-hall.jpg" }}   // 2026-11-01: lobby photo behind the team and college card
            overlay={
              <>
                <div className="absolute inset-0 pointer-events-none bg-gradient-to-tr from-[#7E82C2]/20 via-[#EBE7F5]/10 to-[#bfc2ff]/20 backdrop-blur-[2px]" />
                <div className="absolute inset-0 pointer-events-none" style={{ backgroundColor: "rgba(142, 48, 92, 0.16)", backdropFilter: "blur(1.5px)" }} />
              </>
            }
          />
          {/* 2026-11-01: the moving dots on the right (VantagePills) removed — they jumped around while scrolling */}
        </>
      }
      after={<FloatingMicButton variant="marketing" />}
    >
      <main ref={ref} className="relative z-10 w-full min-h-screen pt-20">
        <div className="flex flex-col w-full relative selection:bg-mk-secondary-container selection:text-white">
          <div className="relative z-10 w-full px-margin-mobile lg:px-margin max-w-7xl mx-auto flex flex-col gap-space-2xl pb-space-2xl">

            {/* ---------- Intro ---------- */}
            <section data-bg="bg-section-courtyard" id="section-hero" className="min-h-[46vh] flex flex-col justify-center items-start pt-space-xl relative">
              <div className="w-full max-w-4xl p-space-xl rounded-lg backdrop-blur-2xl shadow-2xl border border-white/30 flex flex-col items-start gap-space-md" style={cardLarge}>
                <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-white/30 shadow-sm" style={{ background: "rgba(191, 194, 255, 0.25)", backdropFilter: "blur(12px)" }}>
                  <span className="w-2 h-2 rounded-full bg-mk-secondary animate-pulse" />
                  <span className="uppercase tracking-widest font-bold whitespace-nowrap text-mk-secondary glass-text-glow">ABOUT INTELLIVOICE</span>
                </div>
                <h1 className="font-mk-display text-white tracking-tight max-w-3xl font-bold leading-tight glass-text-glow">
                  A Multilingual AI Admission Assistant for <span className="text-mk-secondary underline underline-offset-4">SVIT</span>
                </h1>
                <div className="p-4 rounded-DEFAULT w-full border border-white/20 shadow-sm backdrop-blur-md" style={softFill}>
                  <p className="text-slate-100 leading-relaxed font-medium glass-text-glow">
                    IntelliVoice is a final-year major project built by students of the Information Science &amp; Engineering Department at Sai Vidya Institute of Technology, Bengaluru. It helps students and parents get answers to admission questions by voice, in English, Kannada and Hindi.
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-space-sm mt-2">
                  <div className="flex items-center gap-2 px-4 py-2 rounded-full text-white font-bold border border-white/30 shadow-sm backdrop-blur-md" style={chipFill}>
                    <Icon name="translate" className="text-[18px] text-mk-secondary" />
                    English · <span style={{ fontFamily: '"Noto Sans Kannada", sans-serif' }}>ಕನ್ನಡ</span> · <span style={{ fontFamily: '"Noto Sans Devanagari", sans-serif' }}>हिंदी</span>
                  </div>
                  <div className="flex items-center gap-2 px-4 py-2 rounded-full text-white font-bold border border-white/30 shadow-sm backdrop-blur-md" style={chipFill}>
                    <Icon name="record_voice_over" className="text-[18px] text-mk-secondary" />
                    Voice-First Assistant
                  </div>
                </div>
              </div>
            </section>

            {/* ---------- What it is + campus photo ---------- */}
            <section className="grid grid-cols-1 lg:grid-cols-12 gap-gutter items-stretch">
              <div className="lg:col-span-7 flex flex-col justify-between p-space-xl rounded-lg backdrop-blur-2xl shadow-2xl border border-white/30" style={cardLarge}>
                <div>
                  <div className="flex items-center gap-2 mb-space-md text-mk-secondary font-bold glass-text-glow">
                    <Icon name="psychology" className="text-[22px]" />
                    <span className="uppercase tracking-wider text-mk-secondary">HOW INTELLIVOICE HELPS</span>
                  </div>
                  <h2 className="font-mk-headline-lg text-white mb-space-md font-bold glass-text-glow">What is IntelliVoice?</h2>
                  <p className="font-mk-body-md text-slate-100 leading-relaxed mb-space-md font-medium glass-text-glow">
                    IntelliVoice is a voice-first assistant designed for Sai Vidya Institute of Technology. Students and parents can ask about KCET and COMEDK cutoffs, branch details, fees, hostel facilities and the admission process, in their own language, including natural mixes like Kannada-English or Hindi-English.
                  </p>
                  <p className="font-mk-body-md text-slate-100 leading-relaxed font-medium glass-text-glow">
                    Spoken questions are converted to text using OpenAI Whisper, understood by a hybrid AI classifier, and answered using verified data from the SVIT admissions database. The AI only phrases the answer and never invents facts. Questions it cannot answer are directed to the admissions office.
                  </p>
                </div>
                <div className="flex flex-wrap gap-2.5 mt-space-xl pt-space-md p-3 rounded-DEFAULT border border-white/20 backdrop-blur-md" style={softFill}>
                  {[
                    { icon: "hub", text: "6-Engine Architecture" },
                    { icon: "database", text: "SVIT Admissions Database Grounding" },
                    { icon: "record_voice_over", text: "Voice Output via Sarvam AI" },
                  ].map((c) => (
                    <span key={c.text} className="px-3.5 py-1.5 rounded-full text-white font-bold shadow-sm flex items-center gap-1.5 border border-white/30 backdrop-blur-md" style={chipFill}>
                      <Icon name={c.icon} className="text-[15px] text-mk-secondary" />
                      {c.text}
                    </span>
                  ))}
                </div>
              </div>
              {/* 2026-11-01: opens SVIT on Google Maps */}
              <a href="https://www.google.com/maps/search/?api=1&query=Sai+Vidya+Institute+of+Technology+Rajanukunte+Bengaluru" target="_blank" rel="noopener noreferrer" title="Open SVIT on Google Maps" className="group lg:col-span-5 relative rounded-lg overflow-hidden backdrop-blur-xl shadow-2xl flex flex-col justify-end min-h-[360px] border border-white/90" style={{ boxShadow: "rgba(18, 20, 20, 0.1) 0px 20px 50px" }}>
                <img alt="SVIT campus building" className="absolute inset-0 w-full h-full object-cover transition-all duration-700 opacity-95 scale-105 hover:scale-100" src="/assets/campus-building.jpg" />
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
                <div className="relative z-10 p-space-lg m-4 rounded-DEFAULT backdrop-blur-md border border-white/30 shadow-xl" style={{ background: "rgba(20, 16, 28, 0.6)", backdropFilter: "blur(16px)" }}>
                  <span className="uppercase tracking-wider text-mk-secondary flex items-center gap-1.5 mb-1 font-bold glass-text-glow">
                    <Icon name="location_city" className="text-[16px]" />
                    SVIT CAMPUS
                  </span>
                  <p className="text-white font-bold glass-text-glow">Rajanukunte, Bengaluru</p>
                  <p className="mt-1 text-[13px] text-slate-200 flex items-center gap-1 group-hover:text-white"><Icon name="map" className="text-[16px]" />Open in Google Maps</p>
                </div>
              </a>
            </section>

            {/* ---------- About SVIT (2026-11-01): right after the campus card ---------- */}
            <AboutSvit />

            {/* ---------- The problem ---------- */}
            <section data-bg="bg-section-library" id="section-features" className="flex flex-col gap-space-lg">
              <SectionIntro
                eyebrow="THE PROBLEM"
                title="Why Admission Help Needs to Improve"
                body="During admission season, help desks receive the same questions again and again, and many students struggle to get clear answers in their own language."
              />
              <div className="grid grid-cols-1 md:grid-cols-3 gap-gutter">
                {PROBLEMS.map((p) => (
                  <div key={p.title} className="p-space-xl rounded-lg backdrop-blur-2xl shadow-2xl flex flex-col justify-between group hover:scale-[1.01] transition-all duration-300 border border-white/30" style={card}>
                    <div>
                      <div className="w-12 h-12 rounded-full flex items-center justify-center font-mk-display mb-space-lg shadow-sm border border-red-300/40 backdrop-blur-md" style={{ background: "rgba(239, 68, 68, 0.3)", color: "#fca5a5" }}>
                        <Icon name={p.icon} className="text-[26px]" />
                      </div>
                      <h3 className="font-title-lg text-white font-bold mb-2 glass-text-glow">{p.title}</h3>
                      <p className="font-mk-body-md text-slate-100 leading-relaxed font-medium glass-text-glow">{p.body}</p>
                    </div>
                    <div className="mt-space-lg pt-space-sm text-mk-secondary font-bold flex items-center gap-1.5 border-t border-white/20 glass-text-glow">
                      <span className="w-2 h-2 rounded-full bg-mk-secondary" />
                      {p.tag}
                    </div>
                  </div>
                ))}
              </div>
            </section>

            {/* ---------- Six engines ---------- */}
            <section data-bg="bg-section-library" className="flex flex-col gap-space-lg">
              <SectionIntro
                eyebrow="SYSTEM ARCHITECTURE"
                title="The Six Engines"
                body="A connected pipeline that understands the question, fetches verified facts from the database, and replies in the user's language by voice."
              />
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-gutter">
                {ENGINES.map((e) => (
                  <div key={e.n} className="p-space-xl rounded-lg backdrop-blur-2xl shadow-xl flex flex-col justify-between relative overflow-hidden group hover:scale-[1.01] transition-all border border-white/30" style={card}>
                    <div>
                      <div className="flex items-center justify-between mb-space-md">
                        <Icon name={e.icon} className="text-mk-secondary text-[32px]" />
                        <span className="px-2.5 py-0.5 rounded-full text-white font-bold border border-white/30" style={lavenderFill}>Engine {e.n}</span>
                      </div>
                      <h3 className="text-white mb-2 font-bold glass-text-glow">{e.title}</h3>
                      <p className="font-mk-body-md text-slate-100 leading-relaxed font-medium glass-text-glow">{e.body}</p>
                    </div>
                    <div className="mt-space-lg pt-space-sm flex items-center gap-2 text-mk-secondary font-bold border-t border-white/20 glass-text-glow">
                      <span className="w-2 h-2 rounded-full bg-mk-secondary" />
                      {e.tag}
                    </div>
                  </div>
                ))}
              </div>
              <div className="p-space-lg rounded-lg backdrop-blur-2xl shadow-xl border border-white/30 flex flex-col md:flex-row items-start md:items-center gap-space-md" style={card}>
                <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-white/30 shadow-sm flex-shrink-0" style={{ background: "rgba(191, 194, 255, 0.25)", backdropFilter: "blur(12px)" }}>
                  <Icon name="volume_up" className="text-[18px] text-mk-secondary" />
                  <span className="uppercase tracking-wider font-bold text-mk-secondary glass-text-glow">VOICE OUTPUT</span>
                </div>
                <p className="font-mk-body-md text-slate-100 leading-relaxed font-medium glass-text-glow">
                  Answers are spoken aloud using Sarvam AI&apos;s Bulbul text-to-speech, with natural Indian voices — Ritu for English, Simran for Hindi and Rupa for Kannada. Kannada responses are translated using Sarvam Mayura for natural, conversational Kannada.
                </p>
              </div>
            </section>

            {/* 2026-11-01: team member cards removed (San) */}

            {/* ---------- Institution ---------- */}
            <section data-bg="bg-section-quad" className="p-space-xl rounded-lg backdrop-blur-2xl shadow-2xl relative overflow-hidden border border-white/30" style={cardLarge}>
              <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-space-lg">
                <div className="flex items-start gap-space-md">
                  <div className="w-14 h-14 rounded-full flex-shrink-0 flex items-center justify-center text-white shadow-lg border border-white/40 backdrop-blur-md" style={lavenderFill}>
                    <Icon name="account_balance" className="text-[32px]" />
                  </div>
                  <div>
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      <h3 className="text-white font-bold glass-text-glow">Sai Vidya Institute of Technology</h3>
                      <span className="px-2.5 py-0.5 rounded-full text-white uppercase font-bold shadow-sm border border-white/30" style={lavenderFill}>Autonomous</span>
                    </div>
                    <p className="font-mk-body-md text-slate-100 flex items-center gap-1.5 mt-0.5 font-medium glass-text-glow">
                      <Icon name="pin_drop" className="text-[16px] text-mk-secondary" />
                      Rajanukunte, via Yelahanka, Bengaluru, Karnataka 560119
                    </p>
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-3">
                  {[["KCET Code", "E173"], ["COMEDK Code", "E113"], ["PGCET (MBA)", "B269"]].map(([k, v]) => (
                    <div key={k} className="px-4 py-2 rounded-DEFAULT text-white border border-white/30 font-bold shadow-md backdrop-blur-md" style={chipFill}>
                      {k}: <strong className="text-mk-secondary font-bold ml-1 glass-text-glow">{v}</strong>
                    </div>
                  ))}
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-space-md mt-space-xl pt-space-lg p-space-md rounded-DEFAULT border border-white/20 backdrop-blur-md" style={softFill}>
                {RECOGNITION.map((r) => (
                  <div key={r.label} className="flex items-center gap-2.5">
                    <Icon name={r.icon} className="text-mk-secondary text-[26px]" />
                    <div>
                      <p className="text-mk-secondary font-bold uppercase tracking-wider glass-text-glow">{r.label}</p>
                      <p className="text-white font-bold glass-text-glow">{r.value}</p>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <div className="text-center py-2 px-4 rounded-full mx-auto backdrop-blur-xl border border-white/30 text-slate-100 font-medium shadow-sm max-w-2xl glass-text-glow" style={{ ...card, background: "rgba(18, 22, 28, 0.6)", boxShadow: "rgba(0, 0, 0, 0.3) 0px 4px 20px" }}>
              ISE Final Year Major Project 2026-27 • Department of Information Science &amp; Engineering, Sai Vidya Institute of Technology, Bengaluru.
            </div>
          </div>
        </div>
      </main>
    </PageShell>
  );
}
