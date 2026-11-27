import { DECK, cardLabel } from "../deck";

interface AboutProps {
  onBack: () => void;
}

const STEPS: Array<[string, string, string]> = [
  [
    "01",
    "Create or join",
    "A host signs in and opens a room. Guests join with the six character code at the top of the host's screen. No account, no install.",
  ],
  [
    "02",
    "Queue the stories",
    "The host adds the stories the team wants to size and picks which one is on the table.",
  ],
  [
    "03",
    "Vote in secret",
    "Everyone picks a card. The room shows who has voted and a running count, never a value, so nobody can anchor on the first number they see.",
  ],
  [
    "04",
    "Reveal together",
    "The host flips the whole table in one go. The average and the agreement score appear at once, and the result is written to the record.",
  ],
];

export default function About({ onBack }: AboutProps) {
  return (
    <main className="flex-1 py-10 lg:py-14">
      <div className="pg-enter max-w-3xl">
        <p className="pg-kicker text-brassdeep">About · Planning poker</p>
        <h1 className="mt-3 font-display text-[2.8rem] leading-[1.0] font-black sm:text-display">
          Estimate in secret.
          <span className="block text-evergreen italic">Reveal together.</span>
        </h1>
        <p className="mt-5 text-body leading-relaxed text-inksoft">
          Planning poker is how a team sizes a piece of work without the loudest voice setting the
          price. The team talks a story through, everyone picks a story point card in secret, and
          all the cards flip at the same moment. Where the numbers spread out, the team talks again
          and votes once more, until it lands on one number it can defend.
        </p>
        <p className="mt-4 text-body leading-relaxed text-inksoft">
          The hidden vote is the whole point. The first spoken estimate pulls every later one
          towards it, a pull called anchoring. PointGoblin holds the rule in the protocol, not just
          on the screen: the server keeps the values and never sends one to any client before the
          reveal.
        </p>

        <h2 className="mt-10 font-display text-heading font-black">How a session runs</h2>
        <div className="mt-2">
          {STEPS.map(([num, title, text]) => (
            <div
              key={num}
              className="flex items-baseline gap-4 border-t border-line py-3.5 last:border-b"
            >
              <span className="font-display text-heading font-black text-brassdeep">{num}</span>
              <div>
                <h3 className="font-display text-body font-bold">{title}</h3>
                <p className="mt-0.5 text-body leading-relaxed text-inksoft">{text}</p>
              </div>
            </div>
          ))}
        </div>

        <h2 className="mt-10 font-display text-heading font-black">The deck</h2>
        <p className="mt-2 text-body leading-relaxed text-inksoft">
          The standard Fibonacci style deck, plus a question mark for "this needs more detail before
          it can be sized" and a pass card for sitting a story out.
        </p>
        <div className="mt-4 flex flex-wrap gap-2" aria-label="The voting deck">
          {DECK.map((value) => (
            <span
              key={value}
              className="flex h-14 w-11 items-center justify-center border-[1.5px] border-ink bg-card font-display text-heading font-black text-ink"
            >
              {cardLabel(value)}
            </span>
          ))}
        </div>

        <h2 className="mt-10 font-display text-heading font-black">Under the hood</h2>
        <p className="mt-2 text-body leading-relaxed text-inksoft">
          PointGoblin is a real time backend project. FastAPI serves the rooms, each participant
          holds one WebSocket connection, Redis pub sub carries room events between API instances,
          and PostgreSQL keeps the record. JWT auth separates host accounts from room-scoped guest
          tokens.
        </p>

        <button
          type="button"
          onClick={onBack}
          className="pg-btn pg-print-sm mt-10 bg-evergreen px-4 py-3 font-display text-body font-bold text-paper hover:bg-felt"
        >
          Back to start
        </button>
      </div>
    </main>
  );
}
