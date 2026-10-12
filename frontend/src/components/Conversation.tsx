import { ArrowUp, CircleHelp } from "lucide-react";
import { type FormEvent, useEffect, useRef, useState } from "react";

import type { Analysis } from "@/lib/api";
import type { Turn } from "@/lib/workspace";

import { SourceChip } from "./SourceChip";

type Props = {
  analysis: Analysis;
  turns: Turn[];
  asking: boolean;
  onAsk: (question: string) => void;
  onSelect: (key: string) => void;
};

const MAX_LENGTH = 500;

function suggestions(analysis: Analysis): string[] {
  const text = analysis.fields.filter((field) => field.type !== "mark");
  const date = text.find((field) => field.type === "date");
  const first = text[0];
  return [
    "Кто принимает окончательное решение?",
    first ? `Укажи значение поля «${first.label}»` : "",
    date ? `Какова ${date.label.toLowerCase()}?` : "",
    "Какой размер стипендии положен студенту?",
  ].filter(Boolean);
}

/** Вопросы студента и ответы сервиса со ссылками на источники. */
export function Conversation({ analysis, turns, asking, onAsk, onSelect }: Props) {
  const [draft, setDraft] = useState("");
  const end = useRef<HTMLDivElement>(null);
  const labels = new Map(analysis.fields.map((field) => [field.key, field.label]));

  useEffect(() => {
    if (turns.length > 0) end.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [turns.length]);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const question = draft.trim();
    if (!question || asking) return;
    onAsk(question);
    setDraft("");
  };

  return (
    <section aria-labelledby="ask-title" className="card p-5">
      <h2 id="ask-title" className="text-[17px] font-semibold tracking-[-0.01em]">
        Вопрос по документу
      </h2>
      <p className="mt-0.5 text-[13px] text-muted">
        Отвечаю только по тому, что есть в документе и в Положении.
      </p>

      {turns.length > 0 && (
        <ol className="mt-4 flex flex-col gap-4" aria-live="polite">
          {turns.map((turn) => (
            <li key={turn.id} className="rise flex flex-col gap-2">
              <p className="self-end rounded-2xl rounded-br-md bg-surface-2 px-4 py-2.5 text-[15px] leading-relaxed">
                {turn.question}
              </p>
              {turn.error ? (
                <p role="alert" className="rounded-2xl bg-danger-soft px-4 py-3 text-sm text-danger">
                  {turn.error}
                </p>
              ) : turn.answer ? (
                <div
                  className={`rounded-2xl rounded-tl-md border px-4 py-3 ${
                    turn.answer.answerable
                      ? "border-line bg-surface"
                      : "border-line bg-surface-2/60"
                  }`}
                >
                  {!turn.answer.answerable && (
                    <p className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted">
                      <CircleHelp aria-hidden="true" className="size-3.5" />
                      Ответа в источниках нет
                    </p>
                  )}
                  <p className="text-[15px] leading-relaxed">{turn.answer.answer}</p>
                  {turn.answer.sources.length > 0 && (
                    <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
                      <span className="mr-1 text-[13px] text-muted">Источник:</span>
                      {turn.answer.sources.map((source) => (
                        <SourceChip
                          key={source}
                          source={source}
                          fieldLabel={labels.get(source.replace(/^field:/, ""))}
                          onFieldClick={onSelect}
                        />
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div
                  role="status"
                  aria-label="Готовлю ответ"
                  className="flex w-fit gap-1.5 rounded-2xl rounded-tl-md border border-line px-4 py-3.5"
                >
                  {[0, 1, 2].map((dot) => (
                    <span
                      key={dot}
                      className="size-1.5 animate-pulse rounded-full bg-muted"
                      style={{ animationDelay: `${dot * 160}ms` }}
                    />
                  ))}
                </div>
              )}
            </li>
          ))}
        </ol>
      )}
      <div ref={end} />

      <ul className="mt-4 flex flex-wrap gap-1.5" aria-label="Примеры вопросов">
        {suggestions(analysis).map((text) => (
          <li key={text}>
            <button
              type="button"
              disabled={asking}
              onClick={() => onAsk(text)}
              className="pressable rounded-full border border-line px-3 py-1.5 text-[13px] text-text-2 hover:border-brand/50 hover:text-text disabled:opacity-50"
            >
              {text}
            </button>
          </li>
        ))}
      </ul>

      <form onSubmit={submit} className="mt-3 flex items-end gap-2">
        <label htmlFor="question" className="sr-only">
          Ваш вопрос
        </label>
        <input
          id="question"
          value={draft}
          onChange={(event) => setDraft(event.target.value.slice(0, MAX_LENGTH))}
          placeholder="Например: когда выдана справка?"
          autoComplete="off"
          maxLength={MAX_LENGTH}
          enterKeyHint="send"
          className="h-12 min-w-0 flex-1 rounded-xl border border-line-strong bg-surface px-4 text-[15px] outline-none transition-[border-color,box-shadow] duration-150 placeholder:text-muted focus:border-brand focus:shadow-[0_0_0_4px_rgb(80_184_72/0.16)]"
        />
        <button
          type="submit"
          disabled={!draft.trim() || asking}
          aria-label="Отправить вопрос"
          className="pressable grid size-12 shrink-0 place-items-center rounded-xl bg-brand-strong text-on-brand hover:bg-brand-hover disabled:bg-surface-3 disabled:text-muted"
        >
          <ArrowUp aria-hidden="true" className="size-5" strokeWidth={2.5} />
        </button>
      </form>
    </section>
  );
}
