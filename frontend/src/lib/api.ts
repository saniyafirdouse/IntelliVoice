import type { AuthResponse, QueryContext, QueryResponse, Role, TranscribeResponse } from "./types";
import { storage } from "./storage";

// All calls go to the same origin (/api, /auth). The Express server
// forwards them to the FastAPI backend, so the browser never needs CORS.

const REQUEST_TIMEOUT_MS = 45_000;

export class ApiError extends Error {
  constructor(message: string, public status?: number) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(url: string, init: RequestInit, timeoutMs = REQUEST_TIMEOUT_MS): Promise<T> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  let res: Response;
  try {
    res = await fetch(url, { ...init, signal: controller.signal });
  } catch (err) {
    if ((err as Error).name === "AbortError") {
      throw new ApiError("The server took too long to answer. Please try again.");
    }
    throw new ApiError("Couldn't reach the IntelliVoice server. Please check that it is running.");
  } finally {
    window.clearTimeout(timer);
  }

  let data: unknown = {};
  try {
    data = await res.json();
  } catch {
    /* empty or non-JSON body */
  }
  if (!res.ok) {
    const detail = (data as { detail?: unknown }).detail;
    throw new ApiError(
      typeof detail === "string" ? detail : `Server error (${res.status}). Please try again.`,
      res.status,
    );
  }
  return data as T;
}

/** A random id for this browser, so the expo limit counts each visitor's phone separately (2026-11-01). */
function visitorId(): string {
  let id = storage.get("iv_visitor");
  if (!id) {
    id = Math.random().toString(36).slice(2) + Date.now().toString(36);
    storage.set("iv_visitor", id);
  }
  return id;
}

export interface AskParams {
  sessionId: string;
  text?: string;
  audio?: Blob;
  context?: QueryContext | null;
  speechLanguage?: string;
  responseLanguage?: string;
  token?: string | null;
  /** 2026-11-01: false = text-only reply (no voice, no Sarvam credits) — used by Help & FAQ */
  includeAudio?: boolean;
}

export function askQuestion({ sessionId, text, audio, context, speechLanguage, responseLanguage, token, includeAudio }: AskParams) {
  const form = new FormData();
  form.append("session_id", sessionId);
  if (audio) {
    const ext = (audio.type.split("/")[1] || "webm").split(";")[0];
    form.append("audio", audio, `question.${ext}`);
  } else if (text) {
    form.append("text", text);
  }
  if (context) form.append("context", JSON.stringify(context));
  if (speechLanguage) form.append("speech_language", speechLanguage);
  if (responseLanguage) form.append("response_language", responseLanguage);
  if (includeAudio === false) form.append("include_audio", "false");

  const headers: Record<string, string> = { "X-Visitor-Id": visitorId() };   // 2026-11-01: expo per-visitor limit
  if (token) headers.Authorization = `Bearer ${token}`;
  return request<QueryResponse>("/api/query", { method: "POST", body: form, headers });
}

/** 2026-11-19: memory across visits for signed-in users (backend: GET / DELETE /api/me/history). */
export interface MyHistory {
  has_history: boolean;
  welcome_message: string | null;
  last_topic: string | null;
  last_question?: string;
  last_asked_at?: string | null;
  recent_topics: string[];
}

export function getMyHistory(token: string) {
  return request<MyHistory>("/api/me/history", { method: "GET", headers: { Authorization: `Bearer ${token}` } }, 15_000);
}

export function forgetMyHistory(token: string) {
  return request<{ ok: boolean; removed: number; message: string }>(
    "/api/me/history", { method: "DELETE", headers: { Authorization: `Bearer ${token}` } }, 15_000);
}

