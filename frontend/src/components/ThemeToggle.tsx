import { Moon, Sun } from "lucide-react";

import type { Theme } from "@/lib/theme";

type Props = { theme: Theme; onToggle: (origin?: { x: number; y: number }) => void };

/** Кнопка смены темы: солнце днём, луна ночью. */
export function ThemeToggle({ theme, onToggle }: Props) {
  const dark = theme === "dark";
  const label = dark ? "Включить светлую тему" : "Включить тёмную тему";
  return (
    <button
      type="button"
      onClick={(event) => {
        const box = event.currentTarget.getBoundingClientRect();
        onToggle({ x: box.left + box.width / 2, y: box.top + box.height / 2 });
      }}
      aria-label={label}
      title={label}
      className="theme-toggle pressable relative grid size-10 place-items-center rounded-full border border-line bg-surface text-text-2 transition-colors hover:border-line-strong hover:text-text"
      data-dark={dark || undefined}
    >
      <Sun aria-hidden="true" className="theme-toggle__icon theme-toggle__sun size-[18px]" />
      <Moon aria-hidden="true" className="theme-toggle__icon theme-toggle__moon size-[18px]" />
    </button>
  );
}
