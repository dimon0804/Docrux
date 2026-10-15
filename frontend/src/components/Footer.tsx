import { Link } from "wouter";

import { LogoMark } from "./Logo";

const LINK = "text-text-2 transition-colors hover:text-brand-text";

export function Footer() {
  return (
    <footer className="mt-24 border-t border-line bg-surface/40 backdrop-blur-sm">
      <div className="mx-auto grid max-w-[1240px] gap-10 px-4 py-12 sm:px-6 md:grid-cols-[1.4fr_1fr_1fr]">
        <div className="max-w-md">
          <div className="flex items-center gap-3">
            <LogoMark className="h-8" />
            <span className="text-[17px] font-bold">
              Докрукс <span className="font-medium text-muted">· Цифровой секретарь деканата</span>
            </span>
          </div>
          <p className="mt-4 text-sm leading-relaxed text-muted">
            Учебный проект для кейса «Онлайн-деканат». Сервис делает только предварительную
            проверку. Окончательное решение по документу принимает сотрудник деканата.
          </p>
          <a
            href="https://t.me/docrux_bot"
            target="_blank"
            rel="noopener noreferrer"
            className="mt-5 inline-flex items-center gap-2 rounded-full border border-line-strong px-3.5 py-1.5 text-[13px] font-semibold text-text-2 transition-colors hover:border-brand hover:text-text"
          >
            <span className="pulse-dot size-2 rounded-full bg-brand text-brand" />
            Telegram-бот @docrux_bot
          </a>
        </div>
        <nav aria-label="Возможности сервиса" className="flex flex-col gap-2.5 text-sm">
          <Link href="/batch" className={LINK}>
            Пакетная проверка
          </Link>
          <Link href="/sandbox" className={LINK}>
            Песочница типов документов
          </Link>
          <Link href="/selfcheck" className={LINK}>
            Самопроверка на открытом наборе
          </Link>
          <button
            type="button"
            onClick={() => window.dispatchEvent(new Event("docrux:autopilot"))}
            className={`text-left ${LINK}`}
          >
            Показать демо (Shift+D)
          </button>
        </nav>
        <nav aria-label="Документы сервиса" className="flex flex-col gap-2.5 text-sm">
          <Link href="/privacy" className={LINK}>
            Политика конфиденциальности
          </Link>
          <Link href="/cookies" className={LINK}>
            Файлы cookie и локальное хранилище
          </Link>
          <a href="mailto:ceo.director@clv-digital.tech" className={LINK}>
            ceo.director@clv-digital.tech
          </a>
          <a
            href="https://clv-digital.tech"
            target="_blank"
            rel="noopener noreferrer"
            className="font-semibold text-accent-text transition-colors hover:text-accent"
          >
            Разработано в CLV-DIGITAL
          </a>
        </nav>
      </div>
    </footer>
  );
}
