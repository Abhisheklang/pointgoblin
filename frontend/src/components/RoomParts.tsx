import type { Participant, RoundState, StoryItem } from "../types";

export function PresenceList({
  participants,
  votedNames,
}: {
  participants: Participant[];
  votedNames: string[];
}) {
  if (participants.length === 0) {
    return <p className="text-small text-muted-400">Waiting for people to arrive.</p>;
  }
  return (
    <ul className="flex flex-col gap-2" aria-label="People in this room">
      {participants.map((person) => (
        <li
          key={person.key}
          className="pg-pop flex items-center justify-between gap-2 rounded-lg bg-forest-850 px-3 py-2"
        >
          <span className="flex min-w-0 items-center gap-2">
            <span
              className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-forest-700 text-small font-bold text-goblin-300"
              aria-hidden="true"
            >
              {person.name.charAt(0).toUpperCase()}
            </span>
            <span className="truncate text-body">
              {person.name}
              {person.is_host && <span className="text-muted-400"> · host</span>}
            </span>
          </span>
          {votedNames.includes(person.name) ? (
            <span className="shrink-0 rounded-full bg-goblin-400 px-2 py-0.5 text-small font-semibold text-forest-950">
              Voted
            </span>
          ) : (
            <span className="shrink-0 text-small text-muted-400">Thinking</span>
          )}
        </li>
      ))}
    </ul>
  );
}

export function StoryQueue({
  stories,
  isHost,
  onActivate,
}: {
  stories: StoryItem[];
  isHost: boolean;
  onActivate: (storyId: string) => void;
}) {
  if (stories.length === 0) {
    return (
      <p className="text-small text-muted-400">
        No stories yet. The host adds the first story and voting opens right away.
      </p>
    );
  }
  return (
    <ul className="flex flex-col gap-2" aria-label="Story queue">
      {stories.map((story) => (
        <li
          key={story.id}
          className="pg-pop flex items-center justify-between gap-2 rounded-lg bg-forest-850 px-3 py-2"
        >
          <span className="min-w-0">
            <span className="block truncate text-body">{story.title}</span>
            <span className="text-small text-muted-400">
              {story.status === "active" && "Voting now"}
              {story.status === "revealed" && "Revealed"}
              {story.status === "pending" && "Waiting"}
              {story.status === "done" && "Finished"}
            </span>
          </span>
          {isHost && story.status === "pending" && (
            <button
              type="button"
              onClick={() => onActivate(story.id)}
              className="pg-btn shrink-0 rounded-md bg-forest-700 px-2.5 py-1.5 text-small font-semibold text-cream-50 hover:bg-moss-500"
            >
              Start
            </button>
          )}
        </li>
      ))}
    </ul>
  );
}

export function ResultsPanel({ round }: { round: RoundState }) {
  const results = round.results;
  if (!round.revealed || results === null) {
    return null;
  }
  return (
    <section aria-label="Results" className="pg-enter rounded-xl bg-forest-850 p-4 sm:p-5">
      <h3 className="text-heading font-semibold">Results</h3>
      <div className="mt-3 flex flex-wrap gap-6">
        <div>
          <p className="text-small text-muted-400">Average</p>
          <p className="text-display leading-none font-bold text-goblin-400">
            {results.average === null ? "·" : results.average}
          </p>
        </div>
        <div>
          <p className="text-small text-muted-400">Agreement</p>
          <p className="text-display leading-none font-bold text-goblin-400">
            {results.agreement === null ? "·" : `${results.agreement}%`}
          </p>
        </div>
      </div>
      <ul className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
        {results.votes.map((vote, index) => (
          <li
            key={vote.name}
            className="pg-flip rounded-lg bg-forest-950 px-3 py-3 text-center"
            style={{ animationDelay: `${index * 60}ms` }}
          >
            <span className="block text-title leading-none font-bold">{vote.value}</span>
            <span className="mt-1 block truncate text-small text-muted-400">{vote.name}</span>
          </li>
        ))}
      </ul>
      {results.votes.length === 0 && (
        <p className="mt-3 text-small text-muted-400">Nobody voted on this story.</p>
      )}
    </section>
  );
}

export function RoomSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-[320px_1fr]" aria-hidden="true">
      <div className="pg-skeleton h-64 rounded-xl bg-forest-850" />
      <div className="flex flex-col gap-4">
        <div className="pg-skeleton h-24 rounded-xl bg-forest-850" />
        <div className="pg-skeleton h-48 rounded-xl bg-forest-850" />
      </div>
    </div>
  );
}
