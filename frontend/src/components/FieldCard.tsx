import { Check, Minus } from "lucide-react";

import type { Analysis, FieldValue } from "@/lib/api";

type Props = {
  analysis: Analysis;
  focus: string[];
  onSelect: (key: string) => void;
};

const MONTHS = [
  "января", "февраля", "марта", "апреля", "мая", "июня",
  "июля", "августа", "сентября", "октября", "ноября", "декабря",
];

function humanDate(iso: string) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  if (!match) return iso;
  return `${Number(match[3])} ${MONTHS[Number(match[2]) - 1]} ${match[1]}`;
}

function shown(field: FieldValue): string {
  if (field.type === "mark") return field.found ? "Есть" : "Не найдена";
  if (!field.found) return field.handwritten ? "Заполнено от руки, прочитать надёжно не удалось" : "Не найдено";
  const value = String(field.value);
  return field.type === "date" ? humanDate(value) : value;
}

/** Карточка полей документа. */
export function FieldCard({ analysis, focus, onSelect }: Props) {
  const found = analysis.fields.filter((field) => field.found).length;
  return (
    <section aria-labelledby="card-title" className="card overflow-hidden">
      <header className="flex items-baseline justify-between gap-3 px-5 pb-3 pt-5">
        <div>
          <h2 id="card-title" className="text-[17px] font-semibold tracking-[-0.01em]">
            {analysis.supported ? "Карточка документа" : "Что удалось прочитать"}
          </h2>
          <p className="mt-0.5 text-[13px] text-muted">
            {analysis.document_title}
            {analysis.supported && analysis.type_detected ? " · тип определён автоматически" : ""}
          </p>
        </div>
        <p className="tabular shrink-0 text-[13px] text-muted">
          {found} из {analysis.fields.length}
        </p>
      </header>
      <dl className="border-t border-line">
        {analysis.fields.map((field, index) => {
          const active = focus.includes(field.key);
          return (
            <div
              key={field.key}
              className="rise border-b border-line last:border-b-0"
              style={{ "--i": index } as React.CSSProperties}
            >
              <button
                type="button"
                onClick={() => onSelect(field.key)}
                aria-pressed={active}
                className={`group grid w-full grid-cols-[auto_1fr] items-start gap-x-3 px-5 py-3 text-left transition-colors duration-150 sm:grid-cols-[auto_minmax(0,11rem)_1fr] ${
                  active ? "bg-brand-softer" : "hover:bg-surface-2/70"
                }`}
              >
                <span
                  aria-hidden="true"
                  className={`mt-0.5 grid size-5 place-items-center rounded-full ${
                    field.found ? "bg-brand-soft text-brand-text" : "bg-warn-soft text-warn"
                  }`}
                >
                  {field.found ? <Check className="size-3.5" strokeWidth={3} /> : <Minus className="size-3.5" strokeWidth={3} />}
                </span>
                <dt className="text-[13px] leading-5 text-muted sm:pt-px">{field.label}</dt>
                <dd
                  className={`col-start-2 text-[15px] leading-5 sm:col-start-3 ${
                    field.found ? "font-medium text-text" : "text-warn"
                  } ${field.type === "date" || field.type === "code" ? "tabular" : ""} break-words`}
                >
                  {shown(field)}
                  {field.found && field.origin === "text" && (
                    <span className="ml-2 rounded-full bg-surface-2 px-2 py-0.5 align-middle text-[11px] font-medium text-muted">
                      из текста
                    </span>
                  )}
                  {!field.found && field.handwritten && field.guess && (
                    <span className="mt-1 block text-[13px] font-normal text-muted">
                      Возможно: {field.guess}. Проверьте по снимку.
                    </span>
                  )}
                  {field.found && field.handwritten && (
                    <span className="ml-2 rounded-full bg-surface-2 px-2 py-0.5 align-middle text-[11px] font-medium text-muted">
                      от руки
                    </span>
                  )}
                  <span className="sr-only">
                    {field.found ? "" : `. Обязательно по пункту ${field.rule} Положения`}
                  </span>
                </dd>
              </button>
            </div>
          );
        })}
      </dl>
    </section>
  );
}
