import { ListChecks, MessageSquareQuote, ScanLine } from "lucide-react";

const STEPS = [
  {
    icon: ScanLine,
    title: "Читает снимок",
    text: "Выравнивает фото, убирает тени и распознаёт текст. Работает со сканом, фотографией с телефона и PDF.",
  },
  {
    icon: ListChecks,
    title: "Заполняет карточку",
    text: "Раскладывает сведения по полям: ФИО, даты, номер, подпись и печать. Если поля нет, честно пишет «не найдено».",
  },
  {
    icon: MessageSquareQuote,
    title: "Отвечает со ссылкой",
    text: "Сверяет карточку с Положением и называет пункт, на котором основан ответ. Чего нет в источниках, того нет и в ответе.",
  },
];

export function HowItWorks() {
  return (
    <section id="how" className="mx-auto max-w-[1240px] scroll-mt-24 px-4 pt-20 sm:px-6 sm:pt-28">
      <h2 className="text-[26px] font-semibold tracking-[-0.02em] sm:text-[34px]">
        Три шага в одном проходе
      </h2>
      <p className="mt-2 max-w-[560px] text-[17px] leading-relaxed text-text-2">
        От фотографии до ответа проходит несколько секунд. Все вычисления идут на сервере
        сервиса, без обращений к внешним нейросетям.
      </p>
      <ol className="mt-8 grid gap-4 md:grid-cols-3">
        {STEPS.map((step, index) => (
          <li key={step.title} className="card p-6">
            <div className="flex items-center justify-between">
              <span className="grid size-11 place-items-center rounded-xl bg-brand-soft text-brand-text">
                <step.icon aria-hidden="true" className="size-[22px]" />
              </span>
              <span className="tabular text-sm font-semibold text-muted">0{index + 1}</span>
            </div>
            <h3 className="mt-5 text-lg font-semibold tracking-[-0.01em]">{step.title}</h3>
            <p className="mt-2 text-[15px] leading-relaxed text-text-2">{step.text}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}
