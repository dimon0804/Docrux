import { Sparkles } from "lucide-react";

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
      <legend className="text-sm font-medium">Тип документа</legend>
      <div className="mt-2 flex flex-wrap gap-2">
        {options.map((option) => {
          const checked = value === option.id;
          return (
            <label
              key={option.id || "auto"}
              className={`pressable inline-flex items-center gap-1.5 rounded-full border px-3.5 py-2 text-sm font-medium has-[:focus-visible]:outline has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-brand ${
                checked
                  ? "border-brand bg-brand-soft text-brand-text"
                  : "border-line bg-surface text-text-2 hover:border-line-strong hover:text-text"
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
              {option.id === "" && <Sparkles aria-hidden="true" className="size-3.5" />}
              {option.title}
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}
