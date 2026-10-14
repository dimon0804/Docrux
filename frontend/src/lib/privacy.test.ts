import { describe, expect, it } from "vitest";

import type { Analysis, FieldValue } from "./api";
import { maskAnalysis, maskText, maskValue } from "./privacy";

const person = {
  key: "student_name",
  type: "person",
  value: "Захаров Фёдор Дмитриевич",
  found: true,
} as FieldValue;
const number = {
  key: "document_number",
  type: "code",
  value: "ОБ-1001",
  found: true,
} as FieldValue;
const group = { key: "group", type: "code", value: "ЖР-23-3", found: true } as FieldValue;

describe("privacy", () => {
  it("keeps only the first letter of the surname and the initials", () => {
    expect(maskValue(person)).toBe("З•••••• Ф. Д.");
    expect(maskValue(number)).toBe("ОБ-••••");
  });

  it("hides names in answers, even a surname on its own", () => {
    expect(maskText("ФИО студента: Захаров Фёдор Дмитриевич.", [person])).toBe(
      "ФИО студента: З•••••• Ф. Д.",
    );
    expect(maskText("Студент Захаров подал заявление", [person])).toBe(
      "Студент З•••••• подал заявление",
    );
  });

  it("masks only personal fields of the card", () => {
    const masked = maskAnalysis({
      text: "",
      fields: [person, number, group],
    } as unknown as Analysis);
    expect(masked.fields.map((field) => field.value)).toEqual([
      "З•••••• Ф. Д.",
      "ОБ-••••",
      "ЖР-23-3",
    ]);
  });
});
