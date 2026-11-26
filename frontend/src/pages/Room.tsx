import { useEffect, useRef, useState } from "react";

import { socketUrl } from "../api";
import { cardLabel } from "../deck";
import GithubIcon from "../components/GithubIcon";
import Logo from "../components/Logo";
import { PresenceList, ResultsPanel, RoomSkeleton, StoryQueue } from "../components/RoomParts";
import type { RoomState, Session, SocketMessage } from "../types";

interface RoomProps {
  session: Session;
  onLeave: () => void;
}

export default function Room({ session, onLeave }: RoomProps) {
  const [state, setState] = useState<RoomState | null>(null);
  const myIdRef = useRef<string | null>(null);
  const [isHost, setIsHost] = useState(session.isHostAccount);
  const [myVote, setMyVote] = useState<string | null>(null);
  const [storyTitle, setStoryTitle] = useState("");
  const [connected, setConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<
    "connecting" | "live" | "reconnecting" | "failed"
  >("connecting");
  const [notice, setNotice] = useState("");
  const [confirmReset, setConfirmReset] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let cancelled = false;
    let attempts = 0;
    let timer: number | undefined;
    const fatalCodes: Record<number, string> = {
      4401: "Your session token has expired. Leave the room and join again.",
      4403: "That token belongs to a different room. Leave the room and join again.",
      4404: "That room no longer exists. Leave the room and check the code.",
    };

    function connect() {
      if (cancelled) {
        return;
      }
      const socket = new WebSocket(socketUrl(session.code, session.token));
      socketRef.current = socket;
      socket.onopen = () => {
        attempts = 0;
        setConnected(true);
        setConnectionStatus("live");
      };
      socket.onclose = (event: CloseEvent) => {
        setConnected(false);
        if (cancelled) {
          return;
        }
        if (event.code in fatalCodes) {
          setConnectionStatus("failed");
          setNotice(fatalCodes[event.code]);
          return;
        }
        attempts += 1;
        if (attempts > 6) {
          setConnectionStatus("failed");
          setNotice("The connection was lost and could not be restored. Leave and rejoin.");
          return;
        }
        setConnectionStatus("reconnecting");
        timer = window.setTimeout(connect, Math.min(1000 * 2 ** (attempts - 1), 10000));
      };
      socket.onmessage = (event: MessageEvent<string>) => {
        const message = JSON.parse(event.data) as SocketMessage;
        if (message.type === "you") {
          setIsHost(message.is_host);
          myIdRef.current = message.id;
        } else if (message.type === "error") {
          setNotice(message.message);
        } else {
          setState(message);
          if (
            message.round === null ||
            (myIdRef.current !== null && !message.round.voted.includes(myIdRef.current))
          ) {
            setMyVote(null);
          }
        }
      };
    }

    connect();
    return () => {
      cancelled = true;
      if (timer !== undefined) {
        window.clearTimeout(timer);
      }
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, [session.code, session.token, session.name]);

  useEffect(() => {
    if (!notice) {
      return;
    }
    const timer = window.setTimeout(() => setNotice(""), 5000);
    return () => window.clearTimeout(timer);
  }, [notice]);

  function send(payload: Record<string, string>): boolean {
    const socket = socketRef.current;
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(payload));
      return true;
    }
    return false;
  }

  function handleVote(value: string) {
    // Only mark the card as cast when the vote actually left the browser:
    // a click while disconnected must never look like a counted vote (U4).
    if (send({ action: "vote", value })) {
      setMyVote(value);
    } else {
      setNotice("You are not connected right now. That vote was not sent.");
    }
  }

  function handleAddStory(event: React.FormEvent) {
    event.preventDefault();
    const title = storyTitle.trim();
    if (!title) {
      return;
    }
    if (send({ action: "add_story", title })) {
      setStoryTitle("");
    } else {
      setNotice("You are not connected right now. That story was not added.");
    }
  }

  function handleReset() {
    // Reset permanently deletes every vote in the round, so it takes two
    // clicks: the first arms the button, the second confirms (SEC8).
    if (!confirmReset) {
      setConfirmReset(true);
      setNotice("Reset deletes every vote cast in this round. Click Confirm reset to go ahead.");
      return;
    }
    setConfirmReset(false);
    setMyVote(null);
    send({ action: "reset" });
  }

  async function copyCode() {
    try {
      await navigator.clipboard.writeText(session.code);
      setNotice("Room code copied.");
    } catch {
      setNotice("Copy failed. Read the code out to your team instead.");
    }
  }

  const activeStory = state?.stories.find(
    (story) => story.status === "active" || story.status === "revealed",
  );

  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-6xl flex-col px-4 sm:px-6">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b-2 border-ink py-4">
        <Logo />
        <div className="flex items-center gap-3">
          <span
            className="flex items-center gap-2 border-[1.5px] border-ink bg-card px-2.5 py-1.5"
            role="status"
          >
            <span
              className={`h-2 w-2 rounded-full ${connected ? "bg-evergreen" : "bg-clay"}`}
              aria-hidden="true"
            />
            <span className="pg-kicker text-[0.62rem]">
              {connectionStatus === "live" && "Live"}
              {connectionStatus === "connecting" && "Connecting"}
              {connectionStatus === "reconnecting" && "Reconnecting"}
              {connectionStatus === "failed" && "Connection failed"}
            </span>
          </span>
          <button
            type="button"
            onClick={onLeave}
            className="pg-btn pg-print-sm bg-paper px-3 py-2 text-small font-semibold text-ink hover:bg-parchment"
          >
            Leave room
          </button>
        </div>
      </header>

      {state === null && connectionStatus === "failed" ? (
        <main className="flex flex-1 flex-col items-start gap-3 py-10">
          <h1 className="font-display text-title font-bold">The connection failed</h1>
          <p className="max-w-md text-body text-inksoft">
            {notice || "The room could not be reached."}
          </p>
          <button
            type="button"
            onClick={onLeave}
            className="pg-btn pg-print-sm bg-ink px-4 py-2.5 font-semibold text-paper"
          >
            Leave room
          </button>
        </main>
      ) : state === null ? (
        <div className="pt-6">
          <RoomSkeleton />
        </div>
      ) : (
        <main className="pg-enter flex flex-1 flex-col gap-5 py-6">
          <section className="flex flex-wrap items-end justify-between gap-4">
            <div className="min-w-0">
              <p className="pg-kicker text-brassdeep">Planning poker room</p>
              <h1 className="mt-1 font-display text-4xl font-black break-words">
                {state.room.name}
              </h1>
              <p className="mt-1.5 text-small text-inksoft">
                Hosted by {state.room.host_name ?? "your host"} · You are {session.name}
              </p>
            </div>
            <button
              type="button"
              onClick={copyCode}
              className="pg-btn pg-print-sm bg-ink px-4 py-2.5 text-left text-paper"
              aria-label={`Copy room code ${state.room.code}`}
            >
              <span className="pg-kicker block text-[0.6rem] text-paper/60">Room code</span>
              <span className="block font-mono text-heading font-bold tracking-[0.3em]">
                {state.room.code}
              </span>
            </button>
          </section>
          {notice && (
            <p role="status" className="text-small font-semibold text-evergreen">
              {notice}
            </p>
          )}

          <div className="grid grid-cols-1 items-start gap-5 lg:grid-cols-[330px_1fr]">
            <div className="flex flex-col gap-5">
              <section aria-label="Participants" className="pg-print bg-card p-4">
                <h2 className="flex items-baseline justify-between font-display text-heading font-bold">
                  At the table
                  <span className="pg-kicker text-[0.62rem] text-inksoft">
                    {state.participants.length} seated
                  </span>
                </h2>
                <div className="mt-3">
                  <PresenceList
                    participants={state.participants}
                    votedIds={state.round?.voted ?? []}
                  />
                </div>
              </section>

              <section aria-label="Stories" className="pg-print bg-card p-4">
                <h2 className="font-display text-heading font-bold">Story queue</h2>
                <div className="mt-2">
                  <StoryQueue
                    stories={state.stories}
                    isHost={isHost}
                    onActivate={(storyId) => send({ action: "activate_story", story_id: storyId })}
                  />
                </div>
                {isHost && (
                  <form onSubmit={handleAddStory} className="mt-3 flex gap-2">
                    <label className="sr-only" htmlFor="story-title">
                      Story title
                    </label>
                    <input
                      id="story-title"
                      value={storyTitle}
                      onChange={(event) => setStoryTitle(event.target.value)}
                      placeholder="Add a story"
                      className="pg-input min-w-0 flex-1 border-[1.5px] border-ink bg-paper px-3 py-2 text-body placeholder:text-inksoft"
                    />
                    <button
                      type="submit"
                      className="pg-btn pg-print-sm shrink-0 bg-evergreen px-3.5 py-2 font-semibold text-paper hover:bg-felt"
                    >
                      Add
                    </button>
                  </form>
                )}
              </section>
            </div>

            <div className="flex flex-col gap-5">
              <section aria-label="Voting" className="pg-print bg-felt p-5 text-paper sm:p-7">
                {activeStory ? (
                  <>
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="pg-kicker text-brass">Now voting on</p>
                        <h2 className="mt-1.5 font-display text-title leading-snug font-bold break-words">
                          {activeStory.title}
                        </h2>
                      </div>
                      <p className="pg-kicker pt-1 text-[0.62rem] text-paper/60">
                        {state.round?.revealed
                          ? "Cards face up"
                          : `${state.round?.vote_count ?? 0} of ${state.participants.length} cards in`}
                      </p>
                    </div>
                    <p className="mt-2 max-w-lg text-small text-paper/70">
                      {state.round?.revealed
                        ? "Talk it through, then reset the round or move to the next story."
                        : "Pick a card. It stays face down until the host calls the reveal."}
                    </p>

                    <ul className="mt-5 flex flex-wrap gap-2" aria-label="Seats at the table">
                      {state.participants.map((person) => {
                        const hasVoted = (state.round?.voted ?? []).includes(person.id);
                        return (
                          <li
                            key={person.id}
                            className="pg-pop flex items-center gap-2 rounded-full border border-paper/35 py-1 pr-3 pl-1"
                          >
                            <span
                              className={`flex h-6 w-6 items-center justify-center rounded-full text-[0.7rem] font-bold ${
                                person.is_host ? "bg-brass text-ink" : "bg-paper text-ink"
                              }`}
                              aria-hidden="true"
                            >
                              {person.name.charAt(0).toUpperCase()}
                            </span>
                            <span className="max-w-28 truncate text-small">{person.name}</span>
                            <span
                              className={`inline-block h-4 w-2.5 rounded-[2px] border ${
                                hasVoted
                                  ? "border-brass bg-brass"
                                  : "border-paper/50 bg-transparent"
                              }`}
                              aria-hidden="true"
                            />
                            <span className="sr-only">
                              {hasVoted ? "has voted" : "has not voted"}
                            </span>
                          </li>
                        );
                      })}
                    </ul>

                    <div
                      className="mt-6 grid grid-cols-5 gap-2.5 pt-2 sm:gap-3.5"
                      role="group"
                      aria-label="Pick your card"
                    >
                      {state.deck.map((value, index) => {
                        const selected = myVote === value;
                        const faceUp = state.round?.revealed ?? false;
                        const tilt = (index < 5 ? index - 2 : 7 - index) * 1.1;
                        return (
                          <button
                            key={value}
                            type="button"
                            disabled={faceUp}
                            onClick={() => handleVote(value)}
                            aria-pressed={selected}
                            style={{ "--tilt": `${tilt}deg` } as React.CSSProperties}
                            className={`pg-deck-card flex aspect-[3/4] min-h-14 items-center justify-center overflow-hidden rounded-lg border-2 font-display text-[1.3rem] font-black sm:text-title lg:text-display ${
                              selected
                                ? "border-brass bg-brass text-ink"
                                : "border-ink bg-card text-ink hover:bg-parchment"
                            } ${faceUp ? "opacity-60" : ""}`}
                          >
                            {cardLabel(value)}
                          </button>
                        );
                      })}
                    </div>
                    {isHost && (
                      <div className="mt-6 flex flex-wrap gap-2.5 border-t border-paper/25 pt-5">
                        <button
                          type="button"
                          disabled={state.round?.revealed || (state.round?.vote_count ?? 0) === 0}
                          onClick={() => send({ action: "reveal" })}
                          className="pg-btn border-[1.5px] border-ink bg-brass px-5 py-2.5 font-bold text-ink hover:bg-paper"
                        >
                          Reveal cards
                        </button>
                        <button
                          type="button"
                          onClick={handleReset}
                          className="pg-btn border-[1.5px] border-paper/60 px-4 py-2.5 font-semibold text-paper hover:bg-paper/10"
                        >
                          {confirmReset ? "Confirm reset" : "Reset round"}
                        </button>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="py-8 text-center">
                    <p className="pg-kicker text-brass">The table is set</p>
                    <h2 className="mt-2 font-display text-title font-bold">No story is live yet</h2>
                    <p className="mx-auto mt-2 max-w-sm text-body text-paper/70">
                      {isHost
                        ? "Add a story from the queue panel and voting opens at once."
                        : "The host is preparing the first story. Your cards will appear here."}
                    </p>
                  </div>
                )}
              </section>

              {state.round && <ResultsPanel round={state.round} />}
            </div>
          </div>
        </main>
      )}

      <footer className="flex flex-wrap items-center justify-between gap-2 border-t border-line py-5 text-small text-inksoft">
        <span>PointGoblin. A backend portfolio project.</span>
        <a
          className="inline-flex text-ink hover:text-evergreen"
          href="https://github.com/Abhisheklang"
          target="_blank"
          rel="noreferrer"
          aria-label="GitHub profile of Abhisheklang"
        >
          <GithubIcon />
        </a>
      </footer>
    </div>
  );
}
