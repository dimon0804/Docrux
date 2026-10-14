import type { Analysis, Answer } from "./api";
import type { Turn } from "./workspace";

/** Запись документа в том же формате, что results.json пакетного прогона. */
export function resultRecord(fileName: string, analysis: Analysis, turns: Turn[]) {
  const answered = turns.filter((turn): turn is Turn & { answer: Answer } => turn.answer !== null);
  return {
    version: "1.0",
    documents: [
      {
        document_id: fileName.replace(/\.[^.]+$/, "") || "document",
        document_type: analysis.document_type,
        fields: Object.fromEntries(analysis.fields.map((field) => [field.key, field.value])),
        validation: analysis.validation,
        answers: answered.map((turn, index) => ({
          question_id: `q${index + 1}`,
          question: turn.question,
          answerable: turn.answer.answerable,
          value: turn.answer.value,
          answer: turn.answer.answer,
          sources: turn.answer.sources,
        })),
      },
    ],
  };
}

export function downloadJson(name: string, data: unknown) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Печать листа проверки всегда в светлой теме: тёмный фон на бумаге не нужен. */
export function printReport() {
  const root = document.documentElement;
  const theme = root.dataset.theme;
  root.dataset.theme = "light";
  const restore = () => {
    if (theme) root.dataset.theme = theme;
    window.removeEventListener("afterprint", restore);
  };
  window.addEventListener("afterprint", restore);
  window.print();
}
