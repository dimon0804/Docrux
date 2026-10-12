import { useEffect, useState } from "react";

const STEPS = ["Выравниваю снимок", "Читаю текст", "Заполняю карточку", "Сверяю с Положением"];

type Props = { preview: string | null };

/** Экран ожидания: по снимку идёт линия сканера, под ним меняются шаги. */
export function ReadingState({ preview }: Props) {
  const [step, setStep] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(
      () => setStep((value) => Math.min(value + 1, STEPS.length - 1)),
      1100,
    );
    return () => window.clearInterval(timer);
  }, []);

  return (
    <div role="status" aria-live="polite" className="card mx-auto max-w-[460px] p-6 text-center">
      <div className="scanner relative mx-auto aspect-[1/1.2] w-full max-w-[260px] overflow-hidden rounded-xl border border-line bg-white">
        {preview ? (
          <img src={preview} alt="" className="size-full object-cover object-top opacity-80" />
        ) : (
          <div className="flex size-full flex-col gap-3 p-6">
            {[70, 92, 84, 60, 88, 76, 50].map((width, index) => (
              <span
                key={index}
                className="h-2.5 rounded-full bg-[#e6e8ee]"
                style={{ width: `${width}%` }}
              />
            ))}
          </div>
        )}
        <span aria-hidden="true" className="scanner-line" />
      </div>
      <p className="mt-5 text-[15px] font-semibold">{STEPS[step]}…</p>
      <ol className="mt-3 flex justify-center gap-1.5" aria-hidden="true">
        {STEPS.map((label, index) => (
          <li
            key={label}
            className={`h-1 w-8 rounded-full transition-colors duration-300 ${
              index <= step ? "bg-brand" : "bg-surface-3"
            }`}
          />
        ))}
      </ol>
      <p className="mt-4 text-[13px] text-muted">Обычно это занимает несколько секунд.</p>
    </div>
  );
}
