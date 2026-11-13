import { describe, expect, it, vi } from "vitest";
import { MarkerType, type Edge } from "@xyflow/svelte";
import { reconcileEdges, reconcileNodes, type RenderNode } from "./flow-drafts";

const select = vi.fn();
function node(id = "step-a"): RenderNode {
  return { id, type: "orb", position: { x: 120, y: 40 }, width: 128, height: 84,
    data: { semantic: { id, label: id, detail: "2 loaded", kind: "step", members: ["event-1", "event-2"] }, select },
    selected: false, draggable: true, selectable: false };
}
function edge(): Edge {
  return { id: "a-b", source: "step-a", target: "step-b", type: "semantic", label: "permits",
    data: { relation: "permission", presentation: "diagram" }, markerEnd: { type: MarkerType.ArrowClosed, color: "blue" } };
}

describe("shared renderer draft reconciliation", () => {
  it("keeps the measured nodes, payloads and array through semantically identical replacements", () => {
    const original = { ...node(), measured: { width: 128, height: 84 }, dragging: true };
    const drafts = [original];
    const next = reconcileNodes(drafts, [node()]);
    expect(next).toBe(drafts);
    expect(next[0]?.measured).toBe(original.measured);
    expect(next[0]?.dragging).toBe(true);
  });

  it("updates corrected evidence and selection without invalidating measured handles or adjacent nodes", () => {
    const first = { ...node(), measured: { width: 128, height: 84 } };
    const other = { ...node("step-b"), measured: { width: 128, height: 84 } };
    const incoming = node();
    incoming.selected = true;
    incoming.data = { ...incoming.data, semantic: { ...incoming.data.semantic, detail: "Corrected retained evidence", members: ["event-2", "event-3"] } };
    const next = reconcileNodes([first, other], [incoming, node("step-b")]);
    expect(next[0]).not.toBe(first);
    expect(next[0]?.data.semantic.detail).toBe("Corrected retained evidence");
    expect(next[0]?.data.semantic.members).toEqual(["event-2", "event-3"]);
    expect(next[0]?.selected).toBe(true);
    expect(next[0]?.measured).toBe(first.measured);
    expect(next[0]?.position).toBe(first.position);
    expect(next[1]).toBe(other);
    expect(first.selected).toBe(false);
  });

  it("takes deliberate position changes, drops removed nodes and remeasures changed geometry", () => {
    const original = { ...node(), measured: { width: 128, height: 84 } };
    const moved = { ...node(), position: { x: 350, y: 210 } };
    expect(reconcileNodes([original], [moved])[0]).toMatchObject({ position: moved.position, measured: original.measured });
    const resized = { ...node(), width: 280 };
    expect(reconcileNodes([original], [resized])[0]?.measured).toBeUndefined();
    expect(reconcileNodes([original], [])).toEqual([]);
    expect(reconcileNodes([], [node()])[0]?.measured).toBeUndefined();
  });

  it("keeps identical declared edges and replaces corrected relation or endpoint data", () => {
    const first = edge();
    const drafts = [first];
    expect(reconcileEdges(drafts, [edge()])).toBe(drafts);
    const correction = { ...edge(), target: "step-c", data: { relation: "selection", presentation: "orb" }, markerEnd: undefined };
    const next = reconcileEdges(drafts, [correction]);
    expect(next[0]).toEqual(correction);
    expect(next[0]).not.toBe(first);
    expect(reconcileEdges(drafts, [])).toEqual([]);
  });
});
