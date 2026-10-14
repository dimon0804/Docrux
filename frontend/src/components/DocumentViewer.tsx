import { useState } from "react";

import type { FieldValue } from "@/lib/api";
import { isPersonal } from "@/lib/privacy";

type Props = {
  image: string;
  original?: string | null;
  quality?: Record<string, number | string | boolean>;
  fields: FieldValue[];
  focus: string[];
  width: number;
  height: number;
  pageBreaks?: number[];
  onSelect: (key: string) => void;
  /** Закрасить на снимке ФИО, номер и подпись. */
  masked?: boolean;
};

const percent = (value: number) => `${(value * 100).toFixed(3)}%`;

/** Что сервис сделал со снимком перед чтением, человеческими словами. */
export function describeFixes(quality: Record<string, number | string | boolean> = {}): string[] {
  const fixes: string[] = [];
  if (quality.page_cropped) fixes.push("лист найден и вырезан из фона");
  const skew = Math.abs(Number(quality.skew_degrees) || 0);
  if (skew >= 0.5)
    fixes.push(`наклон исправлен на ${skew.toFixed(skew >= 10 ? 0 : 1).replace(".", ",")}°`);
  if (quality.light_corrected) fixes.push("тени и неровный свет выровнены");
  const upscale = Number(quality.upscale) || 1;
  if (upscale > 1.05) fixes.push(`снимок увеличен в ${upscale.toFixed(1).replace(".", ",")} раза`);
  return fixes;
}

/** Выровненный снимок документа с рамками найденных полей. */
export function DocumentViewer({
  image,
  original = null,
  quality,
  fields,
  focus,
  width,
  height,
  pageBreaks = [],
  onSelect,
  masked = false,
}: Props) {
  const [showOriginal, setShowOriginal] = useState(false);
  // Пустое поле рисуется одной пунктирной рамкой, даже если у него есть и зона почерка.
  const empty = fields.filter((field) => !field.found && field.hint_box);
  const located = fields.filter((field) => field.box && !(!field.found && field.hint_box));
  const fixes = describeFixes(quality);
  // Исходное фото закрасить нельзя: координаты полей есть только у выровненного листа.
  const raw = showOriginal && original && !masked;
  const hidden = masked ? fields.filter((field) => field.box && isPersonal(field)) : [];
  return (
    <figure className="card overflow-hidden p-2 sm:p-3">
      {original && !masked && (
        <div
          role="group"
          aria-label="Какой снимок показать"
          className="no-print mb-2 grid grid-cols-2 gap-1 rounded-xl bg-surface-2 p-1 text-[13px] font-medium"
        >
          {[
            { value: false, label: "После выравнивания" },
            { value: true, label: "Как загружен" },
          ].map((option) => (
            <button
              key={option.label}
              type="button"
              aria-pressed={showOriginal === option.value}
              onClick={() => setShowOriginal(option.value)}
              className={`pressable rounded-lg px-3 py-1.5 ${
                showOriginal === option.value
                  ? "bg-surface text-text shadow-sm"
                  : "text-text-2 hover:text-text"
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      )}
      {raw ? (
        <div className="overflow-hidden rounded-xl bg-surface-2">
          <img
            src={original}
            alt="Документ в том виде, в каком его загрузили"
            className="mx-auto block max-h-[78vh] w-auto max-w-full select-none object-contain"
            draggable={false}
          />
        </div>
      ) : (
        <div
          className="relative overflow-hidden rounded-xl bg-white"
          style={{
            aspectRatio: width && height ? `${width} / ${height}` : undefined,
          }}
        >
          <img
            src={image}
            alt="Загруженный документ после выравнивания"
            className="block size-full select-none object-contain"
            draggable={false}
          />
          {pageBreaks.map((position) => (
            <span
              key={position}
              aria-hidden="true"
              className="absolute inset-x-0 h-0 border-t-2 border-dashed border-[#c9ccd6]"
              style={{ top: percent(position) }}
            />
          ))}
          {located.map((field) => {
            const box = field.box!;
            const active = focus.includes(field.key);
            const pad = 0.004;
            return (
              <button
                key={field.key}
                type="button"
                onClick={() => onSelect(field.key)}
                aria-label={`Поле «${field.label}» на снимке`}
                aria-pressed={active}
                title={field.label}
                className={`absolute rounded-md transition-[background-color,box-shadow,opacity] duration-200 ease-out ${
                  active
                    ? "z-10 bg-brand/20 shadow-[0_0_0_2px_var(--brand),0_0_0_6px_rgb(80_184_72/0.22)]"
                    : "bg-transparent opacity-0 shadow-[0_0_0_1.5px_rgb(80_184_72/0.55)] hover:bg-brand/10 hover:opacity-100 focus-visible:opacity-100"
                }`}
                style={{
                  left: percent(Math.max(0, box.x - pad)),
                  top: percent(Math.max(0, box.y - pad)),
                  width: percent(box.w + pad * 2),
                  height: percent(box.h + pad * 2),
                }}
              />
            );
          })}
          {hidden.map((field) => {
            const box = field.box!;
            const pad = 0.004;
            return (
              <span
                key={`mask-${field.key}`}
                aria-hidden="true"
                className="pointer-events-none absolute z-20 rounded-[3px] bg-[#1b1f2a]"
                style={{
                  left: percent(Math.max(0, box.x - pad)),
                  top: percent(Math.max(0, box.y - pad)),
                  width: percent(box.w + pad * 2),
                  height: percent(box.h + pad * 2),
                }}
              />
            );
          })}
          {/* Пустые поля: место на бланке, где сведения должны были быть. */}
          {empty.map((field) => {
            const box = field.hint_box!;
            const active = focus.includes(field.key);
            return (
              <button
                key={field.key}
                type="button"
                onClick={() => onSelect(field.key)}
                aria-label={`Здесь должно быть поле «${field.label}», оно не заполнено`}
                aria-pressed={active}
                title={`Не найдено: ${field.label}`}
                className={`absolute rounded-md border-2 border-dashed transition-[background-color,border-color] duration-200 ease-out ${
                  active
                    ? "z-10 border-warn bg-warn/15"
                    : "border-warn/55 bg-warn/5 hover:border-warn hover:bg-warn/10"
                }`}
                style={{
                  left: percent(box.x),
                  top: percent(box.y),
                  width: percent(box.w),
                  height: percent(box.h),
                }}
              >
                {active && focus.length === 1 && (
                  <span className="absolute -top-7 left-0 whitespace-nowrap rounded-md bg-warn px-2 py-0.5 text-[11.5px] font-semibold text-white dark:text-[#1a1304]">
                    Нет: {field.label}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      )}
      <figcaption className="px-2 pb-1 pt-3 text-[13px] leading-relaxed text-muted">
        {pageBreaks.length > 0 ? `Страниц в документе: ${pageBreaks.length + 1}. ` : ""}
        {fixes.length > 0
          ? `Перед чтением ${fixes.join(", ")}. `
          : "Снимок выровнен перед чтением. "}
        Нажмите на поле в карточке, чтобы увидеть, откуда взято значение.
        {empty.length > 0 ? " Пунктиром отмечены места, где не хватает сведений." : ""}
      </figcaption>
    </figure>
  );
}
