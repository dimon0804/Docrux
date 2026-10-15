import { ArrowUpFromLine, Camera, FileText, RefreshCw } from "lucide-react";
import { type DragEvent, useEffect, useId, useRef, useState } from "react";

type Props = {
  file: File | null;
  preview: string | null;
  disabled?: boolean;
  onPick: (file: File, more?: File[]) => void;
  /** Сколько ещё страниц выбрано вместе с первым файлом. */
  extraPages?: number;
  /** Разрешить выбрать несколько снимков как страницы одного документа. */
  multiple?: boolean;
};

function size(bytes: number) {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} КБ`;
  return `${(bytes / 1024 / 1024).toFixed(1).replace(".", ",")} МБ`;
}

export function Dropzone({
  file,
  preview,
  disabled,
  onPick,
  extraPages = 0,
  multiple = false,
}: Props) {
  const pickList = (list: FileList | null | undefined) => {
    const chosen = Array.from(list ?? []);
    if (chosen.length === 0) return;
    onPick(chosen[0]!, multiple ? chosen.slice(1) : []);
  };
  const inputId = useId();
  const cameraId = useId();
  const input = useRef<HTMLInputElement>(null);

  // Снимок экрана или скопированное фото можно вставить сочетанием Ctrl+V.
  useEffect(() => {
    if (disabled) return;
    const paste = (event: ClipboardEvent) => {
      const target = event.target;
      if (target instanceof Element && target.closest("input, textarea, [contenteditable]")) return;
      const pasted = Array.from(event.clipboardData?.files ?? []).find((item) =>
        /^image\/(png|jpeg)$|^application\/pdf$/.test(item.type),
      );
      if (pasted) {
        event.preventDefault();
        onPick(pasted);
      }
    };
    window.addEventListener("paste", paste);
    return () => window.removeEventListener("paste", paste);
  }, [disabled, onPick]);
  const [over, setOver] = useState(false);
  const depth = useRef(0);

  const onDrop = (event: DragEvent) => {
    event.preventDefault();
    depth.current = 0;
    setOver(false);
    if (disabled) return;
    pickList(event.dataTransfer.files);
  };

  return (
    <div
      onDragEnter={(event) => {
        event.preventDefault();
        depth.current += 1;
        setOver(true);
      }}
      onDragOver={(event) => event.preventDefault()}
      onDragLeave={() => {
        depth.current -= 1;
        if (depth.current <= 0) setOver(false);
      }}
      onDrop={onDrop}
      className={`relative rounded-[22px] border border-dashed transition-[border-color,background-color,box-shadow] duration-200 ${
        over
          ? "border-accent bg-accent-soft shadow-[0_0_0_4px_var(--accent-soft)]"
          : "border-line-strong bg-surface-2/50 hover:border-brand/60"
      }`}
    >
      <input
        ref={input}
        id={inputId}
        type="file"
        multiple={multiple}
        accept="image/jpeg,image/png,application/pdf,.jpg,.jpeg,.png,.pdf"
        className="sr-only"
        disabled={disabled}
        onChange={(event) => {
          pickList(event.target.files);
          event.target.value = "";
        }}
      />
      <input
        id={cameraId}
        type="file"
        accept="image/*"
        capture="environment"
        aria-label="Сфотографировать документ камерой"
        className="sr-only"
        disabled={disabled}
        onChange={(event) => {
          const chosen = event.target.files?.[0];
          if (chosen) onPick(chosen);
          event.target.value = "";
        }}
      />
      {file ? (
        <div className="flex items-center gap-4 p-4">
          <div className="grid size-16 shrink-0 place-items-center overflow-hidden rounded-2xl border border-line bg-white">
            {preview ? (
              <img src={preview} alt="" className="size-full object-cover object-top" />
            ) : (
              <FileText aria-hidden="true" className="size-6 text-muted" />
            )}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-[15px] font-semibold" title={file.name}>
              {file.name}
            </p>
            <p className="mono mt-1 text-[12px] text-brand-text">
              {extraPages > 0
                ? `и ещё ${extraPages} ${extraPages === 1 ? "страница" : extraPages < 5 ? "страницы" : "страниц"}`
                : size(file.size)}
            </p>
          </div>
          <label
            htmlFor={inputId}
            className="pressable inline-flex shrink-0 items-center gap-2 rounded-xl border border-line-strong bg-surface px-3.5 py-2 text-sm font-semibold text-text-2 hover:border-brand hover:text-text"
          >
            <RefreshCw aria-hidden="true" className="size-4" />
            <span className="hidden sm:inline">Заменить</span>
          </label>
        </div>
      ) : (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-3 p-4 sm:p-5">
          <label
            htmlFor={inputId}
            className={`grid size-14 shrink-0 place-items-center rounded-2xl border border-line-strong bg-gradient-to-b from-surface-3 to-surface text-brand shadow-card transition-transform duration-200 ease-out-strong ${
              over ? "-translate-y-1 scale-105" : ""
            }`}
          >
            <ArrowUpFromLine aria-hidden="true" className="size-6" />
            <span className="sr-only">Выбрать файл</span>
          </label>
          <div className="min-w-[200px] flex-1">
            <p className="text-[18px] font-bold leading-tight">Загрузить скан на проверку</p>
            <p className="mt-1 text-[13px] leading-snug text-muted">
              Перетащите файл, сделайте снимок или вставьте из буфера. JPG, PNG или PDF до 15 МБ
              {multiple ? ", несколько фото читаются как страницы одного документа" : ""}
            </p>
          </div>
          <div className="flex items-center gap-2.5">
            <span className="coarse-hide mono rounded-full border border-accent/40 bg-accent-soft px-3 py-1.5 text-[12px] font-semibold text-accent-text">
              Ctrl + V
            </span>
            <label
              htmlFor={cameraId}
              title="Сфотографировать документ"
              className="pressable grid size-12 place-items-center rounded-2xl border border-line-strong bg-surface text-brand hover:border-brand"
            >
              <Camera aria-hidden="true" className="size-5" />
              <span className="sr-only">Сфотографировать документ</span>
            </label>
            <label
              htmlFor={inputId}
              className="btn-mint pressable flex h-12 flex-col items-center justify-center rounded-2xl px-6 text-[15px] font-black uppercase leading-none tracking-[0.04em]"
            >
              Выбрать
              <span className="mt-0.5 text-[10px] font-bold tracking-[0.12em] opacity-75">
                файл
              </span>
            </label>
          </div>
        </div>
      )}
    </div>
  );
}
