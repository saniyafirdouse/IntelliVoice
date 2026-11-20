// "Your chats" (2026-11-20) — for signed-in students, like ChatGPT's chat list.
// Slides in from the left. Two tabs:
//   Chats     — New chat, search, earlier chats grouped by day; open (and continue), rename, delete;
//               "Forget all my history" at the bottom.
//   Starred   — ☆ answers starred in the chat (2026-11-20, MyStuff.tsx)
//   Checklist — my admission checklist with tick-boxes (2026-11-20, MyStuff.tsx)
//   Callbacks — the callback requests this student sent, with their status.
// Backend: /api/me/conversations, /api/me/callbacks, DELETE /api/me/history.
import { useCallback, useEffect, useMemo, useState } from "react";
import { Icon } from "../../components/Icon";
import {
  ApiError, deleteChat, forgetMyHistory, listChats, myCallbacks, renameChat,
  type MyCallback, type SavedChatSummary,
} from "../../lib/api";
import { MyChecklistPanel, ProfilePanel, SavedAnswers } from "./MyStuff";

const PANEL = {
  background: "linear-gradient(170deg, rgba(40, 33, 27, 0.94) 0%, rgba(22, 20, 17, 0.96) 100%)",
  borderRight: "1px solid rgba(232, 211, 163, 0.25)",
  boxShadow: "18px 0 50px rgba(0,0,0,0.45)",
  backdropFilter: "blur(18px)",
  WebkitBackdropFilter: "blur(18px)",
} as const;
const SMALL_BTN = "w-8 h-8 rounded-lg flex items-center justify-center text-white/60 hover:text-white hover:bg-white/10";

function groupOf(iso: string | null): string {
  if (!iso) return "Older";
  const d = new Date(iso);
  const today = new Date();
  const startOfDay = (x: Date) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
  const days = Math.round((startOfDay(today) - startOfDay(d)) / 86_400_000);
  if (days <= 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 7) return "Previous 7 days";
  return "Older";
}
const GROUPS = ["Today", "Yesterday", "Previous 7 days", "Older"];

function when(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  const sameDay = d.toDateString() === new Date().toDateString();
  return sameDay
    ? d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })
    : d.toLocaleDateString([], { day: "numeric", month: "short" });
}

type Tab = "chats" | "saved" | "checklist" | "callbacks" | "profile";
const TABS: { id: Tab; label: string; icon: string }[] = [
  { id: "chats", label: "Chats", icon: "forum" },
  { id: "saved", label: "Starred", icon: "star" },
  { id: "checklist", label: "Checklist", icon: "checklist" },
  { id: "callbacks", label: "Callbacks", icon: "phone_callback" },
  { id: "profile", label: "Profile", icon: "person" },
];

const STATUS_LOOK: Record<string, { icon: string; color: string }> = {
  new: { icon: "hourglass_top", color: "#f3d48a" },
  called: { icon: "call", color: "#9fd3ff" },
  resolved: { icon: "check_circle", color: "#ced8aa" },
};

