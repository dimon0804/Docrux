import { Moon, Sun } from "lucide-react";

import type { Theme } from "@/lib/theme";

type Props = { theme: Theme; onToggle: (origin?: { x: number; y: number }) => void };

/** Переключатель темы в виде ползунка: днём солнце слева, ночью розовая луна справа. */
export function ThemeToggle({ theme, onToggle }: Props) {
  const dark = theme === "dark";
  const label = dark ? "Включить светлую тему" : "Включить тёмную тему";
  return (
    <button
      type="button"
      role="switch"
      aria-checked={dark}
      onClick={(event) => {
        const box = event.currentTarget.getBoundingClientRect();
        onToggle({ x: box.left + box.width / 2, y: box.top + box.height / 2 });
      }}
      aria-label={label}
      title={label}
      className="theme-toggle pressable relative ml-1 h-9 w-[64px] shrink-0 rounded-full border border-line-strong bg-surface-3 shadow-[inset_0_2px_6px_rgb(0_0_0/0.18)]"
      data-dark={dark || undefined}
    >
      <span className="theme-toggle__knob absolute left-[3px] top-[3px] grid size-[28px] place-items-center rounded-full">
        <Sun aria-hidden="true" className="theme-toggle__icon theme-toggle__sun size-[15px]" />
        <Moon aria-hidden="true" className="theme-toggle__icon theme-toggle__moon size-[15px]" />
      </span>
    </button>
  );
}
