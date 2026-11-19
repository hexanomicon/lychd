import { describe, expect, it } from "vitest";
import { layoutLoom } from "$lib/graph/components/loom-layout";
import { example, project, projectLoomCanvas, validate } from "./blueprint";
describe("local blueprint document", () => {
  it("round trips nested recovery paths and projects only the requested flow", () => {
    const draft = validate(JSON.parse(JSON.stringify(example())));
    expect(project(draft, "recover").edges.map((e) => e.label)).toEqual([
      "Read access available",
      "Lookup unavailable",
    ]);
    expect(project(draft, "").nodes.every((n) => n.id !== "lookup")).toBe(true);
  });
  it("preserves surrounding phases and their wires while expanding a nested router", () => {
    const draft = example(), graph = projectLoomCanvas(draft, "dispatch");
    expect(graph.nodes.map(n => n.id)).toEqual(expect.arrayContaining(["intent", "parallel", "dispatch", "receipt", "delivery", "ledger"]));
    expect(graph.nodes.some(n => n.id === "lookup")).toBe(false);
    const layout = layoutLoom(graph);
    const outer = layout.frames.find(frame => frame.id === "parallel")!, inner = layout.frames.find(frame => frame.id === "dispatch")!;
    expect(inner.x).toBeGreaterThan(outer.x);
    expect(inner.y + inner.height).toBeLessThan(outer.y + outer.height);
    expect(layout.positions.get("receipt")!.y).toBeGreaterThan(inner.y);
    expect(layout.positions.get("review")!.y).toBeGreaterThan(outer.y + outer.height);
    expect(graph.edges.some(edge => edge.source === "parallel" && edge.target === "review")).toBe(true);
  });
  it("rejects dangling connections, cyclic containment, and malformed output schemas", () => {
    const draft = example();
    expect(() => validate({ ...draft, edges: [{ ...draft.edges[0], target: "missing" }] })).toThrow(
      "Invalid connection",
    );
    expect(() =>
      validate({
        ...draft,
        nodes: draft.nodes.map((n) => (n.id === "parallel" ? { ...n, parent: "dispatch" } : n)),
      }),
    ).toThrow("Invalid enclosing");
    expect(() => validate({ ...draft, nodes: draft.nodes.map((n) => ({ ...n, schema: "[]" })) })).toThrow(
      "output schema",
    );
  });
});

import { recipes } from "$lib/compositions/video";
import { compositionBlueprint, compositionRecipe } from "./compositions";
import { studioSession } from "./session";

describe("Atelier composition studies", () => {
  it("opens every recipe as a valid separate local blueprint with a review path", () => {
    for (const name of Object.keys(recipes)) {
      const recipe = compositionRecipe(name)!;
      const draft = validate(compositionBlueprint(recipe));
      expect(project(draft, "").edges.at(-1)?.target).toBe("review");
      expect(project(draft, "direction").edges.some(edge => edge.source === "approval" && edge.target === "plan")).toBe(true);
      expect(studioSession.buffer(recipe)).not.toBe(studioSession.buffer("sdlc"));
    }
    expect(compositionRecipe("unknown-recipe")).toBeNull();
  });
});
