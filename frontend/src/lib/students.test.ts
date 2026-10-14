import { describe, expect, it } from "vitest";

import { groupStudents } from "./students";

describe("groupStudents", () => {
  it("groups documents of one student and flags near-identical names", () => {
    const students = groupStudents([
      { file: "a.png", title: "Справка об обучении", name: "Захаров Фёдор Дмитриевич" },
      {
        file: "b.png",
        title: "Заявление на академический отпуск",
        name: "Захаров Федор Дмитриевич",
      },
      { file: "c.png", title: "Справка о практике", name: "Захарова Фёдор Дмитриевич" },
      { file: "d.png", title: "Справка о практике", name: "Петрова Анна Сергеевна" },
      { file: "e.png", title: "Справка об обучении", name: "Петрова А. С." },
    ]);
    const zakharov = students.find((student) => student.name === "Захаров Фёдор Дмитриевич")!;
    expect(zakharov.docs).toHaveLength(2);
    expect(zakharov.similar).toEqual(["Захарова Фёдор Дмитриевич"]);
    const petrova = students.find((student) => student.name === "Петрова Анна Сергеевна")!;
    expect(petrova.similar).toEqual(["Петрова А. С."]);
  });
});
