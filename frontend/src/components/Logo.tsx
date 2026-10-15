type Props = { className?: string };

/** Искра внутри раскрытого листа: знак Докрукса. */
export function LogoMark({ className }: Props) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 64 64"
      className={`size-9 shrink-0 drop-shadow-[0_1px_0_rgb(0_0_0/0.08)] ${className ?? ""}`}
    >
      <rect width="64" height="64" rx="16" fill="var(--brand)" />
      <path d="M18 9h19l12 12v31a3 3 0 0 1-3 3H18a3 3 0 0 1-3-3V12a3 3 0 0 1 3-3z" fill="#fff" />
      <path d="M37 9v9a3 3 0 0 0 3 3h9z" fill="#cfe9cb" />
      <path
        d="M31 23c1.1 8 3.4 11.4 12.5 13-9.1 1.6-11.4 5-12.5 13-1.1-8-3.4-11.4-12.5-13 9.1-1.6 11.4-5 12.5-13z"
        fill="var(--brand)"
      />
      <path
        d="M42.5 41c.5 2.9 1.3 3.8 4 4.3-2.7.5-3.5 1.4-4 4.3-.5-2.9-1.3-3.8-4-4.3 2.7-.5 3.5-1.4 4-4.3z"
        fill="var(--brand)"
        opacity=".7"
      />
    </svg>
  );
}

export function Logo() {
  return (
    <span className="flex items-center gap-2.5">
      <LogoMark />
      <span className="text-[17px] font-semibold tracking-[-0.01em]">Докрукс</span>
    </span>
  );
}
