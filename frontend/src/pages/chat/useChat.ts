import { useCallback, useEffect, useReducer, useRef } from "react";
import { askQuestion, ApiError } from "../../lib/api";
import { newSessionId, storage } from "../../lib/storage";
import type { MemoryInfo, QueryContext, QueryResponse, Understanding } from "../../lib/types";

export const STAGES = ["speech", "language", "understanding", "knowledge", "memory", "response", "voice"] as const;
export type Stage = (typeof STAGES)[number];
export type StageState = "idle" | "active" | "done" | "skipped";

export type ChatMessage =
  | { id: string; kind: "user"; text: string; voice: boolean; pending: boolean; langLabel?: string; at: Date }
  | { id: string; kind: "bot"; res: QueryResponse; at: Date }
  | { id: string; kind: "error"; text: string; retry?: Question };

export interface Question {
  text?: string;
  audio?: Blob;
}

interface State {
  sessionId: string;
  messages: ChatMessage[];
  busy: boolean;
  understanding: Understanding | null;
  memory: MemoryInfo | null;
  stages: Record<Stage, StageState>;
  status: { text: string; icon: string };
}

const idleStages = () => Object.fromEntries(STAGES.map((s) => [s, "idle"])) as Record<Stage, StageState>;
const READY = { text: "Ready. Tap the mic or type your question.", icon: "mic" };

type Action =
  | { type: "ask"; userId: string; question: Question }
  | { type: "advance"; voice: boolean }
  | { type: "answer"; userId: string; res: QueryResponse; voice: boolean }
  | { type: "fail"; userId: string; question: Question; message: string }
  | { type: "status"; text: string; icon: string }
  | { type: "drop"; ids: string[] }
  | { type: "reset"; sessionId: string };

const LANG_NAMES: Record<string, string> = { en: "English", hi: "Hindi", kn: "Kannada" };
let counter = 0;
const uid = () => `m${Date.now().toString(36)}${(counter++).toString(36)}`;

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "ask": {
      const voice = !!action.question.audio;
      const stages = idleStages();
      if (voice) stages.speech = "active";
      else { stages.speech = "skipped"; stages.language = "active"; }
      return {
        ...state,
        busy: true,
        stages,
        status: voice
          ? { text: "Converting your speech to text…", icon: "progress_activity" }
          : { text: "Understanding your question…", icon: "progress_activity" },
        messages: [...state.messages, {
          id: action.userId, kind: "user", voice, pending: voice, at: new Date(),
          text: voice ? "Transcribing your voice…" : action.question.text ?? "",
        }],
      };
    }
    case "advance": {
      // Visual progress only: never marks the last two stages done before the answer arrives.
      const order = STAGES.filter((s) => state.stages[s] !== "skipped");
      const i = order.findIndex((s) => state.stages[s] === "active");
      if (i < 0 || i >= order.length - 2) return state;
      return { ...state, stages: { ...state.stages, [order[i]]: "done", [order[i + 1]]: "active" } };
    }
    case "answer": {
      const { res, voice } = action;
      const lang = res.language;
      const langLabel = lang?.primary
        ? `${LANG_NAMES[lang.primary] ?? lang.primary} detected${lang.is_code_switched ? " (code-mixed)" : ""}` +
          (typeof lang.confidence === "number" ? ` · ${Math.round(lang.confidence * 100)}%` : "")
        : undefined;
      const hasAudio = !!(res.audio && (res.audio.base64 || res.audio.url));
      const stages = Object.fromEntries(STAGES.map((s) => [s, "done"])) as Record<Stage, StageState>;
      if (!voice) stages.speech = "skipped";
      if (!hasAudio) stages.voice = "skipped";
      return {
        ...state,
        busy: false,
        sessionId: res.session_id || state.sessionId,
        understanding: res.understanding ?? state.understanding,
        memory: res.memory?.topic ? res.memory : state.memory,
        stages,
        status: { text: "Ready. Ask a follow-up question.", icon: "mic" },
        messages: [
          ...state.messages.map((m) =>
            m.id === action.userId && m.kind === "user"
              ? { ...m, pending: false, langLabel, text: res.transcript || (voice ? "(no speech detected)" : m.text) }
              : m),
          { id: uid(), kind: "bot", res, at: new Date() },
        ],
      };
    }
    case "fail":
      return {
        ...state,
        busy: false,
        stages: idleStages(),
        status: { text: "Something went wrong. Please try again.", icon: "error" },
        messages: [
          ...state.messages.map((m) =>
            m.id === action.userId && m.kind === "user" && m.voice ? { ...m, pending: false, text: "(voice message)" } : m),
          { id: uid(), kind: "error", text: action.message, retry: action.question },
        ],
      };
    case "status":
      return { ...state, status: { text: action.text, icon: action.icon } };
    case "drop":
      return { ...state, messages: state.messages.filter((m) => !action.ids.includes(m.id)) };
    case "reset":
      return { ...initialState(), sessionId: action.sessionId };
  }
}

function initialState(): State {
  return {
    sessionId: storage.get("iv_session_id", "session") || newSessionId(),
    messages: [],
    busy: false,
    understanding: null,
    memory: null,
    stages: idleStages(),
    status: READY,
  };
}

interface UseChatOptions {
  getContext: () => QueryContext | null;
  token: string | null;
  speechLanguage: string;
  responseLanguage: string;
}

export function useChat({ getContext, token, speechLanguage, responseLanguage }: UseChatOptions) {
  const [state, dispatch] = useReducer(reducer, undefined, initialState);
  const busyRef = useRef(false);
  busyRef.current = state.busy;

  useEffect(() => { storage.set("iv_session_id", state.sessionId, "session"); }, [state.sessionId]);

  // animate pipeline stages while waiting
  useEffect(() => {
    if (!state.busy) return;
    const voice = state.stages.speech !== "skipped";
    const t = window.setInterval(() => dispatch({ type: "advance", voice }), 650);
    return () => window.clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.busy]);

  const ask = useCallback(async (question: Question) => {
    if (busyRef.current) return;
    if (!question.audio && !question.text?.trim()) return;
    busyRef.current = true;
    const userId = uid();
    const voice = !!question.audio;
    dispatch({ type: "ask", userId, question });
    try {
      const res = await askQuestion({
        sessionId: state.sessionId,
        text: question.text?.trim(),
        audio: question.audio,
        context: getContext(),
        speechLanguage,
        responseLanguage,
        token,
      });
      dispatch({ type: "answer", userId, res, voice });
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Something went wrong. Please try again.";
      dispatch({ type: "fail", userId, question, message });
    }
  }, [state.sessionId, getContext, speechLanguage, responseLanguage, token]);

  const retry = useCallback((errorId: string) => {
    const msg = state.messages.find((m) => m.id === errorId);
    if (!msg || msg.kind !== "error" || !msg.retry) return;
    // remove the failed exchange, then ask again
    const idx = state.messages.indexOf(msg);
    const prev = state.messages[idx - 1];
    dispatch({ type: "drop", ids: prev?.kind === "user" ? [prev.id, msg.id] : [msg.id] });
    void ask(msg.retry);
  }, [state.messages, ask]);

  const setStatus = useCallback((text: string, icon = "info") => dispatch({ type: "status", text, icon }), []);
  const reset = useCallback(() => dispatch({ type: "reset", sessionId: newSessionId() }), []);

  return { ...state, ask, retry, setStatus, reset };
}
