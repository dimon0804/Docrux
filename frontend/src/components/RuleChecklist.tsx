import { Check, X } from "lucide-react";

import type { FieldValue } from "@/lib/api";
import { useReference } from "@/lib/rules";

import { SourceChip } from "./SourceChip";

type Props = {
  documentType: string;
  fields: FieldValue[];
  onSelect: (key: string) => void;
};

type Row = { number: string; text: string; fields: FieldValue[] };

/** Сверка по пунктам Положения: какие сведения требует каждый пункт и что из них нашлось. */
export function RuleChecklist({ documentType, fields, onSelect }: Props) {
  const { docTypes, rules } = useReference();
  const docType = docTypes.find((item) => item.id === documentType);
  if (!docType) return null;

  // Пункты без полей документа (общие оговорки) в сверке не участвуют.
  const rows: Row[] = docType.rules
    .map((number) => ({
      number,
      text: rules.get(number)?.text ?? "",
      fields: fields.filter((field) => field.rule === number),
    }))
    .filter((row) => row.fields.length > 0);
  if (rows.length === 0) return null;
  const passed = rows.filter((row) => row.fields.every((field) => field.found)).length;

  return (
    <section aria-labelledby="checklist-title" className="card overflow-hidden">
      <div className="flex items-baseline justify-between gap-3 px-5 pb-3 pt-4">
        <div>
          <h2 id="checklist-title" className="text-[15px] font-semibold">
            Сверка с Положением
          </h2>
          <p className="mt-0.5 text-[13px] text-muted">
            Что требует каждый пункт и что из этого есть в документе
          </p>
        </div>
        <span className="tabular shrink-0 text-[13px] text-muted">
          {passed} из {rows.length}
        </span>
      </div>
      <ol className="border-t border-line">
        {rows.map((row) => {
          const ok = row.fields.every((field) => field.found);
          return (
            <li
              key={row.number}
              className="flex gap-3.5 border-b border-line px-5 py-3.5 last:border-b-0"
            >
              <span
                aria-hidden="true"
                className={`mt-0.5 grid size-6 shrink-0 place-items-center rounded-full ${
                  ok ? "bg-brand text-white" : "bg-warn text-white dark:text-[#1a1304]"
                }`}
              >
                {ok ? (
                  <Check className="size-3.5" strokeWidth={3} />
                ) : (
                  <X className="size-3.5" strokeWidth={3} />
                )}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <SourceChip source={`rule:${row.number}`} />
                  <span className="sr-only">{ok ? "Выполнен" : "Не выполнен"}</span>
                </div>
                {row.text && (
                  <p className="mt-1.5 line-clamp-2 text-[13px] leading-relaxed text-text-2">
                    {row.text}
                  </p>
                )}
                {
                  <ul className="mt-2 flex flex-wrap gap-1.5">
                    {row.fields.map((field) => (
                      <li key={field.key}>
                        <button
                          type="button"
                          onClick={() => onSelect(field.key)}
                          className={`pressable inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[12.5px] font-medium ${
                            field.found
                              ? "border-line bg-surface-2 text-text-2 hover:border-line-strong hover:text-text"
                              : "border-warn-line bg-warn-soft text-text hover:border-warn"
                          }`}
                        >
                          {field.found ? (
                            <Check
                              aria-hidden="true"
                              className="size-3 text-brand-text"
                              strokeWidth={3}
                            />
                          ) : (
                            <X aria-hidden="true" className="size-3 text-warn" strokeWidth={3} />
                          )}
                          {field.label}
                          <span className="sr-only">{field.found ? ": есть" : ": не найдено"}</span>
                        </button>
                      </li>
                    ))}
                  </ul>
                }
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
