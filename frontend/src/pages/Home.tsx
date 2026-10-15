import {
  ArrowRight,
  BookOpen,
  ChevronDown,
  Eye,
  EyeOff,
  FileJson,
  FileText,
  FileWarning,
  MessageCircleQuestion,
  Printer,
  RotateCcw,
  Stamp,
} from "lucide-react";
import { type FormEvent, useEffect, useState } from "react";
import { toast } from "sonner";

import { CheckBanner } from "@/components/CheckBanner";
import { Conversation } from "@/components/Conversation";
import { DocumentViewer } from "@/components/DocumentViewer";
import { Dropzone } from "@/components/Dropzone";
import { FieldCard } from "@/components/FieldCard";
import { HowItWorks } from "@/components/HowItWorks";
import { Features } from "@/components/Features";
import { Quality } from "@/components/Quality";
import { PhotoAdvice } from "@/components/PhotoAdvice";
import { ReadingState } from "@/components/ReadingState";
import { Remarks } from "@/components/Remarks";
import { ReadingTrace } from "@/components/ReadingTrace";
import { RuleChecklist } from "@/components/RuleChecklist";
import { RulesSection } from "@/components/RulesSection";
import { Samples } from "@/components/Samples";
import { StudentReply } from "@/components/StudentReply";
import { TypePicker } from "@/components/TypePicker";
import { maskAnalysis, maskText } from "@/lib/privacy";
import { downloadJson, printReport, resultRecord } from "@/lib/report";
import { ReferenceProvider, useReference } from "@/lib/rules";
import { useWorkspace } from "@/lib/workspace";

export function Home() {
  return (
    <ReferenceProvider>
      <Workspace />
      <Features />
      <HowItWorks />
      <Quality />
      <RulesSection />
    </ReferenceProvider>
  );
}

