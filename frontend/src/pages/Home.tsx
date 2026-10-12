import { ChevronDown, FileSearch, RotateCcw, ShieldCheck } from "lucide-react";
import { type FormEvent, useEffect, useState } from "react";
import { toast } from "sonner";

import { CheckBanner } from "@/components/CheckBanner";
import { Conversation } from "@/components/Conversation";
import { DocumentViewer } from "@/components/DocumentViewer";
import { Dropzone } from "@/components/Dropzone";
import { FieldCard } from "@/components/FieldCard";
import { HowItWorks } from "@/components/HowItWorks";
import { ReadingState } from "@/components/ReadingState";
import { RulesSection } from "@/components/RulesSection";
import { Samples } from "@/components/Samples";
import { TypePicker } from "@/components/TypePicker";
import { ReferenceProvider, useReference } from "@/lib/rules";
import { useWorkspace } from "@/lib/workspace";

const DEFAULT_QUESTION = "Содержит ли документ все обязательные сведения?";

export function Home() {
  return (
    <ReferenceProvider>
      <Workspace />
      <HowItWorks />
      <RulesSection />
    </ReferenceProvider>
  );
}

function Workspace() {
  const { state, pick, setDocType, read, question, focus, reset } = useWorkspace();
  const { docTypes, failed } = useReference();
  const [draft, setDraft] = useState("");

  // Экран чтения и результат начинаются сверху, даже если форму отправили из середины страницы.
  useEffect(() => {
    if (state.phase !== "idle") window.scrollTo({ top: 0, behavior: "instant" });
  }, [state.phase]);

  const choose = (file: File) => {
    const problem = pick(file);
    if (problem) toast.error(problem);
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!state.file) {
      toast.error("Сначала выберите файл документа.");
      return;
    }
    void read(draft);
  };

  const select = (key: string) => focus(state.focus.length === 1 && state.focus[0] === key ? [] : [key]);

  if (state.phase === "ready" && state.analysis && state.check && state.image) {
    return (
      <section className="mx-auto max-w-[1240px] px-4 pt-6 sm:px-6 sm:pt-10">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold tracking-[-0.02em] sm:text-[28px]">
              {state.analysis.document_title}
            </h1>
            <p className="mt-1 text-sm text-muted">{state.file?.name}</p>
          </div>
          <button
            type="button"
            onClick={() => {
              reset();
              setDraft("");
            }}
            className="pressable inline-flex items-center gap-2 rounded-xl border border-line bg-surface px-4 py-2.5 text-sm font-medium hover:border-line-strong"
          >
            <RotateCcw aria-hidden="true" className="size-4" />
            Другой документ
          </button>
        </div>

        <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
          <div className="lg:sticky lg:top-[84px]">
            <DocumentViewer
              image={state.image}
              fields={state.analysis.fields}
              focus={state.focus}
              width={state.analysis.width}
              height={state.analysis.height}
              pageBreaks={state.analysis.page_breaks}
              onSelect={select}
            />
          </div>
          <div className="flex min-w-0 flex-col gap-5">
            <CheckBanner check={state.check} fields={state.analysis.fields} onSelect={select} />
            <Conversation
              analysis={state.analysis}
              turns={state.turns}
              asking={state.asking}
              onAsk={(text) => void question(text)}
              onSelect={select}
            />
            <FieldCard analysis={state.analysis} focus={state.focus} onSelect={select} />
            <details className="card group">
              <summary className="flex list-none items-center justify-between gap-3 px-5 py-4 text-[15px] font-semibold [&::-webkit-details-marker]:hidden">
                Распознанный текст
                <ChevronDown
                  aria-hidden="true"
                  className="size-4 text-muted transition-transform duration-200 ease-out-strong group-open:rotate-180"
                />
              </summary>
              <pre className="scroll-thin max-h-80 overflow-auto whitespace-pre-wrap border-t border-line px-5 py-4 font-sans text-sm leading-relaxed text-text-2">
                {state.analysis.text}
              </pre>
            </details>
          </div>
        </div>
      </section>
    );
  }

  if (state.phase === "reading") {
    return (
      <section className="mx-auto max-w-[1240px] px-4 py-14 sm:px-6 sm:py-20">
        <ReadingState preview={state.preview} />
      </section>
    );
  }

  return (
    <section className="mx-auto max-w-[1240px] px-4 pt-10 sm:px-6 sm:pt-16">
      <div className="mx-auto max-w-[720px] text-center">
        <p className="rise inline-flex items-center gap-2 rounded-full border border-line bg-surface px-3.5 py-1.5 text-[13px] font-medium text-text-2">
          <span className="size-1.5 rounded-full bg-brand" />
          Цифровой секретарь деканата
        </p>
        <h1
          className="rise mt-5 text-[34px] font-semibold leading-[1.08] tracking-[-0.03em] sm:text-[52px]"
          style={{ "--i": 1 } as React.CSSProperties}
        >
          Прочитаю документ и отвечу <span className="text-brand-text">по Положению</span>
        </h1>
        <p
          className="rise mx-auto mt-4 max-w-[560px] text-[17px] leading-relaxed text-text-2"
          style={{ "--i": 2 } as React.CSSProperties}
        >
          Загрузите фото справки или заявления. Сервис распознает текст, заполнит карточку,
          проверит обязательные сведения и назовёт пункт, на который опирается ответ.
        </p>
      </div>

      <form
        onSubmit={submit}
        className="rise card mx-auto mt-9 flex max-w-[720px] flex-col gap-5 p-4 shadow-pop sm:p-6"
        style={{ "--i": 3 } as React.CSSProperties}
        noValidate
      >
        <Dropzone file={state.file} preview={state.preview} onPick={choose} />

        <TypePicker docTypes={docTypes} value={state.docType} onChange={setDocType} />

        <div>
          <label htmlFor="first-question" className="text-sm font-medium">
            Вопрос <span className="font-normal text-muted">(необязательно)</span>
          </label>
          <input
            id="first-question"
            value={draft}
            onChange={(event) => setDraft(event.target.value.slice(0, 500))}
            placeholder={DEFAULT_QUESTION}
            maxLength={500}
            autoComplete="off"
            className="mt-2 h-12 w-full rounded-xl border border-line-strong bg-surface px-4 text-[15px] outline-none transition-[border-color,box-shadow] duration-150 placeholder:text-muted focus:border-brand focus:shadow-[0_0_0_4px_rgb(80_184_72/0.16)]"
          />
        </div>

        {state.error && (
          <p role="alert" className="rounded-xl bg-danger-soft px-4 py-3 text-sm text-danger">
            {state.error}
          </p>
        )}
        {failed && !state.error && (
          <p role="alert" className="rounded-xl bg-warn-soft px-4 py-3 text-sm text-warn">
            Не удалось связаться с сервисом. Проверьте, что он запущен, и обновите страницу.
          </p>
        )}

        <button
          type="submit"
          disabled={!state.file}
          className="pressable inline-flex h-[52px] items-center justify-center gap-2 rounded-xl bg-brand-strong px-6 text-base font-semibold text-on-brand shadow-[0_1px_0_rgb(255_255_255/0.2)_inset,0_8px_20px_-8px_rgb(47_122_42/0.6)] hover:bg-brand-hover disabled:bg-surface-3 disabled:text-muted disabled:shadow-none"
        >
          <FileSearch aria-hidden="true" className="size-5" />
          Разобрать документ
        </button>

        <p className="flex items-start justify-center gap-2 text-center text-[13px] leading-relaxed text-muted">
          <ShieldCheck aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-brand-text" />
          Файл обрабатывается в памяти и не сохраняется на сервере.
        </p>
      </form>

      <Samples onPick={choose} />
    </section>
  );
}
