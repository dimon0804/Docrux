import { describe, expect, it } from "vitest";

import { csv } from "./Batch";

describe("csv", () => {
  it("does not let Excel run a cell as a formula", () => {
    const item = {
      id: 1,
      file: { name: '=HYPERLINK("http://evil/";"x").png' },
      state: "done",
      error: null,
      result: {
        analysis: {
          supported: false,
          document_title: "+cmd|' /C calc'!A0",
          fields: [],
        },
        check: { value: null, sources: [] },
      },
    };
    const text = csv([item] as never);
    expect(text).toContain(`"'=HYPERLINK(""http://evil/"";""x"").png"`);
    expect(text).toContain(`"'+cmd|' /C calc'!A0"`);
    expect(text).not.toMatch(/;"=|;"\+/);
  });
});

describe("resultsJson", () => {
  it("gives files with the same name different document ids", async () => {
    const { resultsJson } = await import("./Batch");
    const result = {
      analysis: { document_type: "study_certificate", fields: [], validation: {} },
      check: { answerable: true, value: "document_ok", answer: "", sources: [] },
    };
    const items = ["scan.pdf", "scan.pdf", "other.png"].map((name, id) => ({
      id,
      file: { name },
      state: "done",
      error: null,
      result,
    }));
    const ids = resultsJson(items as never).documents.map((doc) => doc.document_id);
    expect(ids).toEqual(["scan", "scan-2", "other"]);
  });
});
