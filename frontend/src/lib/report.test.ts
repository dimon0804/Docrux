import { describe, expect, it } from "vitest";

import { describeFixes } from "@/components/DocumentViewer";

import type { Analysis } from "./api";
import { resultRecord } from "./report";

const analysis = {
  document_type: "academic_leave_application",
  fields: [
    { key: "student_name", value: "Захаров Фёдор Дмитриевич", found: true },
    { key: "application_date", value: "не найдено", found: false },
    { key: "signature_present", value: true, found: true },
  ],
  validation: {
    status: "missing_fields",
    missing_fields: ["application_date"],
    sources: ["rule:4.1"],
  },
} as unknown as Analysis;

describe("resultRecord", () => {
  it("follows the results.json layout", () => {
    const record = resultRecord("open-012.pdf", analysis, [
      {
        id: 1,
        question: "Кто принимает решение?",
        answer: {
          question: "Кто принимает решение?",
          intent: "decision",
          answerable: true,
          value: "сотрудник деканата",
          answer: "Окончательное решение принимает сотрудник деканата.",
          sources: ["rule:1.3"],
          highlight: [],
        },
        error: null,
      },
      {
        id: 2,
        question: "Вопрос без ответа сервера",
        answer: null,
        error: "сбой",
      },
    ]);
    expect(record.version).toBe("1.0");
    const [document] = record.documents;
    expect(document.document_id).toBe("open-012");
    expect(document.fields).toEqual({
      student_name: "Захаров Фёдор Дмитриевич",
      application_date: "не найдено",
      signature_present: true,
    });
    expect(document.answers).toHaveLength(1);
    expect(document.answers[0]).toMatchObject({
      question_id: "q1",
      sources: ["rule:1.3"],
    });
  });
});

describe("describeFixes", () => {
  it("says nothing about a clean scan", () => {
    expect(
      describeFixes({ skew_degrees: 0.1, upscale: 1, light_corrected: false }),
    ).toEqual([]);
  });

  it("names what was corrected on a photo", () => {
    expect(
      describeFixes({
        page_cropped: true,
        skew_degrees: -12.4,
        light_corrected: true,
        upscale: 1.5,
      }),
    ).toEqual([
      "лист найден и вырезан из фона",
      "наклон исправлен на 12°",
      "тени и неровный свет выровнены",
      "снимок увеличен в 1,5 раза",
    ]);
  });
});
