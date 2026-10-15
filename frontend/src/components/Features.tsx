import { Building2, ShieldCheck, Smartphone } from "lucide-react";

const GROUPS = [
  {
    icon: Building2,
    title: "Для деканата",
    accent: false,
    items: [
      "Сверка по пунктам Положения с подсветкой найденных полей на снимке.",
      "Пунктир на месте незаполненной графы бланка.",
      "Ручная правка карточки с мгновенной повторной проверкой.",
      "Пакетная проверка до 60 файлов с выгрузкой results.json и таблицы для Excel.",
      "Замечания для сотрудника: даты не по порядку, справка выдана раньше срока.",
    ],
  },
  {
    icon: Smartphone,
    title: "Для студентов",
    accent: true,
    items: [
      "Снимок камерой телефона или вставка из буфера через Ctrl + V.",
      "Несколько фото читаются как страницы одного документа.",
      "Подсказка, как переснять смазанный, тёмный или мелкий снимок.",
      "Сравнение загруженного фото и выровненного листа.",
      "Вопросы голосом и Telegram-бот с тем же разбором.",
    ],
  },
  {
    icon: ShieldCheck,
    title: "Точность и защита",
    accent: false,
    items: [
      "1.000 по трём метрикам организаторов на открытом наборе и на 720 своих снимках.",
      "Файлы разбираются в памяти и никуда не передаются, внешних сервисов нет.",
      "ФИО приводится к именительному падежу, женские и мужские фамилии.",
      "Кнопка «Скрыть данные» закрашивает ФИО, номер и подпись.",
      "Ничего не выдумывает: если ответа нет, так и говорит.",
    ],
  },
];

export function Features() {
  return (
    <section id="features" className="mx-auto max-w-[1240px] scroll-mt-28 px-4 pt-28 sm:px-6">
      <div className="reveal text-center">
        <p className="inline-flex rounded-full border border-accent/35 bg-accent-soft px-5 py-1.5 text-[14px] font-semibold text-accent-text">
          Возможности сервиса
        </p>
        <h2 className="mt-5 text-[30px] font-extrabold tracking-[-0.01em] sm:text-[44px]">
          Удобно и студенту, и сотруднику
        </h2>
        <p className="mx-auto mt-3 max-w-[560px] text-[17px] text-text-2">
          Все инструменты для работы с документами в одном месте
        </p>
      </div>
      <div className="mt-12 grid gap-5 md:grid-cols-3">
        {GROUPS.map((group, index) => {
          const Icon = group.icon;
          return (
            <article
              key={group.title}
              className="reveal group relative overflow-hidden rounded-[30px] border border-line-strong bg-gradient-to-b from-brand-soft/80 to-surface/60 p-7 shadow-pop transition-[transform,box-shadow] duration-300 ease-out-strong hover:-translate-y-1.5 hover:shadow-float"
              style={{ "--i": index } as React.CSSProperties}
            >
              <span
                className={`grid size-10 place-items-center rounded-xl border ${
                  group.accent
                    ? "border-accent/35 bg-accent-soft text-accent-text"
                    : "border-brand/35 bg-surface text-brand-text"
                }`}
              >
                <Icon aria-hidden="true" className="size-5" />
              </span>
              <h3 className="mt-6 text-[22px] font-bold">{group.title}</h3>
              <ul className="mt-4 flex flex-col gap-3 text-[14.5px] leading-snug text-text-2">
                {group.items.map((item) => (
                  <li key={item} className="flex gap-2.5">
                    <span
                      aria-hidden="true"
                      className={`mt-[7px] size-1.5 shrink-0 rounded-full ${group.accent ? "bg-accent" : "bg-brand"}`}
                    />
                    {item}
                  </li>
                ))}
              </ul>
            </article>
          );
        })}
      </div>
    </section>
  );
}
