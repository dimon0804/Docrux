import { useId } from "react";

type Props = { className?: string };

/** Знак Докрукса: рамка сканера, лист с загнутым углом и искра внутри. */
export function LogoMark({ className }: Props) {
  const id = useId().replace(/:/g, "");
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 260 240"
      fill="none"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={`h-10 w-auto shrink-0 ${className ?? ""}`}
    >
      <defs>
        <linearGradient id={`${id}d`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#17b07a" />
          <stop offset="1" stopColor="var(--logo-doc-end, #0a5a3d)" />
        </linearGradient>
        <linearGradient id={`${id}t`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#f2468e" />
          <stop offset="1" stopColor="#9b2259" />
        </linearGradient>
        <linearGradient id={`${id}b`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#9b2259" />
          <stop offset="1" stopColor="#f2468e" />
        </linearGradient>
      </defs>
      <path d="M90 12h92l66 66v148H90" stroke={`url(#${id}d)`} strokeWidth="19" />
      <path d="M182 12v66h66" stroke={`url(#${id}d)`} strokeWidth="13" />
      <g strokeWidth="13">
        <path d="M8 78V42h38M94 42h38v36" stroke={`url(#${id}t)`} />
        <path d="M8 168v36h38M94 204h38v-36" stroke={`url(#${id}b)`} />
      </g>
      <path
        d="M70 96c3 18 9 25 27 27-18 3-24 9-27 27-3-18-9-24-27-27 18-2 24-9 27-27z"
        fill="var(--logo-spark, #fff)"
      />
    </svg>
  );
}

export function Logo() {
  return (
    <span className="flex items-center gap-3">
      <LogoMark />
      <span className="flex flex-col leading-none">
        <span className="logo-word text-[22px] font-black uppercase tracking-[0.02em]">
          Докрукс
        </span>
        <span className="mt-1 text-[10.5px] font-semibold uppercase tracking-[0.22em] text-brand-text">
          Цифровой секретарь
        </span>
      </span>
    </span>
  );
}
