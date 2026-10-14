import { Link } from "wouter";

import type { Theme } from "@/lib/theme";

import { Logo } from "./Logo";
import { ThemeToggle } from "./ThemeToggle";

type Props = { theme: Theme; onToggleTheme: (origin?: { x: number; y: number }) => void };

export function Header({ theme, onToggleTheme }: Props) {
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-bg/80 backdrop-blur-xl backdrop-saturate-150">
      <div className="mx-auto flex h-16 max-w-[1240px] items-center justify-between gap-4 px-4 sm:px-6">
        <Link href="/" aria-label="Параграф, на главную" className="rounded-xl">
          <Logo />
        </Link>
        <nav aria-label="Основная навигация" className="flex items-center gap-1 sm:gap-2">
          <Link
            href="/sandbox"
            className="hidden rounded-full px-3.5 py-2 text-sm font-medium text-text-2 transition-colors hover:bg-surface-2 hover:text-text lg:block"
          >
            Новый тип
          </Link>
          <Link
            href="/batch"
            className="hidden rounded-full px-3.5 py-2 text-sm font-medium text-text-2 transition-colors hover:bg-surface-2 hover:text-text md:block"
          >
            Пакетная проверка
          </Link>
          <a
            href="/#how"
            className="hidden rounded-full px-3.5 py-2 text-sm font-medium text-text-2 transition-colors hover:bg-surface-2 hover:text-text sm:block"
          >
            Как это работает
          </a>
          <a
            href="/#rules"
            className="hidden rounded-full px-3.5 py-2 text-sm font-medium text-text-2 transition-colors hover:bg-surface-2 hover:text-text sm:block"
          >
            Положение
          </a>
          <ThemeToggle theme={theme} onToggle={onToggleTheme} />
        </nav>
      </div>
    </header>
  );
}
