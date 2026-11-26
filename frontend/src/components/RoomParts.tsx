import type { Participant, RoundState, StoryItem } from "../types";

export function PresenceList({
  participants,
  votedIds,
}: {
  participants: Participant[];
  votedIds: string[];
}) {
  if (participants.length === 0) {
    return <p className="text-small text-inksoft">Waiting for people to arrive.</p>;
  }
  return (
    <ul className="flex flex-col gap-2.5" aria-label="People in this room">
      {participants.map((person) => {
        const hasVoted = votedIds.includes(person.id);
        return (
          <li
            key={person.id}
            className="pg-pop flex items-center justify-between gap-2 border-[1.5px] border-ink bg-card px-3 py-2"
          >
            <span className="flex min-w-0 items-center gap-2.5">
              <span
                className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full font-display text-body font-bold ${
                  person.is_host ? "bg-brass text-ink" : "bg-evergreen text-paper"
                }`}
                aria-hidden="true"
              >
                {person.name.charAt(0).toUpperCase()}
              </span>
              <span className="min-w-0">
                <span className="block truncate text-body leading-tight font-medium">
                  {person.name}
                </span>
                {person.is_host && (
                  <span className="pg-kicker block text-[0.58rem] text-brassdeep">Host</span>
                )}
              </span>
            </span>
            {hasVoted ? (
              <span className="flex shrink-0 items-center gap-1.5">
                <span
                  className="pg-cardback inline-block h-5 w-3.5 rounded-[3px] border border-ink"
                  aria-hidden="true"
                />
                <span className="pg-kicker text-[0.62rem] text-evergreen">Card in</span>
              </span>
            ) : (
              <span className="pg-kicker shrink-0 text-[0.62rem] text-inksoft">Thinking</span>
            )}
          </li>
        );
      })}
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
      <p className="text-small text-inksoft">
        No stories yet. The host adds the first story and voting opens right away.
      </p>
    );
  }
  return (
    <ol className="flex flex-col" aria-label="Story queue">
      {stories.map((story, index) => (
        <li
          key={story.id}
          className={`pg-pop flex items-center justify-between gap-3 border-b border-line py-2.5 last:border-b-0 ${
            story.status === "active" || story.status === "revealed" ? "bg-parchment/70" : ""
          }`}
        >
          <span className="flex min-w-0 items-baseline gap-3">
            <span className="font-display text-heading font-bold text-brassdeep" aria-hidden="true">
              {String(index + 1).padStart(2, "0")}
            </span>
            <span className="min-w-0">
              <span className="block truncate text-body font-medium">{story.title}</span>
              <span className="pg-kicker text-[0.62rem] text-inksoft">
                {story.status === "active" && "Voting now"}
                {story.status === "revealed" && "Revealed"}
                {story.status === "pending" && "Waiting"}
                {story.status === "done" && "Finished"}
              </span>
            </span>
          </span>
          {isHost && (story.status === "pending" || story.status === "done") && (
            <button
              type="button"
              onClick={() => onActivate(story.id)}
              className="pg-btn pg-print-sm shrink-0 bg-paper px-2.5 py-1.5 text-small font-semibold text-ink hover:bg-parchment"
            >
              {story.status === "done" ? "Run again" : "Start"}
            </button>
          )}
        </li>
      ))}
    </ol>
  );
}

export function ResultsPanel({ round }: { round: RoundState }) {
  const results = round.results;
  if (!round.revealed || results === null) {
    return null;
  }
  return (
    <section aria-label="Results" className="pg-enter pg-print relative bg-card p-5 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="pg-kicker text-brassdeep">The reveal</p>
          <div className="mt-2 flex items-end gap-3">
            <p className="font-display text-[4.2rem] leading-[0.85] font-black text-ink">
              {results.average === null ? "·" : results.average}
            </p>
            <p className="pb-1 text-small font-medium text-inksoft">
              average of
              <br />
              the table
            </p>
          </div>
        </div>
        {results.agreement !== null && (
          <div
            className="pg-stamp flex h-24 w-24 shrink-0 flex-col items-center justify-center rounded-full border-[3px] border-double border-evergreen text-evergreen"
            role="img"
            aria-label={`Agreement ${results.agreement} percent`}
          >
            <span className="font-display text-title leading-none font-black">
              {results.agreement}%
            </span>
            <span className="pg-kicker mt-1 text-[0.55rem]">Agreement</span>
          </div>
        )}
      </div>
      <div className="pg-flip-scene mt-5">
        <ul className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-4">
          {results.votes.map((vote, index) => (
            <li
              key={vote.id}
              className="pg-flip border-[1.5px] border-ink bg-paper px-3 py-3 text-center"
              style={{ animationDelay: `${index * 70}ms` }}
            >
              <span className="block font-display text-title leading-none font-black">
                {vote.value === "pass" ? "Pass" : vote.value}
              </span>
              <span className="pg-kicker mt-1.5 block truncate text-[0.6rem] text-inksoft">
                {vote.name}
              </span>
            </li>
          ))}
        </ul>
      </div>
      {results.votes.length === 0 && (
        <p className="mt-3 text-small text-inksoft">Nobody voted on this story.</p>
      )}
    </section>
  );
}

export function RoomSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-[330px_1fr]" aria-hidden="true">
      <div className="pg-skeleton h-64 border-[1.5px] border-line bg-parchment" />
      <div className="flex flex-col gap-5">
        <div className="pg-skeleton h-24 border-[1.5px] border-line bg-parchment" />
        <div className="pg-skeleton h-56 border-[1.5px] border-line bg-parchment" />
      </div>
    </div>
  );
}
