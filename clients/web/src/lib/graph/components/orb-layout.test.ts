import { describe, expect, it } from "vitest";
import type { GraphNode, GraphProjection } from "$lib/graph/model";
import { createOrbLayoutMemory, layoutOrbProjection, orbNodeWidth } from "./orb-layout";

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

  it("lays out parallel Runs as adjacent lanes with aligned headers", () => {
    const members = Array.from({ length: 19 }, (_, index) => node(`run-${index}`, `run-${index}`, "run"));
    const positions = layoutOrbProjection(graph(members), createOrbLayoutMemory());
    const first = positions.get("run-0")!;
    for (const [index, member] of members.entries()) {
      const current = positions.get(member.id)!;
      expect(current.y).toBe(first.y);
      if (index) expect(current.x - positions.get(members[index - 1]!.id)!.x).toBeGreaterThan(orbNodeWidth(member));
    }
  });

  it("places the entry below its actual Run and an Animator beside its dispatch, even when the Pattern loops", () => {
    const run = node("header", "run-a", "run"), entry = { ...node("entry"), entry: true };
    const dispatch = node("dispatch", "run-a", "dispatch"), animator = node("choice", "run-a", "animator");
    const input = { ...graph([run, animator, dispatch, entry]), edges: [
      { id: "membership", source: run.id, target: entry.id, relation: "contains", label: "Run lens" },
      { id: "route", source: entry.id, target: dispatch.id, relation: "permission", label: "Declared permission" },
      { id: "choice", source: dispatch.id, target: animator.id, relation: "selection", label: "Recorded selection" },
      { id: "loop", source: dispatch.id, target: entry.id, relation: "permission", label: "Revisit" }
    ] } satisfies GraphProjection;
    const points = layoutOrbProjection(input, createOrbLayoutMemory());
    expect(points.get(run.id)!.x + orbNodeWidth(run) / 2).toEqual(points.get(entry.id)!.x + orbNodeWidth(entry) / 2);
    expect(points.get(run.id)!.y).toBeLessThan(points.get(entry.id)!.y);
    expect(points.get(entry.id)!.y).toBeLessThan(points.get(dispatch.id)!.y);
    expect(points.get(animator.id)!.x).not.toBe(points.get(dispatch.id)!.x);
    expect(points.get(animator.id)!.y).toBeGreaterThan(points.get(dispatch.id)!.y);
  });

  it("keeps geometry distinct and finite for disconnected records and uncorrelated components", () => {
    const nodes = [node("run-a", "run-a", "run"), ...Array.from({ length: 70 }, (_, index) => node(`record:${index}`, "run-a", "event")),
      node("external", "unknown-group"), node("animator:one", "animators", "animator")];
    const points = layoutOrbProjection(graph(nodes), createOrbLayoutMemory());
    expect(points.size).toBe(nodes.length);
    expect(new Set([...points.values()].map(point => `${point.x}:${point.y}`)).size).toBe(nodes.length);
    expect([...points.values()].every(point => Number.isFinite(point.x) && Number.isFinite(point.y))).toBe(true);
  });
});
