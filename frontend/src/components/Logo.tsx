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
      <path d="M19 11h18l11 11v29a3 3 0 0 1-3 3H19a3 3 0 0 1-3-3V14a3 3 0 0 1 3-3z" fill="#fff" />
      <path d="M37 11v8a3 3 0 0 0 3 3h8z" fill="#cfe9cb" />
      <path
        d="M31 25c.9 6.6 2.9 8.6 9.5 9.5-6.6.9-8.6 2.9-9.5 9.5-.9-6.6-2.9-8.6-9.5-9.5 6.6-.9 8.6-2.9 9.5-9.5z"
        fill="var(--brand)"
      />
      <path
        d="M40.5 40c.4 2.4 1.1 3.1 3.5 3.5-2.4.4-3.1 1.1-3.5 3.5-.4-2.4-1.1-3.1-3.5-3.5 2.4-.4 3.1-1.1 3.5-3.5z"
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
