// Shapes shared between the React app and the backend.
// The full description lives in API_CONTRACT.md.

export type LangCode = "en" | "hi" | "kn";

export type ResponseMode =
  | "informational"
  | "reassurance"
  | "comparison"
  | "recommendation"
  | "escalation";

export interface QueryContext {
  rank: number | null;
  category: string | null;
  branch: string | null;
}

export interface LanguageInfo {
  primary?: LangCode | string;
  confidence?: number;
  is_code_switched?: boolean;
}

export interface Understanding {
  intent?: string;
  confidence?: number;
  entities?: Record<string, string | number | string[] | null>;
  emotion?: string;
  response_mode?: ResponseMode | string;
}

export interface MemoryInfo {
  topic?: string | null;
  context_used?: string[];
}

export interface TableData {
  title?: string;
  columns: string[];
  rows: (string | number)[][];
}

/** "College at a glance" card — sent only for "tell me everything" questions (2026-10-15). */
export interface OverviewItem {
  label: string;
  value: string;
}

export interface OverviewSection {
  id: string;
  title: string;
  /** Material Symbols icon name */
  icon: string;
  items: OverviewItem[];
  note?: string;
}

export interface CollegeOverview {
  title: string;
  sections: OverviewSection[];
  /** GET this to download the full brochure PDF */
  brochure_url?: string;
  generated_at?: string;
}

/** 2026-10-29: a PDF button under a reply (bus routes from the college website, brochure) */
export interface DocumentLink {
  title: string;
  url: string;
  /** true: download (our own brochure); otherwise open in a new tab */
  download?: boolean;
}

export interface AudioInfo {
  format?: "wav" | "mp3" | "ogg" | "webm" | string;
  base64?: string;
  url?: string;
  voice?: string;
}

export interface Escalation {
  needed?: boolean;
  message?: string | null;
  contact?: { phone?: string; email?: string } | null;
}

export interface QueryResponse {
  /** "no_speech" (2026-10-28): the recording had no speech — nothing to show or play */
  status?: string;
  message?: string;
  session_id?: string;
  transcript?: string;
  language?: LanguageInfo;
  understanding?: Understanding;
  memory?: MemoryInfo;
  response?: {
    text?: string;
    /** language/script the reply is written in: en | kn | kn-Latn | hi | hi-Latn */
    language?: string;
    text_romanized?: string;
  };
  data?: TableData | null;
  audio?: AudioInfo | null;
  escalation?: Escalation | null;
  source?: string;
  /** College-at-a-glance card data (only for "tell me everything" questions) */
  overview?: CollegeOverview | null;
  /** PDF buttons under the reply */
  documents?: DocumentLink[];
  /** 2026-10-31: offer "Get my document checklist" under this reply */
  checklist_available?: boolean;
  /** set by the Express demo mode */
  demo?: boolean;
}

/** 2026-10-31: POST /api/transcribe — the words heard, shown before sending */
export interface TranscribeResponse {
  status: "ok" | "no_speech";
  text?: string;
  language?: string;
  unclear?: boolean;
  message?: string;
}

export type Role = "student" | "admin";

export interface User {
  name: string;
  email: string;
  role: Role;
}

export interface AuthResponse {
  token: string;
  user: User;
}
