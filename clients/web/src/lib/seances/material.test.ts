import { describe, expect, it } from "vitest";
import { materialMarkdown, sourceHref, sourceSignature, type SeanceMaterial } from "./material";

const material: SeanceMaterial = {
  id: "local-1", sessionId: "session-a", kind: "Open question", note: "Investigate this",
  source: { role: "user", created_at: "2026-11-06T10:00:00Z", run_id: "run-a", state: "settled", content: "Question?\nSecond line" }
};

describe("Séance source material", () => {
  it("exports exact quotation and provenance without claiming memory admission", () => {
    const markdown = materialMarkdown("A séance", [material]);
    expect(markdown).toContain("Not admitted to memory");
    expect(markdown).toContain("/bridge/session-a?run=run-a");
    expect(markdown).toContain("> Question?\n> Second line");
    expect(markdown).toContain("2026-11-06T10:00:00Z");
    expect(markdown).toContain("Note: Investigate this");
  });
  it("keeps source matching separate from absent or invalid Run hints", () => {
    const source = { ...material.source, run_id: null };
    expect(sourceHref({ ...material, source })).toBe("/seances/session-a");
    expect(sourceHref({ ...material, source: { ...source, run_id: "bad/run" } })).toBe("/seances/session-a");
    expect(sourceSignature(source)).not.toBe(sourceSignature(material.source));
    expect(sourceSignature({ ...source, content: "Changed" })).not.toBe(sourceSignature(source));
  });
});
