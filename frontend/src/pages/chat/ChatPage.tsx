import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { FloatingMicButton } from "../../components/FloatingMicButton";
import { Icon } from "../../components/Icon";
import { PageShell } from "../../components/PageShell";
import { useAuth } from "../../context/AuthContext";
import { RESPONSE_SHORT, SPEECH_OPTIONS, useLanguage } from "../../context/LanguageContext";
import { useElapsed } from "../../hooks/useElapsed";
import { useRecorder, type RecorderError } from "../../hooks/useRecorder";
import { storage } from "../../lib/storage";
import { MessageList, Welcome } from "./Messages";
import { MicDock } from "./MicDock";
import { PipelineBar } from "./PipelineBar";
import { LanguageCard, OneTapPanel, QueryContextCard, UnderstandingPanel, toQueryContext, type ContextFields } from "./SidePanels";
import { useChat } from "./useChat";

const MIC_ERRORS: Record<RecorderError, string> = {
  unsupported: "Voice recording isn't supported in this browser. Please use Chrome or Edge, or type your question.",
  denied: "Microphone access was blocked. Click the lock icon in the address bar, allow the microphone, and try again.",
  "no-mic": "No microphone was found. Please connect one, or type your question.",
  failed: "Couldn't start the microphone. Please type your question instead.",
};

const SHORTCUTS = [
  { icon: "apartment", title: "Hostel facilities", sub: "Rooms, mess, fee & rules", q: "What hostel facilities are available at SVIT?" },
  { icon: "workspace_premium", title: "Placement companies", sub: "Top recruiters & packages", q: "Which companies come to SVIT for placements?" },
  { icon: "commute", title: "Transport & bus routes", sub: "City pickup & metro feeder", q: "What transport and bus routes does SVIT have?" },
];

