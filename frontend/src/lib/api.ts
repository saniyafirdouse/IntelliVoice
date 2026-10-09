import type { AuthResponse, QueryContext, QueryResponse, Role } from "./types";

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

export interface AskParams {
  sessionId: string;
  text?: string;
  audio?: Blob;
  context?: QueryContext | null;
  speechLanguage?: string;
  responseLanguage?: string;
  token?: string | null;
}

export function askQuestion({ sessionId, text, audio, context, speechLanguage, responseLanguage, token }: AskParams) {
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

  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  return request<QueryResponse>("/api/query", { method: "POST", body: form, headers });
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
