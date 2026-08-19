"use client";
import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { api } from "./api";

type User = { id: number; email: string; username: string; is_seller: boolean };

type AuthState = {
  token: string | null;
  user: User | null;
  ready: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (d: { email: string; username: string; password: string; is_seller?: boolean; display_name?: string }) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthState | null>(null);
const TOKEN_KEY = "shoplive_token";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const saved = typeof window !== "undefined" ? localStorage.getItem(TOKEN_KEY) : null;
    if (!saved) {
      setReady(true);
      return;
    }
    setToken(saved);
    api.me(saved)
      .then(setUser)
      .catch(() => {
        localStorage.removeItem(TOKEN_KEY);
        setToken(null);
      })
      .finally(() => setReady(true));
  }, []);

  async function applyToken(t: string) {
    localStorage.setItem(TOKEN_KEY, t);
    setToken(t);
    setUser(await api.me(t));
  }

  async function login(email: string, password: string) {
    const { access_token } = await api.login(email, password);
    await applyToken(access_token);
  }

  async function register(d: { email: string; username: string; password: string; is_seller?: boolean; display_name?: string }) {
    const { access_token } = await api.register(d);
    await applyToken(access_token);
  }

  function logout() {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ token, user, ready, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
