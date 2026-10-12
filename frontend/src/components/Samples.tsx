import { useState } from "react";
import { toast } from "sonner";

type Sample = { file: string; title: string; note: string };

const SAMPLES: Sample[] = [
  { file: "study-certificate.png", title: "Справка об обучении", note: "Все сведения на месте" },
  { file: "academic-leave.png", title: "Заявление на отпуск", note: "Нет даты заявления" },
  { file: "internship.png", title: "Справка о практике", note: "Нет подписи и печати" },
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
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch {
      toast.error("Не удалось загрузить пример.");
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="mx-auto mt-10 max-w-[720px]">
      <p className="text-center text-sm text-muted">Нет документа под рукой? Возьмите пример</p>
      <ul className="mt-4 grid gap-3 sm:grid-cols-3">
        {SAMPLES.map((sample, index) => (
          <li key={sample.file} className="rise" style={{ "--i": index + 4 } as React.CSSProperties}>
            <button
              type="button"
              onClick={() => void load(sample)}
              disabled={loading !== null}
              className="pressable group flex w-full items-center gap-3 rounded-2xl border border-line bg-surface p-2.5 text-left hover:border-brand/50 hover:shadow-card disabled:opacity-60 sm:flex-col sm:items-stretch sm:p-3"
            >
              <span className="block h-16 w-14 shrink-0 overflow-hidden rounded-lg border border-line bg-white sm:h-32 sm:w-full">
                <img
                  src={`/samples/${sample.file}`}
                  alt=""
                  loading="lazy"
                  className="size-full object-cover object-top transition-transform duration-300 ease-out-strong group-hover:scale-[1.04]"
                />
              </span>
              <span className="min-w-0">
                <span className="block truncate text-sm font-semibold">{sample.title}</span>
                <span className="mt-0.5 block text-[13px] text-muted">{sample.note}</span>
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
