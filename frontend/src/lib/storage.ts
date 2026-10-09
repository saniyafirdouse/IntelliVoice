// Browser storage can be blocked (private mode, strict settings), so every access is guarded.

type Store = "local" | "session";

const pick = (store: Store): Storage | null => {
  try {
    return store === "local" ? window.localStorage : window.sessionStorage;
  } catch {
    return null;
  }
};

export const storage = {
  get(key: string, store: Store = "local"): string | null {
    try {
      return pick(store)?.getItem(key) ?? null;
    } catch {
      return null;
    }
  },
  set(key: string, value: string, store: Store = "local") {
    try {
      pick(store)?.setItem(key, value);
    } catch {
      /* ignore */
    }
  },
  remove(key: string, store: Store = "local") {
    try {
      pick(store)?.removeItem(key);
    } catch {
      /* ignore */
    }
  },
};

export function newSessionId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `sess-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}
