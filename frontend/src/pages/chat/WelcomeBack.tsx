// "Welcome back" card for signed-in students (2026-11-19).
// The backend already remembers each signed-in user's last 20 questions
// (engines/user_history.py). This card shows them on the chat start screen:
//   - "Welcome back, Saniya! Last time you asked about CSE fees."
//   - the last question and recent topics as buttons (tap = ask again)
//   - "Forget my history" (asks "Are you sure?" first) -> DELETE /api/me/history
// Text only: no voice, so no Sarvam credits are used.
import { useEffect, useState } from "react";
import { EvaAvatar } from "../../components/EvaAvatar";
import { Icon } from "../../components/Icon";
import { ApiError, forgetMyHistory, getMyHistory, listChats, type MyHistory, type SavedChatSummary } from "../../lib/api";

const CARD = {
  background: "rgba(24, 22, 18, 0.62)",
  border: "1px solid rgba(232, 211, 163, 0.28)",
  backdropFilter: "blur(12px)",
  WebkitBackdropFilter: "blur(12px)",
} as const;
const CHIP = "inline-flex items-center gap-1.5 h-9 px-4 rounded-full text-[13.5px] text-white/90 transition-colors hover:bg-white/15 disabled:opacity-50";
const CHIP_STYLE = { background: "rgba(255, 250, 240, 0.08)", border: "1px solid rgba(255, 245, 225, 0.22)" } as const;

function firstName(name: string) {
  return (name || "").trim().split(/\s+/)[0] || "";
}

export function WelcomeBack({ token, name, onAsk, disabled, onOpenChat }: {
  token: string;
  name: string;
  onAsk: (question: string) => void;
  disabled: boolean;
  /** 2026-11-20: "Continue my last chat" opens the newest saved chat */
  onOpenChat?: (id: string) => Promise<void>;
}) {
  const [lastChat, setLastChat] = useState<SavedChatSummary | null>(null);
  const [opening, setOpening] = useState(false);
  const [history, setHistory] = useState<MyHistory | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [working, setWorking] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    getMyHistory(token)
      .then((h) => { if (alive) setHistory(h); })
      .catch(() => { if (alive) setHistory(null); });   // not reachable / logged out: just don't show the card
    listChats(token)
      .then((items) => { if (alive) setLastChat(items[0] ?? null); })
      .catch(() => undefined);
    return () => { alive = false; };
  }, [token]);

  if (!history) return null;
  const who = firstName(name);

  const forget = async () => {
    setWorking(true);
    setError(null);
    try {
      const res = await forgetMyHistory(token);
      setHistory({ has_history: false, welcome_message: null, last_topic: null, recent_topics: [] });
      setLastChat(null);
      setNotice(res.message || "Done. Eva has forgotten your earlier questions.");
      setConfirming(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't clear your history. Please try again.");
    } finally {
      setWorking(false);
    }
  };

  return (
    <section className="w-full max-w-[860px] mx-auto rounded-[22px] px-5 py-4 md:px-6 md:py-5 flex gap-4 items-start" style={CARD} aria-label="Welcome back">
      <EvaAvatar size={46} className="mt-0.5" />
      <div className="min-w-0 flex-1">
        {history.has_history ? (
          <>
            <p className="text-[17px] md:text-[18px] font-medium text-white">
              Welcome back{who ? `, ${who}` : ""}! Last time you asked about{" "}
              <span style={{ color: "#e8d3a3" }}>{history.last_topic}</span>.
            </p>
            {history.last_question && (
              <p className="mt-1 text-[13.5px] text-white/60 truncate" title={history.last_question}>
                “{history.last_question}”
              </p>
            )}
            <div className="mt-3 flex flex-wrap gap-2">
              {lastChat && onOpenChat && (
                <button
                  type="button"
                  className={CHIP}
                  style={{ ...CHIP_STYLE, background: "rgba(232, 211, 163, 0.2)", borderColor: "rgba(232, 211, 163, 0.6)" }}
                  disabled={disabled || opening}
                  title={lastChat.title}
                  onClick={() => { setOpening(true); void onOpenChat(lastChat.id).catch(() => undefined).finally(() => setOpening(false)); }}
                >
                  <Icon name={opening ? "progress_activity" : "forum"} className={`text-[16px] ${opening ? "animate-spin" : ""}`} />
                  Continue my last chat
                </button>
              )}
              {history.last_question && (
                <button type="button" className={CHIP} style={CHIP_STYLE} disabled={disabled} onClick={() => onAsk(history.last_question!)}>
                  <Icon name="replay" className="text-[16px]" />
                  Ask that again
                </button>
              )}
              {history.recent_topics.filter((t) => t !== history.last_topic).map((topic) => (
                <button key={topic} type="button" className={CHIP} style={CHIP_STYLE} disabled={disabled} onClick={() => onAsk(`Tell me about ${topic}`)}>
                  <Icon name="history" className="text-[16px]" />
                  {topic}
                </button>
              ))}
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-3 text-[13px]">
              {!confirming ? (
                <button type="button" className="inline-flex items-center gap-1 text-white/55 underline underline-offset-2 hover:text-white/85" onClick={() => setConfirming(true)}>
                  <Icon name="delete" className="text-[15px]" />
                  Forget my history
                </button>
              ) : (
                <>
                  <span className="text-white/80">Eva will forget all your earlier questions and saved chats. This can't be undone.</span>
                  <button type="button" className={CHIP} style={{ ...CHIP_STYLE, borderColor: "rgba(240, 150, 140, 0.55)" }} disabled={working} onClick={() => void forget()}>
                    {working ? "Forgetting…" : "Yes, forget"}
                  </button>
                  <button type="button" className={CHIP} style={CHIP_STYLE} disabled={working} onClick={() => setConfirming(false)}>
                    Cancel
                  </button>
                </>
              )}
            </div>
          </>
        ) : (
          <>
            <p className="text-[17px] md:text-[18px] font-medium text-white">
              {notice ? notice : `Welcome${who ? `, ${who}` : ""}! Eva will remember your questions for your next visit.`}
            </p>
            {!notice && (
              <p className="mt-1 text-[13px] text-white/55">You can clear them any time with “Forget my history”.</p>
            )}
          </>
        )}
        {error && <p className="mt-2 text-[13px]" style={{ color: "#f0a49a" }} role="alert">{error}</p>}
      </div>
    </section>
  );
}
