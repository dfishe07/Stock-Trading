import type { User } from "./types";

export interface StoredSession {
  token: string;
  user: User;
  organization: string | null;
  originalSession?: {
    token: string;
    user: User;
    organization: string | null;
  };
  impersonationAuditId?: string;
}

const STORAGE_KEY = "stock-trading-session";

export function readSession(): StoredSession | null {
  const value = window.localStorage.getItem(STORAGE_KEY);
  if (!value) {
    return null;
  }

  try {
    return JSON.parse(value) as StoredSession;
  } catch {
    window.localStorage.removeItem(STORAGE_KEY);
    return null;
  }
}

export function writeSession(session: StoredSession | null): void {
  if (!session) {
    window.localStorage.removeItem(STORAGE_KEY);
    return;
  }
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
}

