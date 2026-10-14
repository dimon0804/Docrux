import { Eye } from "lucide-react";

import type { Remark } from "@/lib/api";

type Props = { remarks?: Remark[]; onSelect: (key: string) => void };

/** Замечания для сотрудника: сведения есть, но выглядят странно. На итог не влияют. */
export function Remarks({ remarks, onSelect }: Props) {
  if (!remarks?.length) return null;
  return (
    <section
      aria-labelledby="remarks-title"
      className="rounded-[20px] border border-line bg-surface px-5 py-4"
    >
      <div className="flex items-start gap-3">
        <span className="mt-0.5 grid size-8 shrink-0 place-items-center rounded-full bg-surface-3 text-text-2">
          <Eye aria-hidden="true" className="size-4" />
        </span>
        <div className="min-w-0 flex-1">
          <h2 id="remarks-title" className="text-[15px] font-semibold">
            На что обратить внимание
          </h2>
          <p className="mt-0.5 text-[13px] text-muted">
            Сведения на месте, но выглядят необычно. На итог проверки по Положению это не влияет.
          </p>
          <ul className="mt-2.5 flex flex-col gap-2">
            {remarks.map((remark) => (
              <li key={remark.text}>
                <button
                  type="button"
                  disabled={remark.fields.length === 0}
                  onClick={() => remark.fields[0] && onSelect(remark.fields[0])}
                  className="pressable w-full rounded-xl bg-surface-2 px-3.5 py-2.5 text-left text-sm leading-relaxed text-text hover:bg-surface-3 disabled:cursor-default"
                >
                  {remark.text}
                </button>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
