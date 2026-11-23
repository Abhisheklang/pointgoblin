import type { RoomState } from "./types";

const API_BASE = import.meta.env.VITE_API_URL ?? "";

export class ApiProblem extends Error {
  readonly code: string;

  constructor(code: string, message: string) {
    super(message);
    this.code = code;
  }
}

async function request<T>(path: string, init: RequestInit = {}, token?: string): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const problem = body as { error?: { code?: string; message?: string } } | null;
    throw new ApiProblem(
      problem?.error?.code ?? "request_failed",
      problem?.error?.message ?? "Something went wrong. Please try again.",
    );
  }
  return body as T;
}

interface TokenBody {
  access_token: string;
  name: string;
}

export function register(name: string, email: string, password: string): Promise<TokenBody> {
  return request<TokenBody>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ name, email, password }),
  });
}

export function login(email: string, password: string): Promise<TokenBody> {
  return request<TokenBody>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

interface CreateRoomBody {
  room: { code: string; name: string };
  state: RoomState;
}

export function createRoom(token: string, name: string): Promise<CreateRoomBody> {
  return request<CreateRoomBody>(
    "/api/rooms",
    { method: "POST", body: JSON.stringify({ name }) },
    token,
  );
}

interface JoinBody {
  access_token: string;
  room: { code: string; name: string };
  state: RoomState;
}

export function joinRoom(code: string, name: string): Promise<JoinBody> {
  return request<JoinBody>("/api/rooms/join", {
    method: "POST",
    body: JSON.stringify({ code: code.toUpperCase(), name }),
  });
}

export function socketUrl(code: string, token: string): string {
  const apiBase = import.meta.env.VITE_API_URL as string | undefined;
  if (apiBase) {
    const url = new URL(apiBase);
    url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
    return `${url.origin}/ws/rooms/${code}?token=${encodeURIComponent(token)}`;
  }
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/ws/rooms/${code}?token=${encodeURIComponent(token)}`;
}
