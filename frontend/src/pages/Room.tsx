import { useEffect, useRef, useState } from "react";

import { socketUrl } from "../api";
import Logo from "../components/Logo";
import { PresenceList, ResultsPanel, RoomSkeleton, StoryQueue } from "../components/RoomParts";
import type { RoomState, Session, SocketMessage } from "../types";

interface RoomProps {
  session: Session;
  onLeave: () => void;
}

export default function Room({ session, onLeave }: RoomProps) {
  const [state, setState] = useState<RoomState | null>(null);
  const [isHost, setIsHost] = useState(session.isHostAccount);
  const [myVote, setMyVote] = useState<string | null>(null);
  const [storyTitle, setStoryTitle] = useState("");
  const [connected, setConnected] = useState(false);
  const [notice, setNotice] = useState("");
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const socket = new WebSocket(socketUrl(session.code, session.token));
    socketRef.current = socket;
    socket.onopen = () => setConnected(true);
    socket.onclose = () => setConnected(false);
    socket.onmessage = (event: MessageEvent<string>) => {
      const message = JSON.parse(event.data) as SocketMessage;
      if (message.type === "you") {
        setIsHost(message.is_host);
      } else {
        setState(message);
        if (message.round === null || !message.round.voted.includes(session.name)) {
          setMyVote(null);
        }
      }
    };
    return () => {
      socket.close();
      socketRef.current = null;
    };
  }, [session.code, session.token, session.name]);

  function send(payload: Record<string, string>) {
    const socket = socketRef.current;
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(payload));
    }
  }

  function handleVote(value: string) {
    setMyVote(value);
    send({ action: "vote", value });
  }

  function handleAddStory(event: React.FormEvent) {
    event.preventDefault();
    const title = storyTitle.trim();
    if (!title) {
      return;
    }
    send({ action: "add_story", title });
    setStoryTitle("");
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
      <header className="flex flex-wrap items-center justify-between gap-3 py-5">
        <Logo />
        <div className="flex items-center gap-3">
          <span
            className={`rounded-full px-2.5 py-1 text-small font-semibold ${
              connected ? "bg-forest-800 text-goblin-300" : "bg-forest-800 text-rose-soft"
            }`}
            role="status"
          >
            {connected ? "Live" : "Connecting"}
          </span>
          <button
            type="button"
            onClick={onLeave}
            className="pg-btn rounded-lg bg-forest-850 px-3 py-2 text-small font-semibold text-cream-300 hover:bg-forest-800"
          >
            Leave room
          </button>
        </div>
      </header>

      {state === null ? (
        <RoomSkeleton />
      ) : (
        <main className="pg-enter flex flex-1 flex-col gap-5 pb-8">
          <section className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h1 className="text-title font-bold">{state.room.name}</h1>
              <p className="mt-1 text-small text-muted-400">
                Hosted by {state.room.host_name ?? "your host"} · You are {session.name}
              </p>
            </div>
            <button
              type="button"
              onClick={copyCode}
              className="pg-btn rounded-lg bg-forest-850 px-3 py-2 text-left"
              aria-label={`Copy room code ${state.room.code}`}
            >
              <span className="block text-small text-muted-400">Room code</span>
              <span className="block text-heading font-bold tracking-[0.25em]">
                {state.room.code}
              </span>
            </button>
          </section>
          {notice && (
            <p role="status" className="text-small text-goblin-300">
              {notice}
            </p>
          )}

          <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-[320px_1fr]">
            <div className="flex flex-col gap-4">
              <section aria-label="Participants" className="rounded-xl bg-forest-900 p-4">
                <h2 className="text-heading font-semibold">
                  People <span className="text-muted-400">({state.participants.length})</span>
                </h2>
                <div className="mt-3">
                  <PresenceList
                    participants={state.participants}
                    votedNames={state.round?.voted ?? []}
                  />
                </div>
              </section>

              <section aria-label="Stories" className="rounded-xl bg-forest-900 p-4">
                <h2 className="text-heading font-semibold">Story queue</h2>
                <div className="mt-3">
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
                      className="min-w-0 flex-1 rounded-lg border border-forest-700 bg-forest-950 px-3 py-2 text-body focus:border-goblin-400 focus:outline-none"
                    />
                    <button
                      type="submit"
                      className="pg-btn shrink-0 rounded-lg bg-forest-700 px-3 py-2 font-semibold hover:bg-moss-500"
                    >
                      Add
                    </button>
                  </form>
                )}
              </section>
            </div>

            <div className="flex flex-col gap-4">
              <section aria-label="Voting" className="rounded-xl bg-forest-900 p-4 sm:p-5">
                {activeStory ? (
                  <>
                    <p className="text-small font-semibold text-muted-400">Now voting on</p>
                    <h2 className="mt-1 text-heading font-semibold break-words">
                      {activeStory.title}
                    </h2>
                    <p className="mt-2 text-small text-muted-400">
                      {state.round?.revealed
                        ? "Cards are face up. Talk it through, then reset or move on."
                        : `${state.round?.vote_count ?? 0} of ${state.participants.length} people have voted. Cards stay face down until the host reveals.`}
                    </p>
                    <div
                      className="mt-4 grid grid-cols-5 gap-2 sm:gap-3"
                      role="group"
                      aria-label="Pick your card"
                    >
                      {state.deck.map((value) => {
                        const selected = myVote === value;
                        const faceUp = state.round?.revealed ?? false;
                        return (
                          <button
                            key={value}
                            type="button"
                            disabled={faceUp}
                            onClick={() => handleVote(value)}
                            aria-pressed={selected}
                            className={`pg-card-btn flex aspect-[3/4] min-h-14 items-center justify-center rounded-xl border-2 text-title font-bold sm:text-display ${
                              selected
                                ? "border-goblin-400 bg-goblin-400 text-forest-950"
                                : "border-forest-700 bg-forest-850 text-cream-50 hover:border-moss-500"
                            } ${faceUp ? "opacity-70" : ""}`}
                          >
                            {value === "pass" ? "Pass" : value}
                          </button>
                        );
                      })}
                    </div>
                    {isHost && (
                      <div className="mt-4 flex flex-wrap gap-2">
                        <button
                          type="button"
                          disabled={state.round?.revealed || (state.round?.vote_count ?? 0) === 0}
                          onClick={() => send({ action: "reveal" })}
                          className="pg-btn rounded-lg bg-goblin-400 px-4 py-2.5 font-bold text-forest-950 hover:bg-goblin-300"
                        >
                          Reveal cards
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setMyVote(null);
                            send({ action: "reset" });
                          }}
                          className="pg-btn rounded-lg bg-forest-700 px-4 py-2.5 font-semibold hover:bg-moss-500"
                        >
                          Reset round
                        </button>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="py-6 text-center">
                    <h2 className="text-heading font-semibold">No story is live yet</h2>
                    <p className="mx-auto mt-2 max-w-sm text-body text-muted-400">
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
