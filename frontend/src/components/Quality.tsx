import { Play } from "lucide-react";
import { Link } from "wouter";

/**
 * Цифры из README, раздел «Качество». Все получены распознаванием изображений
 * скриптами из репозитория; при новом замере обновляются здесь и в README.
 */
const TILES = [
  {
    value: "1.0",
    label: "по всем трём метрикам автопроверки",
    text: "Открытый набор организаторов: 30 документов, 120 вопросов. Поля, проверка комплектности и ответы со ссылками совпадают с эталоном.",
  },
  {
    value: "90",
    label: "своих документов вдобавок",
    text: "Бланки с другими фамилиями, вузами, шифрами групп и номерами, тоже 1.0. Сервис читает документ, а не помнит открытый набор.",
  },
  {
    value: "630",
    label: "испорченных снимков",
    text: "Наклон до 30°, тень, блик, низкое разрешение, сжатие, смаз, фото листа на столе. Все семь видов порчи дают 1.0.",
  },
  {
    value: "42 из 42",
    label: "документа свободной формы",
    text: "Справки сплошным текстом без бланка: тип определён у всех, поля найдены в тексте, фамилия приведена к именительному падежу.",
  },
];

export function Quality() {
  return (
    <section
      id="quality"
      className="mx-auto max-w-[1240px] scroll-mt-28 px-4 pt-20 sm:px-6 sm:pt-28"
    >
      <p className="inline-flex rounded-full border border-accent/35 bg-accent-soft text-accent-text px-4 py-1 text-[13px] font-semibold">
        Качество
      </p>
      <h2 className="mt-4 text-[30px] font-extrabold sm:text-[44px]">
        Проверено на сотнях документов
      </h2>
      <p className="mt-2 max-w-[600px] text-[17px] leading-relaxed text-text-2">
        Качество мерили скриптом организаторов после каждого изменения. В наших тестах на вопросы,
        ответа на которые нет ни в документе, ни в Положении, сервис ни разу не ответил выдумкой.
      </p>
      <Link
        href="/selfcheck"
        className="pressable mt-5 inline-flex items-center gap-2 rounded-xl border border-line bg-surface px-4 py-2.5 text-sm font-semibold hover:border-line-strong"
      >
        <Play aria-hidden="true" className="size-4 text-brand-text" />
        Проверить сейчас на открытом наборе
      </Link>
      <ul className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {TILES.map((tile) => (
          <li key={tile.label} className="card flex flex-col p-6">
            <p className="tabular text-[34px] font-semibold leading-none tracking-[-0.03em] text-brand-text">
              {tile.value}
            </p>
            <p className="mt-2 text-[15px] font-semibold">{tile.label}</p>
            <p className="mt-2 text-[14px] leading-relaxed text-text-2">{tile.text}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
