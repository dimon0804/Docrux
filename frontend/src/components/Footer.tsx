import { Link } from "wouter";

import { LogoMark } from "./Logo";

export function Footer() {
  return (
    <footer className="mt-20 border-t border-line">
      <div className="mx-auto flex max-w-[1240px] flex-col gap-6 px-4 py-10 sm:px-6 md:flex-row md:items-start md:justify-between">
        <div className="max-w-md">
          <div className="flex items-center gap-2.5">
            <LogoMark className="size-7 rounded-lg text-[17px]" />
            <span className="font-semibold">Параграф</span>
          </div>
          <p className="mt-3 text-sm leading-relaxed text-muted">
            Учебный проект для кейса «Онлайн-деканат». Сервис делает только предварительную
            проверку. Окончательное решение по документу принимает сотрудник деканата.
          </p>
        </div>
        <nav aria-label="Документы сервиса" className="flex flex-col gap-2.5 text-sm">
          <Link href="/privacy" className="text-text-2 transition-colors hover:text-brand-text">
            Политика конфиденциальности
          </Link>
          <Link href="/cookies" className="text-text-2 transition-colors hover:text-brand-text">
            Файлы cookie и локальное хранилище
          </Link>
        </nav>
      </div>
    </footer>
  );
}
