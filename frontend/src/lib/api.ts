import type { StoredSession } from "./session";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export class ApiError extends Error {
  status: number;
  payload: unknown;

  constructor(message: string, status: number, payload: unknown) {
    super(message);
    this.status = status;
    this.payload = payload;
  }
}

export async function apiFetch<T>(path: string, init: RequestInit = {}, session?: StoredSession | null): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (session?.token) {
    headers.set("Authorization", `Bearer ${session.token}`);
  }
  if (session?.organization) {
    headers.set("X-Organization-Slug", session.organization);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  const payload = text ? JSON.parse(text) : null;

  if (!response.ok) {
    const detail = typeof payload === "object" && payload !== null && "detail" in payload ? String(payload.detail) : response.statusText;
    throw new ApiError(detail, response.status, payload);
  }

  return payload as T;
}

