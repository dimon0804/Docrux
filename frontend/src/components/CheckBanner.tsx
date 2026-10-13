import { CircleAlert, CircleCheck, FileQuestion } from "lucide-react";

import type { Answer, FieldValue } from "@/lib/api";

import { SourceChip } from "./SourceChip";

type Props = {
  check: Answer;
  fields: FieldValue[];
  supported?: boolean;
  title?: string;
  onSelect: (key: string) => void;
};

/** Итог предварительной проверки: документ в порядке или чего-то не хватает. */
export function CheckBanner({ check, fields, supported = true, title, onSelect }: Props) {
  if (!supported) {
    return (
      <section
        aria-label="Результат предварительной проверки"
        className="rounded-[20px] border border-line bg-surface-2 p-5"
      >
        <div className="flex items-start gap-3.5">
          <span className="mt-0.5 grid size-9 shrink-0 place-items-center rounded-full bg-surface-3 text-text-2">
            <FileQuestion aria-hidden="true" className="size-5" />
          </span>
          <div className="min-w-0">
            <h2 className="text-[17px] font-semibold leading-snug tracking-[-0.01em]">
              Документ другого типа{title ? `: ${title}` : ""}
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-text-2">{check.answer}</p>
            <div className="mt-3 flex flex-wrap items-center gap-1.5">
              <span className="mr-1 text-[13px] text-muted">Основание:</span>
              {check.sources.map((source) => (
                <SourceChip key={source} source={source} />
              ))}
            </div>
          </div>
        </div>
      </section>
    );
  }
  const ok = check.value === "document_ok";
  const missing = fields.filter((field) => !field.found);
  return (
    <section
      aria-label="Результат предварительной проверки"
      className={`rounded-[20px] border p-5 ${
        ok ? "border-brand/30 bg-brand-softer" : "border-warn-line bg-warn-soft"
      }`}
    >
      <div className="flex items-start gap-3.5">
        <span
          className={`mt-0.5 grid size-9 shrink-0 place-items-center rounded-full ${
            ok ? "bg-brand text-white" : "bg-warn text-white dark:text-[#1a1304]"
          }`}
        >
          {ok ? (
            <CircleCheck aria-hidden="true" className="size-5" />
          ) : (
            <CircleAlert aria-hidden="true" className="size-5" />
          )}
        </span>
        <div className="min-w-0">
          <h2 className="text-[17px] font-semibold leading-snug tracking-[-0.01em]">
            {ok ? "Все обязательные сведения на месте" : "В документе кое-чего не хватает"}
          </h2>
          {!ok && (
            <ul className="mt-2.5 flex flex-wrap gap-1.5">
              {missing.map((field) => (
                <li key={field.key}>
                  <button
                    type="button"
                    onClick={() => onSelect(field.key)}
                    className="pressable rounded-full border border-warn-line bg-surface px-3 py-1 text-[13px] font-medium text-text hover:border-warn"
                  >
                    {field.label}
                  </button>
                </li>
              ))}
            </ul>
          )}
          <p className="mt-2.5 text-sm leading-relaxed text-text-2">{check.answer}</p>
          <div className="mt-3 flex flex-wrap items-center gap-1.5">
            <span className="mr-1 text-[13px] text-muted">Основание:</span>
            {check.sources.map((source) => (
              <SourceChip key={source} source={source} />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
