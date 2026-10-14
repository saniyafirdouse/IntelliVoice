import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Icon } from "../../components/Icon";
import { PageShell } from "../../components/PageShell";
import { useAuth } from "../../context/AuthContext";
import { RESPONSE_SHORT, SPEECH_OPTIONS, useLanguage } from "../../context/LanguageContext";
import { useRecorder, type RecorderError } from "../../hooks/useRecorder";
import { storage } from "../../lib/storage";
import { MessageList } from "./Messages";
import { ActionCards, CHAT_HOME_CSS, ChatHeading, Composer, DecorLine, HandsFreeSide, HumanOfficerCard, TryAsking } from "./ChatHome";
import { VoiceConversation } from "./VoiceConversation";
import { useVoiceConversation } from "./useVoiceConversation";
import { ContactDialog } from "./ContactDialog";
import { useChat } from "./useChat";

const MIC_ERRORS: Record<RecorderError, string> = {
  unsupported: "Voice recording isn't supported in this browser. Please use Chrome or Edge, or type your question.",
  denied: "Microphone access was blocked. Click the lock icon in the address bar, allow the microphone, and try again.",
  "no-mic": "No microphone was found. Please connect one, or type your question.",
  failed: "Couldn't start the microphone. Please type your question instead.",
};

const TOOL_BTN = "h-10 px-4 rounded-full text-white text-[13.5px] font-medium flex items-center gap-1.5 transition-all hover:brightness-125 disabled:opacity-60";
const TOOL_ICON = "w-10 h-10 rounded-full text-white flex items-center justify-center transition-all hover:brightness-125";
const TOOL_STYLE = { background: "rgba(24, 22, 18, 0.62)", border: "1px solid rgba(255, 255, 255, 0.16)", backdropFilter: "blur(12px)", WebkitBackdropFilter: "blur(12px)" } as const;

