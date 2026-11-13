import { describe, expect, it } from "vitest";
import { runtimeEvent, runtimeSnapshot } from "$lib/pages/orb/state/__fixtures__/runtime";
import { activityKey, advanceRuntimeHighWater, projectRuntime, receivedRuntimeEvents, RUNTIME_NODE_LIMIT, RUNTIME_SOURCE_HISTORY_LIMIT } from "./runtime-projection";
import { runtimeIcon } from "./icons";

describe("runtime projection", () => {
  it("keeps uninstrumented components and actual non-Run attempts separate from declarations", () => {
    const snapshot = runtimeSnapshot();
    const graph = projectRuntime(snapshot);
    expect(graph.projection.nodes).toHaveLength(4);
    expect(graph.projection.nodes.find(node => node.label === "resource")?.detail).toContain("activity unavailable");
    expect(graph.projection.nodes.find(node => node.kind === "call attempt")?.state).toBe("outcome unknown");
    expect(graph.projection.edges.map(edge => edge.relation)).toEqual(["declared", "activity", "activity"]);
    expect(snapshot.activities[0]!.run_id).toBeNull();
  });
  it("preserves two attempts from one station and separate transport and effect results", () => {
    const events = [runtimeEvent(), runtimeEvent(2, { kind: "transport_result", phase: "succeeded", http_status: 200 }),
      runtimeEvent(3, { attempt_id: "attempt-b", station_attempt_id: "same-station" })];
    const graph = projectRuntime(runtimeSnapshot(events));
    expect(graph.projection.nodes.filter(node => node.kind === "call attempt")).toHaveLength(2);
    expect([...graph.selections.values()].filter(item => "activities" in item).map(item => "activities" in item && item.activities.length)).toEqual([2, 1]);
    expect(events[1]!.effect_outcome).toBeNull();
  });
  it("highlights only new events in a continuously observed same-source generation", () => {
    const old = runtimeSnapshot();
    const next = runtimeSnapshot([runtimeEvent(), runtimeEvent(2)]);
    expect([...receivedRuntimeEvents(old, next, true)]).toEqual([activityKey(next.activities[1]!)]);
    expect(receivedRuntimeEvents(null, next, true).size).toBe(0);
    expect(receivedRuntimeEvents(old, next, false).size).toBe(0);
    expect(receivedRuntimeEvents(next, next, true).size).toBe(0);
    expect(receivedRuntimeEvents(next, old, true).size).toBe(0);
    const restarted = runtimeSnapshot([runtimeEvent(3, { source_generation: "generation-b" })]);
    expect(receivedRuntimeEvents(old, restarted, true).size).toBe(0);
    const stale = { ...old, sources: old.sources.map(source => ({ ...source, status: "stale" as const })) };
    expect(receivedRuntimeEvents(stale, next, true).size).toBe(0);
  });
  it("bounds renderer nodes and edges and reports omissions", () => {
    const snapshot = runtimeSnapshot(Array.from({ length: 300 }, (_, i) => runtimeEvent(i + 1, { attempt_id: `attempt-${i}` })));
    const graph = projectRuntime(snapshot);
    expect(graph.projection.nodes).toHaveLength(RUNTIME_NODE_LIMIT);
    expect(graph.omittedNodes).toBe(47);
    const ids = new Set(graph.projection.nodes.map(node => node.id));
    expect(graph.projection.edges.every(edge => ids.has(edge.source) && ids.has(edge.target))).toBe(true);
    expect(graph.selections.size).toBe(RUNTIME_NODE_LIMIT);
  });
  it("resolves only packaged icons and never fetches source-provided locations", () => {
    expect(runtimeIcon("icons/discord.svg")).toBeTruthy();
    for (const path of ["https://example.test/icon.svg", "//example.test/icon.svg", "icons/../../secret.svg", "icons/unknown.svg", "data:image/svg+xml,bad"]) expect(runtimeIcon(path)).toBeUndefined();
  });
});

it("never collapses component, attempt and operation identities with the same spelling", () => {
  const snapshot = runtimeSnapshot([runtimeEvent(1, { attempt_id: "edge" }), runtimeEvent(2, { attempt_id: null, operation_id: "edge", kind: "operation_result", phase: "unknown" })]);
  const field = projectRuntime(snapshot);
  expect(new Set(field.projection.nodes.map(node => node.id)).size).toBe(5);
  expect(field.selections.size).toBe(5);
});

