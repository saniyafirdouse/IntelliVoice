import { Link } from "react-router-dom";
import { CampusBackdrop, VantagePills } from "../components/CampusBackdrop";
import { EvaAvatar } from "../components/EvaAvatar";
import { Icon } from "../components/Icon";
import { PageShell } from "../components/PageShell";
import { useLanguage } from "../context/LanguageContext";
import { useSectionBackground } from "../hooks/useSectionBackground";
import type { LangCode } from "../lib/types";

const HERO_LANGS: { code: LangCode; label: string; font?: string }[] = [
  { code: "en", label: "English" },
  { code: "kn", label: "ಕನ್ನಡ (Kannada)", font: '"Noto Sans Kannada", Inter, sans-serif' },
  { code: "hi", label: "हिंदी (Hindi)", font: '"Noto Sans Devanagari", Inter, sans-serif' },
];


const ENGINES = [
  { code: "E1", icon: "translate", title: "Engine 1: Language", body: "Real-time acoustic dialect detection and code-mixed stream parsing across Kannada, Hindi, and English (including Kanglish and Hinglish).", footIcon: "check_circle", foot: "Code-mixed Speech Detection" },
  { code: "E2", icon: "psychology", title: "Engine 2: Understanding", body: "Fine-grained Intent Extraction across 11 Entity Types with automated emotion detection and responsive conversational mode classification.", footIcon: "check_circle", foot: "11 Entity Types & Intent Parsing" },
  { code: "E3", icon: "verified", title: "Engine 3: Knowledge", body: "Grounded semantic retrieval from the verified SVIT Admissions Database, guaranteeing zero hallucination for cutoffs, seats, and programs.", footIcon: "check_circle", foot: "Verified Institutional Data" },
  { code: "E4", icon: "history", title: "Engine 4: Memory", body: "Multi-turn session state management, retaining inquiry context, user category, preferred course branch, and conversational topic history.", footIcon: "check_circle", foot: "Multi-turn Topic Retention" },
  { code: "E5", icon: "dynamic_form", title: "Engine 5: Response", body: "Adaptive dynamic generation featuring dedicated modes: Informational briefing, Reassurance, Branch Comparison, and Human Escalation.", footIcon: "check_circle", foot: "Adaptive Response & Escalation" },
  { code: "E6", icon: "bar_chart", title: "Engine 6: Analytics", body: "Logs queries and system performance to help the admissions team understand what students ask most.", footIcon: "insights", foot: "Query Analytics" },
];

const STATS = [
  { value: "6", label: "Core Engines", note: "Integrated neural pipeline" },
  { value: "11", label: "Entity Types", note: "Accurate intent parsing" },
  { value: "100%", label: "Intent Accuracy", note: "Held-out Test Set" },
  { value: "3", label: "Languages", note: "Kannada, Hindi & English" },
];

const HIGHLIGHTS = [
  { icon: "local_library", title: "SVIT Central Library", body: "Spread over 15,000 sq.ft with dedicated digital audio-visual zones, national journals, e-consortium access, and quiet study alcoves." },
  { icon: "memory", title: "ISE & CSE Innovations", body: "Specialized Labs in AI/ML, Cyber Security, Cloud Computing, and Edge Computing. Home to student projects like IntelliVoice." },
  { icon: "corporate_fare", title: "Top Corporate Recruiters", body: "TCS, Infosys, Capgemini, Wipro, Mindtree, Cognizant, Toyota, and specialized fintech engineering firms visit campus annually." },
];

