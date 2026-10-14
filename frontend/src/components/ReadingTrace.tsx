import { ChevronDown, FileInput, ListChecks, ScanLine, Scale, Search, Wand2 } from "lucide-react";

import type { Analysis } from "@/lib/api";

import { describeFixes } from "./DocumentViewer";

type Step = { icon: typeof ScanLine; title: string; text: string; ms?: number };

const num = (value: unknown) => (typeof value === "number" ? value : undefined);

function plural(count: number, one: string, few: string, many: string) {
  const mod10 = count % 10;
  const mod100 = count % 100;
  if (mod10 === 1 && mod100 !== 11) return one;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return few;
  return many;
}

/** Шаги разбора этого документа: что сервис сделал и сколько это заняло. */
export function traceSteps(analysis: Analysis): Step[] {
  const q = analysis.quality ?? {};
  const pages = num(q.pages) ?? 1;
  const kind = String(q.file_kind ?? "").toUpperCase() || "файл";
  const fixes = describeFixes(q);
  const lines = num(q.ocr_lines);
  const words = num(q.ocr_words);
  const found = analysis.fields.filter((field) => field.found).length;
  const steps: Step[] = [
    {
      icon: FileInput,
      title: "Файл принят",
      text: `${kind}, ${pages} ${plural(pages, "страница", "страницы", "страниц")}. Формат проверен по содержимому, а не по расширению.`,
      ms: num(q.ms_load),
    },
    {
      icon: Wand2,
      title: "Снимок подготовлен",
      text: q.pdf_text
        ? "Взят текстовый слой PDF."
        : fixes.length
          ? `${fixes.join(", ")}.`.replace(/^./, (c) => c.toUpperCase())
          : "Снимок ровный, исправлять ничего не пришлось.",
      ms: num(q.ms_prepare),
    },
    {
      icon: ScanLine,
      title: "Текст распознан",
      text:
        lines !== undefined && words !== undefined
          ? `Tesseract нашёл ${lines} ${plural(lines, "строку", "строки", "строк")} и ${words} ${plural(words, "слово", "слова", "слов")}.`
          : "Текст распознан.",
      ms: num(q.ms_ocr),
    },
    {
      icon: Search,
      title: analysis.supported ? "Тип определён" : "Тип не из Положения",
      text: analysis.supported
        ? analysis.type_detected
          ? `«${analysis.document_title}» по заголовку и ключевым словам.`
          : `«${analysis.document_title}» выбран вручную.`
        : `Похоже на «${analysis.document_title}». Положение такой документ не описывает.`,
      ms: num(q.ms_detect),
    },
    {
      icon: ListChecks,
      title: "Поля найдены",
      text: `${found} из ${analysis.fields.length}. Значения приведены к единому виду: даты ГГГГ-ММ-ДД, ФИО в именительном падеже.`,
      ms: num(q.ms_extract),
    },
  ];
  if (analysis.supported) {
    steps.push({
      icon: Scale,
      title: "Сверено с Положением",
      text:
        analysis.validation.status === "document_ok"
          ? "Все обязательные сведения на месте."
          : `Не хватает: ${analysis.validation.missing_fields.length}. Основание: ${analysis.validation.sources
              .map((source) => source.replace("rule:", "п. "))
              .join(", ")}.`,
    });
  }
  return steps;
}

export function ReadingTrace({ analysis }: { analysis: Analysis }) {
  const steps = traceSteps(analysis);
  const total = steps.reduce((sum, step) => sum + (step.ms ?? 0), 0);
  return (
    <details className="no-print card group">
      <summary className="flex list-none items-center justify-between gap-3 px-5 py-4 [&::-webkit-details-marker]:hidden">
        <span className="text-[15px] font-semibold">Как сервис читал документ</span>
        <span className="flex items-center gap-3 text-[13px] text-muted">
          {total > 0 && (
            <span className="tabular">{(total / 1000).toFixed(1).replace(".", ",")} с</span>
          )}
          <ChevronDown
            aria-hidden="true"
            className="size-4 transition-transform duration-200 ease-out-strong group-open:rotate-180"
          />
        </span>
      </summary>
      <ol className="relative border-t border-line px-5 py-4">
        {steps.map((step, index) => (
          <li key={step.title} className="relative flex gap-3.5 pb-4 last:pb-0">
            {index < steps.length - 1 && (
              <span
                aria-hidden="true"
                className="absolute left-[15px] top-8 h-[calc(100%-28px)] w-px bg-line"
              />
            )}
            <span className="grid size-8 shrink-0 place-items-center rounded-full bg-brand-soft text-brand-text">
              <step.icon aria-hidden="true" className="size-4" />
            </span>
            <div className="min-w-0 flex-1 pt-1">
              <div className="flex items-baseline justify-between gap-3">
                <p className="text-sm font-semibold">{step.title}</p>
                {step.ms !== undefined && (
                  <span className="tabular shrink-0 text-[12.5px] text-muted">
                    {step.ms < 1000
                      ? `${step.ms} мс`
                      : `${(step.ms / 1000).toFixed(1).replace(".", ",")} с`}
                  </span>
                )}
              </div>
              <p className="mt-0.5 text-[13px] leading-relaxed text-text-2">{step.text}</p>
            </div>
          </li>
        ))}
      </ol>
    </details>
  );
}