it("suppresses duplicate event identities even if a producer supplies a later sequence", () => {
  const old = runtimeSnapshot();
  const next = runtimeSnapshot([runtimeEvent(2, { event_id: "event-1" })]);
  expect(receivedRuntimeEvents(old, next, true).size).toBe(0);
});

it.each([
  { producer_id: "resource", producer_generation: "producer-a" },
  { producer_id: "edge", producer_generation: "producer-b" }
])("keeps attempt identities separate for distinct producers or producer generations: %j", (otherProducer) => {
  const unfinished = runtimeEvent(1, { producer_id: "edge", producer_generation: "producer-a", producer_seq: 1 });
  const started = runtimeEvent(2, { ...otherProducer, producer_seq: 1, source: "resource", target: "edge" });
  const finished = runtimeEvent(3, { ...otherProducer, producer_seq: 2, source: "resource", target: "edge", kind: "transport_result", phase: "succeeded", http_status: 200 });
  const field = projectRuntime(runtimeSnapshot([unfinished, started, finished]));
  const calls = field.projection.nodes.filter(node => node.kind === "call attempt");
  expect(calls).toHaveLength(2);
  const pending = calls.find(node => node.state === "outcome unknown")!;
  const completed = calls.find(node => node.state === "succeeded")!;
  expect(field.selections.get(pending.id)).toEqual({ activities: [unfinished] });
  expect(field.selections.get(completed.id)).toEqual({ activities: [started, finished] });
  const pendingEdge = field.projection.edges.find(edge => edge.target === pending.id)!;
  const completedEdge = field.projection.edges.find(edge => edge.target === completed.id)!;
  expect(pendingEdge.source).not.toBe(completedEdge.source);
});

it("keeps all 128 components and the newest 128 of 256 attempts inspectable at capacity", () => {
  const events = Array.from({ length: 256 }, (_, index) => runtimeEvent(index + 1, { attempt_id: `attempt-${index + 1}`, operation: `call-${index + 1}` }));
  const snapshot = runtimeSnapshot(events);
  snapshot.components = [...snapshot.components, ...Array.from({ length: 125 }, (_, index) => ({ ...snapshot.components[2]!, key: `resource-${index}`, label: `Resource ${index}` }))];
  const field = projectRuntime(snapshot, new Set([activityKey(events.at(-1)!)]));
  expect(field.projection.nodes).toHaveLength(256);
  expect([...field.selections.values()].filter(selection => "component" in selection)).toHaveLength(128);
  expect(field.omittedNodes).toBe(128);
  expect(field.omittedEdges).toBe(256);
  const newest = field.projection.nodes.find(node => node.label === "call-256")!;
  expect(newest.attention).toBe("received");
  // Canvas and the semantic inspector consume these exact node and selection identities.
  expect(field.selections.get(newest.id)).toEqual({ activities: [events[255]!] });
  expect(field.projection.nodes.some(node => node.label === "call-1")).toBe(false);
  expect(field.projection.edges.filter(edge => edge.source === newest.id || edge.target === newest.id)).toHaveLength(2);
});

it("prioritizes an older attempt whose newly supplied result is at the window tail", () => {
  const events = Array.from({ length: 255 }, (_, index) => runtimeEvent(index + 1, { attempt_id: `attempt-${index + 1}`, operation: `call-${index + 1}` }));
  events.push(runtimeEvent(256, { attempt_id: "attempt-1", operation: "call-1", kind: "transport_result", phase: "succeeded" }));
  const snapshot = runtimeSnapshot(events);
  snapshot.components = [...snapshot.components, ...Array.from({ length: 125 }, (_, index) => ({ ...snapshot.components[2]!, key: `resource-${index}`, label: `Resource ${index}` }))];
  const field = projectRuntime(snapshot);
  const recent = field.projection.nodes.find(node => node.label === "call-1")!;
  expect(recent.state).toBe("succeeded");
  expect(field.selections.get(recent.id)).toEqual({ activities: [events[0]!, events[255]!] });
});


it("bounds retained source-generation sequence memory and never lowers a retained maximum", () => {
  let highWater: ReadonlyMap<string, number> = new Map();
  for (let generation = 0; generation < 100; generation++) {
    highWater = advanceRuntimeHighWater(highWater, runtimeSnapshot([runtimeEvent(10, { source_generation: `generation-${generation}` })]));
  }
  expect(highWater.size).toBe(RUNTIME_SOURCE_HISTORY_LIMIT);
  highWater = advanceRuntimeHighWater(highWater, runtimeSnapshot([runtimeEvent(5, { source_generation: "generation-99" })]));
  expect([...highWater.values()].every(head => head === 10)).toBe(true);
});
