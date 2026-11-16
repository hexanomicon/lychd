import { describe, expect, it } from "vitest";

// Enforces the source layout rule in src/README.md: code under lib/pages/<page>/ belongs to one
// page, so no other page and no shared folder may import it. The shell composes pages and may
// import them. Tests and fixtures may cross pages because integration tests span instruments.

const sources = import.meta.glob<string>("/src/lib/**/*.{ts,js,svelte}", {
  query: "?raw",
  import: "default",
  eager: true
});

const specifierPattern = /(?:\bfrom\s*|\bimport\s*\(?\s*)["']([^"']+)["']/g;

function isTestSupport(file: string): boolean {
  return /\.test\.ts$/.test(file) || /\.fixtures\.ts$/.test(file) || file.includes("/__fixtures__/");
}

/** The page a lib file belongs to, "shell" for the app frame, or null for shared code. */
function ownerOf(file: string): string | null {
  const page = /^\/src\/lib\/pages\/([^/]+)\//.exec(file);
  if (page) return page[1]!;
  return file.startsWith("/src/lib/shell/") ? "shell" : null;
}

/** The page an import specifier points into, or null when it targets no page. */
function targetPageOf(file: string, specifier: string): string | null {
  let path: string;
  if (specifier.startsWith("$lib/")) path = `/src/lib/${specifier.slice("$lib/".length)}`;
  else if (specifier.startsWith(".")) path = new URL(specifier, `file://${file}`).pathname;
  else return null;
  return /^\/src\/lib\/pages\/([^/]+)\//.exec(path)?.[1] ?? null;
}

function boundaryViolations(files: Readonly<Record<string, string>>): string[] {
  const violations: string[] = [];
  for (const [file, source] of Object.entries(files)) {
    if (isTestSupport(file)) continue;
    const owner = ownerOf(file);
    if (owner === "shell") continue;
    for (const match of source.matchAll(specifierPattern)) {
      const target = targetPageOf(file, match[1]!);
      if (target !== null && target !== owner) {
        violations.push(`${file} imports ${match[1]} (${owner ?? "shared code"} → page ${target})`);
      }
    }
  }
  return violations.sort();
}

describe("source layout boundaries", () => {
  it("scans the page folders rather than passing on an empty set", () => {
    const pageFiles = Object.keys(sources).filter((file) => ownerOf(file) !== null && ownerOf(file) !== "shell");
    expect(pageFiles.length).toBeGreaterThan(50);
  });

  it("keeps each page's code private to that page", () => {
    expect(boundaryViolations(sources)).toEqual([]);
  });

  it("reports cross-page and shared-to-page imports, including relative ones", () => {
    expect(boundaryViolations({
      "/src/lib/pages/orb/components/A.svelte": `import B from "$lib/pages/bridge/components/B.svelte";`,
      "/src/lib/pages/orb/state/a.ts": `import { b } from "../../loom/state/b";`,
      "/src/lib/components/shared/C.svelte": `import type { D } from "$lib/pages/canvas/state/types";`,
      "/src/lib/graph/e.ts": `const f = await import("$lib/pages/nexus/state/map");`
    })).toEqual([
      "/src/lib/components/shared/C.svelte imports $lib/pages/canvas/state/types (shared code → page canvas)",
      "/src/lib/graph/e.ts imports $lib/pages/nexus/state/map (shared code → page nexus)",
      "/src/lib/pages/orb/components/A.svelte imports $lib/pages/bridge/components/B.svelte (orb → page bridge)",
      "/src/lib/pages/orb/state/a.ts imports ../../loom/state/b (orb → page loom)"
    ]);
  });

  it("allows same-page, shell, test and fixture imports", () => {
    expect(boundaryViolations({
      "/src/lib/pages/orb/components/A.svelte": `import { x } from "$lib/pages/orb/state/x"; import B from "./B.svelte";`,
      "/src/lib/shell/components/Shell.svelte": `import V from "$lib/pages/bridge/components/BridgeView.svelte";`,
      "/src/lib/pages/bridge/state/a.test.ts": `import { c } from "$lib/pages/canvas/state/engine";`,
      "/src/lib/pages/orb/state/__fixtures__/f.ts": `import { s } from "$lib/pages/seances/state/material";`,
      "/src/lib/components/shared/C.svelte": `import { api } from "$lib/api/client";`
    })).toEqual([]);
  });
});
