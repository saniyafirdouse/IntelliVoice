// Admin panel API — talks to Bhuvana's backend (backend/routes/admin.py) under /api/admin.
// Every call sends the admin's login token. The Express server forwards /api to FastAPI.

import { ApiError } from "./api";

// ── shapes returned by the backend ─────────────────────────────────────────
export interface DatasetColumn { field: string; required: boolean; help: string }
export interface Dataset {
  name: string;
  title: string;
  records: number;
  last_updated: string | null;
  columns: DatasetColumn[];
}

export interface FieldChange { field: string; old: string | number | null; new: string | number | null }
export interface UploadChange {
  action: "new" | "update";
  row: number;
  label: string;
  fields: FieldChange[];
  warnings: string[];
}
export type UploadStatus = "pending" | "applied" | "cancelled" | "undone" | "expired";
export interface UploadSummary {
  upload_id: string;
  dataset: string;
  filename: string | null;
  status: UploadStatus;
  uploaded_by: string | null;
  uploaded_at: string | null;
  applied_at: string | null;
  undone_at: string | null;
  counts: { new: number; updated: number; unchanged: number; not_in_file: number; errors: number; warnings: number };
  can_confirm: boolean;
  errors: { row: number; message: string }[];
  file_warnings: string[];
  changes?: UploadChange[];
}

export interface Dashboard {
  days: number;
  total_queries: number;
  unique_sessions: number;
  answered_rate: number;
  status: { answered: number; no_data: number; out_of_scope: number; error: number };
  escalations: number;
  top_intents: { intent: string; count: number }[];
  top_categories: { category: string; count: number }[];
  languages: { language: string; code: string; count: number; percent: number }[];
  code_switched_percent: number;
  emotions: { emotion: string; count: number }[];
  input_types: Record<string, number>;
  busiest_hours: { hour: number; label: string; count: number }[];
  daily_queries: { date: string; count: number }[];
  avg_response_time_ms: number | null;
}

export interface MissingDataGroup {
  intent: string | null;
  collection: string | null;
  count: number;
  entities_asked: { value: string; count: number }[];
  examples: { text: string; language: string | null; asked_at: string }[];
  log_ids: string[];
}
export interface OutOfScopeGroup {
  text: string;
  count: number;
  language: string | null;
  last_asked: string | null;
  log_ids: string[];
}
export interface Unanswered {
  days: number;
  total_unanswered: number;
  missing_data: MissingDataGroup[];
  out_of_scope: OutOfScopeGroup[];
}

/** Thrown when the backend refuses because of a conflict; lists the affected records. */
export class AdminConflictError extends ApiError {
  constructor(message: string, status: number, public records: string[]) {
    super(message, status);
  }
}

// ── request helper ─────────────────────────────────────────────────────────
type OnUnauthorized = () => void;
let onUnauthorized: OnUnauthorized = () => {};
/** AdminLayout registers this so an expired login sends the admin back to sign in. */
export function setUnauthorizedHandler(fn: OnUnauthorized) { onUnauthorized = fn; }

