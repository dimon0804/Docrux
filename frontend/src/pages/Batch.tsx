import {
  CircleAlert,
  CircleCheck,
  Download,
  FileQuestion,
  FileStack,
  FileX,
  LoaderCircle,
  Trash2,
} from "lucide-react";
import { useCallback, useEffect, useId, useRef, useState } from "react";
import { toast } from "sonner";
import { Link } from "wouter";

import { type AnalyzeResponse, analyze, ApiError, checkFile } from "@/lib/api";
import { downloadJson } from "@/lib/report";

const MAX_FILES = 60;

type Item = {
  id: number;
  file: File;
  state: "queued" | "reading" | "done" | "failed";
  result: AnalyzeResponse | null;
  error: string | null;
};

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

function stem(name: string) {
  return name.replace(/\.[^.]+$/, "") || "document";
}

/** Все разобранные документы в формате results.json. */
function resultsJson(items: Item[]) {
  return {
    version: "1.0",
    documents: items
      .filter((item) => item.result)
      .map(({ file, result }) => ({
        document_id: stem(file.name),
        document_type: result!.analysis.document_type,
        fields: Object.fromEntries(
          result!.analysis.fields.map((field) => [field.key, field.value]),
        ),
        validation: result!.analysis.validation,
        answers: [
          {
            question_id: "q1",
            answerable: result!.check.answerable,
            value: result!.check.value,
            answer: result!.check.answer,
            sources: result!.check.sources,
          },
        ],
      })),
  };
}

function csv(items: Item[]) {
  const quote = (value: string) => `"${value.replace(/"/g, '""')}"`;
  const rows = [["Файл", "Тип документа", "Итог", "Не хватает", "Основание"]];
  for (const { file, result, error } of items) {
    if (!result) {
      rows.push([file.name, "", "ошибка", error ?? "", ""]);
      continue;
    }
    const { analysis, check } = result;
    const missing = analysis.fields.filter((field) => !field.found).map((field) => field.label);
    const status = !analysis.supported
      ? "другой тип"
      : check.value === "document_ok"
        ? "в порядке"
        : "не хватает сведений";
    rows.push([
      file.name,
      analysis.document_title,
      status,
      analysis.supported ? missing.join("; ") : "",
      check.sources.map((source) => source.replace("rule:", "п. ")).join(", "),
    ]);
  }
  // Excel открывает CSV в UTF-8 правильно только с меткой порядка байтов.
  return "﻿" + rows.map((row) => row.map(quote).join(";")).join("\r\n");
}

