import { Check, Copy, MailCheck } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import type { Analysis, Answer } from "@/lib/api";

type Props = { analysis: Analysis; check: Answer };

function points(sources: string[]) {
  const numbers = sources.filter((source) => source.startsWith("rule:")).map((s) => s.slice(5));
  if (numbers.length === 0) return "";
  return numbers.length === 1 ? `пункт ${numbers[0]}` : `пункты ${numbers.join(", ")}`;
}

/** «Печать вуза» → «печать вуза», но «ФИО студента» остаётся как есть. */
function lower(label: string) {
  return /^[А-ЯЁA-Z]{2}/.test(label) ? label : label.charAt(0).toLowerCase() + label.slice(1);
}

/**
 * Текст ответа студенту по итогам проверки. Собирается по шаблону только из
 * результата проверки: какие сведения нашлись, чего не хватает и какие пункты
 * Положения это требуют. Ничего сверх этого письмо не обещает.
 */
export function replyText(analysis: Analysis, check: Answer): string {
  const title = analysis.document_title.toLowerCase();
  const missing = analysis.fields.filter((field) => !field.found);
  const lines = ["Здравствуйте!", ""];
  if (check.value === "document_ok") {
    lines.push(
      `Мы предварительно проверили ваш документ «${title}». Все обязательные сведения на месте (${points(check.sources)} Положения о приёме документов).`,
      "",
      "Окончательное решение примет сотрудник деканата, о нём мы сообщим отдельно.",
    );
  } else {
    lines.push(
      `Мы предварительно проверили ваш документ «${title}». В нём не хватает обязательных сведений:`,
      ...missing.map((field) => `— ${lower(field.label)} (пункт ${field.rule} Положения);`),
      "",
      "Пожалуйста, пришлите документ, в котором есть эти сведения. Окончательное решение примет сотрудник деканата.",
    );
  }
  lines.push("", "С уважением, деканат");
  return lines.join("\n").replace(/;\n\n/, ".\n\n");
}

/** Готовый ответ студенту, который сотрудник может скопировать в почту или чат. */
export function StudentReply({ analysis, check }: Props) {
  const [copied, setCopied] = useState(false);
  if (!analysis.supported) return null;
  const text = replyText(analysis, check);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      toast.error("Браузер не дал скопировать текст. Выделите его и скопируйте вручную.");
    }
  };

  return (
    <details className="no-print card group">
      <summary className="flex list-none items-center justify-between gap-3 px-5 py-4 [&::-webkit-details-marker]:hidden">
        <span className="flex items-center gap-2.5 text-[15px] font-semibold">
          <MailCheck aria-hidden="true" className="size-[18px] text-brand-text" />
          Ответ студенту
        </span>
        <span className="text-[13px] text-muted group-open:hidden">Показать готовый текст</span>
      </summary>
      <div className="border-t border-line px-5 py-4">
        <pre className="whitespace-pre-wrap rounded-xl bg-surface-2 px-4 py-3 font-sans text-sm leading-relaxed text-text">
          {text}
        </pre>
        <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
          <p className="text-[12.5px] text-muted">
            Текст собран из результата проверки. Перед отправкой его можно поправить.
          </p>
          <button
            type="button"
            onClick={() => void copy()}
            className="pressable inline-flex items-center gap-1.5 rounded-lg border border-line px-3 py-1.5 text-[13px] font-medium text-text-2 hover:border-line-strong hover:text-text"
          >
            {copied ? (
              <Check aria-hidden="true" className="size-3.5 text-brand-text" />
            ) : (
              <Copy aria-hidden="true" className="size-3.5" />
            )}
            {copied ? "Скопировано" : "Скопировать"}
          </button>
        </div>
      </div>
    </details>
  );
}