// ── "Your chats" for signed-in students (2026-11-20; backend: /api/me/conversations) ──
export interface SavedChatSummary {
  id: string;
  session_id: string;
  title: string;
  questions: number;
  preview: string;
  created_at: string | null;
  updated_at: string | null;
}
export interface SavedMessage {
  role: "user" | "eva";
  text: string;
  mode?: "voice" | "text";
  language?: string | null;
  intent?: string | null;
  at: string | null;
  /** Eva's extras, so an old reply looks the same: PDF buttons, help card, overview… */
  extra?: Partial<QueryResponse>;
}
export interface SavedChat {
  id: string;
  session_id: string;
  title: string;
  created_at: string | null;
  updated_at: string | null;
  messages: SavedMessage[];
}

const auth = (token: string) => ({ Authorization: `Bearer ${token}` });

export function listChats(token: string, search?: string) {
  const q = search?.trim() ? `?q=${encodeURIComponent(search.trim())}` : "";
  return request<{ items: SavedChatSummary[] }>(`/api/me/conversations${q}`, { method: "GET", headers: auth(token) }, 15_000)
    .then((r) => r.items);
}

export function getChat(token: string, id: string) {
  return request<SavedChat>(`/api/me/conversations/${encodeURIComponent(id)}`, { method: "GET", headers: auth(token) }, 15_000);
}

export function renameChat(token: string, id: string, title: string) {
  return request<{ ok: boolean }>(`/api/me/conversations/${encodeURIComponent(id)}`, {
    method: "PATCH", headers: { ...auth(token), "Content-Type": "application/json" }, body: JSON.stringify({ title }),
  }, 15_000);
}

export function deleteChat(token: string, id: string) {
  return request<{ ok: boolean }>(`/api/me/conversations/${encodeURIComponent(id)}`, { method: "DELETE", headers: auth(token) }, 15_000);
}

// ── callback requests (2026-11-20; backend: POST /api/callback, GET /api/me/callbacks) ──
export interface CallbackInput {
  name: string;
  phone: string;
  question?: string;
  language?: string;
  preferred_time?: string;
  session_id?: string;
}
export interface MyCallback {
  id: string;
  reference: string;
  question: string | null;
  phone: string | null;
  preferred_time: string | null;
  status: "new" | "called" | "resolved" | string;
  status_text: string;
  created_at: string | null;
}

export function requestCallback(body: CallbackInput, token?: string | null) {
  return request<{ ok: boolean; reference: string; message: string }>("/api/callback", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(token ? auth(token) : {}) },
    body: JSON.stringify(body),
  }, 20_000);
}

export function myCallbacks(token: string) {
  return request<{ items: MyCallback[] }>("/api/me/callbacks", { method: "GET", headers: auth(token) }, 15_000).then((r) => r.items);
}

// ── ⭐ saved answers + my checklist (2026-11-20; backend: /api/me/saved, /api/me/checklist) ──
export interface SavedAnswer { id: string; question: string; answer: string; language: string | null; saved_at: string | null }
export interface MyChecklist {
  admission_type: string;
  category: string;
  admission_types: Record<string, string>;
  categories: string[];
  documents: string[];
  steps: string[];
  done: string[];
  note: string;
}

export function listSaved(token: string) {
  return request<{ items: SavedAnswer[] }>("/api/me/saved", { method: "GET", headers: auth(token) }, 15_000).then((r) => r.items);
}

export function saveAnswer(token: string, question: string, answer: string, language?: string) {
  return request<SavedAnswer>("/api/me/saved", {
    method: "POST", headers: { ...auth(token), "Content-Type": "application/json" },
    body: JSON.stringify({ question: question.slice(0, 500), answer, language }),
  }, 15_000);
}

export function deleteSaved(token: string, id: string) {
  return request<{ ok: boolean }>(`/api/me/saved/${encodeURIComponent(id)}`, { method: "DELETE", headers: auth(token) }, 15_000);
}

export function getMyChecklist(token: string, admissionType?: string, category?: string) {
  const q = new URLSearchParams();
  if (admissionType) q.set("admission_type", admissionType);
  if (category) q.set("category", category);
  const qs = q.toString();
  return request<MyChecklist>(`/api/me/checklist${qs ? `?${qs}` : ""}`, { method: "GET", headers: auth(token) }, 15_000);
}

