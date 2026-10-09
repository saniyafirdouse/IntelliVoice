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
  /** set by the Express demo mode */
  demo?: boolean;
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
