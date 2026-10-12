import type { FieldValue } from "@/lib/api";

type Props = {
  image: string;
  fields: FieldValue[];
  focus: string[];
  width: number;
  height: number;
  pageBreaks?: number[];
  onSelect: (key: string) => void;
};

const percent = (value: number) => `${(value * 100).toFixed(3)}%`;

/** Выровненный снимок документа с рамками найденных полей. */
export function DocumentViewer({
  image,
  fields,
  focus,
  width,
  height,
  pageBreaks = [],
  onSelect,
}: Props) {
  const located = fields.filter((field) => field.box);
  return (
    <figure className="card overflow-hidden p-2 sm:p-3">
      <div
        className="relative overflow-hidden rounded-xl bg-white"
        style={{ aspectRatio: width && height ? `${width} / ${height}` : undefined }}
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
      </div>
      <figcaption className="px-2 pb-1 pt-3 text-[13px] leading-relaxed text-muted">
        {pageBreaks.length > 0 ? `Страниц в документе: ${pageBreaks.length + 1}. ` : ""}
        Снимок выровнен перед чтением. Нажмите на поле в карточке, чтобы увидеть, откуда взято
        значение.
      </figcaption>
    </figure>
  );
}
