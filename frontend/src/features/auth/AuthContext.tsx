import {
  ReactNode,
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { apiFetch } from "../../lib/api";
import { readSession, writeSession, type StoredSession } from "../../lib/session";
import type { User } from "../../lib/types";

interface AuthContextValue {
  session: StoredSession | null;
  login: (payload: { username: string; password: string }) => Promise<void>;
  register: (payload: {
    username: string;
    email: string;
    password: string;
    first_name: string;
    last_name: string;
    organization_name: string;
  }) => Promise<void>;
  logout: () => Promise<void>;
  refreshMe: () => Promise<void>;
  acceptImpersonation: (payload: { token: string; user: User; auditId: string }) => void;
  exitImpersonation: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<StoredSession | null>(() => readSession());

  useEffect(() => {
    writeSession(session);
  }, [session]);

  const refreshMe = async () => {
    if (!session) {
      return;
    }
    const payload = await apiFetch<{ user: User; organization: string | null }>("/api/auth/me/", {}, session);
    setSession((current) =>
      current
        ? {
            ...current,
            user: payload.user,
            organization: payload.organization,
          }
        : current,
    );
  };

  const login = async (payload: { username: string; password: string }) => {
    const response = await apiFetch<{ token: string; user: User }>("/api/auth/login/", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    const nextSession: StoredSession = {
      token: response.token,
      user: response.user,
      organization: response.user.memberships.find((membership) => membership.is_default)?.organization.slug ?? null,
    };
    setSession(nextSession);
  };

  const register = async (payload: {
    username: string;
    email: string;
    password: string;
    first_name: string;
    last_name: string;
    organization_name: string;
  }) => {
    const response = await apiFetch<{ token: string; user: User; organization: string }>("/api/auth/register/", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    setSession({
      token: response.token,
      user: response.user,
      organization: response.organization,
    });
  };

  const logout = async () => {
    if (session) {
      try {
        await apiFetch("/api/auth/logout/", { method: "POST" }, session);
      } catch {
        // Clearing local state is more important than surfacing logout failures here.
      }
    }
    setSession(null);
  };

  const acceptImpersonation = (payload: { token: string; user: User; auditId: string }) => {
    if (!session) {
      return;
    }
    setSession({
      token: payload.token,
      user: payload.user,
      organization: session.organization,
      originalSession: {
        token: session.token,
        user: session.user,
        organization: session.organization,
      },
      impersonationAuditId: payload.auditId,
    });
  };

  const exitImpersonation = () => {
    setSession((current) => {
      if (!current?.originalSession) {
        return current;
      }
      return {
        ...current.originalSession,
      };
    });
  };

  const value = useMemo(
    () => ({
      session,
      login,
      register,
      logout,
      refreshMe,
      acceptImpersonation,
      exitImpersonation,
    }),
    [session],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}

