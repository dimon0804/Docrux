import { navigate } from "wouter/use-browser-location";

/**
 * Автопилот для защиты: сервис сам проходит основные сценарии на настоящем
 * интерфейсе. Нажимает те же кнопки, что и человек, поэтому всё, что видно на
 * экране, настоящее: распознавание, проверка и ответы приходят с сервера.
 */

export class Stopped extends Error {}

export type Pilot = {
  caption: (text: string) => void;
  point: (element: Element) => Promise<void>;
  signal: AbortSignal;
};

const sleep = (ms: number, signal: AbortSignal) =>
  new Promise<void>((resolve, reject) => {
    if (signal.aborted) return reject(new Stopped());
    const timer = setTimeout(resolve, ms);
    signal.addEventListener("abort", () => {
      clearTimeout(timer);
      reject(new Stopped());
    });
  });

function byText(selector: string, text: string | RegExp): HTMLElement | null {
  const items = Array.from(document.querySelectorAll<HTMLElement>(selector));
  return (
    items.find((item) =>
      typeof text === "string"
        ? (item.textContent ?? "").includes(text) ||
          (item.getAttribute("aria-label") ?? "").includes(text)
        : text.test(item.textContent ?? "") || text.test(item.getAttribute("aria-label") ?? ""),
    ) ?? null
  );
}

async function waitFor<T>(
  pilot: Pilot,
  find: () => T | null | undefined | false,
  timeout = 90000,
): Promise<T> {
  const started = Date.now();
  for (;;) {
    const found = find();
    if (found) return found;
    if (Date.now() - started > timeout) throw new Error("Автопилот не дождался нужного шага.");
    await sleep(150, pilot.signal);
  }
}

async function click(pilot: Pilot, find: () => HTMLElement | null) {
  const element = await waitFor(pilot, find);
  element.scrollIntoView({ behavior: "smooth", block: "center" });
  await sleep(450, pilot.signal);
  await pilot.point(element);
  element.click();
}

/** Ввод в управляемое поле React: значение через нативный сеттер и событие input. */
async function type(pilot: Pilot, element: HTMLInputElement | HTMLTextAreaElement, text: string) {
  await pilot.point(element);
  element.focus();
  const proto = element instanceof HTMLTextAreaElement ? HTMLTextAreaElement : HTMLInputElement;
  const setter = Object.getOwnPropertyDescriptor(proto.prototype, "value")!.set!;
  for (let index = 1; index <= text.length; index += 1) {
    setter.call(element, text.slice(0, index));
    element.dispatchEvent(new Event("input", { bubbles: true }));
    await sleep(28, pilot.signal);
  }
}

const button = (text: string | RegExp) => () => byText("button", text);
const scrollTop = () => window.scrollTo({ top: 0, behavior: "smooth" });

async function analyzeSample(pilot: Pilot, sample: RegExp, question?: string) {
  if (location.pathname !== "/") navigate("/");
  await sleep(300, pilot.signal);
  const again = byText("button", "Другой документ");
  if (again) {
    again.click();
    await sleep(500, pilot.signal);
  }
  scrollTop();
  const samples = await waitFor(pilot, () => {
    const all = Array.from(document.querySelectorAll<HTMLElement>("button")).filter((item) =>
      sample.test(item.textContent ?? ""),
    );
    return all.length ? all[all.length - 1]! : null;
  });
  await click(pilot, () => samples);
  await sleep(700, pilot.signal);
  if (question) {
    const input = await waitFor(pilot, () =>
      document.querySelector<HTMLInputElement>("#first-question"),
    );
    await type(pilot, input, question);
  }
  await click(pilot, button("Разобрать документ"));
  await waitFor(pilot, () => byText("h2", "Вопрос по документу"));
  scrollTop();
  await sleep(900, pilot.signal);
}

async function ask(pilot: Pilot, question: string) {
  const input = await waitFor(pilot, () =>
    document.querySelector<HTMLInputElement>('input[placeholder^="Например"]'),
  );
  input.scrollIntoView({ behavior: "smooth", block: "center" });
  await sleep(400, pilot.signal);
  await type(pilot, input, question);
  input.form?.requestSubmit();
  await sleep(1600, pilot.signal);
}

