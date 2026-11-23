interface LogoProps {
  compact?: boolean;
}

export function LogoMark() {
  return (
    <svg viewBox="0 0 64 64" className="h-9 w-9 shrink-0" role="img" aria-label="PointGoblin logo">
      <rect
        x="6"
        y="14"
        width="26"
        height="38"
        rx="5"
        transform="rotate(-14 19 33)"
        fill="none"
        stroke="#4C7A3F"
        strokeWidth="3"
      />
      <rect
        x="32"
        y="14"
        width="26"
        height="38"
        rx="5"
        transform="rotate(14 45 33)"
        fill="none"
        stroke="#4C7A3F"
        strokeWidth="3"
      />
      <path d="M44 12 L59 3 L52 19 Z" fill="#8BD450" />
      <rect x="18" y="10" width="28" height="42" rx="5" fill="#8BD450" />
      <path d="M32 20 L40 30 L32 44 L24 30 Z" fill="#10240F" />
      <circle cx="32" cy="30" r="2.6" fill="#EAF6E3" />
    </svg>
  );
}

export default function Logo({ compact = false }: LogoProps) {
  return (
    <span className="inline-flex items-center gap-2.5">
      <LogoMark />
      {!compact && (
        <span className="text-lg font-bold tracking-wide text-cream-50">
          Point<span className="text-goblin-400">Goblin</span>
        </span>
      )}
    </span>
  );
}