export function ChatSidebar({ open, onClose, token, activeSessionId, refreshKey, onOpenChat, onNewChat, onHistoryCleared }: {
  open: boolean;
  onClose: () => void;
  token: string;
  activeSessionId: string;
  /** changes after every answer, so the list stays up to date */
  refreshKey: number;
  onOpenChat: (id: string) => Promise<void>;
  onNewChat: () => void;
  onHistoryCleared: () => void;
}) {
  const [tab, setTab] = useState<Tab>("chats");
  const [search, setSearch] = useState("");
  const [chats, setChats] = useState<SavedChatSummary[] | null>(null);
  const [callbacks, setCallbacks] = useState<MyCallback[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [renaming, setRenaming] = useState<{ id: string; title: string } | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [opening, setOpening] = useState<string | null>(null);
  const [forgetAsk, setForgetAsk] = useState(false);

  const loadChats = useCallback(async (q: string) => {
    try {
      setChats(await listChats(token, q));
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't load your chats.");
    }
  }, [token]);

  // load when opened, after each answer, and (a moment after typing) when searching
  useEffect(() => {
    if (!open || tab !== "chats") return;
    const t = window.setTimeout(() => void loadChats(search), search ? 300 : 0);
    return () => window.clearTimeout(t);
  }, [open, tab, search, refreshKey, loadChats]);

  // 2026-11-20: callbacks reload when the tab opens, when you come back to the page, and every 20 s,
  // so "Waiting" changes to "Called" / "Resolved" as soon as the office updates it
  const loadCallbacks = useCallback(() => {
    myCallbacks(token).then((items) => { setCallbacks(items); setError(null); }).catch((err) =>
      setError(err instanceof ApiError ? err.message : "Couldn't load your callback requests."));
  }, [token]);
  useEffect(() => {
    if (!open || tab !== "callbacks") return;
    loadCallbacks();
    const timer = window.setInterval(loadCallbacks, 20_000);
    window.addEventListener("focus", loadCallbacks);
    return () => { window.clearInterval(timer); window.removeEventListener("focus", loadCallbacks); };
  }, [open, tab, loadCallbacks]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const grouped = useMemo(() => {
    const out: Record<string, SavedChatSummary[]> = {};
    for (const c of chats ?? []) (out[groupOf(c.updated_at)] ??= []).push(c);
    return out;
  }, [chats]);

  const saveRename = async () => {
    if (!renaming) return;
    const title = renaming.title.trim();
    if (!title) { setRenaming(null); return; }
    try {
      await renameChat(token, renaming.id, title);
      setChats((cs) => cs?.map((c) => (c.id === renaming.id ? { ...c, title } : c)) ?? null);
      setRenaming(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't rename the chat.");
    }
  };

  const remove = async (c: SavedChatSummary) => {
    try {
      await deleteChat(token, c.id);
      setChats((cs) => cs?.filter((x) => x.id !== c.id) ?? null);
      setDeleting(null);
      if (c.session_id === activeSessionId) onNewChat();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't delete the chat.");
    }
  };

  const forgetAll = async () => {
    try {
      await forgetMyHistory(token);
      setChats([]);
      setForgetAsk(false);
      onHistoryCleared();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't clear your history.");
    }
  };

  const openChat = async (id: string) => {
    setOpening(id);
    setError(null);
    try { await onOpenChat(id); } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't open this chat.");
    } finally { setOpening(null); }
  };

  return (
    <>
      <div
        className={`fixed inset-0 z-[60] transition-opacity duration-200 ${open ? "opacity-100" : "opacity-0 pointer-events-none"}`}
        style={{ background: "rgba(8, 6, 5, 0.45)" }}
        onClick={onClose}
        aria-hidden="true"
      />
      <aside
        className={`fixed inset-y-0 left-0 z-[61] w-[350px] max-w-[88vw] flex flex-col text-white transition-transform duration-200 ${open ? "translate-x-0" : "-translate-x-full"}`}
        style={PANEL}
        aria-label="Your chats"
        aria-hidden={!open}
      >
        <div className="flex items-center justify-between px-4 pt-4 pb-2">
          <h2 className="text-[20px] font-semibold flex items-center gap-2"><Icon name="forum" className="text-[22px]" style={{ color: "#e8d3a3" }} />Your chats</h2>
          <button type="button" onClick={onClose} className={SMALL_BTN} aria-label="Close"><Icon name="close" className="text-[20px]" /></button>
        </div>

        <div className="px-3 flex gap-0.5" role="tablist">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              role="tab"
              aria-selected={tab === t.id}
              onClick={() => { setTab(t.id); setError(null); }}
              className="flex-1 min-w-0 h-12 rounded-lg flex flex-col items-center justify-center gap-0.5 text-[10.5px] font-medium transition-colors"
              style={tab === t.id ? { background: "rgba(232, 211, 163, 0.18)", color: "#fff", border: "1px solid rgba(232, 211, 163, 0.4)" } : { color: "rgba(255,255,255,0.65)" }}
            >
              <Icon name={t.icon} className="text-[18px]" filled={tab === t.id} />
              {t.label}
            </button>
          ))}
        </div>

        {error && <p className="mx-4 mt-3 text-[13px] rounded-lg px-3 py-2" style={{ background: "rgba(110, 20, 20, 0.4)", color: "#ffd6d1" }} role="alert">{error}</p>}

        {tab === "saved" && <SavedAnswers token={token} open={open} />}
        {tab === "checklist" && <MyChecklistPanel token={token} open={open} />}
        {tab === "profile" && <ProfilePanel token={token} open={open} />}
        {tab === "chats" ? (
          <>
            <div className="px-4 pt-3 flex flex-col gap-2">
              <button
                type="button"
                onClick={() => { onNewChat(); onClose(); }}
                className="h-10 rounded-xl flex items-center justify-center gap-2 text-[14.5px] font-semibold"
                style={{ background: "#c2cc99", color: "#1d2214" }}
              >
                <Icon name="add" className="text-[19px]" />New chat
              </button>
              <label className="relative">
                <Icon name="search" className="absolute left-3 top-1/2 -translate-y-1/2 text-[18px] text-white/50" />
                <input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search your chats"
                  className="w-full h-10 pl-9 pr-3 rounded-xl text-[14px] text-white placeholder:text-white/45 outline-none focus:ring-2 focus:ring-white/30"
                  style={{ background: "rgba(255,255,255,0.07)", border: "1px solid rgba(255,255,255,0.14)" }}
                  aria-label="Search your chats"
                />
              </label>
            </div>

            <div className="flex-1 overflow-y-auto px-2 pt-2 pb-3">
              {chats === null && <p className="px-3 py-4 text-[14px] text-white/60">Loading…</p>}
              {chats && chats.length === 0 && (
                <p className="px-3 py-4 text-[14px] text-white/60">
                  {search ? "No chats match your search." : "No saved chats yet. Ask Eva something, and the chat is saved here automatically."}
                </p>
              )}
              {GROUPS.filter((g) => grouped[g]?.length).map((g) => (
                <div key={g} className="mt-2">
                  <div className="px-3 py-1 text-[11.5px] font-semibold uppercase tracking-[0.08em] text-white/45">{g}</div>
                  {grouped[g].map((c) => {
                    const active = c.session_id === activeSessionId;
                    if (renaming?.id === c.id) {
                      return (
                        <div key={c.id} className="flex items-center gap-1 px-2 py-1">
                          <input
                            autoFocus
                            value={renaming.title}
                            maxLength={80}
                            onChange={(e) => setRenaming({ id: c.id, title: e.target.value })}
                            onKeyDown={(e) => { if (e.key === "Enter") void saveRename(); if (e.key === "Escape") setRenaming(null); }}
                            className="flex-1 h-9 px-2.5 rounded-lg text-[14px] text-white outline-none"
                            style={{ background: "rgba(0,0,0,0.35)", border: "1px solid rgba(232, 211, 163, 0.5)" }}
                            aria-label="New name for this chat"
                          />
                          <button type="button" className={SMALL_BTN} onClick={() => void saveRename()} aria-label="Save name"><Icon name="check" className="text-[19px]" /></button>
                          <button type="button" className={SMALL_BTN} onClick={() => setRenaming(null)} aria-label="Cancel"><Icon name="close" className="text-[19px]" /></button>
                        </div>
                      );
                    }
                    if (deleting === c.id) {
                      return (
                        <div key={c.id} className="mx-2 my-1 px-3 py-2 rounded-lg flex items-center gap-2 text-[13.5px]" style={{ background: "rgba(110, 20, 20, 0.35)" }}>
                          <span className="flex-1">Delete this chat?</span>
                          <button type="button" className="px-2.5 h-8 rounded-lg font-semibold hover:bg-white/10" style={{ color: "#ffb4ab" }} onClick={() => void remove(c)}>Delete</button>
                          <button type="button" className="px-2.5 h-8 rounded-lg hover:bg-white/10" onClick={() => setDeleting(null)}>Cancel</button>
                        </div>
                      );
                    }
                    return (
                      <div key={c.id} className="group relative flex items-center rounded-xl" style={active ? { background: "rgba(232, 211, 163, 0.14)" } : undefined}>
                        <button
                          type="button"
                          onClick={() => void openChat(c.id)}
                          className="flex-1 min-w-0 text-left px-3 py-2 rounded-xl hover:bg-white/[0.07]"
                          title={c.title}
                        >
                          <span className="flex items-center gap-1.5">
                            {opening === c.id && <Icon name="progress_activity" className="text-[15px] animate-spin" />}
                            <span className="truncate text-[14.5px] text-white">{c.title}</span>
                          </span>
                          <span className="block truncate text-[12.5px] text-white/50">
                            {when(c.updated_at)} · {c.questions} question{c.questions === 1 ? "" : "s"}
                          </span>
                        </button>
                        <span className="flex pr-1 opacity-100 md:opacity-0 md:group-hover:opacity-100 md:focus-within:opacity-100">
                          <button type="button" className={SMALL_BTN} onClick={() => setRenaming({ id: c.id, title: c.title })} aria-label={`Rename chat: ${c.title}`} title="Rename"><Icon name="edit" className="text-[17px]" /></button>
                          <button type="button" className={SMALL_BTN} onClick={() => setDeleting(c.id)} aria-label={`Delete chat: ${c.title}`} title="Delete"><Icon name="delete" className="text-[17px]" /></button>
                        </span>
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>

            <div className="px-4 py-3 border-t border-white/10 text-[13px]">
              {!forgetAsk ? (
                <button type="button" onClick={() => setForgetAsk(true)} className="inline-flex items-center gap-1.5 text-white/60 hover:text-white underline underline-offset-2">
                  <Icon name="delete_sweep" className="text-[17px]" />Forget all my history
                </button>
              ) : (
                <div className="flex flex-col gap-2">
                  <span className="text-white/85">Delete all your saved chats and what Eva remembers about you? This can't be undone.</span>
                  <span className="flex gap-2">
                    <button type="button" onClick={() => void forgetAll()} className="h-8 px-3 rounded-lg font-semibold" style={{ background: "rgba(220, 90, 80, 0.3)", color: "#ffd6d1", border: "1px solid rgba(240, 150, 140, 0.5)" }}>Yes, forget everything</button>
                    <button type="button" onClick={() => setForgetAsk(false)} className="h-8 px-3 rounded-lg hover:bg-white/10">Cancel</button>
                  </span>
                </div>
              )}
            </div>
          </>
        ) : tab === "callbacks" && (
          <div className="flex-1 overflow-y-auto px-4 pt-3 pb-4 flex flex-col gap-2.5">
            {callbacks === null && !error && <p className="py-2 text-[14px] text-white/60">Loading…</p>}
            {callbacks && callbacks.length === 0 && (
              <p className="py-2 text-[14px] text-white/65">
                No callback requests yet. Use “Talk to a Human Officer” → “Request a callback”, and the admission office will call you.
              </p>
            )}
            {callbacks?.map((c) => {
              const look = STATUS_LOOK[c.status] ?? STATUS_LOOK.new;
              return (
                <div key={c.id} className="rounded-xl px-3.5 py-3" style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)" }}>
                  <div className="flex items-center justify-between gap-2 text-[12.5px] text-white/55">
                    <span>Ref {c.reference}</span>
                    <span>{when(c.created_at)}</span>
                  </div>
                  {c.question && <p className="mt-1 text-[14px] text-white line-clamp-2">“{c.question}”</p>}
                  <p className="mt-1.5 flex items-start gap-1.5 text-[13.5px]" style={{ color: look.color }}>
                    <Icon name={look.icon} className="text-[17px] mt-px" />{c.status_text}
                  </p>
                </div>
              );
            })}
          </div>
        )}
      </aside>
    </>
  );
}
