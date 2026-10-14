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
