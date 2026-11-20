import { describe, expect, it } from "vitest";
import { DEFAULT_INK, inkPaint } from "./ink";

describe("inkPaint", () => {
  it("paints the stored default ink with the theme ink role", () => {
    expect(inkPaint(DEFAULT_INK)).toBe("var(--color-ink-default)");
    expect(inkPaint(DEFAULT_INK.toUpperCase())).toBe("var(--color-ink-default)");
  });

  it("renders any other recorded colour unchanged", () => {
    expect(inkPaint("#3a7bd5")).toBe("#3a7bd5");
  });
});
