import { afterEach, describe, expect, it, vi } from "vitest";

import { analyze, ApiError, checkFile, MAX_FILE_MB } from "./api";

function file(name: string, type: string, size = 1024) {
  const blob = new File([new Uint8Array(1)], name, { type });
  Object.defineProperty(blob, "size", { value: size });
  return blob;
}

describe("checkFile", () => {
  it("accepts supported formats", () => {
    expect(checkFile(file("doc.png", "image/png"))).toBeNull();
    expect(checkFile(file("doc.jpg", "image/jpeg"))).toBeNull();
    expect(checkFile(file("doc.pdf", "application/pdf"))).toBeNull();
  });

  it("accepts a known extension when the browser gives no type", () => {
    expect(checkFile(file("scan.PDF", ""))).toBeNull();
  });

  it("rejects other formats", () => {
    expect(checkFile(file("doc.docx", "application/msword"))).toMatch(/JPG, PNG или PDF/);
    expect(checkFile(file("run.exe", "application/octet-stream"))).not.toBeNull();
  });

  it("rejects oversized and empty files", () => {
    expect(checkFile(file("big.png", "image/png", (MAX_FILE_MB + 1) * 1024 * 1024))).toMatch(/больше/);
    expect(checkFile(file("empty.png", "image/png", 0))).toMatch(/пустой/);
  });
});

describe("analyze", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("turns a server problem into a readable error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "Файл больше 15 МБ.", code: "too_large" }), {
          status: 413,
          headers: { "content-type": "application/json" },
        }),
      ),
    );
    const error = await analyze(file("a.png", "image/png")).catch((caught: unknown) => caught);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).message).toBe("Файл больше 15 МБ.");
    expect((error as ApiError).code).toBe("too_large");
  });

  it("reports a network failure without leaking details", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("ECONNREFUSED 10.0.0.5")));
    const error = (await analyze(file("a.png", "image/png")).catch((caught: unknown) => caught)) as ApiError;
    expect(error.code).toBe("network");
    expect(error.message).not.toMatch(/ECONNREFUSED/);
  });

  it("never sends cookies", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await analyze(file("a.png", "image/png"), { docType: "study_certificate", question: "Вопрос" });
    const init = fetchMock.mock.calls[0]![1] as RequestInit;
    expect(init.credentials).toBe("omit");
    const body = init.body as FormData;
    expect(body.get("doc_type")).toBe("study_certificate");
    expect(body.get("question")).toBe("Вопрос");
  });
});
