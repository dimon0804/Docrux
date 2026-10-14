import type { Analysis, FieldValue } from "./api";

/** Поля с персональными данными: ФИО, номера документов, подпись. */
export function isPersonal(field: FieldValue) {
  return (
    field.type === "person" ||
    field.key === "document_number" ||
    (field.type === "mark" && field.key.startsWith("signature"))
  );
}

/** «Захаров Фёдор Дмитриевич» → «З••••••• Ф. Д.», «ОБ-1001» → «ОБ-••••». */
export function maskValue(field: FieldValue): string | boolean {
  if (!field.found || typeof field.value !== "string") return field.value;
  if (field.type === "person") {
    const [surname = "", ...rest] = field.value.split(/\s+/);
    const initials = rest.map((part) => `${part.charAt(0)}.`).join(" ");
    return `${surname.charAt(0)}${"•".repeat(Math.max(surname.length - 1, 3))}${initials ? ` ${initials}` : ""}`;
  }
  return field.value.replace(/\d/g, "•");
}

/** Заменяет в тексте значения персональных полей их скрытым видом. */
export function maskText(text: string, fields: FieldValue[]): string {
  let out = text;
  for (const field of fields) {
    if (!isPersonal(field) || !field.found || typeof field.value !== "string") continue;
    const masked = String(maskValue(field));
    out = out.split(field.value).join(masked);
    // Фамилия встречается и отдельно, например в ответе «Руководитель: Чижова».
    if (field.type === "person") {
      const surname = field.value.split(/\s+/)[0];
      if (surname && surname.length > 2) out = out.split(surname).join(masked.split(" ")[0]!);
    }
  }
  // «Ф. Д.» в конце предложения не должно давать две точки подряд.
  return out.replace(/(\p{L})\.\.(?!\.)/gu, "$1.");
}

/** Карточка со скрытыми персональными данными: для выгрузки и печати. */
export function maskAnalysis(analysis: Analysis): Analysis {
  return {
    ...analysis,
    text: maskText(analysis.text, analysis.fields),
    fields: analysis.fields.map((field) =>
      isPersonal(field) ? { ...field, value: maskValue(field), raw: null } : field,
    ),
  };
}