function Workspace() {
  const { state, pick, setDocType, read, question, focus, edit, reset } = useWorkspace();
  const { docTypes, failed } = useReference();
  const [draft, setDraft] = useState("");
  const [masked, setMasked] = useState(false);

  // Экран чтения и результат начинаются сверху, даже если форму отправили из середины страницы.
  useEffect(() => {
    if (state.phase !== "idle") window.scrollTo({ top: 0, behavior: "instant" });
  }, [state.phase]);

  const choose = (file: File, more: File[] = []) => {
    const problem = pick(file, more);
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

  const select = (key: string) =>
    focus(state.focus.length === 1 && state.focus[0] === key ? [] : [key]);

  if (state.phase === "ready" && state.analysis && state.check && state.image) {
    return (
      <section className="mx-auto max-w-[1240px] px-3 pt-6 sm:px-6 sm:pt-10">
        <div className="rise panel p-3 sm:p-6">
          <div className="mb-5 flex flex-wrap items-center justify-between gap-3 border-b border-line pb-4 sm:mb-6 sm:pb-5">
            <div className="flex min-w-0 items-center gap-4">
              <span aria-hidden="true" className="window-dots no-print hidden sm:inline-flex">
                <i />
                <i />
                <i />
              </span>
              <div className="min-w-0">
                <h1 className="text-[22px] font-bold leading-tight sm:text-[26px]">
                  {state.analysis.document_title}
                </h1>
                <p className="mono mt-1 truncate text-[12px] text-muted">
                  {state.analysis.document_title} / {state.file?.name}
                  {state.more.length > 0 ? ` и ещё ${state.more.length} стр.` : ""}
                </p>
              </div>
            </div>
            <div className="no-print flex flex-wrap items-center gap-2">
              <button
                type="button"
                aria-pressed={masked}
                onClick={() => setMasked((value) => !value)}
                title="Скрыть ФИО, номер и подпись на снимке, в карточке и при выгрузке"
                className={`pressable inline-flex items-center gap-2 rounded-xl border px-3.5 py-2.5 text-sm font-semibold ${
                  masked
                    ? "border-accent/45 bg-accent-soft text-accent-text"
                    : "border-line-strong bg-surface/60 text-text-2 hover:border-brand hover:text-text"
                }`}
              >
                {masked ? (
                  <EyeOff aria-hidden="true" className="size-4" />
                ) : (
                  <Eye aria-hidden="true" className="size-4" />
                )}
                <span className="hidden sm:inline">
                  {masked ? "Данные скрыты" : "Скрыть данные"}
                </span>
                <span className="sr-only sm:hidden">Скрыть персональные данные</span>
              </button>
              <button
                type="button"
                onClick={printReport}
                title="Распечатать или сохранить в PDF"
                className="pressable inline-flex items-center gap-2 rounded-xl border border-line-strong bg-surface/60 px-3.5 py-2.5 text-sm font-semibold text-text-2 hover:border-brand hover:text-text"
              >
                <Printer aria-hidden="true" className="size-4" />
                <span className="hidden sm:inline">Лист проверки</span>
                <span className="sr-only sm:hidden">Распечатать лист проверки</span>
              </button>
              <button
                type="button"
                onClick={() => {
                  const name = state.file?.name ?? "document";
                  downloadJson(
                    `${name.replace(/\.[^.]+$/, "")}.docrux.json`,
                    masked
                      ? resultRecord(
                          name,
                          maskAnalysis(state.analysis!),
                          state.turns.map((turn) =>
                            turn.answer
                              ? {
                                  ...turn,
                                  answer: {
                                    ...turn.answer,
                                    answer: maskText(turn.answer.answer, state.analysis!.fields),
                                  },
                                }
                              : turn,
                          ),
                        )
                      : resultRecord(name, state.analysis!, state.turns),
                  );
                }}
                title="Карточка, проверка и ответы в формате results.json"
                className="pressable inline-flex items-center gap-2 rounded-xl border border-brand/45 bg-brand-soft/60 px-3.5 py-2.5 text-sm font-semibold text-brand-text hover:border-brand"
              >
                <FileJson aria-hidden="true" className="size-4" />
                <span className="hidden sm:inline">JSON</span>
                <span className="sr-only sm:hidden">Скачать результат в JSON</span>
              </button>
              <button
                type="button"
                onClick={() => {
                  reset();
                  setDraft("");
                }}
                className="btn-accent pressable inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-bold"
              >
                <RotateCcw aria-hidden="true" className="size-4" />
                Другой документ
              </button>
            </div>
          </div>
          <p className="print-only mb-4 text-[13px] text-text-2">
            Лист предварительной проверки сервиса «Докрукс» от{" "}
            {new Date().toLocaleDateString("ru-RU", {
              day: "numeric",
              month: "long",
              year: "numeric",
            })}{" "}
            Окончательное решение принимает сотрудник деканата (пункт 1.3 Положения).
          </p>

          <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
            <div className="lg:sticky lg:top-[112px]">
              <DocumentViewer
                masked={masked}
                image={state.image}
                original={state.preview}
                quality={state.analysis.quality}
                fields={state.analysis.fields}
                focus={state.focus}
                width={state.analysis.width}
                height={state.analysis.height}
                pageBreaks={state.analysis.page_breaks}
                onSelect={select}
              />
            </div>
            <div className="flex min-w-0 flex-col gap-5">
              <PhotoAdvice advice={state.analysis.advice} />
              <CheckBanner
                check={state.check}
                fields={state.analysis.fields}
                supported={state.analysis.supported}
                title={state.analysis.document_title}
                onSelect={select}
              />
              <Remarks remarks={state.analysis.remarks} onSelect={select} />
              <Conversation
                masked={masked}
                analysis={state.analysis}
                turns={state.turns}
                asking={state.asking}
                onAsk={(text) => void question(text)}
                onSelect={select}
              />
              {state.analysis.supported && (
                <RuleChecklist
                  documentType={state.analysis.document_type}
                  fields={state.analysis.fields}
                  onSelect={select}
                />
              )}
              <FieldCard
                masked={masked}
                analysis={state.analysis}
                focus={state.focus}
                onSelect={select}
                onEdit={edit}
                edited={state.edited}
              />
              <StudentReply analysis={state.analysis} check={state.check} />
              <ReadingTrace analysis={state.analysis} />
              <details className="no-print card group">
                <summary className="section-title flex list-none items-center justify-between gap-3 px-5 py-4 [&::-webkit-details-marker]:hidden">
                  Распознанный текст
                  <ChevronDown
                    aria-hidden="true"
                    className="size-4 text-muted transition-transform duration-200 ease-out-strong group-open:rotate-180"
                  />
                </summary>
                <pre className="scroll-thin max-h-80 overflow-auto whitespace-pre-wrap border-t border-line px-5 py-4 font-sans text-sm leading-relaxed text-text-2">
                  {masked
                    ? maskText(state.analysis.text, state.analysis.fields)
                    : state.analysis.text}
                </pre>
              </details>
            </div>
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
    <section className="relative mx-auto max-w-[1240px] px-4 pt-10 sm:px-6 sm:pt-16">
      <HeroCards />
      <div className="relative mx-auto max-w-[900px] text-center">
        <p className="rise inline-flex items-center gap-2.5 rounded-full border border-line-strong bg-surface/70 px-4 py-1.5 backdrop-blur">
          <span className="pulse-dot size-2 rounded-full bg-accent text-accent" />
          <span className="mono text-[12px] font-semibold uppercase tracking-[0.06em] text-accent-text">
            750 документов в проверке · 1.000 по трём метрикам
          </span>
        </p>
        <h1
          className="rise mt-6 text-[40px] font-extrabold leading-[1.04] tracking-[-0.01em] sm:text-[64px] lg:text-[76px]"
          style={{ "--i": 1 } as React.CSSProperties}
        >
          Проверит документ.
          <br />
          <span className="text-headline">Ответит по </span>
          <span className="text-headline-2">Положению.</span>
        </h1>
        <p
          className="rise mx-auto mt-6 max-w-[640px] text-[17px] leading-relaxed text-text-2"
          style={{ "--i": 2 } as React.CSSProperties}
        >
          ИИ, который видит документ насквозь. Загрузите скан или фото с телефона: сервис выровняет
          наклон, найдёт подпись и печать, сверит данные с Положением и назовёт пункт, на который
          опирается ответ.
        </p>
      </div>

      <form
        onSubmit={submit}
        className="rise panel relative mx-auto mt-10 flex max-w-[780px] flex-col gap-6 p-4 sm:p-7"
        style={{ "--i": 3 } as React.CSSProperties}
        noValidate
      >
        <Dropzone
          file={state.file}
          preview={state.preview}
          onPick={choose}
          multiple
          extraPages={state.more.length}
        />

        <TypePicker docTypes={docTypes} value={state.docType} onChange={setDocType} />

        <div>
          <label htmlFor="first-question" className="sr-only">
            Вопрос (необязательно)
          </label>
          <div className="flex items-center gap-2 rounded-[20px] border border-line-strong bg-surface-2/60 p-1.5 pl-4 transition-[border-color,box-shadow] duration-150 focus-within:border-brand focus-within:shadow-[0_0_0_4px_var(--brand-soft)]">
            <MessageCircleQuestion aria-hidden="true" className="size-5 shrink-0 text-accent" />
            <input
              id="first-question"
              value={draft}
              onChange={(event) => setDraft(event.target.value.slice(0, 500))}
              placeholder="Вопрос, если есть: «Хватит ли справки для перевода?»"
              maxLength={500}
              autoComplete="off"
              className="h-11 min-w-0 flex-1 bg-transparent text-[15px] outline-none placeholder:text-muted"
            />
            <button
              type="submit"
              disabled={!state.file}
              aria-label="Разобрать документ"
              title={state.file ? "Разобрать документ" : "Сначала выберите файл"}
              className="btn-accent pressable inline-flex h-11 shrink-0 items-center justify-center gap-2 rounded-2xl px-4 text-[15px] font-bold disabled:bg-none disabled:bg-surface-3 disabled:text-muted disabled:shadow-none sm:px-5"
            >
              <span className="hidden sm:inline">Разобрать</span>
              <ArrowRight aria-hidden="true" className="size-5" />
            </button>
          </div>
          <p className="mt-2 pl-1 text-[12.5px] text-muted">
            Без вопроса сервис проверит, все ли обязательные сведения на месте.
          </p>
        </div>

        {state.error && (
          <p role="alert" className="rounded-2xl bg-danger-soft px-4 py-3 text-sm text-danger">
            {state.error}
          </p>
        )}
        {failed && !state.error && (
          <p role="alert" className="rounded-2xl bg-warn-soft px-4 py-3 text-sm text-warn">
            Не удалось связаться с сервисом. Проверьте, что он запущен, и обновите страницу.
          </p>
        )}

        <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2 border-t border-line pt-4">
          <p className="flex items-center gap-2 text-[13px] text-muted">
            <span className="pulse-dot size-2 rounded-full bg-brand text-brand" />
            Файл обрабатывается в памяти и не сохраняется
          </p>
          <Samples onPick={choose} />
        </div>
      </form>
    </section>
  );
}

const HERO_CARDS = [
  {
    icon: FileText,
    title: "Справка об обучении",
    note: "10 из 10 полей на месте",
    accent: false,
    place: "left-0 top-16",
    rotate: "-4deg",
  },
  {
    icon: BookOpen,
    title: "Положение",
    note: "пункты 1.1–6.5",
    accent: false,
    place: "-left-2 top-[330px]",
    rotate: "5deg",
  },
  {
    icon: FileWarning,
    title: "Заявление на академотпуск",
    note: "не хватает даты · п. 4.1",
    accent: true,
    place: "right-0 top-12",
    rotate: "6deg",
  },
  {
    icon: Stamp,
    title: "Подпись и печать",
    note: "найдены на снимке",
    accent: true,
    place: "-right-2 top-[340px]",
    rotate: "-5deg",
  },
];

/** Карточки вокруг заголовка, как в макете. Только для широкого экрана. */
function HeroCards() {
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none absolute inset-x-0 top-0 hidden xl:block"
    >
      {HERO_CARDS.map((card, index) => {
        const Icon = card.icon;
        return (
          <div
            key={card.title}
            className={`rise absolute ${card.place}`}
            style={{ "--i": index + 3 } as React.CSSProperties}
          >
            <div
              className={`float-card flex items-center gap-3 rounded-2xl border bg-surface/85 py-2.5 pl-2.5 pr-5 shadow-pop backdrop-blur ${
                card.accent ? "border-accent/35" : "border-brand/35"
              }`}
              style={{ "--d": index, "--r": card.rotate } as React.CSSProperties}
            >
              <span
                className={`grid size-9 place-items-center rounded-xl border ${
                  card.accent
                    ? "border-accent/30 bg-accent-soft text-accent-text"
                    : "border-brand/30 bg-brand-soft text-brand-text"
                }`}
              >
                <Icon className="size-[18px]" />
              </span>
              <span className="text-left leading-tight">
                <span className="block text-[14px] font-bold">{card.title}</span>
                <span
                  className={`mono mt-0.5 block text-[11px] ${card.accent ? "text-accent-text" : "text-brand-text"}`}
                >
                  {card.note}
                </span>
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
