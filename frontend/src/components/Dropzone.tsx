import { FileText, ImageUp, RefreshCw } from "lucide-react";
import { type DragEvent, useId, useRef, useState } from "react";

type Props = {
  file: File | null;
  preview: string | null;
  disabled?: boolean;
  onPick: (file: File) => void;
};

function size(bytes: number) {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} КБ`;
  return `${(bytes / 1024 / 1024).toFixed(1).replace(".", ",")} МБ`;
}

export function Dropzone({ file, preview, disabled, onPick }: Props) {
  const inputId = useId();
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const depth = useRef(0);

  const onDrop = (event: DragEvent) => {
    event.preventDefault();
    depth.current = 0;
    setOver(false);
    if (disabled) return;
    const dropped = event.dataTransfer.files[0];
    if (dropped) onPick(dropped);
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
      className={`relative rounded-2xl border-2 border-dashed transition-[border-color,background-color] duration-200 ${
        over
          ? "border-brand bg-brand-softer"
          : "border-line-strong bg-surface-2/60 hover:border-brand/60"
      }`}
    >
      <input
        ref={input}
        id={inputId}
        type="file"
        accept="image/jpeg,image/png,application/pdf,.jpg,.jpeg,.png,.pdf"
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
          <div className="grid size-16 shrink-0 place-items-center overflow-hidden rounded-xl border border-line bg-surface">
            {preview ? (
              <img src={preview} alt="" className="size-full object-cover object-top" />
            ) : (
              <FileText aria-hidden="true" className="size-6 text-muted" />
            )}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium" title={file.name}>
              {file.name}
            </p>
            <p className="mt-0.5 text-[13px] text-muted">{size(file.size)}</p>
          </div>
          <label
            htmlFor={inputId}
            className="pressable inline-flex shrink-0 items-center gap-2 rounded-xl border border-line bg-surface px-3.5 py-2 text-sm font-medium text-text-2 hover:border-line-strong hover:text-text"
          >
            <RefreshCw aria-hidden="true" className="size-4" />
            <span className="hidden sm:inline">Заменить</span>
          </label>
        </div>
      ) : (
        <label
          htmlFor={inputId}
          className="flex flex-col items-center gap-3 px-6 py-10 text-center sm:py-12"
        >
          <span
            className={`grid size-12 place-items-center rounded-2xl bg-brand-soft text-brand-text transition-transform duration-200 ease-out-strong ${
              over ? "-translate-y-1 scale-105" : ""
            }`}
          >
            <ImageUp aria-hidden="true" className="size-6" />
          </span>
          <span>
            <span className="block text-[15px] font-semibold">
              Перетащите фото документа сюда
            </span>
            <span className="mt-1 block text-sm text-muted">
              или <span className="font-medium text-brand-text">выберите файл</span>. JPG, PNG
              или PDF до 15 МБ
            </span>
          </span>
        </label>
      )}
    </div>
  );
}
