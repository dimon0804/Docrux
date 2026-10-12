type Props = { className?: string };

/** Знак параграфа в зелёной плашке. */
export function LogoMark({ className }: Props) {
  return (
    <span
      aria-hidden="true"
      className={`inline-grid size-9 place-items-center rounded-[11px] bg-brand text-[22px] font-semibold leading-none text-white shadow-[inset_0_-2px_0_rgb(0_0_0/0.12)] ${className ?? ""}`}
    >
      <span className="-translate-y-px">§</span>
    </span>
  );
}

export function Logo() {
  return (
    <span className="flex items-center gap-2.5">
      <LogoMark />
      <span className="text-[17px] font-semibold tracking-[-0.01em]">Параграф</span>
    </span>
  );
}
