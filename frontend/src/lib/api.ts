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
