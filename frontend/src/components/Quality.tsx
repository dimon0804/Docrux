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
    text: "Наклон до 30°, тень, блик, низкое разрешение, сжатие, смаз, фото листа на столе. Шесть видов порчи из семи дают 1.0.",
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
      className="mx-auto max-w-[1240px] scroll-mt-24 px-4 pt-20 sm:px-6 sm:pt-28"
    >
      <h2 className="text-[26px] font-semibold tracking-[-0.02em] sm:text-[34px]">
        Проверено на сотнях документов
      </h2>
      <p className="mt-2 max-w-[600px] text-[17px] leading-relaxed text-text-2">
        Качество мерили скриптом организаторов после каждого изменения. В наших тестах на вопросы,
        ответа на которые нет ни в документе, ни в Положении, сервис ни разу не ответил выдумкой.
      </p>
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
