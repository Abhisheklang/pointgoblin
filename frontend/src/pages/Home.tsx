import { useState } from "react";

import { ApiProblem, createRoom, joinRoom, login, register } from "../api";
import Logo from "../components/Logo";
import type { Session } from "../types";

interface HomeProps {
  onSession: (session: Session) => void;
}

type Mode = "create" | "join";

export default function Home({ onSession }: HomeProps) {
  const [mode, setMode] = useState<Mode>("create");
  const [authName, setAuthName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [hasAccount, setHasAccount] = useState(true);
  const [roomName, setRoomName] = useState("");
  const [guestName, setGuestName] = useState("");
  const [roomCode, setRoomCode] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const auth = hasAccount
        ? await login(email, password)
        : await register(authName, email, password);
      const created = await createRoom(auth.access_token, roomName);
      onSession({
        token: auth.access_token,
        name: auth.name,
        code: created.room.code,
        isHostAccount: true,
      });
    } catch (problem) {
      setError(
        problem instanceof ApiProblem ? problem.message : "Something went wrong. Try again.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleJoin(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const joined = await joinRoom(roomCode, guestName);
      onSession({
        token: joined.access_token,
        name: guestName,
        code: joined.room.code,
        isHostAccount: false,
      });
    } catch (problem) {
      setError(
        problem instanceof ApiProblem ? problem.message : "Something went wrong. Try again.",
      );
    } finally {
      setBusy(false);
    }
  }

  const inputClass =
    "w-full rounded-lg border border-forest-700 bg-forest-950 px-3 py-2.5 text-body text-cream-50 placeholder:text-muted-400 focus:border-goblin-400 focus:outline-none";
  const labelClass = "block text-small font-semibold text-cream-300";

  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-6xl flex-col px-4 sm:px-6">
      <header className="flex items-center justify-between py-5">
        <Logo />
        <a href="/" className="text-small font-semibold text-muted-400 hover:text-cream-50">
          About planning poker
        </a>
      </header>

      <main className="grid flex-1 items-start gap-10 py-8 lg:grid-cols-2 lg:py-14">
        <section className="pg-enter">
          <h1 className="text-display leading-tight font-bold">
            Estimate together.
            <span className="block text-goblin-400">Reveal all at once.</span>
          </h1>
          <p className="mt-4 max-w-md text-body text-cream-300">
            PointGoblin runs a planning poker session the fair way. Everyone picks a card in secret,
            the host reveals the whole table in one go, and the team lands on one number it can
            defend.
          </p>
          <ul className="mt-6 flex flex-col gap-3 text-body text-cream-300">
            <li>Votes stay hidden, so the loudest voice cannot anchor the room.</li>
            <li>Guests join with a six character code. No account needed.</li>
            <li>Average and agreement appear the moment the cards flip.</li>
          </ul>
        </section>

        <section
          className="pg-enter rounded-2xl bg-forest-900 p-5 shadow-xl sm:p-6"
          aria-label="Start"
        >
          <div className="grid grid-cols-2 gap-2" role="tablist" aria-label="Choose how to start">
            <button
              type="button"
              role="tab"
              aria-selected={mode === "create"}
              onClick={() => setMode("create")}
              className={`pg-btn rounded-lg px-3 py-2.5 font-semibold ${
                mode === "create" ? "bg-goblin-400 text-forest-950" : "bg-forest-850 text-cream-300"
              }`}
            >
              Create a room
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={mode === "join"}
              onClick={() => setMode("join")}
              className={`pg-btn rounded-lg px-3 py-2.5 font-semibold ${
                mode === "join" ? "bg-goblin-400 text-forest-950" : "bg-forest-850 text-cream-300"
              }`}
            >
              Join a room
            </button>
          </div>

          {error && (
            <p
              role="alert"
              className="mt-4 rounded-lg bg-forest-850 px-3 py-2 text-small text-rose-soft"
            >
              {error}
            </p>
          )}

          {mode === "create" ? (
            <form onSubmit={handleCreate} className="mt-5 flex flex-col gap-4">
              {!hasAccount && (
                <div>
                  <label className={labelClass} htmlFor="auth-name">
                    Your name
                  </label>
                  <input
                    id="auth-name"
                    className={inputClass}
                    value={authName}
                    onChange={(event) => setAuthName(event.target.value)}
                    required
                    autoComplete="name"
                    placeholder="Harriet Host"
                  />
                </div>
              )}
              <div>
                <label className={labelClass} htmlFor="auth-email">
                  Email
                </label>
                <input
                  id="auth-email"
                  type="email"
                  className={inputClass}
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  required
                  autoComplete="email"
                  placeholder="you@company.com"
                />
              </div>
              <div>
                <label className={labelClass} htmlFor="auth-password">
                  Password
                </label>
                <input
                  id="auth-password"
                  type="password"
                  className={inputClass}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                  minLength={hasAccount ? 1 : 8}
                  autoComplete={hasAccount ? "current-password" : "new-password"}
                  placeholder="At least 8 characters"
                />
              </div>
              <div>
                <label className={labelClass} htmlFor="room-name">
                  Room name
                </label>
                <input
                  id="room-name"
                  className={inputClass}
                  value={roomName}
                  onChange={(event) => setRoomName(event.target.value)}
                  required
                  placeholder="Sprint 24 planning"
                />
              </div>
              <button
                type="submit"
                disabled={busy}
                className="pg-btn rounded-lg bg-goblin-400 px-4 py-3 font-bold text-forest-950 hover:bg-goblin-300"
              >
                {busy ? "Opening your room..." : "Create room"}
              </button>
              <button
                type="button"
                onClick={() => setHasAccount(!hasAccount)}
                className="text-small font-semibold text-muted-400 hover:text-cream-50"
              >
                {hasAccount
                  ? "New here? Create a host account instead."
                  : "Already have an account? Sign in instead."}
              </button>
            </form>
          ) : (
            <form onSubmit={handleJoin} className="mt-5 flex flex-col gap-4">
              <div>
                <label className={labelClass} htmlFor="guest-name">
                  Your name
                </label>
                <input
                  id="guest-name"
                  className={inputClass}
                  value={guestName}
                  onChange={(event) => setGuestName(event.target.value)}
                  required
                  autoComplete="name"
                  placeholder="Gus Guest"
                />
              </div>
              <div>
                <label className={labelClass} htmlFor="room-code">
                  Room code
                </label>
                <input
                  id="room-code"
                  className={`${inputClass} tracking-[0.3em] uppercase`}
                  value={roomCode}
                  onChange={(event) => setRoomCode(event.target.value.toUpperCase())}
                  required
                  minLength={6}
                  maxLength={6}
                  placeholder="ABC123"
                />
              </div>
              <button
                type="submit"
                disabled={busy}
                className="pg-btn rounded-lg bg-goblin-400 px-4 py-3 font-bold text-forest-950 hover:bg-goblin-300"
              >
                {busy ? "Joining..." : "Join room"}
              </button>
              <p className="text-small text-muted-400">
                Ask the host for the code. It is the six characters at the top of their room.
              </p>
            </form>
          )}
        </section>
      </main>

      <footer className="flex flex-wrap items-center justify-between gap-2 py-5 text-small text-muted-400">
        <span>PointGoblin. Fair estimates for remote teams.</span>
        <span>
          Developed by{" "}
          <a
            className="font-semibold text-cream-300 hover:text-goblin-300"
            href="https://github.com/Abhisheklang"
          >
            Abhisheklang
          </a>
        </span>
      </footer>
    </div>
  );
}