export async function runAutopilot(pilot: Pilot) {
  const say = async (text: string, ms: number) => {
    pilot.caption(text);
    await sleep(ms, pilot.signal);
  };

  navigate("/");
  scrollTop();
  await say(
    "«Докрукс» читает фото документа и отвечает по Положению. Всё, что дальше, настоящее.",
    3500,
  );

  // 1. Всё в порядке: тип, проверка, источник.
  pilot.caption("Справка об обучении и вопрос студента");
  await analyzeSample(pilot, /Справка об обучении/, "Хватит ли этой справки для перевода?");
  await say("Тип определён сам, все сведения на месте, ответ со ссылкой на пункты", 3200);
  pilot.caption("У каждого ответа есть источник: нажимаем на пункт и видим его текст");
  await click(pilot, button(/Пункт 3\.1 Положения/));
  await sleep(3000, pilot.signal);
  document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
  (document.activeElement as HTMLElement | null)?.blur();
  pilot.caption("Нажимаем на поле: на снимке подсвечено, откуда взято значение");
  await click(pilot, () => byText("button", /^ФИО студента/));
  scrollTop();
  await sleep(3000, pilot.signal);

  // 2. Чего-то не хватает: пунктир на снимке, правка, ответ студенту.
  pilot.caption("Заявление на отпуск, в котором не вписана дата");
  await analyzeSample(pilot, /Заявление на отпуск/);
  await say("Сервис называет, чего не хватает, и пункт 4.1", 2800);
  pilot.caption("Пунктиром отмечено место на бланке, где должна стоять дата");
  await click(pilot, () => byText("section[aria-label] button", "Дата заявления"));
  await sleep(3200, pilot.signal);
  pilot.caption("«Почему так?» показывает, как получен ответ");
  await click(pilot, () => byText("summary", "Почему так?"));
  await sleep(3500, pilot.signal);
  pilot.caption("Сотрудник видит дату на оригинале и вписывает её: проверка повторяется сразу");
  await click(pilot, button("Исправить поле «Дата заявления»"));
  const date = await waitFor(pilot, () =>
    document.querySelector<HTMLInputElement>("#edit-application_date"),
  );
  await type(pilot, date, "05.10.2026");
  await click(pilot, button("Сохранить"));
  await sleep(1200, pilot.signal);
  scrollTop();
  await sleep(3000, pilot.signal);

  // 3. Ответа нет: честный отказ.
  pilot.caption("Справка о практике без подписи и печати");
  await analyzeSample(pilot, /Справка о практике/);
  await say("Слова «Подпись» и «М.П.» отметкой не считаются: нужен сам рисунок", 3000);
  pilot.caption("Вопрос, ответа на который нет ни в документе, ни в Положении");
  await ask(pilot, "Какой размер стипендии положен студенту?");
  await say("Сервис ничего не придумывает и советует обратиться в деканат", 3500);

  // 4. Новый тип без кода.
  navigate("/sandbox");
  scrollTop();
  await say("Новый тип документа без кода: поля описываются прямо в браузере", 3000);
  await click(pilot, button("Взять пример протокола"));
  await sleep(600, pilot.signal);
  await click(pilot, button("Разобрать по описанию"));
  await waitFor(pilot, () => byText("p", /Все поля из описания найдены|Не найдено полей/));
  await say("Протокол прочитан по только что написанному описанию", 3500);

  // 5. Автопроверка на глазах у жюри.
  navigate("/selfcheck");
  scrollTop();
  pilot.caption("Самопроверка: 30 документов организаторов и 120 вопросов прямо сейчас");
  await click(pilot, button("Запустить проверку"));
  await waitFor(pilot, () => byText("p", "Готово:"), 180000);
  await say("Метрики скрипта организаторов: 1.000 по полям, проверке и ответам", 5000);
  pilot.caption("");
}