export default function ChatPage() {
  const { token } = useAuth();
  const { speechLanguage, responseLanguage } = useLanguage();
  const [params, setParams] = useSearchParams();

  // (2026-10-13: the "Your Query Context" box was removed — no extra filters are sent)
  const getContext = useCallback(() => null, []);

  const chat = useChat({ getContext, token, speechLanguage, responseLanguage });

  // ---- audio playback: one reply at a time, optional auto-play ----
  const [autoplay, setAutoplay] = useState(() => storage.get("iv_autoplay") !== "off");
  const current = useRef<HTMLAudioElement | null>(null);
  const [conversationOn, setConversationOn] = useState(false);
  const audioControl = {
    autoplay: autoplay && !conversationOn,   // the conversation plays its own replies
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
  const { recording, start, stop } = recorder;

  // ---- hands-free voice conversation ----
  const conversation = useVoiceConversation({
    ask: (audio) => ask({ audio }),
    onEnd: () => {
      setConversationOn(false);
      // Show the conversation's questions and answers in the chat right away.
      window.setTimeout(() => {
        const el = scrollRef.current;
        el?.scrollIntoView({ behavior: "smooth", block: "center" });
        if (el) el.scrollTop = el.scrollHeight;
      }, 50);
    },
  });
  const startConversation = () => {
    current.current?.pause();
    setConversationOn(true);
    void conversation.begin();
  };

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
  const languageSummary = `Speaking: ${SPEECH_OPTIONS.find((o) => o.value === speechLanguage)?.label.replace(/ \(.*\)$/, "") ?? "Auto-detect"} · Reply: ${RESPONSE_SHORT[responseLanguage]}`;

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

  const empty = chat.messages.length === 0 && !chat.busy;
  const [contactOpen, setContactOpen] = useState(false);   // "Talk to a Human Officer" pop-up

  return (
    <PageShell
      scope="pg-chat"
      variant="app"
      title="Voice Chat"
      className="bg-background font-body-md text-on-surface antialiased selection:bg-secondary-container selection:text-on-secondary-container"
    >
      <style>{CHAT_HOME_CSS}</style>
      <main className="w-full pt-20 bg-background min-h-screen relative">
        <div className="flex flex-col w-full relative -mt-20">
          <div className="fixed inset-0 z-0 pointer-events-none bg-cover bg-center" style={{ backgroundImage: 'url("/assets/campus-sunset.jpg")' }} aria-hidden="true">
            <div className="absolute inset-0" style={{ background: "linear-gradient(180deg, rgba(14, 11, 9, 0.5) 0%, rgba(14, 11, 9, 0.12) 34%, rgba(14, 11, 9, 0.1) 60%, rgba(10, 8, 8, 0.45) 100%)" }} />
          </div>

          {/* ---------- Voice Chat (2026-10-14 redesign, reference: "Hello! How can I help you today?") ---------- */}
          <div className="relative z-10 w-full px-margin-mobile lg:px-margin pt-[18px] pb-10 min-h-screen flex flex-col">
            {/* top row: chat tools (while chatting) + highlighted "Talk to a Human Officer" */}
            <div className="w-full flex flex-wrap items-start justify-between gap-3">
              <div className="flex items-center gap-2 min-h-[44px]">
                {!empty && (
                  <>
                    <button type="button" onClick={newChat} className={TOOL_BTN} style={TOOL_STYLE}>
                      <Icon name="add_comment" className="text-[18px]" />
                      <span className="hidden sm:inline">New chat</span>
                    </button>
                    <button type="button" onClick={saveChat} className={TOOL_BTN} style={TOOL_STYLE}>
                      <Icon name="download" className="text-[18px]" />
                      <span className="hidden sm:inline">Save chat</span>
                    </button>
                    <button type="button" onClick={toggleAutoplay} aria-pressed={autoplay} title={`Auto-play voice replies: ${autoplay ? "on" : "off"}`} className={TOOL_ICON} style={TOOL_STYLE}>
                      <Icon name={autoplay ? "volume_up" : "volume_off"} className="text-[19px]" />
                    </button>
                    {topic && (
                      <span className="hidden md:inline-flex items-center gap-1.5 h-10 px-4 rounded-full text-[13px] text-white/85" style={TOOL_STYLE} title={contextUsed.length ? `Using context: ${contextUsed.join(", ")}` : undefined}>
                        <span className="w-1.5 h-1.5 rounded-full" style={{ background: "#c9dc9b" }} />
                        Topic: {topic}
                      </span>
                    )}
                  </>
                )}
              </div>
              <HumanOfficerCard onClick={() => setContactOpen(true)} disabled={false} />
            </div>

            {empty ? (
              <>
                <div className="mt-6 md:mt-[10px]"><ChatHeading /></div>
                <div className="mt-12 md:mt-[66px]">
                  <ActionCards
                    busy={chat.busy}
                    recording={recording}
                    levels={recorder.levels}
                    onSend={askText}
                    onHandsFree={startConversation}
                    onStartRecording={() => void start()}
                    onStopRecording={stop}
                  />
                </div>
                <div className="mt-9 md:mt-[40px]">
                  <TryAsking onAsk={askText} disabled={chat.busy} />
                </div>
              </>
            ) : (
              <>
                <DecorLine />
                {/* conversation: messages straight on the background (no box), hands-free on the right */}
                <div className="relative z-10 w-full max-w-[1480px] mx-auto mt-6 grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_330px] gap-6 xl:gap-8 items-end">
                  <div
                    ref={scrollRef}
                    className="chat-scroll flex flex-col gap-7 h-[max(260px,calc(100vh-340px))] overflow-y-auto pr-1 xl:pl-[4%]"
                    aria-live="polite"
                    aria-label="Conversation"
                  >
                    <MessageList messages={chat.messages} busy={chat.busy} control={audioControl} onRetry={chat.retry} onAsk={askText} />
                  </div>
                  <div className="hidden xl:flex justify-center pb-10">
                    <HandsFreeSide onStart={startConversation} disabled={chat.busy || recording} />
                  </div>
                </div>
                <div className="relative z-10 w-full max-w-[1210px] mx-auto mt-5">
                  <div className="xl:hidden mb-3 flex justify-center">
                    <HandsFreeSide compact onStart={startConversation} disabled={chat.busy || recording} />
                  </div>
                  <Composer busy={chat.busy} recording={recording} onSend={askText} onStartRecording={() => void start()} onStopRecording={stop} />
                  <p className="mt-2 px-4 flex flex-wrap items-center justify-between gap-2 text-[12.5px] text-white/60" aria-live="polite">
                    <span className="flex items-center gap-1.5 min-w-0">
                      <Icon name={chat.status.icon} className={`text-[15px] ${chat.status.icon === "progress_activity" ? "animate-spin" : ""}`} />
                      <span className="truncate">{chat.status.text}</span>
                    </span>
                    <span className="hidden md:inline">{languageSummary} · hold SPACE to talk</span>
                  </p>
                </div>
                <style>{`
                  .chat-scroll { scrollbar-width: thin; scrollbar-color: rgba(255, 245, 220, 0.25) transparent; }
                  .chat-scroll::-webkit-scrollbar { width: 6px; }
                  .chat-scroll::-webkit-scrollbar-thumb { background: rgba(255, 245, 220, 0.25); border-radius: 999px; }
                `}</style>
              </>
            )}
          </div>
        </div>
      </main>
      <ContactDialog open={contactOpen} onClose={() => setContactOpen(false)} />
      <VoiceConversation
        phase={conversation.phase}
        levelRef={conversation.levelRef}
        error={conversation.error}
        lastQuestion={conversation.lastQuestion}
        lastReply={conversation.lastReply}
        startedAt={conversation.startedAt}
        turns={conversation.turns}
        languageSummary={languageSummary}
        onTap={conversation.tap}
        onEnd={() => void conversation.end()}
      />
    </PageShell>
  );
}
