import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { Analysis, Answer } from "@/lib/api";

import { CheckBanner } from "./CheckBanner";
import { FieldCard } from "./FieldCard";

const analysis: Analysis = {
  document_type: "study_certificate",
  document_title: "Справка об обучении",
  type_detected: true,
  type_confidence: 0.9,
  ocr_engine: "tesseract",
  text: "",
  width: 1000,
  height: 1400,
  quality: {},
  page_breaks: [],
  validation: { status: "missing_fields", missing_fields: ["issue_date"], sources: ["rule:3.1"] },
  fields: [
    {
      key: "student_name", label: "ФИО студента", type: "person", value: "Ёлкин Артём Игоревич",
      found: true, raw: null, box: null, confidence: 0.9, rule: "3.1",
    },
    {
      key: "study_start", label: "Начало периода обучения", type: "date", value: "2023-09-01",
      found: true, raw: null, box: null, confidence: 0.9, rule: "3.1",
    },
    {
      key: "issue_date", label: "Дата выдачи", type: "date", value: "не найдено",
      found: false, raw: null, box: null, confidence: null, rule: "3.1",
    },
    {
      key: "seal_present", label: "Печать вуза", type: "mark", value: true,
      found: true, raw: null, box: null, confidence: 0.8, rule: "3.3",
    },
  ],
};

const check: Answer = {
  question: "",
  intent: "completeness",
  answerable: true,
  value: "missing_fields",
  answer: "Не хватает: дата выдачи (п. 3.1).",
  sources: ["rule:3.1"],
  highlight: ["issue_date"],
};

describe("FieldCard", () => {
  it("shows values, human dates and missing fields", () => {
    render(<FieldCard analysis={analysis} focus={[]} onSelect={() => {}} />);
    expect(screen.getByText("Ёлкин Артём Игоревич")).toBeInTheDocument();
    expect(screen.getByText("1 сентября 2023")).toBeInTheDocument();
    expect(screen.getByText("Не найдено")).toBeInTheDocument();
    expect(screen.getByText("Есть")).toBeInTheDocument();
    expect(screen.getByText("3 из 4")).toBeInTheDocument();
  });

  it("reports the clicked field", async () => {
    const onSelect = vi.fn();
    render(<FieldCard analysis={analysis} focus={[]} onSelect={onSelect} />);
    await userEvent.click(screen.getByText("Ёлкин Артём Игоревич"));
    expect(onSelect).toHaveBeenCalledWith("student_name");
  });
});

describe("CheckBanner", () => {
  it("lists what is missing and cites the rule", () => {
    render(<CheckBanner check={check} fields={analysis.fields} onSelect={() => {}} />);
    expect(screen.getByText("В документе кое-чего не хватает")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Дата выдачи" })).toBeInTheDocument();
    expect(screen.getByText(/п\. 3\.1$/)).toBeInTheDocument();
  });

  it("says the document is complete", () => {
    const ok: Answer = { ...check, value: "document_ok", answer: "Документ содержит все сведения." };
    render(<CheckBanner check={ok} fields={analysis.fields} onSelect={() => {}} />);
    expect(screen.getByText("Все обязательные сведения на месте")).toBeInTheDocument();
  });
});
