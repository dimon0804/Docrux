import { ChevronDown } from "lucide-react";

import { useReference } from "@/lib/rules";

/** Положение целиком: по нему сервис проверяет документы и отвечает на вопросы. */
export function RulesSection() {
  const { ruleList, loaded } = useReference();
  if (!loaded) return null;

  const sections: { title: string; number: string; points: typeof ruleList }[] = [];
  for (const rule of ruleList) {
    const number = rule.number.split(".")[0] ?? "";
    const last = sections[sections.length - 1];
    if (last && last.number === number) last.points.push(rule);
    else sections.push({ title: rule.section, number, points: [rule] });
  }

  return (
    <section id="rules" className="mx-auto max-w-[1240px] scroll-mt-24 px-4 pt-20 sm:px-6 sm:pt-28">
      <h2 className="text-[26px] font-semibold tracking-[-0.02em] sm:text-[34px]">Положение</h2>
      <p className="mt-2 max-w-[560px] text-[17px] leading-relaxed text-text-2">
        Единственный источник правил. Сервис ссылается на эти пункты и не добавляет ничего от
        себя.
      </p>
      <div className="mt-8 flex flex-col gap-3">
        {sections.map((section, index) => (
          <details key={section.number} className="card group" open={index === 0}>
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
                  <span className="text-[15px] leading-relaxed text-text-2">{point.text}</span>
                </li>
              ))}
            </ol>
          </details>
        ))}
      </div>
    </section>
  );
}
