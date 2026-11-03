import type { ObservedActivity, OrbRuntimeSnapshot, RuntimeComponent } from "$lib/api/models";
import type { GraphEdge, GraphNode, GraphProjection } from "./model";
import { runtimeIcon } from "./icons";

export const RUNTIME_NODE_LIMIT = 256;
export const RUNTIME_EDGE_LIMIT = 512;
export const RUNTIME_SOURCE_HISTORY_LIMIT = 64;
export type RuntimeSelection = { readonly component: RuntimeComponent } | { readonly activities: readonly ObservedActivity[] };

export function runtimeKey(source: string, generation: string, key: string, namespace = "component"): string {
  return `runtime:${[source, generation, namespace, key].map(encodeURIComponent).join("/")}`;
}
export function activityKey(event: ObservedActivity): string {
  return runtimeKey(event.source_id, event.source_generation, event.event_id, "event");
}
function attemptKey(event: ObservedActivity): string {
  const identity = JSON.stringify([event.producer_id, event.producer_generation ?? null, event.attempt_id ?? event.operation_id]);
  return runtimeKey(event.source_id, event.source_generation, identity, event.attempt_id ? "attempt" : "operation");
}

/** Presentation only: declared attachment never becomes observed traffic. */
export function projectRuntime(snapshot: OrbRuntimeSnapshot | null, received: ReadonlySet<string> = new Set()) {
  const nodes: GraphNode[] = [], edges: GraphEdge[] = [];
  const selections = new Map<string, RuntimeSelection>();
  if (!snapshot) return { projection: { identity: "runtime", nodes, edges } as GraphProjection, selections, omittedNodes: 0, omittedEdges: 0 };
  const sourceStatus = new Map(snapshot.sources.map(source => [source.source_id, source.status]));
  for (const component of snapshot.components) {
    const id = runtimeKey(component.source_id, component.source_generation, component.key);
    nodes.push({ id, label: component.label, kind: component.kind, state: component.lifecycle,
      detail: `${component.source_id} · ${sourceStatus.get(component.source_id) ?? "unavailable"} source · activity ${component.activity_coverage}`,
      group: runtimeKey(component.source_id, component.source_generation, "components", "group"),
      icon: runtimeIcon(component.icon_asset), accent: "frost" });
    selections.set(id, { component });
  }
  for (const relation of snapshot.relations) edges.push({
    id: runtimeKey(relation.source_id, relation.source_generation, relation.key, "relation"),
    source: runtimeKey(relation.source_id, relation.source_generation, relation.source),
    target: runtimeKey(relation.source_id, relation.source_generation, relation.target),
    label: `Declared ${relation.relation}`, relation: "declared"
  });
  const attempts = new Map<string, ObservedActivity[]>();
  for (const event of snapshot.activities) {
    const id = attemptKey(event);
    const members = attempts.get(id) ?? [];
    members.push(event);
    // An older attempt with a newly supplied result also belongs at the visible tail.
    attempts.delete(id); attempts.set(id, members);
  }
  for (const [id, unsorted] of attempts) {
    const activities = unsorted.toSorted((a, b) => a.seq - b.seq);
    const last = activities.at(-1)!;
    const transport = activities.some(event => event.kind === "transport_attempt" || event.kind === "transport_result");
    const attention = activities.some(event => received.has(activityKey(event))) ? "received" as const : undefined;
    const observedResult = activities.toReversed().find(event => event.kind === "transport_result");
    const startedOnly = transport && !observedResult;
    nodes.push({ id, label: last.operation, kind: transport ? "call attempt" : "operation", state: startedOnly ? "outcome unknown" : transport ? observedResult!.phase : last.phase,
      detail: `${last.source} → ${last.target} · ${last.attempt_id ?? last.operation_id} · ${last.source_id}`,
      group: runtimeKey(last.source_id, last.source_generation, "components", "group"), count: activities.length, attention, accent: "frost" });
    selections.set(id, { activities });
    edges.push({ id: `${id}:from`, source: runtimeKey(last.source_id, last.source_generation, last.source), target: id,
      label: `${last.source} → ${last.operation} · observed ${transport ? "transport" : "operation"}`, relation: "activity", attention },
    { id: `${id}:to`, source: id, target: runtimeKey(last.source_id, last.source_generation, last.target),
      label: `${last.operation} → ${last.target}`, relation: "activity", attention });
  }
  // Keep components, then the latest attempt groups in the supplied window.
  // This display priority establishes no cross-source chronology or causality.
  const componentCount = Math.min(snapshot.components.length, RUNTIME_NODE_LIMIT);
  const attemptSlots = RUNTIME_NODE_LIMIT - componentCount;
  const bounded = [...nodes.slice(0, componentCount),
    ...(attemptSlots ? nodes.slice(snapshot.components.length).slice(-attemptSlots) : [])];
  const visible = new Set(bounded.map(node => node.id));
  const boundedEdges = edges.filter(edge => visible.has(edge.source) && visible.has(edge.target)).slice(0, RUNTIME_EDGE_LIMIT);
  for (const id of selections.keys()) if (!visible.has(id)) selections.delete(id);
  return { projection: { identity: "runtime", nodes: bounded, edges: boundedEdges } as GraphProjection, selections,
    omittedNodes: nodes.length - bounded.length, omittedEdges: edges.length - boundedEdges.length };
}

/** Retain sequence maxima across replaceable windows; old snapshots cannot lower them.
 * The bounded cache is presentation memory, not source or execution authority.
 */
export function advanceRuntimeHighWater(previous: ReadonlyMap<string, number>, snapshot: OrbRuntimeSnapshot): ReadonlyMap<string, number> {
  const next = new Map(previous);
  for (const source of snapshot.sources) {
    const head = source.coverage.last_seq;
    if (source.generation === null || source.generation === undefined || head == null || !Number.isSafeInteger(head)) continue;
    const key = runtimeKey(source.source_id, source.generation, "sequence", "cursor");
    const maximum = Math.max(next.get(key) ?? 0, head);
    next.delete(key); next.set(key, maximum);
  }
  while (next.size > RUNTIME_SOURCE_HISTORY_LIMIT) next.delete(next.keys().next().value!);
  return next;
}

/** Each generation orders itself. A first/recovered snapshot establishes a silent baseline. */
export function receivedRuntimeEvents(previous: OrbRuntimeSnapshot | null, next: OrbRuntimeSnapshot, continuous: boolean, highWater: ReadonlyMap<string, number> = new Map()): ReadonlySet<string> {
  if (!previous || !continuous) return new Set();
  const sources = new Map(previous.sources.map(source => [source.source_id, source]));
  const known = new Set(previous.activities.map(activityKey));
  const current = new Map(next.sources.map(source => [source.source_id, source]));
  return new Set(next.activities.filter(event => {
    const before = sources.get(event.source_id), after = current.get(event.source_id);
    return !known.has(activityKey(event)) && Number.isSafeInteger(event.seq) && before?.status === "current" && after?.status === "current" &&
      !after.generation_changed && before.generation === after.generation && after.generation === event.source_generation &&
      (after.coverage.last_seq ?? 0) >= (before.coverage.last_seq ?? 0) &&
      event.seq > Math.max(before.coverage.last_seq ?? 0, highWater.get(runtimeKey(event.source_id, event.source_generation, "sequence", "cursor")) ?? 0);
  }).map(activityKey));
}
