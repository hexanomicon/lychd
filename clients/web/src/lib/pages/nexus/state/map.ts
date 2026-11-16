import type { NexusCovenRow, NexusSnapshot, TransitionPlan } from "$lib/api/models";

export type NexusMapImpact = "evict" | "launch" | "both" | null;
type MapIdentity = { readonly id: string; readonly label: string; readonly impact: NexusMapImpact };
export type NexusMapObject = MapIdentity & (
  | { readonly kind: "animator"; readonly animator: string; readonly rows: readonly NexusCovenRow[]; readonly groups: readonly string[] }
  | { readonly kind: "capability"; readonly scope: "managed" | "portal"; readonly row: NexusCovenRow }
  | { readonly kind: "delegated"; readonly runtime: NexusSnapshot["delegated_runtimes"][number] }
);
export type NexusMapNode = { readonly objectId: string; readonly x: number; readonly y: number; readonly width: number; readonly height: number };
export type NexusMapEdge = { readonly id: string; readonly from: string; readonly to: string };
export type NexusMapSection = { readonly id: string; readonly label: string; readonly note: string; readonly y: number };
export type NexusMapModel = {
  readonly objects: readonly NexusMapObject[];
  readonly nodes: readonly NexusMapNode[];
  readonly edges: readonly NexusMapEdge[];
  readonly sections: readonly NexusMapSection[];
  readonly bounds: { readonly width: number; readonly height: number };
  readonly target: string | null;
};

const compare = (a: string, b: string) => a < b ? -1 : a > b ? 1 : 0;
const identity = (...parts: string[]) => JSON.stringify(parts);
const animatorId = (name: string) => identity("animator", name);
const capabilityId = (scope: "managed" | "portal", key: string) => identity("capability", scope, key);

/** A disposable observation projection. Coordinates never imply capacity or physical membership. */
export function createNexusMap(snapshot: NexusSnapshot, plan: TransitionPlan | null = null, target: string | null = null): NexusMapModel {
  const evict = new Set(plan?.evict_coven_ids ?? []);
  const launch = new Set(plan?.launch_coven_ids ?? []);
  const impact = (name: string): NexusMapImpact => evict.has(name) ? (launch.has(name) ? "both" : "evict") : launch.has(name) ? "launch" : null;
  const objects: NexusMapObject[] = [];
  const nodes: NexusMapNode[] = [];
  const edges: NexusMapEdge[] = [];
  const sections: NexusMapSection[] = [];
  const animatorRows = new Map<string, Map<string, NexusCovenRow>>();
  const animatorGroups = new Map<string, Set<string>>();
  const managed = new Map<string, NexusCovenRow>();

  // Sort before deduplicating so input order cannot move or replace a projected identity.
  const groups = [...snapshot.board.covens].sort(([a], [b]) => compare(a, b));
  for (const [group, rows] of groups) {
    for (const row of [...rows].sort((a, b) => compare(a.capability_key, b.capability_key) || compare(a.animator_name, b.animator_name))) {
      if (!managed.has(row.capability_key)) managed.set(row.capability_key, row);
      if (!row.animator_name) continue;
      const observed = animatorRows.get(row.animator_name) ?? new Map<string, NexusCovenRow>();
      observed.set(row.capability_key, row);
      animatorRows.set(row.animator_name, observed);
      const names = animatorGroups.get(row.animator_name) ?? new Set<string>();
      names.add(group);
      animatorGroups.set(row.animator_name, names);
    }
  }
  for (const [name, rows] of [...animatorRows].sort(([a], [b]) => compare(a, b))) {
    objects.push({ id: animatorId(name), label: name, kind: "animator", animator: name,
      rows: [...rows.values()].sort((a, b) => compare(a.capability_key, b.capability_key)),
      groups: [...(animatorGroups.get(name) ?? [])].sort(compare), impact: impact(name) });
  }
  for (const [key, row] of [...managed].sort(([a], [b]) => compare(a, b))) {
    const id = capabilityId("managed", key);
    objects.push({ id, label: key || "Capability identity not reported", kind: "capability", scope: "managed", row, impact: row.animator_name ? impact(row.animator_name) : null });
    if (row.animator_name) edges.push({ id: identity("ownership", row.animator_name, key), from: animatorId(row.animator_name), to: id });
  }
  const portals = new Map([...snapshot.board.portals].sort((a, b) => compare(a.capability_key, b.capability_key)).map((row) => [row.capability_key, row]));
  for (const [key, row] of portals) objects.push({ id: capabilityId("portal", key), label: key || "Capability identity not reported", kind: "capability", scope: "portal", row, impact: null });
  const runtimes = new Map([...snapshot.delegated_runtimes].sort((a, b) => compare(a.runtime_id, b.runtime_id)).map((runtime) => [runtime.runtime_id, runtime]));
  for (const runtime of runtimes.values()) {
    objects.push({ id: identity("delegated", runtime.runtime_id), label: runtime.display_name || runtime.runtime_id || "Runtime identity not reported", kind: "delegated", runtime, impact: null });
  }

  const width = 256, height = 112, gap = 20, left = 24, right = 328;
  let y = 76;
  const section = (id: string, label: string, note: string) => { sections.push({ id, label, note, y: y - 52 }); };
  const place = (objectId: string, x: number, at: number) => nodes.push({ objectId, x, y: at, width, height });
  section("managed", "Managed capabilities", managed.size ? "Lines show the reported Animator only · Coven names are display groups" : "No managed capabilities reported");
  const adjacency = new Map<string, NexusMapObject[]>();
  for (const object of objects) {
    if (object.kind !== "capability" || object.scope !== "managed") continue;
    const bucket = adjacency.get(object.row.animator_name) ?? [];
    bucket.push(object);
    adjacency.set(object.row.animator_name, bucket);
  }
  for (const animator of objects.filter((object) => object.kind === "animator")) {
    const capabilities = adjacency.get(animator.animator) ?? [];
    place(animator.id, left, y);
    capabilities.forEach((object, index) => place(object.id, right, y + index * (height + gap)));
    y += Math.max(1, capabilities.length) * (height + gap) + 16;
  }
  const unknown = adjacency.get("") ?? [];
  unknown.forEach((object) => { place(object.id, right, y); y += height + gap; });
  if (!managed.size) y += 36;
  const standalone = (id: string, label: string, note: string, items: readonly NexusMapObject[]) => {
    if (!items.length) return;
    y += 60;
    section(id, label, note);
    items.forEach((object, index) => place(object.id, index % 2 ? right : left, y + Math.floor(index / 2) * (height + gap)));
    y += Math.ceil(items.length / 2) * (height + gap);
  };
  standalone("portal", "Portals", "Remote observations · read only · no physical relationship implied", objects.filter((object) => object.kind === "capability" && object.scope === "portal"));
  standalone("delegated", "Delegated runtime pools", "Extension observations · read only", objects.filter((object) => object.kind === "delegated"));
  return { objects, nodes, edges, sections, bounds: { width: 608, height: Math.max(240, y + 8) }, target };
}
