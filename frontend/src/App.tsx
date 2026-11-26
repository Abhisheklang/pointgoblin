import { useState } from "react";

import Home from "./pages/Home";
import Room from "./pages/Room";
import type { Session } from "./types";

const SESSION_KEY = "pointgoblin.session";

// Token lifetimes from the backend: guest tokens live 12 hours and user
// tokens 24 hours. A stored session older than its token lifetime is
// discarded instead of being offered to a doomed reconnect.
const GUEST_MAX_AGE_MS = 12 * 60 * 60 * 1000;
const USER_MAX_AGE_MS = 24 * 60 * 60 * 1000;

interface StoredSession {
  session: Session;
  savedAt: number;
}

function loadSession(): Session | null {
  try {
    const raw = window.localStorage.getItem(SESSION_KEY);
    if (!raw) {
      return null;
    }
    const stored = JSON.parse(raw) as StoredSession;
    const maxAge = stored.session.isHostAccount ? USER_MAX_AGE_MS : GUEST_MAX_AGE_MS;
    if (Date.now() - stored.savedAt > maxAge) {
      window.localStorage.removeItem(SESSION_KEY);
      return null;
    }
    return stored.session;
  } catch {
    return null;
  }
}

function saveSession(session: Session | null) {
  try {
    if (session === null) {
      window.localStorage.removeItem(SESSION_KEY);
    } else {
      const stored: StoredSession = { session, savedAt: Date.now() };
      window.localStorage.setItem(SESSION_KEY, JSON.stringify(stored));
    }
  } catch {
    // Storage can be unavailable (private mode, quotas). The session then
    // behaves as before: it lives in memory only for this page.
  }
}

export default function App() {
  // Persisting the session is what makes a refresh safe (K1): the same
  // token comes back, so a guest returns as the same participant identity
  // and still owns the vote they cast before the refresh, instead of
  // rejoining as a new guest and orphaning a phantom vote in the round.
  const [session, setSession] = useState<Session | null>(loadSession);

  function updateSession(next: Session | null) {
    saveSession(next);
    setSession(next);
  }

  if (session === null) {
    return <Home onSession={updateSession} />;
  }
  return <Room session={session} onLeave={() => updateSession(null)} />;
}
