import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { authApi } from "../lib/api";
import { storage } from "../lib/storage";
import type { Role, User } from "../lib/types";

// Login is optional. Signed-in state is kept in localStorage so it survives a page refresh.

const KEY = "intellivoice_auth";

interface AuthState {
  token: string | null;
  user: User | null;
}

interface AuthValue extends AuthState {
  login: (email: string, password: string, role: Role) => Promise<User>;
  signup: (name: string, email: string, phone: string, password: string) => Promise<User>;
  logout: () => void;
}

const AuthContext = createContext<AuthValue | null>(null);

function loadAuth(): AuthState {
  try {
    const raw = storage.get(KEY);
    if (!raw) return { token: null, user: null };
    const parsed = JSON.parse(raw) as AuthState;
    return parsed && parsed.user ? parsed : { token: null, user: null };
  } catch {
    return { token: null, user: null };
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>(loadAuth);

  const save = useCallback((next: AuthState) => {
    setState(next);
    storage.set(KEY, JSON.stringify(next));
  }, []);

  const login = useCallback(async (email: string, password: string, role: Role) => {
    const res = await authApi.login(email, password, role);
    save({ token: res.token, user: res.user });
    return res.user;
  }, [save]);

  const signup = useCallback(async (name: string, email: string, phone: string, password: string) => {
    const res = await authApi.signup(name, email, phone, password);
    save({ token: res.token, user: res.user });
    return res.user;
  }, [save]);

  const logout = useCallback(() => {
    setState({ token: null, user: null });
    storage.remove(KEY);
  }, []);

  const value = useMemo(() => ({ ...state, login, signup, logout }), [state, login, signup, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