// 2026-11-02: QR code of the address this page was opened with. On expo day the stall screen
// opens the tunnel address, so the code always matches the current tunnel (it changes each start).
function PhoneQrCard() {
  const { hostname, origin } = window.location;
  if (/^(localhost|127\.0\.0\.1|\[::1\])$/.test(hostname)) return null;
  const url = `${origin}/chat`;
  const qr = `https://api.qrserver.com/v1/create-qr-code/?size=640x640&margin=12&data=${encodeURIComponent(url)}`;
  // 2026-11-02: same look as the /expo page (big QR code, steps, Eva)
  return (
    <div className="mb-10 w-full max-w-4xl grid grid-cols-1 md:grid-cols-2 gap-8 items-center rounded-[28px] p-6 md:p-10 text-left"
      style={{ background: "linear-gradient(160deg, rgba(34, 24, 52, 0.88), rgba(18, 14, 28, 0.92))", border: "1px solid rgba(232, 211, 163, 0.45)", boxShadow: "0 24px 60px rgba(0,0,0,0.5)" }}>
      <div className="flex flex-col gap-5">
        <div className="flex items-center gap-4">
          <EvaAvatar size={72} />
          <div>
            <p className="text-[14px] font-semibold" style={{ color: "#e8d3a3" }}>SVIT Admissions · IntelliVoice</p>
            <h2 className="text-[30px] md:text-[38px] font-bold leading-tight text-white">Talk to Eva on your phone</h2>
          </div>
        </div>
        <p className="text-[17px] text-white/90 leading-relaxed">Ask about admissions, fees, cutoffs, hostel, buses and placements, in English, ಕನ್ನಡ or हिंदी.</p>
        <ol className="flex flex-col gap-3 list-none p-0 m-0">
          {[
            { icon: "qr_code_scanner", text: "Scan the code with your phone camera" },
            { icon: "mic", text: "Allow the microphone when asked" },
            { icon: "record_voice_over", text: "Say “Hey Eva” or tap Speak to Eva, and ask" },
          ].map((step, i) => (
            <li key={step.icon} className="flex items-center gap-3 text-[16px] text-white">
              <span className="w-8 h-8 rounded-full flex items-center justify-center font-bold flex-shrink-0" style={{ background: "#e8d3a3", color: "#2d1f45" }}>{i + 1}</span>
              <Icon name={step.icon} className="text-[21px] text-white/80" />
              {step.text}
            </li>
          ))}
        </ol>
        <p className="text-[13px] text-white/60">Each phone can ask 10 questions every 5 minutes, so everyone gets a turn. Works best in Chrome.</p>
      </div>
      <div className="flex flex-col items-center gap-3">
        <div className="rounded-2xl p-3 bg-white" style={{ boxShadow: "0 0 0 6px rgba(232, 211, 163, 0.5)" }}>
          <img src={qr} alt="QR code to open Eva on your phone" width={280} height={280} className="w-[min(64vw,280px)] h-[min(64vw,280px)]" />
        </div>
        <p className="text-[14px] font-semibold break-all text-center" style={{ color: "#e8d3a3" }}>{url}</p>
      </div>
    </div>
  );
}

