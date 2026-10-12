import { useEffect, useState } from "react";
import { Link } from "wouter";

const KEY = "paragraf:notice";

function seen(): boolean {
  try {
    return localStorage.getItem(KEY) === "1";
  } catch {
    return true;
  }
}

/**
 * Уведомление о локальном хранилище. Сервис не ставит рекламных и аналитических
 * cookie, поэтому согласия не требуется: достаточно один раз сообщить.
 */
export function CookieNotice() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (seen()) return;
    const timer = window.setTimeout(() => setOpen(true), 900);
    return () => window.clearTimeout(timer);
  }, []);

  const close = () => {
    try {
      localStorage.setItem(KEY, "1");
    } catch {
      // Без хранилища уведомление просто покажется снова при следующем визите.
    }
    setOpen(false);
  };

  return (
    <div
      role="region"
      aria-label="Уведомление о файлах cookie"
      aria-hidden={!open}
      inert={!open}
      className={`fixed inset-x-3 bottom-3 z-40 mx-auto max-w-[560px] transition-[transform,opacity] duration-300 ease-out-strong sm:inset-x-6 sm:bottom-6 ${
        open ? "translate-y-0 opacity-100" : "pointer-events-none translate-y-4 opacity-0"
      }`}
    >
      <div className="flex flex-col gap-3 rounded-2xl border border-line bg-surface p-4 shadow-float sm:flex-row sm:items-center sm:gap-4 sm:p-5">
        <p className="text-sm leading-relaxed text-text-2">
          Мы не используем рекламные и аналитические cookie. В браузере хранится только выбранная
          тема оформления.{" "}
          <Link href="/cookies" className="font-medium text-brand-text underline-offset-4 hover:underline">
            Подробнее
          </Link>
        </p>
        <button
          type="button"
          onClick={close}
          className="pressable shrink-0 rounded-xl bg-brand-strong px-5 py-2.5 text-sm font-semibold text-on-brand hover:bg-brand-hover"
        >
          Понятно
        </button>
      </div>
    </div>
  );
}