export function saveMyChecklist(token: string, admissionType: string, category: string, done: string[]) {
  return request<{ ok: boolean }>("/api/me/checklist", {
    method: "PUT", headers: { ...auth(token), "Content-Type": "application/json" },
    body: JSON.stringify({ admission_type: admissionType, category, done }),
  }, 15_000);
}

// ── my profile (2026-11-20; backend: /api/me/profile) ──
export interface MyProfile {
  exam: string | null;
  rank: number | null;
  category: string | null;
  branches: string[];
  updated_at: string | null;
  options?: { exams: Record<string, string>; categories: string[]; branches: string[] };
}

export function getMyProfile(token: string) {
  return request<MyProfile>("/api/me/profile", { method: "GET", headers: auth(token) }, 15_000);
}

export function saveMyProfile(token: string, p: { exam: string | null; rank: number | null; category: string | null; branches: string[] }) {
  return request<MyProfile>("/api/me/profile", {
    method: "PUT", headers: { ...auth(token), "Content-Type": "application/json" }, body: JSON.stringify(p),
  }, 15_000);
}

// ── "Email me" (2026-11-20; backend: /api/me/email; hidden until the backend has an email account) ──
let emailStatusCache: { token: string; promise: Promise<boolean> } | null = null;
export function emailEnabled(token: string): Promise<boolean> {
  if (!emailStatusCache || emailStatusCache.token !== token) {
    const promise = request<{ enabled: boolean }>("/api/me/email", { method: "GET", headers: auth(token) }, 10_000)
      .then((r) => !!r.enabled).catch(() => false);
    emailStatusCache = { token, promise };
  }
  return emailStatusCache.promise;
}

export function emailMe(token: string, body: { kind: "answer" | "starred" | "checklist"; question?: string; answer?: string }) {
  return request<{ ok: boolean; message: string }>("/api/me/email", {
    method: "POST", headers: { ...auth(token), "Content-Type": "application/json" }, body: JSON.stringify(body),
  }, 30_000);
}

/** 2026-11-01: Eva's spoken hello after "Hey Eva" (en | hi | kn). */
export function getGreeting(language: string) {
  return request<QueryResponse>(`/api/greeting?language=${encodeURIComponent(language)}`, { method: "GET" });
}

/** 2026-10-31: speech to text only — the mic shows what it heard before sending. */
export function transcribeAudio(audio: Blob, speechLanguage?: string) {
  const form = new FormData();
  const ext = (audio.type.split("/")[1] || "webm").split(";")[0];
  form.append("audio", audio, `question.${ext}`);
  if (speechLanguage) form.append("speech_language", speechLanguage);
  return request<TranscribeResponse>("/api/transcribe", { method: "POST", body: form });
}

/** 2026-10-31: the personal document checklist PDF (backend: POST /api/checklist). */
export async function downloadChecklist(admissionType: string, category: string, name?: string) {
  const res = await fetch("/api/checklist", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ admission_type: admissionType, category, name: name?.trim() || null }),
  });
  if (!res.ok) {
    let detail = "";
    try { detail = ((await res.json()) as { detail?: string }).detail ?? ""; } catch { /* not JSON */ }
    throw new ApiError(detail || `Couldn't make the checklist (${res.status}). Please try again.`, res.status);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = Object.assign(document.createElement("a"), { href: url, download: `SVIT_document_checklist_${admissionType}.pdf` });
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function postJson<T>(url: string, body: unknown) {
  return request<T>(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }, 20_000);
}

export const authApi = {
  login: (email: string, password: string, role: Role) =>
    postJson<AuthResponse>("/auth/login", { email, password, role }),
  signup: (name: string, email: string, phone: string, password: string) =>
    postJson<AuthResponse>("/auth/signup", { name, email, phone, password }),
};