export default function HomePage() {
  const { ref, active } = useSectionBackground<HTMLElement>("bg-section-courtyard");
  const { quickLanguage: language, setQuickLanguage: setLanguage } = useLanguage();

  return (
    <PageShell
      scope="pg-home"
      variant="marketing"
      title="Home"
      className="antialiased selection:bg-[#7E82C2] selection:text-white relative"
      before={
        <>
          <CampusBackdrop
            active={active}
            images={{ "bg-section-quad": "/assets/campus-front.jpg" }}   // 2026-10-17: SVIT front entrance on the first screen
            overlay={
              <>
                <div className="glass-veil" style={{ background: "linear-gradient(rgba(16, 12, 30, 0.25) 0%, rgba(20, 15, 38, 0.15) 50%, rgba(10, 8, 20, 0.35) 100%)", pointerEvents: "none" }} />
                <div className="absolute inset-0 bg-gradient-to-b from-[#100c1e]/20 via-transparent to-[#0a0814]/30 pointer-events-none" />
              </>
            }
          />
          <VantagePills active={active} />
        </>
      }
    >
      <main ref={ref} className="relative z-10 w-full min-h-screen pt-20">
        {/* ---------- Hero ---------- */}
        <section className="min-h-screen flex flex-col justify-center items-center text-center px-margin-mobile lg:px-margin pt-10 pb-16 relative" data-bg="bg-section-quad" id="section-hero">
          <div className="max-w-5xl mx-auto flex flex-col items-center mt-auto mb-auto">
            <div className="inline-flex items-center gap-space-sm px-4 py-2 rounded-full mb-6 glass-card shadow-lg max-w-full">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse flex-shrink-0" />
              <span className="text-xs sm:text-sm font-semibold text-white tracking-wide whitespace-normal text-center drop-shadow-sm">
                🏛️ Sai Vidya Institute of Technology — Rajanukunte, Bengaluru • VTU Affiliated • KCET Code: E173
              </span>
            </div>
            <h1 className="font-mk-display text-4xl sm:text-5xl md:text-[66px] font-extrabold tracking-tight text-white mb-6 max-w-4xl text-balance leading-[1.12] drop-shadow-[0_4px_24px_rgba(20,10,35,0.45)]">
              Your SVIT admission questions, <span className="text-white font-extrabold">answered in seconds.</span>
            </h1>
            <p className="text-base sm:text-xl text-white/95 max-w-2xl mb-8 text-balance font-medium leading-relaxed drop-shadow-[0_2px_12px_rgba(10,5,20,0.5)]">
              Ask in Hindi, Kannada, or English. Voice or text. Available 24 hours a day, 365 days a year for VTU, KCET &amp; COMEDK admissions.
            </p>

            <div className="inline-flex flex-wrap justify-center items-center p-1.5 rounded-full gap-1.5 mb-8 glass-card" role="group" aria-label="Preferred language">
              {HERO_LANGS.map((l) => {
                const on = l.code === language;
                return (
                  <button
                    key={l.code}
                    type="button"
                    aria-pressed={on}
                    onClick={() => setLanguage(l.code)}
                    className={`px-5 py-2 rounded-full text-xs sm:text-sm text-white transition-all duration-300 ${on ? "font-bold" : "font-semibold hover:bg-white/20"}`}
                    style={{
                      fontFamily: l.font,
                      ...(on
                        ? { background: "rgba(126, 130, 194, 0.85)", border: "1px solid rgba(255, 255, 255, 0.6)", boxShadow: "rgba(126, 130, 194, 0.45) 0px 4px 18px" }
                        : { background: "rgba(255, 255, 255, 0.12)", border: "1px solid rgba(255, 255, 255, 0.28)" }),
                    }}
                  >
                    {l.label}
                  </button>
                );
              })}
            </div>

            <div className="flex flex-wrap items-center justify-center gap-4 mb-10">
              {/* 2026-11-01: one clear way in — "Talk to Eva" (Start Talking Now, the sample-question buttons and the floating mic were removed) */}
              <Link to="/chat" className="group relative pl-2 pr-8 py-2 rounded-full text-white font-bold text-base sm:text-lg flex items-center gap-3 transition-all duration-300 hover:scale-105 active:scale-95 cursor-pointer shadow-xl" style={{ background: "linear-gradient(135deg, rgba(62, 40, 92, 0.92), rgba(36, 24, 52, 0.92))", border: "1px solid rgba(232, 211, 163, 0.7)" }}>
                <EvaAvatar size={52} />
                <span className="flex flex-col items-start leading-tight">
                  <span>Talk to Eva</span>
                  <span className="text-[12px] sm:text-[13px] font-medium text-white/75">SVIT's admission assistant</span>
                </span>
                <span className="absolute -inset-1 rounded-full blur-md -z-10 transition-all" style={{ background: "rgba(232, 211, 163, 0.25)" }} />
              </Link>
              <a href="#section-features" className="px-8 py-4 rounded-full text-white font-semibold text-base sm:text-lg glass-card glass-card-hover transition-all duration-200 flex items-center gap-2">
                <span>Explore Capabilities</span>
                <Icon name="arrow_downward" className="text-[20px]" />
              </a>
            </div>

            {/* 2026-11-02: "Use Eva on your phone" — only when the site was opened through the
                Cloudflare tunnel (a localhost QR code would not work on phones). */}
            <PhoneQrCard />

          </div>
          <div className="mt-6">
            <a aria-label="Scroll down" className="animate-bounce inline-flex p-2 rounded-full text-white/80 hover:text-white glass-card" href="#section-features">
              <Icon name="keyboard_double_arrow_down" className="text-[26px]" />
            </a>
          </div>
        </section>

        {/* ---------- Six engines ---------- */}
        <section className="min-h-screen flex flex-col justify-center px-margin-mobile lg:px-margin py-20 relative" data-bg="bg-section-library" id="section-features">
          <div className="max-w-6xl mx-auto w-full flex flex-col gap-10">
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
              <div>
                <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full glass-card text-white text-xs font-bold uppercase tracking-wider mb-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-400" />
                  <span>Autonomous Voice AI Engine</span>
                </div>
                <h2 className="font-mk-display text-3xl sm:text-4xl md:text-5xl font-extrabold text-white tracking-tight drop-shadow-md">
                  Architectural Edge: Built for admissions
                </h2>
              </div>
              <p className="text-white/90 text-sm sm:text-base max-w-md font-medium leading-relaxed glass-card p-4 rounded-2xl">
                A high-performance pipeline powered by 6 dedicated neural engines, delivering zero-hallucination admission guidance grounded in the verified SVIT Admissions Database.
              </p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {ENGINES.map((e) => (
                <div key={e.code} className="glass-card glass-card-hover p-6 rounded-2xl flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between mb-4">
                      <div className="w-12 h-12 rounded-xl bg-[#7E82C2]/60 text-white flex items-center justify-center border border-white/40 shadow-md">
                        <Icon name={e.icon} className="text-[26px]" />
                      </div>
                      <span className="text-xs font-mono font-bold text-white/80 px-2 py-0.5 rounded-full bg-white/10">{e.code}</span>
                    </div>
                    <h3 className="font-mk-display font-bold text-lg text-white mb-2">{e.title}</h3>
                    <p className="text-white/85 text-sm leading-relaxed">{e.body}</p>
                  </div>
                  <div className="mt-4 pt-3 border-t border-white/20 flex items-center text-xs text-[#EBE7F5] font-semibold gap-1">
                    <Icon name={e.footIcon} className="text-[16px]" />
                    {e.foot}
                  </div>
                </div>
              ))}
            </div>
            <div className="text-center mt-2 px-4 py-2 rounded-full glass-card inline-flex mx-auto items-center justify-center text-xs text-white/80 font-medium tracking-wide shadow-sm">
              <span>Voice input via OpenAI Whisper · Voice output via Sarvam AI Bulbul (Ritu, Simran, Rupa)</span>
            </div>
          </div>
        </section>

        {/* ---------- Numbers & campus ---------- */}
        <section className="min-h-screen flex flex-col justify-center px-margin-mobile lg:px-margin py-20 relative" data-bg="bg-section-library" id="section-academics">
          <div className="max-w-6xl mx-auto w-full flex flex-col gap-10">
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
              <div>
                <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full glass-card text-white text-xs font-bold uppercase tracking-wider mb-2">
                  <span className="w-2 h-2 rounded-full bg-[#bfc2ff]" />
                  <span>Grounding: Verified Institutional Data</span>
                </div>
                <h2 className="font-mk-display text-3xl sm:text-4xl md:text-5xl font-extrabold text-white tracking-tight drop-shadow-md">
                  Academic Excellence &amp; Placements
                </h2>
              </div>
              <div className="glass-card px-5 py-3 rounded-2xl text-center md:text-right">
                <span className="text-xs uppercase tracking-wider text-white/80 font-bold block">Source</span>
                <span className="font-mk-display text-lg font-bold text-white">SVIT Admissions Database</span>
              </div>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 sm:gap-6">
              {STATS.map((s) => (
                <div key={s.label} className="glass-card glass-card-hover p-6 rounded-2xl text-center flex flex-col items-center">
                  <span className="font-mk-display text-3xl sm:text-5xl font-extrabold text-white">{s.value}</span>
                  <span className="text-xs sm:text-sm font-bold text-white mt-2">{s.label}</span>
                  <span className="text-xs text-white/80 mt-1">{s.note}</span>
                </div>
              ))}
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {HIGHLIGHTS.map((h) => (
                <div key={h.title} className="glass-card p-6 rounded-2xl">
                  <div className="flex items-center gap-3 mb-3">
                    <Icon name={h.icon} className="text-[24px] text-white" />
                    <h3 className="font-mk-display font-bold text-base text-white">{h.title}</h3>
                  </div>
                  <p className="text-xs sm:text-sm text-white/85 leading-relaxed">{h.body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ---------- Call to action ---------- */}
        <section className="min-h-screen flex flex-col justify-center items-center px-margin-mobile lg:px-margin py-20 relative" data-bg="bg-section-courtyard" id="section-cta">
          <div className="max-w-4xl mx-auto w-full glass-card p-8 sm:p-12 md:p-16 rounded-3xl text-center flex flex-col items-center shadow-2xl relative">
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full mb-6 glass-card text-white text-xs font-bold uppercase tracking-wider">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              <span>Source: SVIT Admissions Database</span>
            </div>
            <h2 className="font-mk-display text-3xl sm:text-4xl md:text-5xl font-extrabold text-white max-w-2xl mb-4 leading-tight drop-shadow-md">
              Ready to get started? Experience next-generation admissions.
            </h2>
            <p className="text-sm sm:text-lg text-white/95 max-w-xl mb-8 leading-relaxed font-medium">
              Skip long queues and phone holds. Get accurate, verified admission guidelines for CET, COMEDK, and Management quotas right now in English, Kannada, or Hindi.
            </p>
            <div className="flex flex-col sm:flex-row items-center gap-4 w-full sm:w-auto">
              <Link to="/help" className="w-full sm:w-auto px-8 py-4 rounded-full text-white font-semibold text-base sm:text-lg glass-card glass-card-hover transition-all flex items-center justify-center gap-2">
                <span>Read Admission FAQ</span>
                <Icon name="arrow_forward" className="text-[18px]" />
              </Link>
            </div>
            <div className="mt-10 pt-6 border-t border-white/20 flex flex-wrap items-center justify-center gap-6 text-xs text-white/85 font-medium">
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
                6-Engine Neural Pipeline Active
              </span>
              <span>•</span>
              <span>Grounding: Verified Institutional Data</span>
              <span>•</span>
              <span>Voices: Ritu, Simran &amp; Rupa</span>
            </div>
          </div>
        </section>
      </main>
    </PageShell>
  );
}