export function Batch() {
  const inputId = useId();
  const [items, setItems] = useState<Item[]>([]);
  const [running, setRunning] = useState(false);
  const counter = useRef(0);
  const stop = useRef(false);

  useEffect(
    () => () => {
      stop.current = true;
    },
    [],
  );

  const add = (files: FileList | File[]) => {
    const accepted: Item[] = [];
    const rejected: string[] = [];
    for (const file of Array.from(files)) {
      const problem = checkFile(file);
      if (problem) rejected.push(`${file.name}: ${problem}`);
      else
        accepted.push({ id: ++counter.current, file, state: "queued", result: null, error: null });
    }
    if (rejected.length) toast.error(rejected.slice(0, 3).join("\n"));
    setItems((current) => {
      const room = MAX_FILES - current.length;
      if (accepted.length > room)
        toast.error(`За один раз можно проверить до ${MAX_FILES} файлов.`);
      return [...current, ...accepted.slice(0, Math.max(0, room))];
    });
  };

  const update = (id: number, patch: Partial<Item>) =>
    setItems((current) => current.map((item) => (item.id === id ? { ...item, ...patch } : item)));

  const run = useCallback(async () => {
    setRunning(true);
    stop.current = false;
    const queue = items.filter((item) => item.state === "queued" || item.state === "failed");
    for (const item of queue) {
      if (stop.current) break;
      update(item.id, { state: "reading", error: null });
      for (let attempt = 0; ; attempt += 1) {
        try {
          const result = await analyze(item.file);
          update(item.id, { state: "done", result });
          break;
        } catch (error) {
          // Сервис ограничивает частоту запросов: ждём столько, сколько он попросил.
          if (error instanceof ApiError && error.status === 429 && attempt < 5) {
            await wait((error.retryAfter ?? 10) * 1000);
            continue;
          }
          const message =
            error instanceof ApiError ? error.message : "Не удалось разобрать документ.";
          update(item.id, { state: "failed", error: message });
          break;
        }
      }
    }
    setRunning(false);
  }, [items]);

  const done = items.filter((item) => item.state === "done");
  const ok = done.filter(
    (item) => item.result!.analysis.supported && item.result!.check.value === "document_ok",
  ).length;
  const incomplete = done.filter(
    (item) => item.result!.analysis.supported && item.result!.check.value !== "document_ok",
  ).length;
  const other = done.length - ok - incomplete;
  const failed = items.filter((item) => item.state === "failed").length;
  const finished = done.length + failed;
  const pending = items.some((item) => item.state === "queued" || item.state === "failed");

  return (
    <section className="mx-auto max-w-[1040px] px-4 pb-10 pt-8 sm:px-6 sm:pt-12">
      <div className="max-w-[640px]">
        <p className="inline-flex items-center gap-2 rounded-full border border-line bg-surface px-3.5 py-1.5 text-[13px] font-medium text-text-2">
          <FileStack aria-hidden="true" className="size-3.5 text-brand-text" />
          Для сотрудника деканата
        </p>
        <h1 className="mt-4 text-[30px] font-semibold leading-tight tracking-[-0.025em] sm:text-[38px]">
          Пакетная проверка
        </h1>
        <p className="mt-3 text-[16px] leading-relaxed text-text-2">
          Загрузите сразу несколько справок и заявлений. Сервис разберёт их по очереди, покажет итог
          по каждому и соберёт общий файл в формате results.json или таблицу для Excel. Чтобы задать
          вопросы по одному документу, откройте его на{" "}
          <Link href="/" className="font-medium text-brand-text underline-offset-4 hover:underline">
            главной странице
          </Link>
          .
        </p>
      </div>

      <div
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => {
          event.preventDefault();
          if (!running) add(event.dataTransfer.files);
        }}
        className="card mt-7 p-4 sm:p-5"
      >
        <input
          id={inputId}
          type="file"
          multiple
          accept="image/jpeg,image/png,application/pdf,.jpg,.jpeg,.png,.pdf"
          className="sr-only"
          disabled={running}
          onChange={(event) => {
            if (event.target.files) add(event.target.files);
            event.target.value = "";
          }}
        />
        <div className="flex flex-wrap items-center gap-3">
          <label
            htmlFor={inputId}
            aria-disabled={running}
            className="pressable inline-flex cursor-pointer items-center gap-2 rounded-xl border border-line-strong bg-surface px-4 py-2.5 text-sm font-semibold hover:border-brand/60 aria-disabled:pointer-events-none aria-disabled:opacity-50"
          >
            <FileStack aria-hidden="true" className="size-4 text-brand-text" />
            Добавить файлы
          </label>
          <button
            type="button"
            disabled={!pending || running}
            onClick={() => void run()}
            className="pressable inline-flex items-center gap-2 rounded-xl bg-brand-strong px-4 py-2.5 text-sm font-semibold text-on-brand hover:bg-brand-hover disabled:bg-surface-3 disabled:text-muted"
          >
            {running ? (
              <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />
            ) : (
              <CircleCheck aria-hidden="true" className="size-4" />
            )}
            {running ? "Проверяю…" : "Проверить"}
          </button>
          {running && (
            <button
              type="button"
              onClick={() => {
                stop.current = true;
              }}
              className="pressable rounded-xl px-3 py-2.5 text-sm font-medium text-text-2 hover:text-text"
            >
              Остановить
            </button>
          )}
          <span className="ml-auto text-[13px] text-muted">
            {items.length === 0
              ? `JPG, PNG или PDF, до ${MAX_FILES} файлов`
              : `Файлов: ${items.length}`}
          </span>
        </div>

        {items.length > 0 && (
          <>
            <div
              role="progressbar"
              aria-label="Сколько документов проверено"
              aria-valuemin={0}
              aria-valuemax={items.length}
              aria-valuenow={finished}
              className="mt-4 h-1.5 overflow-hidden rounded-full bg-surface-3"
            >
              <div
                className="h-full rounded-full bg-brand transition-[width] duration-300 ease-out"
                style={{ width: `${(finished / items.length) * 100}%` }}
              />
            </div>
            <dl className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
              {[
                { label: "В порядке", value: ok, tone: "text-brand-text" },
                { label: "Не хватает сведений", value: incomplete, tone: "text-warn" },
                { label: "Другой тип", value: other, tone: "text-text-2" },
                { label: "Не прочитаны", value: failed, tone: "text-danger" },
              ].map((tile) => (
                <div key={tile.label} className="rounded-xl bg-surface-2 px-3.5 py-2.5">
                  <dt className="text-[12.5px] text-muted">{tile.label}</dt>
                  <dd className={`tabular mt-0.5 text-xl font-semibold ${tile.tone}`}>
                    {tile.value}
                  </dd>
                </div>
              ))}
            </dl>
          </>
        )}
      </div>

      {items.length > 0 && (
        <div className="card mt-5 overflow-hidden">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-5 py-3">
            <h2 className="text-[15px] font-semibold">Документы</h2>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                disabled={done.length === 0}
                onClick={() => downloadJson("results.json", resultsJson(items))}
                className="pressable inline-flex items-center gap-1.5 rounded-lg border border-line px-3 py-1.5 text-[13px] font-medium text-text-2 hover:border-line-strong hover:text-text disabled:opacity-50"
              >
                <Download aria-hidden="true" className="size-3.5" />
                results.json
              </button>
              <button
                type="button"
                disabled={finished === 0}
                onClick={() => {
                  const blob = new Blob([csv(items.filter((item) => item.state !== "queued"))], {
                    type: "text/csv;charset=utf-8",
                  });
                  const url = URL.createObjectURL(blob);
                  const link = document.createElement("a");
                  link.href = url;
                  link.download = "проверка-документов.csv";
                  link.click();
                  setTimeout(() => URL.revokeObjectURL(url), 1000);
                }}
                className="pressable inline-flex items-center gap-1.5 rounded-lg border border-line px-3 py-1.5 text-[13px] font-medium text-text-2 hover:border-line-strong hover:text-text disabled:opacity-50"
              >
                <Download aria-hidden="true" className="size-3.5" />
                Таблица CSV
              </button>
              <button
                type="button"
                disabled={running}
                onClick={() => setItems([])}
                className="pressable inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[13px] font-medium text-text-2 hover:text-danger disabled:opacity-50"
              >
                <Trash2 aria-hidden="true" className="size-3.5" />
                Очистить
              </button>
            </div>
          </div>
          <ul aria-live="polite">
            {items.map((item) => (
              <BatchRow key={item.id} item={item} />
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

function BatchRow({ item }: { item: Item }) {
  const { result } = item;
  let icon = <span className="size-2 rounded-full bg-line-strong" />;
  let title = "В очереди";
  let detail = "";
  let tone = "text-muted";
  if (item.state === "reading") {
    icon = <LoaderCircle aria-hidden="true" className="size-4 animate-spin text-brand-text" />;
    title = "Читаю…";
  } else if (item.state === "failed") {
    icon = <FileX aria-hidden="true" className="size-4 text-danger" />;
    title = "Не удалось прочитать";
    detail = item.error ?? "";
    tone = "text-danger";
  } else if (result) {
    const { analysis, check } = result;
    const missing = analysis.fields.filter((field) => !field.found).map((field) => field.label);
    if (!analysis.supported) {
      icon = <FileQuestion aria-hidden="true" className="size-4 text-text-2" />;
      title = `Другой тип: ${analysis.document_title}`;
      tone = "text-text-2";
    } else if (check.value === "document_ok") {
      icon = <CircleCheck aria-hidden="true" className="size-4 text-brand-text" />;
      title = "Все сведения на месте";
      tone = "text-brand-text";
    } else {
      icon = <CircleAlert aria-hidden="true" className="size-4 text-warn" />;
      title = "Не хватает сведений";
      detail = missing.join(", ");
      tone = "text-warn";
    }
    if (analysis.supported) {
      const sources = check.sources.map((source) => source.replace("rule:", "п. ")).join(", ");
      detail = [detail, sources && `основание: ${sources}`].filter(Boolean).join(" · ");
    }
  }
  return (
    <li className="flex items-start gap-3 border-b border-line px-5 py-3 last:border-b-0">
      <span className="mt-0.5 grid size-5 shrink-0 place-items-center">{icon}</span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-baseline justify-between gap-x-3">
          <p className="truncate text-sm font-medium" title={item.file.name}>
            {item.file.name}
          </p>
          {result && result.analysis.supported && (
            <span className="text-[12.5px] text-muted">{result.analysis.document_title}</span>
          )}
        </div>
        <p className={`mt-0.5 text-[13px] ${tone}`}>
          {title}
          {detail && <span className="text-text-2"> · {detail}</span>}
        </p>
      </div>
    </li>
  );
}
