import { Braces, FileSearch, LoaderCircle, RotateCcw } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { DocumentViewer } from "@/components/DocumentViewer";
import { Dropzone } from "@/components/Dropzone";
import { FieldCard } from "@/components/FieldCard";
import {
  ApiError,
  checkFile,
  fetchSandboxExample,
  type SandboxResponse,
  trySandbox,
} from "@/lib/api";

export function Sandbox() {
  const [config, setConfig] = useState("");
  const [example, setExample] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [result, setResult] = useState<SandboxResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [focus, setFocus] = useState<string[]>([]);

  useEffect(() => {
    const abort = new AbortController();
    fetchSandboxExample(abort.signal)
      .then(({ text }) => {
        setExample(text);
        setConfig((current) => current || text);
      })
      .catch(() => {});
    return () => abort.abort();
  }, []);

  useEffect(
    () => () => {
      if (preview) URL.revokeObjectURL(preview);
    },
    [preview],
  );

  const pick = (chosen: File) => {
    const problem = checkFile(chosen);
    if (problem) {
      toast.error(problem);
      return;
    }
    setFile(chosen);
    setResult(null);
    setPreview(
      /\.(jpe?g|png)$/i.test(chosen.name) || chosen.type.startsWith("image/")
        ? URL.createObjectURL(chosen)
        : null,
    );
  };

  const loadProtocol = async () => {
    const response = await fetch("/samples/protocol.png");
    if (!response.ok) return toast.error("Не удалось загрузить пример.");
    pick(new File([await response.blob()], "protocol.png", { type: "image/png" }));
  };

  const run = async () => {
    if (!file) return toast.error("Сначала выберите документ.");
    setBusy(true);
    setError(null);
    try {
      const answer = await trySandbox(file, config);
      setResult(answer);
      setFocus([]);
    } catch (problem) {
      setResult(null);
      setError(problem instanceof ApiError ? problem.message : "Не удалось разобрать документ.");
    } finally {
      setBusy(false);
    }
  };

  const missing = result?.analysis.fields.filter((field) => !field.found) ?? [];
  const select = (key: string) => setFocus(focus.length === 1 && focus[0] === key ? [] : [key]);

  return (
    <section className="mx-auto max-w-[1240px] px-4 pb-10 pt-8 sm:px-6 sm:pt-12">
      <div className="max-w-[700px]">
        <p className="inline-flex items-center gap-2 rounded-full border border-line bg-surface px-3.5 py-1.5 text-[13px] font-medium text-text-2">
          <Braces aria-hidden="true" className="size-3.5 text-brand-text" />
          Новый тип без кода
        </p>
        <h1 className="mt-4 text-[30px] font-semibold leading-tight tracking-[-0.025em] sm:text-[38px]">
          Песочница типов документов
        </h1>
        <p className="mt-3 text-[16px] leading-relaxed text-text-2">
          Каждый тип документа в сервисе описан таким текстом: поля, их названия на бланке и пункт
          правил, который их требует. Поменяйте описание, загрузите документ и посмотрите, что
          сервис найдёт. Описание действует только на этот разбор, настоящие типы сервиса не
          меняются.
        </p>
      </div>

      <div className="mt-7 grid items-start gap-5 lg:grid-cols-2">
        <div className="card flex flex-col overflow-hidden">
          <div className="flex items-center justify-between gap-3 border-b border-line px-5 py-3">
            <label htmlFor="sandbox-config" className="text-[15px] font-semibold">
              Описание типа
            </label>
            <button
              type="button"
              disabled={!example || config === example}
              onClick={() => setConfig(example)}
              className="pressable inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[13px] font-medium text-text-2 hover:text-text disabled:opacity-40"
            >
              <RotateCcw aria-hidden="true" className="size-3.5" />
              Вернуть пример
            </button>
          </div>
          <textarea
            id="sandbox-config"
            value={config}
            onChange={(event) => setConfig(event.target.value.slice(0, 8000))}
            spellCheck={false}
            autoComplete="off"
            className="scroll-thin min-h-[420px] w-full resize-y bg-surface-2/50 px-5 py-4 font-mono text-[13px] leading-relaxed text-text outline-none focus:bg-surface"
          />
          <p className="border-t border-line px-5 py-3 text-[12.5px] leading-relaxed text-muted">
            Поля: key, label, type (text, person, date, integer, code, mark), rule, aliases. Для
            отметок type: mark и mark: signature или seal. Образцы фраз из регулярных выражений в
            песочнице отключены.
          </p>
        </div>

        <div className="flex flex-col gap-4">
          <div className="card flex flex-col gap-4 p-4 sm:p-5">
            <Dropzone file={file} preview={preview} disabled={busy} onPick={pick} />
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                disabled={busy || !file}
                onClick={() => void run()}
                className="pressable inline-flex h-11 items-center gap-2 rounded-xl bg-brand-strong px-5 text-sm font-semibold text-on-brand hover:bg-brand-hover disabled:bg-surface-3 disabled:text-muted"
              >
                {busy ? (
                  <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />
                ) : (
                  <FileSearch aria-hidden="true" className="size-4" />
                )}
                Разобрать по описанию
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => void loadProtocol()}
                className="pressable inline-flex h-11 items-center rounded-xl border border-line px-4 text-sm font-medium text-text-2 hover:border-line-strong hover:text-text"
              >
                Взять пример протокола
              </button>
            </div>
            {error && (
              <p role="alert" className="rounded-xl bg-danger-soft px-4 py-3 text-sm text-danger">
                {error}
              </p>
            )}
          </div>

          {result && (
            <>
              <div
                className={`rounded-[20px] border p-5 text-sm leading-relaxed ${
                  missing.length
                    ? "border-warn-line bg-warn-soft"
                    : "border-brand/30 bg-brand-softer"
                }`}
              >
                <p className="text-[15px] font-semibold">
                  {missing.length
                    ? `Не найдено полей: ${missing.length} из ${result.analysis.fields.length}`
                    : "Все поля из описания найдены"}
                </p>
                {missing.length > 0 && (
                  <p className="mt-1 text-text-2">
                    {missing.map((field) => `${field.label} (п. ${field.rule})`).join(", ")}
                  </p>
                )}
              </div>
              <FieldCard
                analysis={result.analysis}
                title="Карточка по вашему описанию"
                focus={focus}
                onSelect={select}
              />
              <DocumentViewer
                image={result.image}
                original={preview}
                quality={result.analysis.quality}
                fields={result.analysis.fields}
                focus={focus}
                width={result.analysis.width}
                height={result.analysis.height}
                pageBreaks={result.analysis.page_breaks}
                onSelect={select}
              />
            </>
          )}
        </div>
      </div>
    </section>
  );
}
