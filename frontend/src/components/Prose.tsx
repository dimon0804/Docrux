import type { ReactNode } from "react";

type Props = { title: string; updated: string; children: ReactNode };

/** Обёртка для текстовых страниц: политика конфиденциальности и cookie. */
export function Prose({ title, updated, children }: Props) {
  return (
    <article className="mx-auto max-w-[720px] px-4 pt-10 sm:px-6 sm:pt-16">
      <h1 className="text-[30px] font-semibold leading-tight tracking-[-0.02em] sm:text-[40px]">
        {title}
      </h1>
      <p className="mt-3 text-sm text-muted">Редакция от {updated}</p>
      <div className="prose mt-8">{children}</div>
    </article>
  );
}
