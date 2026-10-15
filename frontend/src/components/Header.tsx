import { useEffect, useState } from "react";
import { Link } from "wouter";

import type { Theme } from "@/lib/theme";

import { Logo } from "./Logo";
import { ThemeToggle } from "./ThemeToggle";

type Props = { theme: Theme; onToggleTheme: (origin?: { x: number; y: number }) => void };

const LINK =
  "rounded-full px-3 py-2 text-[13.5px] font-semibold uppercase tracking-[0.04em] text-brand-text transition-colors hover:text-text";

export function Header({ theme, onToggleTheme }: Props) {
  // После прокрутки шапка становится плотнее и опускает тень, как в макете.
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const update = () => setScrolled(window.scrollY > 12);
    update();
    window.addEventListener("scroll", update, { passive: true });
    return () => window.removeEventListener("scroll", update);
  }, []);

  return (
    <header className="sticky top-0 z-30 px-3 pt-3 sm:px-6 sm:pt-4">
      <div
        className={`mx-auto flex h-[68px] max-w-[1240px] items-center justify-between gap-3 rounded-full border px-4 transition-[background-color,box-shadow,border-color] duration-300 sm:h-[76px] sm:px-6 ${
          scrolled
            ? "border-line-strong bg-surface/85 shadow-float backdrop-blur-xl backdrop-saturate-150"
            : "border-line bg-surface/60 backdrop-blur-md"
        }`}
      >
        <Link href="/" aria-label="Докрукс, на главную" className="rounded-2xl">
          <Logo />
        </Link>
        <nav aria-label="Основная навигация" className="flex items-center gap-1 sm:gap-1.5">
          <a href="/#features" className={`${LINK} hidden xl:block`}>
            Возможности
          </a>
          <a href="/#how" className={`${LINK} hidden lg:block`}>
            Как это работает
          </a>
          <Link href="/batch" className={`${LINK} hidden md:block`}>
            Пакетная проверка
          </Link>
          <Link href="/sandbox" className={`${LINK} hidden lg:block`}>
            Новый тип
          </Link>
          <a
            href="/#rules"
            className="ml-1 hidden rounded-xl border border-brand/60 px-3.5 py-2 text-[13.5px] font-bold uppercase tracking-[0.04em] text-text transition-colors hover:border-brand hover:bg-brand-softer sm:block"
          >
            Положение
          </a>
          <ThemeToggle theme={theme} onToggle={onToggleTheme} />
        </nav>
      </div>
    </header>
  );
}
