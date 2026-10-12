import { Popover } from "@base-ui/react/popover";
import { ScanText } from "lucide-react";

import { useReference } from "@/lib/rules";

type Props = {
  source: string;
  fieldLabel?: string;
  onFieldClick?: (key: string) => void;
};

const chip =
  "pressable inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[13px] font-medium leading-none";

/** Ссылка на источник ответа: пункт Положения или поле документа. */
export function SourceChip({ source, fieldLabel, onFieldClick }: Props) {
  const { rules } = useReference();

  if (source.startsWith("field:")) {
    const key = source.slice(6);
    return (
      <button
        type="button"
        onClick={() => onFieldClick?.(key)}
        className={`${chip} border-line bg-surface-2 text-text-2 hover:border-line-strong hover:text-text`}
      >
        <ScanText aria-hidden="true" className="size-3.5" />
        Поле «{fieldLabel ?? key}»
      </button>
    );
  }

  const number = source.replace(/^rule:/, "");
  const rule = rules.get(number);
  const trigger = `${chip} border-transparent bg-brand-soft text-brand-text hover:bg-brand-soft/70 tabular`;

  if (!rule) {
    return <span className={trigger}>п. {number}</span>;
  }

  return (
    <Popover.Root>
      <Popover.Trigger className={trigger} aria-label={`Пункт ${number} Положения, показать текст`}>
        <span aria-hidden="true" className="text-[11px] opacity-70">
          §
        </span>
        п. {number}
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Positioner sideOffset={8} collisionPadding={12} className="z-50">
          <Popover.Popup className="w-[min(92vw,380px)] origin-[var(--transform-origin)] rounded-2xl border border-line bg-surface p-4 shadow-float outline-none transition-[transform,opacity] duration-200 ease-out-strong data-[ending-style]:scale-[0.97] data-[ending-style]:opacity-0 data-[starting-style]:scale-[0.97] data-[starting-style]:opacity-0">
            <Popover.Title className="text-xs font-semibold uppercase tracking-wide text-brand-text">
              Пункт {number} · {rule.section}
            </Popover.Title>
            <Popover.Description className="mt-2 text-sm leading-relaxed text-text">
              {rule.text}
            </Popover.Description>
          </Popover.Popup>
        </Popover.Positioner>
      </Popover.Portal>
    </Popover.Root>
  );
}
