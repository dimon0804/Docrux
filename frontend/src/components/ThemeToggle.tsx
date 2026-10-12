import { Moon, Sun } from "lucide-react";

import type { Theme } from "@/lib/theme";

type Props = { theme: Theme; onToggle: () => void };

export function ThemeToggle({ theme, onToggle }: Props) {
  const dark = theme === "dark";
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-label={dark ? "Включить светлую тему" : "Включить тёмную тему"}
      title={dark ? "Светлая тема" : "Тёмная тема"}
      className="pressable relative grid size-10 place-items-center overflow-hidden rounded-full border border-line bg-surface text-text-2 hover:border-line-strong hover:text-text"
    >
      <Sun
        aria-hidden="true"
        className={`absolute size-[18px] transition-[transform,opacity] duration-300 ease-out-strong ${
          dark ? "translate-y-6 rotate-45 opacity-0" : "translate-y-0 rotate-0 opacity-100"
        }`}
      />
      <Moon
        aria-hidden="true"
        className={`absolute size-[18px] transition-[transform,opacity] duration-300 ease-out-strong ${
          dark ? "translate-y-0 rotate-0 opacity-100" : "-translate-y-6 -rotate-45 opacity-0"
        }`}
      />
    </button>
  );
}
