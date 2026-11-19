import { describe, expect, it } from "vitest";
import { example, project, validate } from "./blueprint";
describe("local blueprint document", () => {
  it("round trips nested recovery paths and projects only the requested flow", () => {
    const draft = validate(JSON.parse(JSON.stringify(example())));
    expect(project(draft, "recover").edges.map((e) => e.label)).toEqual([
      "Read access available",
      "Lookup unavailable",
    ]);
    expect(project(draft, "").nodes.every((n) => n.id !== "lookup")).toBe(true);
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