export default function ChatPage() {
  const { token } = useAuth();
  const { speechLanguage, responseLanguage, setSpeechLanguage, setResponseLanguage } = useLanguage();
  const [params, setParams] = useSearchParams();

  const [ctx, setCtx] = useState<ContextFields>({ rank: "", category: "", branch: "" });
  const ctxRef = useRef(ctx);
  ctxRef.current = ctx;
  const getContext = useCallback(() => toQueryContext(ctxRef.current), []);

  const chat = useChat({ getContext, token, speechLanguage, responseLanguage });
  const elapsed = useElapsed(chat.sessionId);

  // ---- audio playback: one reply at a time, optional auto-play ----
  const [autoplay, setAutoplay] = useState(() => storage.get("iv_autoplay") !== "off");
  const current = useRef<HTMLAudioElement | null>(null);
  const audioControl = {
    autoplay,
    claim: (a: HTMLAudioElement) => {
      if (current.current && current.current !== a) current.current.pause();
      current.current = a;
    },
  };
  const toggleAutoplay = () => {
    setAutoplay((on) => {
      storage.set("iv_autoplay", on ? "off" : "on");
      return !on;
    });
  };

  // ---- microphone ----
  const { setStatus, ask } = chat;
  const recorder = useRecorder({
    onRecorded: (audio) => void ask({ audio }),
    onTooShort: () => setStatus("That was too short. Tap the mic and speak your full question.", "mic"),
    onError: (kind) => setStatus(MIC_ERRORS[kind], "mic_off"),
  });
  const { recording, start, stop, toggle } = recorder;

  useEffect(() => {
    if (recording) {
      current.current?.pause();
      setStatus("Listening… speak in English, ಕನ್ನಡ or हिंदी", "graphic_eq");
    }
  }, [recording, setStatus]);

  // hold SPACEBAR to talk (when not typing in a field)
  useEffect(() => {
    let held = false;
    const typing = () => ["INPUT", "TEXTAREA", "SELECT", "BUTTON", "A"].includes(document.activeElement?.tagName ?? "");
    const down = (e: KeyboardEvent) => {
      if (e.code !== "Space" || e.repeat || typing()) return;
      e.preventDefault();
      held = true;
      void start();
    };
    const up = (e: KeyboardEvent) => {
      if (e.code !== "Space" || !held) return;
      e.preventDefault();
      held = false;
      stop();
    };
    window.addEventListener("keydown", down);
    window.addEventListener("keyup", up);
    return () => {
      window.removeEventListener("keydown", down);
      window.removeEventListener("keyup", up);
    };
  }, [start, stop]);

  // question handed over from another page: /chat?q=...
  useEffect(() => {
    const q = params.get("q");
    if (q) {
      setParams({}, { replace: true });
      void ask({ text: q.slice(0, 500) });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // keep the newest message in view
  const scrollRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [chat.messages.length, chat.busy]);

  const askText = (q: string) => void ask({ text: q });

  const saveChat = () => {
    const lines = ["IntelliVoice — SVIT Admission Assistant", `Saved ${new Date().toLocaleString()}`, ""];
    for (const m of chat.messages) {
      if (m.kind === "user" && !m.pending) lines.push(`[${m.at.toLocaleTimeString()}] You: ${m.text}`, "");
      if (m.kind === "bot") lines.push(`[${m.at.toLocaleTimeString()}] IntelliVoice: ${m.res.response?.text ?? ""}`, "");
    }
    if (lines.length === 3) {
      setStatus("Nothing to save yet. Ask a question first.", "info");
      return;
    }
    const url = URL.createObjectURL(new Blob([lines.join("\n")], { type: "text/plain;charset=utf-8" }));
    const a = Object.assign(document.createElement("a"), { href: url, download: "intellivoice-chat.txt" });
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  const newChat = () => {
    if (recording) stop();
    current.current?.pause();
    chat.reset();
  };

  const topic = chat.memory?.topic;
  const contextUsed = chat.memory?.context_used?.filter(Boolean) ?? [];

  return (
    <PageShell
      scope="pg-chat"
      variant="app"
      title="Voice Chat"
      className="bg-background font-body-md text-on-surface antialiased selection:bg-secondary-container selection:text-on-secondary-container"
      after={<FloatingMicButton variant="app" onClick={toggle} active={recording} />}
    >
      <main className="w-full pt-20 bg-background min-h-screen relative">
        <div className="flex flex-col w-full relative -mt-20">
          <div className="fixed inset-0 z-0 pointer-events-none bg-cover bg-center" style={{ backgroundImage: 'url("/assets/campus-corridor.jpg")' }} aria-hidden="true">
            <div className="absolute inset-0 bg-black/15 pointer-events-none" />
            <div className="absolute inset-0 bg-gradient-to-b from-black/40 via-transparent to-black/60 pointer-events-none" />
          </div>

          <div className="relative z-10 w-full px-margin-mobile lg:px-margin pt-28 pb-12 flex flex-col gap-space-lg min-h-screen">
            <PipelineBar stages={chat.stages} elapsed={elapsed} />

            <div className="w-full grid grid-cols-1 lg:grid-cols-12 gap-space-lg items-start">
              {/* ---------- left: context, engine 2, quick questions ---------- */}
              <aside className="order-2 lg:order-none lg:col-span-4 xl:col-span-3 flex flex-col gap-space-md">
                <LanguageCard
                  speech={speechLanguage}
                  response={responseLanguage}
                  onSpeech={setSpeechLanguage}
                  onResponse={setResponseLanguage}
                />
                <QueryContextCard value={ctx} onChange={setCtx} />
                <UnderstandingPanel data={chat.understanding} busy={chat.busy} />
                <OneTapPanel onAsk={askText} disabled={chat.busy} />
              </aside>

              {/* ---------- right: conversation ---------- */}
              <section className="order-1 lg:order-none lg:col-span-8 xl:col-span-9 flex flex-col gap-space-md" aria-label="Conversation">
                {topic && (
                  <div
                    className="w-full rounded-[2rem] sm:rounded-full px-space-lg py-space-sm shadow-[0_8px_32px_rgba(0,0,0,0.5)] flex flex-wrap items-center justify-between gap-space-sm"
                    style={{ background: "linear-gradient(90deg, rgba(32, 20, 56, 0.32), rgba(20, 22, 48, 0.28))", backdropFilter: "blur(20px)", border: "1px solid rgba(216, 180, 254, 0.3)", boxShadow: "rgba(0, 0, 0, 0.35) 0px 8px 32px, rgba(168, 85, 247, 0.15) 0px 0px 20px", textShadow: "rgba(0, 0, 0, 0.8) 0px 1px 3px" }}
                  >
                    <div className="flex items-center gap-space-sm min-w-0 flex-wrap">
                      <Icon name="memory" className="text-[20px] text-secondary font-bold flex-shrink-0" />
                      <span className="font-title-md text-title-md text-white font-bold truncate">Current Topic: {topic}</span>
                      {contextUsed.length > 0 && (
                        <span className="px-2.5 py-0.5 rounded-full bg-white/15 text-white font-label-sm text-label-sm font-semibold border border-white/20">
                          Using context: {contextUsed.join(", ")}
                        </span>
                      )}
                    </div>
                    <button type="button" onClick={newChat} aria-label="Start a new chat" className="px-3 py-1 rounded-full bg-white/20 hover:bg-white/30 text-white font-label-sm text-label-sm font-bold flex items-center gap-1 transition-colors border border-white/25">
                      <Icon name="refresh" className="text-[16px] font-bold" />
                      <span>New Chat</span>
                    </button>
                  </div>
                )}

                <div
                  className="rounded-xl p-space-md md:p-space-lg shadow-[0_20px_50px_rgba(0,0,0,0.7)] flex flex-col gap-space-lg"
                  style={{ background: "linear-gradient(135deg, rgba(20, 16, 38, 0.32), rgba(28, 22, 54, 0.28))", backdropFilter: "blur(24px)", border: "1px solid rgba(191, 194, 255, 0.28)", boxShadow: "rgba(0, 0, 0, 0.45) 0px 20px 50px, rgba(130, 120, 240, 0.12) 0px 0px 35px", textShadow: "rgba(0, 0, 0, 0.7) 0px 1px 3px" }}
                >
                  <div className="flex flex-wrap items-center justify-between pb-space-md gap-space-md border-b border-white/10">
                    <div className="flex items-center gap-space-sm">
                      <div className="w-9 h-9 rounded-full bg-black/50 border border-white/20 flex items-center justify-center text-secondary shadow-[0_0_12px_rgba(191,194,255,0.3)]">
                        <Icon name="account_balance" className="text-[20px] font-bold" />
                      </div>
                      <div className="flex flex-col">
                        <span className="font-title-md text-title-md text-white font-bold leading-tight">IntelliVoice Admission Desk</span>
                        <span className="font-label-sm text-label-sm text-secondary font-medium">Sai Vidya Institute of Technology • Bengaluru</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-space-sm">
                      <button type="button" onClick={saveChat} className="px-4 py-1.5 rounded-full text-white font-label-md text-label-md font-semibold flex items-center gap-1.5 transition-colors shadow-sm" style={{ backgroundColor: "rgb(88, 92, 176)", border: "1px solid rgba(255, 255, 255, 0.35)", textShadow: "rgba(0, 0, 0, 0.7) 0px 1px 2px" }}>
                        <Icon name="download" className="text-[16px] font-bold" />
                        <span>Save Chat (.txt)</span>
                      </button>
                      <button type="button" onClick={toggleAutoplay} aria-pressed={autoplay} title={`Auto-play voice replies: ${autoplay ? "on" : "off"}`} className="w-8 h-8 rounded-full bg-black/40 border border-white/20 hover:bg-white/20 text-white flex items-center justify-center transition-colors">
                        <Icon name={autoplay ? "volume_up" : "volume_off"} className="text-[18px]" />
                      </button>
                      <button type="button" onClick={newChat} title="New chat" aria-label="Start a new chat" className="w-8 h-8 rounded-full bg-black/40 border border-white/20 hover:bg-white/20 text-white flex items-center justify-center transition-colors">
                        <Icon name="history_edu" className="text-[18px]" />
                      </button>
                    </div>
                  </div>

                  <div ref={scrollRef} className="flex flex-col gap-space-lg max-h-[580px] overflow-y-auto pr-1" aria-live="polite">
                    {chat.messages.length === 0 && !chat.busy ? (
                      <Welcome onAsk={askText} disabled={chat.busy} />
                    ) : (
                      <MessageList messages={chat.messages} busy={chat.busy} control={audioControl} onRetry={chat.retry} />
                    )}
                  </div>

                  <MicDock
                    languageSummary={`Speaking: ${SPEECH_OPTIONS.find((o) => o.value === speechLanguage)?.label.replace(/ \(.*\)$/, "") ?? "Auto-detect"} · Reply: ${RESPONSE_SHORT[responseLanguage]}`}
                    recording={recording}
                    levels={recorder.levels}
                    busy={chat.busy}
                    status={chat.status}
                    onMic={toggle}
                    onSend={askText}
                  />
                </div>

                <div className="w-full grid grid-cols-1 md:grid-cols-3 gap-space-md">
                  {SHORTCUTS.map((s) => (
                    <button
                      key={s.title}
                      type="button"
                      disabled={chat.busy}
                      onClick={() => askText(s.q)}
                      className="p-space-md rounded-lg flex items-center justify-between gap-space-md shadow-[0_8px_28px_rgba(0,0,0,0.5)] transition-all hover:scale-105 active:scale-95 group text-left cursor-pointer disabled:opacity-60"
                      style={{ background: "rgba(18, 20, 20, 0.3)", backdropFilter: "blur(20px)", border: "1px solid rgba(255, 255, 255, 0.25)", textShadow: "rgba(0, 0, 0, 0.7) 0px 1px 3px" }}
                    >
                      <div className="flex items-center gap-space-md min-w-0">
                        <div className="w-10 h-10 rounded-full flex items-center justify-center text-white flex-shrink-0 shadow-md" style={{ backgroundColor: "#585cb0", border: "1px solid rgba(255, 255, 255, 0.3)" }}>
                          <Icon name={s.icon} className="text-[20px] font-bold" />
                        </div>
                        <div className="flex flex-col min-w-0">
                          <span className="font-title-md text-title-md text-white font-bold truncate">{s.title}</span>
                          <span className="font-body-sm text-body-sm text-white/90 font-medium truncate">{s.sub}</span>
                        </div>
                      </div>
                      <Icon name="north_east" className="text-[20px] text-secondary group-hover:translate-x-0.5 transition-transform flex-shrink-0" />
                    </button>
                  ))}
                </div>
              </section>
            </div>
          </div>
        </div>
      </main>
    </PageShell>
  );
}
