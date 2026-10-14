import { Check, LoaderCircle, Minus, Pencil } from "lucide-react";
import { type FormEvent, useEffect, useRef, useState } from "react";

import type { Analysis, FieldValue } from "@/lib/api";
import { isPersonal, maskValue } from "@/lib/privacy";

type Props = {
  analysis: Analysis;
  title?: string;
  focus: string[];
  onSelect: (key: string) => void;
  /** Ручная правка значения. Возвращает текст ошибки или null. */
  onEdit?: (key: string, value: string | boolean) => Promise<string | null>;
  edited?: string[];
  /** Показать персональные данные скрытыми. */
  masked?: boolean;
};

const PLACEHOLDER: Record<string, string> = {
  date: "Например: 01.09.2026",
  person: "Фамилия Имя Отчество",
  integer: "Число",
  code: "Например: ОБ-1234",
  text: "Значение с документа",
};

function EditRow({
  field,
  onSave,
  onCancel,
}: {
  field: FieldValue;
  onSave: (value: string | boolean) => Promise<string | null>;
  onCancel: () => void;
}) {
  const mark = field.type === "mark";
  const [draft, setDraft] = useState<string | boolean>(
    mark ? field.found : field.found ? String(field.value) : "",
  );
  const [saving, setSaving] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const form = useRef<HTMLFormElement>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    const error = await onSave(draft);
    setSaving(false);
    if (error) {
      setProblem(error);
      // Кнопка на время сохранения была неактивна и отпустила фокус: возвращаем его в форму.
      form.current?.querySelector<HTMLElement>("input, [aria-checked=true]")?.focus();
    } else onCancel();
  };

  return (
    <form
      ref={form}
      onSubmit={submit}
      onKeyDown={(event) => {
        if (event.key === "Escape") onCancel();
      }}
      className="bg-surface-2/60 px-5 py-3.5"
    >
      <label htmlFor={`edit-${field.key}`} className="text-[13px] text-muted">
        {field.label}
      </label>
      <div className="mt-1.5 flex flex-wrap items-center gap-2">
        {mark ? (
          <div
            role="radiogroup"
            aria-label={field.label}
            className="flex gap-1 rounded-xl bg-surface-3 p-1"
          >
            {[
              { value: true, label: "Есть" },
              { value: false, label: "Нет" },
            ].map((option) => (
              <button
                key={option.label}
                id={option.value ? `edit-${field.key}` : undefined}
                autoFocus={draft === option.value}
                type="button"
                role="radio"
                aria-checked={draft === option.value}
                onClick={() => setDraft(option.value)}
                className={`pressable rounded-lg px-4 py-1.5 text-sm font-medium ${
                  draft === option.value ? "bg-surface text-text shadow-sm" : "text-text-2"
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>
        ) : (
          <input
            id={`edit-${field.key}`}
            autoFocus
            value={String(draft)}
            onChange={(event) => setDraft(event.target.value.slice(0, 300))}
            placeholder={PLACEHOLDER[field.type] ?? PLACEHOLDER.text}
            autoComplete="off"
            className="h-10 min-w-0 flex-1 rounded-xl border border-line-strong bg-surface px-3.5 text-[15px] outline-none focus:border-brand focus:shadow-[0_0_0_4px_rgb(80_184_72/0.16)]"
          />
        )}
        <button
          type="submit"
          disabled={saving}
          className="pressable inline-flex h-10 items-center gap-1.5 rounded-xl bg-brand-strong px-4 text-sm font-semibold text-on-brand hover:bg-brand-hover disabled:opacity-60"
        >
          {saving && <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />}
          Сохранить
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="pressable h-10 rounded-xl px-3 text-sm font-medium text-text-2 hover:text-text"
        >
          Отмена
        </button>
      </div>
      {problem && (
        <p role="alert" className="mt-2 text-[13px] text-danger">
          {problem}
        </p>
      )}
    </form>
  );
}

const MONTHS = [
  "января",
  "февраля",
  "марта",
  "апреля",
  "мая",
  "июня",
  "июля",
  "августа",
  "сентября",
  "октября",
  "ноября",
  "декабря",
];

function humanDate(iso: string) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  if (!match) return iso;
  return `${Number(match[3])} ${MONTHS[Number(match[2]) - 1]} ${match[1]}`;
}

/** Ниже этой уверенности распознавания значение стоит сверить со снимком (как PRINTED_TRUST на сервере). */
const UNSURE = 0.6;

function unsure(field: FieldValue) {
  return (
    field.found &&
    field.type !== "mark" &&
    field.origin !== "generic" &&
    !field.handwritten &&
    field.confidence !== null &&
    field.confidence < UNSURE
  );
}

function shown(field: FieldValue): string {
  if (field.type === "mark") return field.found ? "Есть" : "Не найдена";
  if (!field.found)
    return field.handwritten ? "Заполнено от руки, прочитать надёжно не удалось" : "Не найдено";
  const value = String(field.value);
  return field.type === "date" ? humanDate(value) : value;
}

/** Карточка полей документа. */
export function FieldCard({
  analysis,
  title,
  onSelect,
  focus,
  onEdit,
  edited = [],
  masked = false,
}: Props) {
  const [editing, setEditing] = useState<string | null>(null);
  // После правки фокус возвращается на карандаш того же поля, а не теряется.
  const pencils = useRef(new Map<string, HTMLButtonElement>());
  const [returnTo, setReturnTo] = useState<string | null>(null);
  useEffect(() => {
    if (returnTo && editing === null) {
      pencils.current.get(returnTo)?.focus();
      setReturnTo(null);
    }
  }, [returnTo, editing]);
  const editable = Boolean(onEdit) && analysis.supported;
  const found = analysis.fields.filter((field) => field.found).length;
  return (
    <section aria-labelledby="card-title" className="card overflow-hidden">
      <header className="flex items-baseline justify-between gap-3 px-5 pb-3 pt-5">
        <div>
          <h2 id="card-title" className="text-[17px] font-semibold tracking-[-0.01em]">
            {title ?? (analysis.supported ? "Карточка документа" : "Что удалось прочитать")}
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
      <ul className="border-t border-line">
        {analysis.fields.map((field, index) => {
          const active = focus.includes(field.key);
          if (editing === field.key && onEdit) {
            return (
              <li key={field.key} className="border-b border-line last:border-b-0">
                <EditRow
                  field={field}
                  onSave={(value) => onEdit(field.key, value)}
                  onCancel={() => {
                    setEditing(null);
                    setReturnTo(field.key);
                  }}
                />
              </li>
            );
          }
          return (
            <li
              key={field.key}
              className="rise group/row relative border-b border-line last:border-b-0"
              style={{ "--i": index } as React.CSSProperties}
            >
              {editable && (
                <button
                  ref={(node) => {
                    if (node) pencils.current.set(field.key, node);
                    else pencils.current.delete(field.key);
                  }}
                  type="button"
                  onClick={() => setEditing(field.key)}
                  aria-label={`Исправить поле «${field.label}»`}
                  title="Исправить вручную"
                  className="no-print pressable absolute right-3 top-2 z-[1] grid size-8 place-items-center rounded-lg text-muted opacity-0 transition-opacity hover:bg-surface-3 hover:text-text focus-visible:opacity-100 group-hover/row:opacity-100 [@media(pointer:coarse)]:opacity-100"
                >
                  <Pencil aria-hidden="true" className="size-3.5" />
                </button>
              )}
              <button
                type="button"
                onClick={() => onSelect(field.key)}
                aria-pressed={active}
                className={`group grid w-full grid-cols-[auto_1fr] items-start gap-x-3 px-5 py-3 text-left ${editable ? "pr-12" : ""} transition-colors duration-150 sm:grid-cols-[auto_minmax(0,11rem)_1fr] ${
                  active ? "bg-brand-softer" : "hover:bg-surface-2/70"
                }`}
              >
                <span
                  aria-hidden="true"
                  className={`mt-0.5 grid size-5 place-items-center rounded-full ${
                    field.found ? "bg-brand-soft text-brand-text" : "bg-warn-soft text-warn"
                  }`}
                >
                  {field.found ? (
                    <Check className="size-3.5" strokeWidth={3} />
                  ) : (
                    <Minus className="size-3.5" strokeWidth={3} />
                  )}
                </span>
                <span className="text-[13px] leading-5 text-muted sm:pt-px">{field.label}</span>
                <span
                  className={`col-start-2 text-[15px] leading-5 sm:col-start-3 ${
                    field.found ? "font-medium text-text" : "text-warn"
                  } ${field.type === "date" || field.type === "code" ? "tabular" : ""} break-words`}
                >
                  {masked && isPersonal(field) && field.type !== "mark"
                    ? String(maskValue(field))
                    : shown(field)}
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
                  {edited.includes(field.key) && (
                    <span className="ml-2 rounded-full bg-surface-2 px-2 py-0.5 align-middle text-[11px] font-medium text-muted">
                      исправлено вручную
                    </span>
                  )}
                  {unsure(field) && !edited.includes(field.key) && (
                    <span
                      title="Буквы распознаны неуверенно. Сверьте значение со снимком."
                      className="ml-2 rounded-full bg-warn-soft px-2 py-0.5 align-middle text-[11px] font-medium text-warn"
                    >
                      сверьте со снимком
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
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
