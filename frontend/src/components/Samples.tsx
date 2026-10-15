import { useState } from "react";
import { toast } from "sonner";

type Sample = { file: string; title: string; note: string; tone: string };

const SAMPLES: Sample[] = [
  {
    file: "study-certificate.png",
    title: "Справка об обучении",
    note: "Без замечаний",
    tone: "text-brand-text",
  },
  {
    file: "academic-leave.png",
    title: "Заявление на отпуск",
    note: "Без даты",
    tone: "text-warn",
  },
  {
    file: "internship.png",
    title: "Справка о практике",
    note: "Без печати",
    tone: "text-accent-text",
  },
];

type Props = { onPick: (file: File) => void };

/** Готовые примеры из открытого набора: можно попробовать сервис без своего документа. */
export function Samples({ onPick }: Props) {
  const [loading, setLoading] = useState<string | null>(null);

  const load = async (sample: Sample) => {
    setLoading(sample.file);
    try {
      const response = await fetch(`/samples/${sample.file}`);
      if (!response.ok) throw new Error("sample");
      const blob = await response.blob();
      onPick(new File([blob], sample.file, { type: "image/png" }));
    } catch {
      toast.error("Не удалось загрузить пример.");
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[13px]">
      <span className="text-muted">Примеры:</span>
      {SAMPLES.map((sample, index) => (
        <span key={sample.file} className="inline-flex items-center gap-2">
          {index > 0 && <span aria-hidden="true" className="size-1 rounded-full bg-muted/60" />}
          <button
            type="button"
            onClick={() => void load(sample)}
            disabled={loading !== null}
            title={`${sample.title}: ${sample.note.toLowerCase()}`}
            className={`rounded-md font-semibold underline-offset-4 transition-opacity hover:underline disabled:opacity-50 ${sample.tone}`}
          >
            <span className="sr-only">{sample.title}, </span>
            {sample.note}
          </button>
        </span>
      ))}
    </div>
  );
}
