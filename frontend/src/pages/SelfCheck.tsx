import { CircleCheck, CircleX, FlaskConical, LoaderCircle, Play } from "lucide-react";
import { useEffect, useRef, useState } from "react";

type DocumentEvent = {
  type: "document";
  document_id: string;
  document_title: string;
  type_ok: boolean;
  fields_ok: number;
  fields_total: number;
  validation_ok: boolean;
  answers_ok: number;
  answers_total: number;
  ms: number;
};

type DoneEvent = {
  type: "done";
  documents: number;
  questions: number;
  field_accuracy_macro: number;
  validation_exact_match: number;
  question_exact_match: number;
  errors: unknown[];
};

type Event = { type: "start"; documents: number } | DocumentEvent | DoneEvent;

const FALLBACK = "Не удалось запустить самопроверку. Попробуйте ещё раз.";

/** Читает поток событий самопроверки. fetch, а не EventSource: так видны коды ошибок. */
async function stream(signal: AbortSignal, onEvent: (event: Event) => void) {
  const response = await fetch("/api/selfcheck", { signal, credentials: "omit" });
  if (!response.ok || !response.body) {
    let detail = FALLBACK;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // Ответ без JSON: оставляем общее сообщение.
    }
    throw new Error(detail);
  }
  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += value;
    let end = buffer.indexOf("\n\n");
    while (end !== -1) {
      const chunk = buffer.slice(0, end);
      buffer = buffer.slice(end + 2);
      const data = chunk
        .split("\n")
        .filter((line) => line.startsWith("data: "))
        .map((line) => line.slice(6))
        .join("");
      if (data) onEvent(JSON.parse(data) as Event);
      end = buffer.indexOf("\n\n");
    }
  }
}

const metric = (value: number) => value.toFixed(3);