async function adminFetch(path: string, token: string, init: RequestInit = {}, timeoutMs = 30_000): Promise<Response> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${token}`);
  try {
    return await fetch(`/api/admin${path}`, { ...init, headers, signal: controller.signal });
  } catch (err) {
    if ((err as Error).name === "AbortError") throw new ApiError("The server took too long to answer. Please try again.");
    throw new ApiError("Couldn't reach the IntelliVoice server. Please check that it is running.");
  } finally {
    window.clearTimeout(timer);
  }
}

async function readError(res: Response): Promise<never> {
  let data: { detail?: unknown; records?: unknown } = {};
  try { data = await res.json(); } catch { /* not JSON */ }
  if (res.status === 401) onUnauthorized();
  const message = typeof data.detail === "string" ? data.detail : `Server error (${res.status}). Please try again.`;
  if (Array.isArray(data.records)) throw new AdminConflictError(message, res.status, data.records as string[]);
  throw new ApiError(message, res.status);
}

async function json<T>(path: string, token: string, init: RequestInit = {}): Promise<T> {
  const res = await adminFetch(path, token, init);
  if (!res.ok) return readError(res);
  return (await res.json()) as T;
}

const post = <T>(path: string, token: string, body?: unknown) =>
  json<T>(path, token, {
    method: "POST",
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

// ── endpoints ──────────────────────────────────────────────────────────────
export const adminApi = {
  datasets: (token: string) => json<{ datasets: Dataset[] }>("/datasets", token).then((r) => r.datasets),

  /** Downloads the pre-filled Excel template and saves it in the browser. */
  async downloadTemplate(token: string, dataset: string) {
    const res = await adminFetch(`/datasets/${encodeURIComponent(dataset)}/template`, token);
    if (!res.ok) return readError(res);
    const blob = await res.blob();
    const match = /filename="?([^"]+)"?/.exec(res.headers.get("Content-Disposition") || "");
    const filename = match?.[1] || `intellivoice_${dataset}.xlsx`;
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    return filename;
  },

  /** Uploads an edited file and returns the PREVIEW (nothing is saved yet). */
  upload(token: string, dataset: string, file: File) {
    const form = new FormData();
    form.append("file", file, file.name);
    return json<UploadSummary>(`/datasets/${encodeURIComponent(dataset)}/upload`, token, { method: "POST", body: form });
  },

  uploadDetail: (token: string, id: string) => json<UploadSummary>(`/uploads/${id}`, token),
  confirm: (token: string, id: string) => post<UploadSummary>(`/uploads/${id}/confirm`, token),
  cancel: (token: string, id: string) => post<UploadSummary>(`/uploads/${id}/cancel`, token),
  undo: (token: string, id: string) => post<UploadSummary>(`/uploads/${id}/undo`, token),
  history: (token: string, dataset?: string, limit = 50) => {
    const q = new URLSearchParams({ limit: String(limit) });
    if (dataset) q.set("dataset", dataset);
    return json<{ uploads: UploadSummary[] }>(`/uploads?${q}`, token).then((r) => r.uploads);
  },

  dashboard: (token: string, days: number) => json<Dashboard>(`/dashboard?days=${days}`, token),
  unanswered: (token: string, days: number, includeResolved = false) =>
    json<Unanswered>(`/unanswered?days=${days}&include_resolved=${includeResolved}`, token),
  resolve: (token: string, logIds: string[]) => post<{ resolved: number }>("/unanswered/resolve", token, { log_ids: logIds }),
};

// ── small display helpers shared by the admin pages ────────────────────────
/** Backend times from MongoDB come without a timezone but are UTC; show them in Indian time. */
export function formatWhen(iso: string | null | undefined): string {
  if (!iso) return "—";
  const hasZone = /[zZ]|[+-]\d\d:?\d\d$/.test(iso);
  const d = new Date(hasZone ? iso : `${iso}Z`);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("en-IN", { day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit", timeZone: "Asia/Kolkata" });
}

/** "2026-04-10" → "10 Apr 2026" */
export function formatDay(day: string | null | undefined): string {
  if (!day) return "—";
  const d = new Date(`${day}T00:00:00`);
  return Number.isNaN(d.getTime()) ? day : d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

/** "ask_fees_branch" → "Fees branch" */
export function prettyIntent(intent: string | null | undefined): string {
  if (!intent) return "Unknown topic";
  const s = intent.replace(/^ask_/, "").replace(/_/g, " ").trim();
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export function formatValue(v: string | number | null | undefined): string {
  if (v === null || v === undefined || v === "") return "(empty)";
  return typeof v === "number" ? v.toLocaleString("en-IN") : String(v);
}

export const LANGUAGE_NAMES: Record<string, string> = { en: "English", hi: "Hindi", kn: "Kannada" };
