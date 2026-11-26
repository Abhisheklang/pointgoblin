import { useState } from "react";

import { ApiProblem, createRoom, joinRoom, login, register } from "../api";
import Logo from "../components/Logo";
import { DECK, cardLabel } from "../deck";
import type { Session } from "../types";

interface HomeProps {
  onSession: (session: Session) => void;
}

type Mode = "create" | "join";

function DeckStrip() {
  const row = (hidden: boolean) => (
    <span aria-hidden={hidden} className="flex shrink-0 items-center">
      {DECK.concat(DECK).map((value, index) => (
        <span key={index} className="flex items-center">
          <span className="px-4 font-display text-heading font-black text-ink">
            {cardLabel(value)}
          </span>
          <span className="text-brassdeep" aria-hidden="true">
            ◆
          </span>
        </span>
      ))}
    </span>
  );
  return (
    <div className="pg-strip border-y-2 border-ink bg-parchment py-2.5" aria-hidden="true">
      <div className="pg-strip-track">
        {row(false)}
        {row(true)}
      </div>
    </div>
  );
}

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
    "pg-input w-full border-[1.5px] border-ink bg-paper px-3 py-2.5 text-body text-ink placeholder:text-inksoft";
  const labelClass = "pg-kicker mb-1.5 block text-[0.65rem] text-inksoft";

  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-6xl flex-col px-4 sm:px-6">
      <header className="flex items-center justify-between border-b-2 border-ink py-4">
        <Logo />
        <a
          href="/"
          className="pg-kicker text-[0.65rem] text-inksoft transition-colors hover:text-evergreen"
        >
          About planning poker
        </a>
      </header>

      <main className="grid flex-1 items-start gap-10 py-10 lg:grid-cols-2 lg:py-14">
        <section className="pg-enter">
          <p className="pg-kicker text-brassdeep">
            Real time planning poker · FastAPI · WebSockets · Redis
          </p>
          <h1 className="mt-3 font-display text-[3.4rem] leading-[0.98] font-black sm:text-display">
            Cards down.
            <span className="block text-evergreen italic">Numbers honest.</span>
          </h1>
          <p className="mt-5 max-w-md text-body leading-relaxed text-inksoft">
            PointGoblin runs a planning poker session the fair way. Everyone picks a card in secret,
            the host reveals the whole table in one go, and the team lands on one number it can
            defend.
          </p>
          <div className="mt-8">
            {[
              ["01", "Votes stay hidden, so the loudest voice cannot anchor the room."],
              ["02", "Guests join with a six character code. No account needed."],
              ["03", "Average and agreement appear the moment the cards flip."],
            ].map(([num, text]) => (
              <p
                key={num}
                className="flex items-baseline gap-4 border-t border-line py-3 text-body last:border-b"
              >
                <span className="font-display text-heading font-black text-brassdeep">{num}</span>
                <span>{text}</span>
              </p>
            ))}
          </div>
          <div className="mt-8 hidden lg:block">
            <DeckStrip />
          </div>
        </section>

        <section className="pg-enter pg-print bg-card p-5 sm:p-7" aria-label="Start">
          <div className="grid grid-cols-2 gap-2.5" role="group" aria-label="Choose how to start">
            <button
              type="button"
              aria-pressed={mode === "create"}
              onClick={() => {
                setMode("create");
                setError("");
              }}
              className={`pg-btn border-[1.5px] border-ink px-3 py-2.5 font-display text-body font-bold ${
                mode === "create" ? "bg-ink text-paper" : "bg-paper text-ink hover:bg-parchment"
              }`}
            >
              Create a room
            </button>
            <button
              type="button"
              aria-pressed={mode === "join"}
              onClick={() => {
                setMode("join");
                setError("");
              }}
              className={`pg-btn border-[1.5px] border-ink px-3 py-2.5 font-display text-body font-bold ${
                mode === "join" ? "bg-ink text-paper" : "bg-paper text-ink hover:bg-parchment"
              }`}
            >
              Join a room
            </button>
          </div>

          {error && (
            <p
              role="alert"
              className="mt-4 border-[1.5px] border-clay bg-paper px-3 py-2 text-small font-medium text-clay"
            >
              {error}
            </p>
          )}

          {mode === "create" ? (
            <form onSubmit={handleCreate} className="mt-6 flex flex-col gap-4">
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
                  placeholder={hasAccount ? "Your password" : "At least 8 characters"}
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
                className="pg-btn pg-print-sm mt-1 bg-evergreen px-4 py-3 font-display text-body font-bold text-paper hover:bg-felt"
              >
                {busy ? "Opening your room..." : "Create room"}
              </button>
              <button
                type="button"
                onClick={() => {
                  setHasAccount(!hasAccount);
                  setError("");
                }}
                className="text-small font-semibold text-inksoft underline underline-offset-4 hover:text-evergreen"
              >
                {hasAccount
                  ? "New here? Create a host account instead."
                  : "Already have an account? Sign in instead."}
              </button>
            </form>
          ) : (
            <form onSubmit={handleJoin} className="mt-6 flex flex-col gap-4">
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
                  className={`${inputClass} font-mono text-heading font-bold tracking-[0.3em] uppercase`}
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
                className="pg-btn pg-print-sm mt-1 bg-evergreen px-4 py-3 font-display text-body font-bold text-paper hover:bg-felt"
              >
                {busy ? "Joining..." : "Join room"}
              </button>
              <p className="text-small text-inksoft">
                Ask the host for the code. It is the six characters at the top of their room.
              </p>
            </form>
          )}
        </section>
      </main>

      <div className="pb-8 lg:hidden">
        <DeckStrip />
      </div>

      <footer className="flex flex-wrap items-center justify-between gap-2 border-t border-line py-5 text-small text-inksoft">
        <span>PointGoblin. A backend portfolio project.</span>
      </footer>
    </div>
  );
}
