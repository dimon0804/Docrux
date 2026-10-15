import { ChevronDown, Search } from "lucide-react";
import { Fragment, useState } from "react";

import { useReference } from "@/lib/rules";

const norm = (text: string) => text.toLowerCase().replace(/ё/g, "е");

/** Подсвечивает найденные слова в тексте пункта. */
function Marked({ text, words }: { text: string; words: string[] }) {
  if (words.length === 0) return <>{text}</>;
  const lowered = norm(text);
  const parts: { text: string; hit: boolean }[] = [];
  let index = 0;
  while (index < text.length) {
    let next = -1;
    let size = 0;
    for (const word of words) {
      const at = lowered.indexOf(word, index);
      if (at !== -1 && (next === -1 || at < next)) {
        next = at;
        size = word.length;
      }
    }
    if (next === -1) {
      parts.push({ text: text.slice(index), hit: false });
      break;
    }
    if (next > index) parts.push({ text: text.slice(index, next), hit: false });
    parts.push({ text: text.slice(next, next + size), hit: true });
    index = next + size;
  }
  return (
    <>
      {parts.map((part, i) =>
        part.hit ? (
          <mark key={i} className="rounded bg-brand-soft px-0.5 text-text">
            {part.text}
          </mark>
        ) : (
          <Fragment key={i}>{part.text}</Fragment>
        ),
      )}
    </>
  );
}

/** Положение целиком: по нему сервис проверяет документы и отвечает на вопросы. */
export function RulesSection() {
  const { ruleList, loaded } = useReference();
  const [query, setQuery] = useState("");
  if (!loaded) return null;

  // Слова короче трёх букв не ищем: «в», «по» нашлись бы везде.
  // Ищем по основе слова, чтобы «печать» находила и «печати».
  const words = norm(query)
    .split(/[^a-zа-я0-9.]+/)
    .filter((word) => word.length >= 3 || /^\d/.test(word))
    .map((word) => (/^[а-я]{6,}$/.test(word) ? word.slice(0, -2) : word));
  const matches = (text: string) => words.every((word) => norm(text).includes(word));
  const shown = words.length
    ? ruleList.filter((rule) => matches(`${rule.number} ${rule.section} ${rule.text}`))
    : ruleList;

  const sections: { title: string; number: string; points: typeof ruleList }[] = [];
  for (const rule of shown) {
    const number = rule.number.split(".")[0] ?? "";
    const last = sections[sections.length - 1];
    if (last && last.number === number) last.points.push(rule);
    else sections.push({ title: rule.section, number, points: [rule] });
  }

  return (
    <section id="rules" className="mx-auto max-w-[1240px] scroll-mt-28 px-4 pt-20 sm:px-6 sm:pt-28">
      <p className="inline-flex rounded-full border border-brand/35 bg-brand-soft text-brand-text px-4 py-1 text-[13px] font-semibold">
        База положений
      </p>
      <h2 className="mt-4 text-[30px] font-extrabold sm:text-[44px]">Положение</h2>
      <p className="mt-2 max-w-[560px] text-[17px] leading-relaxed text-text-2">
        Единственный источник правил. Сервис ссылается на эти пункты и не добавляет ничего от себя.
      </p>
      <div className="relative mt-6 max-w-[480px]">
        <Search
          aria-hidden="true"
          className="pointer-events-none absolute left-4 top-1/2 size-4 -translate-y-1/2 text-muted"
        />
        <label htmlFor="rules-search" className="sr-only">
          Поиск по Положению
        </label>
        <input
          id="rules-search"
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value.slice(0, 80))}
          placeholder="Найти в Положении: печать, отпуск, 3.4"
          autoComplete="off"
          className="h-11 w-full rounded-xl border border-line-strong bg-surface pl-11 pr-4 text-[15px] outline-none transition-[border-color,box-shadow] duration-150 placeholder:text-muted focus:border-brand focus:shadow-[0_0_0_4px_rgb(47_216_158/0.16)]"
        />
      </div>
      {words.length > 0 && (
        <p aria-live="polite" className="mt-3 text-[13px] text-muted">
          {shown.length ? `Найдено пунктов: ${shown.length}` : "В Положении таких слов нет."}
        </p>
      )}
      <div className="mt-6 flex flex-col gap-3">
        {sections.map((section, index) => (
          <details
            key={`${section.number}-${words.join(" ")}`}
            className="card group"
            open={words.length > 0 || index === 0}
          >
            <summary className="flex list-none items-center gap-4 px-5 py-4 [&::-webkit-details-marker]:hidden">
              <span className="tabular grid size-8 shrink-0 place-items-center rounded-lg bg-brand-soft text-sm font-semibold text-brand-text">
                {section.number}
              </span>
              <span className="flex-1 text-[16px] font-semibold tracking-[-0.01em]">
                {section.title}
              </span>
              <ChevronDown
                aria-hidden="true"
                className="size-4 text-muted transition-transform duration-200 ease-out-strong group-open:rotate-180"
              />
            </summary>
            <ol className="border-t border-line px-5 py-2">
              {section.points.map((point) => (
                <li
                  key={point.number}
                  id={`rule-${point.number}`}
                  className="grid grid-cols-[3rem_1fr] gap-2 border-b border-line py-3 last:border-b-0"
                >
                  <span className="tabular text-sm font-semibold text-brand-text">
                    {point.number}
                  </span>
                  <span className="text-[15px] leading-relaxed text-text-2">
                    <Marked text={point.text} words={words} />
                  </span>
                </li>
              ))}
            </ol>
          </details>
        ))}
      </div>
    </section>
  );
}
