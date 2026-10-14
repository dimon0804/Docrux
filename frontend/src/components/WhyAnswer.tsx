import { ChevronDown } from "lucide-react";

/** Раскрывающееся объяснение ответа: какие шаги привели к нему. */
export function WhyAnswer({ trace }: { trace?: string[] }) {
  if (!trace?.length) return null;
  return (
    <details className="no-print group mt-2.5">
      <summary className="inline-flex cursor-pointer list-none items-center gap-1 rounded-md text-[13px] font-medium text-text-2 hover:text-text [&::-webkit-details-marker]:hidden">
        Почему так?
        <ChevronDown
          aria-hidden="true"
          className="size-3.5 transition-transform duration-200 ease-out-strong group-open:rotate-180"
        />
      </summary>
      <ol className="mt-2 flex flex-col gap-1.5 border-l-2 border-line pl-3">
        {trace.map((step) => (
          <li key={step} className="text-[13px] leading-relaxed text-text-2">
            {step}
          </li>
        ))}
      </ol>
    </details>
  );
}
