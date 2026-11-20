import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { accentColor, type GraphAccent } from "./accent";

// Vitest runs from the package root and stubs CSS imports, so read the theme from disk.
const theme = readFileSync("src/styles/themes/dark.css", "utf8");

describe("accentColor", () => {
  it("defaults to the interactive role", () => {
    expect(accentColor()).toBe("var(--color-interactive)");
  });

  it("resolves every accent to a role the canonical theme defines", () => {
    const accents: GraphAccent[] = ["rune", "primary", "frost", "lich", "heat"];
    for (const accent of accents) {
      const role = accentColor(accent).slice(4, -1);
      expect(theme).toContain(`${role}:`);
    }
  });
});