export function SelfCheck() {
  const [available, setAvailable] = useState<boolean | null>(null);
  const [running, setRunning] = useState(false);
  const [total, setTotal] = useState(30);
  const [rows, setRows] = useState<DocumentEvent[]>([]);
  const [done, setDone] = useState<DoneEvent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const controller = useRef<AbortController | null>(null);

  useEffect(() => {
    const abort = new AbortController();
    fetch("/api/selfcheck/available", { signal: abort.signal })
      .then((response) => response.json() as Promise<{ available: boolean }>)
      .then((body) => setAvailable(body.available))
      .catch(() => setAvailable(false));
    return () => {
      abort.abort();
      controller.current?.abort();
    };
  }, []);

  const start = async () => {
    const abort = new AbortController();
    controller.current = abort;
    setRunning(true);
    setRows([]);
    setDone(null);
    setError(null);
    try {
      await stream(abort.signal, (event) => {
        if (event.type === "start") setTotal(event.documents);
        else if (event.type === "document") setRows((current) => [...current, event]);
        else setDone(event);
      });
    } catch (problem) {
      if (!abort.signal.aborted) setError(problem instanceof Error ? problem.message : FALLBACK);
    } finally {
      setRunning(false);
    }
  };

  const fields = rows.reduce((sum, row) => sum + row.fields_ok, 0);
  const fieldsTotal = rows.reduce((sum, row) => sum + row.fields_total, 0);
  const answers = rows.reduce((sum, row) => sum + row.answers_ok, 0);
  const answersTotal = rows.reduce((sum, row) => sum + row.answers_total, 0);
  const checks = rows.filter((row) => row.validation_ok).length;

  return (
    <section className="mx-auto max-w-[1040px] px-4 pb-10 pt-8 sm:px-6 sm:pt-12">
      <div className="max-w-[680px]">
        <p className="inline-flex items-center gap-2 rounded-full border border-line bg-surface px-3.5 py-1.5 text-[13px] font-medium text-text-2">
          <FlaskConical aria-hidden="true" className="size-3.5 text-brand-text" />
          Автопроверка на ваших глазах
        </p>
        <h1 className="mt-4 text-[30px] font-semibold leading-tight tracking-[-0.025em] sm:text-[38px]">
          Самопроверка на открытом наборе
        </h1>
        <p className="mt-3 text-[16px] leading-relaxed text-text-2">
          Сервис прямо сейчас прочитает 30 документов организаторов, ответит на 120 вопросов и
          сравнит результат с эталоном. Итоговые метрики считает скрипт организаторов evaluate.py,
          тот же, что в автопроверке.
        </p>
      </div>

      <div className="card mt-7 p-4 sm:p-5">
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            disabled={running || available === false}
            onClick={() => void start()}
            className="pressable inline-flex h-11 items-center gap-2 rounded-xl bg-brand-strong px-5 text-sm font-semibold text-on-brand hover:bg-brand-hover disabled:bg-surface-3 disabled:text-muted"
          >
            {running ? (
              <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />
            ) : (
              <Play aria-hidden="true" className="size-4" />
            )}
            {running ? "Проверяю…" : done ? "Проверить ещё раз" : "Запустить проверку"}
          </button>
          {running && (
            <button
              type="button"
              onClick={() => controller.current?.abort()}
              className="pressable rounded-xl px-3 py-2.5 text-sm font-medium text-text-2 hover:text-text"
            >
              Остановить
            </button>
          )}
          <span className="tabular ml-auto text-[13px] text-muted">
            {rows.length} из {total}
          </span>
        </div>
        {available === false && (
          <p role="alert" className="mt-3 rounded-xl bg-warn-soft px-4 py-3 text-sm text-warn">
            Открытый набор не найден в этой установке сервиса.
          </p>
        )}
        {error && (
          <p role="alert" className="mt-3 rounded-xl bg-danger-soft px-4 py-3 text-sm text-danger">
            {error}
          </p>
        )}
        <div
          role="progressbar"
          aria-label="Сколько документов проверено"
          aria-valuemin={0}
          aria-valuemax={total}
          aria-valuenow={rows.length}
          className="mt-4 h-1.5 overflow-hidden rounded-full bg-surface-3"
        >
          <div
            className="h-full rounded-full bg-brand transition-[width] duration-300 ease-out"
            style={{ width: `${(rows.length / total) * 100}%` }}
          />
        </div>
        <dl className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-3">
          {[
            {
              label: "Точность полей",
              live: fieldsTotal ? `${fields} из ${fieldsTotal}` : "—",
              final: done && metric(done.field_accuracy_macro),
            },
            {
              label: "Проверка комплектности",
              live: rows.length ? `${checks} из ${rows.length}` : "—",
              final: done && metric(done.validation_exact_match),
            },
            {
              label: "Ответы на вопросы",
              live: answersTotal ? `${answers} из ${answersTotal}` : "—",
              final: done && metric(done.question_exact_match),
            },
          ].map((tile) => (
            <div key={tile.label} className="rounded-xl bg-surface-2 px-4 py-3">
              <dt className="text-[13px] text-muted">{tile.label}</dt>
              <dd className="tabular mt-1 text-2xl font-semibold text-brand-text">
                {tile.final ?? tile.live}
              </dd>
              {tile.final && <dd className="tabular text-[12.5px] text-muted">{tile.live}</dd>}
            </div>
          ))}
        </dl>
        {done && (
          <p className="mt-3 text-sm text-text-2">
            Готово: {done.documents} документов, {done.questions} вопросов, расхождений с эталоном:{" "}
            {done.errors.length}.
          </p>
        )}
      </div>

      {rows.length > 0 && (
        <div className="card mt-5 overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-line text-[12.5px] text-muted">
              <tr>
                <th className="px-5 py-2.5 font-medium">Документ</th>
                <th className="px-3 py-2.5 font-medium">Поля</th>
                <th className="hidden px-3 py-2.5 font-medium sm:table-cell">Проверка</th>
                <th className="px-3 py-2.5 font-medium">Ответы</th>
                <th className="hidden px-5 py-2.5 text-right font-medium sm:table-cell">Время</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const ok =
                  row.type_ok &&
                  row.validation_ok &&
                  row.fields_ok === row.fields_total &&
                  row.answers_ok === row.answers_total;
                return (
                  <tr key={row.document_id} className="border-b border-line last:border-b-0">
                    <td className="px-5 py-2.5">
                      <span className="flex items-center gap-2">
                        {ok ? (
                          <CircleCheck
                            aria-label="Совпало"
                            className="size-4 shrink-0 text-brand-text"
                          />
                        ) : (
                          <CircleX
                            aria-label="Есть расхождения"
                            className="size-4 shrink-0 text-danger"
                          />
                        )}
                        <span className="font-medium">{row.document_id}</span>
                        <span className="hidden text-muted md:inline">{row.document_title}</span>
                      </span>
                    </td>
                    <td className="tabular px-3 py-2.5">
                      {row.fields_ok}/{row.fields_total}
                    </td>
                    <td className="hidden px-3 py-2.5 sm:table-cell">
                      {row.validation_ok ? "совпадает" : "расходится"}
                    </td>
                    <td className="tabular px-3 py-2.5">
                      {row.answers_ok}/{row.answers_total}
                    </td>
                    <td className="tabular hidden px-5 py-2.5 text-right text-muted sm:table-cell">
                      {(row.ms / 1000).toFixed(1).replace(".", ",")} с
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
