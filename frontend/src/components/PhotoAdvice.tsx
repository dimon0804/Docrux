import { Lightbulb } from "lucide-react";

/** Советы по снимку: что поправить, чтобы следующий снимок прочитался надёжнее. */
export function PhotoAdvice({ advice }: { advice?: string[] }) {
  if (!advice?.length) return null;
  return (
    <section
      aria-label="Совет по снимку"
      className="no-print flex items-start gap-3 rounded-[20px] border border-line bg-surface px-5 py-4"
    >
      <span className="mt-0.5 grid size-8 shrink-0 place-items-center rounded-full bg-brand-soft text-brand-text">
        <Lightbulb aria-hidden="true" className="size-4" />
      </span>
      <div className="min-w-0">
        <h2 className="text-[15px] font-semibold">Как снять документ лучше</h2>
        <ul className="mt-1 flex flex-col gap-1 text-sm leading-relaxed text-text-2">
          {advice.map((tip) => (
            <li key={tip}>{tip}</li>
          ))}
        </ul>
      </div>
    </section>
  );
}
