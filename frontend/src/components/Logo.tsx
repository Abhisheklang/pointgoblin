interface LogoProps {
  compact?: boolean;
}

export function LogoMark() {
  return (
    <svg
      viewBox="0 0 64 64"
      className="h-10 w-10 shrink-0"
      role="img"
      aria-label="PointGoblin logo"
    >
      <rect
        x="19"
        y="8"
        width="26"
        height="40"
        rx="4"
        transform="rotate(-20 32 52)"
        fill="#FFFDF4"
        stroke="#17573A"
        strokeWidth="3"
      />
      <rect
        x="19"
        y="8"
        width="26"
        height="40"
        rx="4"
        transform="rotate(20 32 52)"
        fill="#FFFDF4"
        stroke="#17573A"
        strokeWidth="3"
      />
      <path d="M43 9 L58 1 L53 16 Z" fill="#CE9F3E" />
      <rect x="19" y="8" width="26" height="40" rx="4" fill="#17573A" />
      <path d="M32 17 L39.5 28 L32 41 L24.5 28 Z" fill="#F7F2E2" />
      <circle cx="32" cy="28" r="2.6" fill="#152A1E" />
    </svg>
  );
}

export default function Logo({ compact = false }: LogoProps) {
  return (
    <span className="inline-flex items-center gap-2.5">
      <LogoMark />
      {!compact && (
        <span className="font-display text-[1.35rem] leading-none font-bold tracking-tight text-ink">
          Point<span className="text-evergreen italic">Goblin</span>
        </span>
      )}
    </span>
  );
}
