import { Link } from "wouter";

export function NotFound() {
  return (
    <section className="mx-auto max-w-[560px] px-4 py-24 text-center sm:px-6">
      <p className="tabular text-sm font-semibold text-brand-text">404</p>
      <h1 className="mt-3 text-[32px] font-semibold tracking-[-0.02em]">Такой страницы нет</h1>
      <p className="mt-3 text-[17px] leading-relaxed text-text-2">
        Возможно, ссылка устарела или в адресе опечатка.
      </p>
      <Link
        href="/"
        className="pressable mt-7 inline-flex h-12 items-center rounded-xl bg-brand-strong px-6 font-semibold text-on-brand hover:bg-brand-hover"
      >
        На главную
      </Link>
    </section>
  );
}
