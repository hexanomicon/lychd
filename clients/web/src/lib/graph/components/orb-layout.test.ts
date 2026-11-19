import { describe, expect, it } from "vitest";
import type { GraphNode, GraphProjection } from "$lib/graph/model";
import { createOrbLayoutMemory, layoutOrbProjection, orbTerritories } from "./orb-layout";

const node = (id: string, group = "run-a", kind = "step"): GraphNode => ({ id, group, kind, label: id, detail: id });
const graph = (nodes: readonly GraphNode[]): GraphProjection => ({ identity: "orb-field", nodes, edges: [] });

describe("Orb static spatial presentation", () => {
  it("preserves Run and station positions across new first-page Runs, filtering, selection input and streams", () => {
    const memory = createOrbLayoutMemory();
    const original = graph([node("run-a", "run-a", "run"), node("station-a")]);
    const first = layoutOrbProjection(original, memory);
    const update = graph([node("new-run", "new-run", "run"), ...original.nodes, node("new-record", "run-a", "event")]);
    const streamed = layoutOrbProjection(update, memory);
    for (const [id, point] of first) expect(streamed.get(id)).toEqual(point);
    layoutOrbProjection(graph([node("other", "other", "run")]), memory);
    expect(layoutOrbProjection(original, memory)).toEqual(first);
    expect(layoutOrbProjection({ ...original, nodes: original.nodes.map(item => ({ ...item, attention: "cursor" })) }, memory)).toEqual(first);
  });

  it("preserves dragged positions and folded member positions without mutating semantic input", () => {
    const memory = createOrbLayoutMemory();
    const expanded = graph([node("run-a", "run-a", "run"), node("station-a"), node("record-a", "run-a", "event")]);
    expanded.nodes.forEach(Object.freeze); Object.freeze(expanded.nodes); Object.freeze(expanded);
    const before = structuredClone(expanded);
    const positions = layoutOrbProjection(expanded, memory);
    const dragged = { x: 717, y: -91 };
    memory.positions.set("station-a", dragged);
    const folded = graph([{ ...node("run-a", "run-a", "run"), members: ["station-a", "record-a"] }]);
    expect(layoutOrbProjection(folded, memory).get("run-a")).toEqual(positions.get("run-a"));
    const restored = layoutOrbProjection(expanded, memory);
    expect(restored.get("station-a")).toEqual(dragged);
    expect(restored.get("record-a")).toEqual(positions.get("record-a"));
    expect(expanded).toEqual(before);
  });

  it("places Animator selections within the recorded Run territory", () => {
    const input = graph([node("run-a", "run-a", "run"), node("run-b", "run-b", "run"), node("run-c", "run-c", "run"),
      node("selection", "run-a", "animator")]);
    const positions = layoutOrbProjection(input, createOrbLayoutMemory());
    const selection = positions.get("selection")!, run = positions.get("run-a")!;
    expect(Math.hypot(selection.x - run.x, selection.y - run.y)).toBeLessThan(400);
    expect(positions.get("run-a")!.y).not.toBe(positions.get("run-b")!.y);
    expect(positions.get("run-b")!.x).not.toBe(positions.get("run-c")!.x);
  });

  it("reserves separated hex cells with a shallow first-three Run row", () => {
    const input = graph(Array.from({ length: 19 }, (_, index) => node(`run-${index}`, `run-${index}`, "run")));
    const positions = layoutOrbProjection(input, createOrbLayoutMemory());
    const first = [0, 1, 2].map(index => positions.get(`run-${index}`)!);
    expect(first[1]!.x - first[0]!.x).toBeGreaterThan(950);
    expect(first[0]!.x - first[2]!.x).toBeGreaterThan(950);
    expect(Math.max(...first.map(point => point.y)) - Math.min(...first.map(point => point.y))).toBeLessThan(30);
    const cells = [...positions.values()];
    for (let a = 0; a < cells.length; a++) for (let b = a + 1; b < cells.length; b++) {
      expect(Math.hypot(cells[a]!.x - cells[b]!.x, cells[a]!.y - cells[b]!.y)).toBeGreaterThan(950);
    }
  });

  it("only decorates supplied Run membership and keeps geometry finite for a bounded busy Run", () => {
    const nodes = [node("run-a", "run-a", "run"), ...Array.from({ length: 70 }, (_, index) => node(`record:${index}`, "run-a", "event")),
      node("external", "unknown-group"), node("animator:one", "animators", "animator")];
    const input = graph(nodes);
    const points = layoutOrbProjection(input, createOrbLayoutMemory());
    expect(points.size).toBe(nodes.length);
    expect(new Set([...points.values()].map(point => `${point.x}:${point.y}`)).size).toBe(nodes.length);
    expect([...points.values()].every(point => Number.isFinite(point.x) && Number.isFinite(point.y))).toBe(true);
    const territories = orbTerritories(input, points);
    expect(territories).toHaveLength(1);
    expect(territories[0]!.id).toBe("run-a");
    expect(territories[0]!.path).not.toMatch(/NaN|Infinity/);
    expect(orbTerritories(graph([node("run-a", "run-a", "run")]), points)).toEqual([]);
  });
});
