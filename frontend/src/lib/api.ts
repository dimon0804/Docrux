export type Box = { x: number; y: number; w: number; h: number };

export type FieldValue = {
  key: string;
  label: string;
  type: "text" | "person" | "date" | "integer" | "code" | "mark";
  value: string | boolean;
  found: boolean;
  raw: string | null;
  box: Box | null;
  confidence: number | null;
  handwritten?: boolean;
  guess?: string | null;
  origin?: "label" | "text" | "mark" | "generic";
  rule: string;
};

export type Validation = {
  status: "document_ok" | "missing_fields" | "not_applicable";
  missing_fields: string[];
  sources: string[];
};

export type Answer = {
  question: string;
  intent: "completeness" | "decision" | "field" | "about" | "rule" | "model" | "unknown";
  answerable: boolean;
  value: string | null;
  answer: string;
  sources: string[];
  quote?: string | null;
  highlight: string[];
};

export type Analysis = {
  document_type: string;
  document_title: string;
  supported: boolean;
  type_detected: boolean;
  type_confidence: number | null;
  ocr_engine: string;
  text: string;
  fields: FieldValue[];
  validation: Validation;
  quality: Record<string, number | string | boolean>;
  page_breaks: number[];
  width: number;
  height: number;
};

export type AnalyzeResponse = {
  analysis: Analysis;
  check: Answer;
  answer: Answer | null;
  image: string;
};

export type DocType = {
  id: string;
  title: string;
  rules: string[];
  fields: { key: string; label: string; type: string; rule: string }[];
};

export type Rule = { number: string; section: string; text: string };

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const FALLBACK = "Сервис не отвечает. Проверьте соединение и попробуйте ещё раз.";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, { ...init, credentials: "omit" });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError(FALLBACK, 0, "network");
  }
  if (!response.ok) {
    let detail = FALLBACK;
    let code = "error";
    try {
      const body = (await response.json()) as { detail?: unknown; code?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
      if (typeof body.code === "string") code = body.code;
    } catch {
      // Ответ без JSON: оставляем общее сообщение.
    }
    throw new ApiError(detail, response.status, code);
  }
  return (await response.json()) as T;
}

export function fetchDocTypes(signal?: AbortSignal) {
  return request<DocType[]>("/api/doc-types", { signal });
}

export function fetchRules(signal?: AbortSignal) {
  return request<Rule[]>("/api/rules", { signal });
}

export function analyze(
  file: File,
  options: { docType?: string; question?: string; signal?: AbortSignal } = {},
) {
  const body = new FormData();
  body.append("file", file);
  if (options.docType) body.append("doc_type", options.docType);
  if (options.question) body.append("question", options.question);
  return request<AnalyzeResponse>("/api/analyze", { method: "POST", body, signal: options.signal });
}

export function ask(analysis: Analysis, question: string, signal?: AbortSignal) {
  return request<Answer>("/api/ask", {
    method: "POST",
    headers: { "content-type": "application/json" },
    signal,
    body: JSON.stringify({
      document_type: analysis.document_type,
      document_title: analysis.document_title,
      question,
      text: analysis.text.slice(0, 20000),
      fields: analysis.fields.map(({ key, value, found, label }) => ({ key, value, found, label })),
    }),
  });
}

export const MAX_FILE_MB = 15;
export const ACCEPTED_TYPES = ["image/jpeg", "image/png", "application/pdf"];

/** Проверка файла до отправки: тип и размер. Сервер проверяет всё ещё раз. */
export function checkFile(file: File): string | null {
  const byName = /\.(jpe?g|png|pdf)$/i.test(file.name);
  if (!ACCEPTED_TYPES.includes(file.type) && !byName) {
    return "Подойдёт фото или скан в JPG, PNG или PDF.";
  }
  if (file.size > MAX_FILE_MB * 1024 * 1024) {
    return `Файл больше ${MAX_FILE_MB} МБ. Сожмите его или сделайте снимок меньшего размера.`;
  }
  if (file.size === 0) return "Файл пустой.";
  return null;
}
