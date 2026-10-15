import { Sparkles } from "lucide-react";
import { Link } from "wouter";

import type { DocType } from "@/lib/api";

type Props = {
  docTypes: DocType[];
  value: string;
  disabled?: boolean;
  onChange: (value: string) => void;
};

/** Выбор типа документа: автоматически или вручную. */
export function TypePicker({ docTypes, value, disabled, onChange }: Props) {
  const options = [{ id: "", title: "Определить автоматически" }, ...docTypes];
  return (
    <fieldset disabled={disabled}>
      <legend className="sr-only">Тип документа</legend>
      <div className="flex items-baseline justify-between gap-3">
        <span
          aria-hidden="true"
          className="text-[13px] font-bold uppercase tracking-[0.08em] text-brand-text"
        >
          Тип документа
        </span>
        <Link
          href="/sandbox"
          className="text-[13px] font-semibold text-accent-text transition-colors hover:text-accent"
        >
          + Добавить свой тип
        </Link>
      </div>
      <div className="mt-3 flex flex-wrap gap-2.5">
        {options.map((option) => {
          const checked = value === option.id;
          const auto = option.id === "";
          return (
            <label
              key={option.id || "auto"}
              className={`pressable inline-flex items-center gap-2 rounded-2xl border px-4 py-2.5 text-sm font-semibold has-[:focus-visible]:outline has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-brand ${
                checked
                  ? auto
                    ? "btn-accent border-transparent"
                    : "border-brand bg-brand-soft text-brand-text"
                  : "border-line-strong bg-surface-2/40 text-text-2 hover:border-brand/60 hover:text-text"
              }`}
            >
              <input
                type="radio"
                name="doc-type"
                value={option.id}
                checked={checked}
                onChange={() => onChange(option.id)}
                className="sr-only"
              />
              {auto && <Sparkles aria-hidden="true" className="size-4" />}
              {option.title}
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}
