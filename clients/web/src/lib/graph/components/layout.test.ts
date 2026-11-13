import { describe, expect, it } from "vitest";
import type { GraphProjection } from "$lib/graph/model";
import { layoutProjection } from "./layout";

function graph(ids: string[], links: [string, string][]): GraphProjection {
  return {
    identity: "exact-pattern",
    nodes: ids.map(id => ({ id, label:id, detail:id, kind:"step" })),
    edges: links.map(([source,target], i) => ({ id:String(i), source, target, label:"permits", relation:"permission" }))
  };
}

describe("semantic graph layout", () => {
  it("keeps branches distinct and rejoins after both prerequisites", () => {
    const input = graph(["intent","explore","constrain","merge"], [["intent","explore"],["intent","constrain"],["explore","merge"],["constrain","merge"]]);
    const result = layoutProjection(input);
    expect(result.get("explore")!.x).toBe(result.get("constrain")!.x);
    expect(result.get("explore")!.y).not.toBe(result.get("constrain")!.y);
    expect(result.get("merge")!.x).toBeGreaterThan(result.get("constrain")!.x);
    expect(new Set([...result.values()].map(p => `${p.x}:${p.y}`)).size).toBe(4);
  });

  it("terminates on self-loops and rebuttal cycles without changing declared edges", () => {
    const input = graph(["start","a","b","end"], [["start","a"],["a","b"],["b","a"],["a","a"],["b","end"]]);
    const before = structuredClone(input);
    input.nodes.forEach(Object.freeze); input.edges.forEach(Object.freeze);
    Object.freeze(input.nodes); Object.freeze(input.edges); Object.freeze(input);
    const result = layoutProjection(input);
    expect(result.get("a")!.x).toBe(result.get("b")!.x);
    expect(result.get("a")!.y).not.toBe(result.get("b")!.y);
    expect(result.get("end")!.x).toBeGreaterThan(result.get("a")!.x);
    expect(input).toEqual(before);
    expect(layoutProjection(input)).toEqual(result);
  });

  it("separates exact Run groups without deriving membership from geometry", () => {
    const input = graph(["a1","a2","b1","b2"], [["a1","a2"],["b1","b2"],["a2","b1"]]);
    const grouped = { ...input, nodes:input.nodes.map(node => ({ ...node, group:node.id[0] })) };
    const result = layoutProjection(grouped);
    expect(result.get("b1")!.x).toBe(result.get("a1")!.x);
    expect(result.get("b1")!.y).toBeGreaterThan(result.get("a2")!.y);
    expect(grouped.edges).toHaveLength(3);
  });

  it("ignores missing endpoints for positioning while preserving the caller's record", () => {
    const input = graph(["present"], [["missing","present"]]);
    expect(layoutProjection(input).size).toBe(1);
    expect(input.edges[0]!.source).toBe("missing");
    expect(layoutProjection(graph([],[])).size).toBe(0);
  });
});
