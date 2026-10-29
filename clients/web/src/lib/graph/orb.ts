import type { LoomView, OrbRunSnapshot } from "$lib/api/models";
import type { GraphNode, GraphProjection } from "./model";
import { animatorAccent, evidenceAt } from "$lib/orb/playback";

type Evidence = OrbRunSnapshot["evidence"][number];
type Gap = OrbRunSnapshot["gaps"][number];

/** Only explicit node subjects can annotate an exact declared station. */
export function orbEvidenceNodeId(record: Evidence, pattern: LoomView | null): string {
  if (record.kind === "node" && pattern?.nodes.some((node) => node.key === record.subject_key)) {
    return `station:${record.subject_key}`;
  }
  return `subject:${record.kind}:${record.subject_key == null ? "unknown" : `key:${encodeURIComponent(record.subject_key)}`}`;
}

function occurrenceNodeId(record: Evidence, pattern: LoomView | null): string {
  return `occurrence:${orbEvidenceNodeId(record, pattern)}:${record.occurrence_id == null ? "unknown" : `id:${encodeURIComponent(record.occurrence_id)}`}`;
}

/** Recorded subject groups and declared permissions are separate semantic relations. */
export function projectOrb(snapshot: OrbRunSnapshot, pattern: LoomView | null, cursor: number | null = null): GraphProjection {
  const viewed = evidenceAt(snapshot, cursor);
  const head = viewed.evidence.toSorted((a, b) => a.seq - b.seq).at(-1);
  const attention = (records: Evidence[]) => head && (cursor === null || head.seq === cursor) && records.some((record) => record.event_id === head.event_id)
    ? cursor === null ? "latest" as const : "cursor" as const : undefined;
  const groups = new Map<string, Evidence[]>();
  for (const record of viewed.evidence) {
    const id = orbEvidenceNodeId(record, pattern);
    const records = groups.get(id) ?? [];
    records.push(record);
    groups.set(id, records);
  }
  const nodes: GraphNode[] = (pattern?.nodes ?? []).map((station) => {
    const id = `station:${station.key}`;
    const records = groups.get(id) ?? [];
    const latest = records.toSorted((a, b) => b.seq - a.seq)[0];
    groups.delete(id);
    return {
      id, label: station.label, kind: station.kind, entry: station.key === pattern?.entry_node,
      detail: `${records.length} loaded records · ${latest?.phase ? `last recorded: ${latest.phase}` : "no recorded phase"}`,
      count: records.length, state: latest?.phase ?? "unknown", group: "Declared stations", attention: attention(records)
    };
  });
  for (const [id, records] of groups) {
    const latest = records.toSorted((a, b) => b.seq - a.seq)[0]!;
    nodes.push({
      id, label: latest.subject_key ?? (latest.kind === "status" ? "Run status" : latest.kind === "done" ? "Run outcome" : "Unknown subject"), kind: latest.kind,
      detail: `${records.length} loaded records · ${latest.phase ? `last recorded: ${latest.phase}` : "phase not supplied"}`,
      count: records.length, state: latest.phase ?? "unknown", group: "Other recorded subjects", attention: attention(records),
      accent: latest.kind === "dispatch" && latest.animator_name ? animatorAccent(latest.animator_name) : undefined
    });
  }
  for (const gap of viewed.gaps) {
    nodes.push({
      id: `gap:${gap.start_seq}:${gap.end_seq}`, label: "Unknown interval", kind: "gap",
      detail: `#${gap.start_seq}–${gap.end_seq} · unknown or omitted`, state: "unknown", group: "Evidence gaps"
    });
  }
  return {
    identity: `orb:${snapshot.run.run_id}:${pattern?.digest ?? "unverified"}`,
    nodes,
    edges: (pattern?.edges ?? []).map((edge) => ({
      id: `permission:${edge.key}`, source: `station:${edge.source}`, target: `station:${edge.target}`,
      label: "Declared permission", relation: "permission" as const
    }))
  };
}

export function matchesOrbPattern(snapshot: OrbRunSnapshot, pattern: LoomView): boolean {
  return snapshot.pattern.exact && snapshot.pattern.digest !== null &&
    snapshot.pattern.pattern_id === pattern.pattern_id && snapshot.pattern.revision === pattern.revision &&
    snapshot.pattern.digest === pattern.digest;
}

/** Replayed rows retain one stable event identity; sequence remains supplied order. */
export function mergeOrbEvidence(...pages: readonly Evidence[][]): Evidence[] {
  const byId = new Map<string, Evidence>();
  for (const page of pages) for (const record of page) byId.set(record.event_id, record);
  return [...byId.values()].sort((a, b) => a.seq - b.seq);
}

/** Supplied intervals keep first-seen order and the latest value for each interval. */
export function mergeOrbGaps(...pages: readonly (readonly Gap[])[]): Gap[] {
  const byInterval = new Map<string, Gap>();
  for (const page of pages) for (const gap of page) byInterval.set(`${gap.start_seq}:${gap.end_seq}`, gap);
  return [...byInterval.values()];
}

export type OrbDetailLevel = "runs" | "stations" | "occurrences" | "records";
export interface OrbFieldLens { readonly snapshot: OrbRunSnapshot; readonly pattern: LoomView | null; readonly trimmed?: boolean }
export interface OrbFieldSelection { readonly runId: string; readonly eventId?: string }

function runCoverage(snapshot?: OrbRunSnapshot, trimmed = false): string {
  if (!snapshot) return "Evidence not loaded";
  const records = snapshot.evidence.length;
  const gaps = snapshot.gaps.length;
  const detail = [
    `${records} loaded record${records === 1 ? "" : "s"}`,
    `${gaps} supplied gap${gaps === 1 ? "" : "s"}`
  ];
  if (snapshot.known_omissions.length) detail.push(`Known omissions: ${snapshot.known_omissions.join(" ")}`);
  if (snapshot.has_more || trimmed) detail.push("More retained history exists outside this lens");
  return detail.join(" · ");
}

/** Explicit Run membership supplies groups; zoom changes only their presentation. */
export function projectOrbField(
  runs: readonly OrbRunSnapshot["run"][],
  lenses: ReadonlyMap<string, OrbFieldLens>,
  level: OrbDetailLevel
): { projection: GraphProjection; selections: ReadonlyMap<string, OrbFieldSelection> } {
  const nodes: GraphNode[] = [];
  const edges: GraphProjection["edges"][number][] = [];
  const selections = new Map<string, OrbFieldSelection>();
  const animators = new Map<string, { count: number; runs: Set<string>; attention: boolean }>();
  for (const summary of runs) {
    const lens = lenses.get(summary.run_id);
    const run = lens?.snapshot.run ?? summary;
    const header = `run:${run.run_id}`;
    const prefix = (id: string) => `${header}|${encodeURIComponent(id)}`;
    const graph = lens ? projectOrb(lens.snapshot, lens.pattern) : null;
    const occurrenceIds = lens ? [...new Set(lens.snapshot.evidence.map((record) => occurrenceNodeId(record, lens.pattern)))] : [];
    const members = graph ? [...graph.nodes.map((node) => prefix(node.id)), ...occurrenceIds.map(prefix),
      ...lens!.snapshot.evidence.map((record) => prefix(`record:${record.event_id}`))] : [];
    nodes.push({ id: header, label: run.workflow_name, detail: `${run.run_id} · recorded: ${run.status} · ${runCoverage(lens?.snapshot, lens?.trimmed)}`,
      kind: "run", state: run.status, group: run.run_id, count: lens?.snapshot.evidence.length, members: level === "runs" ? members : undefined,
      attention: level === "runs" && graph?.nodes.some((node) => node.attention) ? "latest" : undefined });
    selections.set(header, { runId: run.run_id });
    for (const record of lens?.snapshot.evidence ?? []) {
      if (record.kind !== "dispatch" || !record.animator_name) continue;
      const name = record.animator_name, id = `animator:${encodeURIComponent(name)}`;
      const source = level === "runs" ? header : prefix(orbEvidenceNodeId(record, lens!.pattern));
      const observation = animators.get(name) ?? { count: 0, runs: new Set<string>(), attention: false };
      observation.count++; observation.runs.add(run.run_id);
      observation.attention ||= lens!.snapshot.evidence.at(-1)?.event_id === record.event_id;
      animators.set(name, observation);
      if (!selections.has(id)) selections.set(id, { runId: run.run_id, eventId: record.event_id });
      const edgeId = `${source}:animator:${encodeURIComponent(name)}`;
      if (!edges.some((edge) => edge.id === edgeId)) edges.push({ id: edgeId, source, target: id, label: "Recorded Animator selection", relation: "selection" });
    }
    if (!lens || !graph || level === "runs") continue;
    for (const node of graph.nodes) {
      const records = lens.snapshot.evidence.filter((item) => orbEvidenceNodeId(item, lens.pattern) === node.id);
      nodes.push({ ...node, id: prefix(node.id), group: run.run_id,
        members: level === "stations" ? [...new Set(records.flatMap((record) => [prefix(occurrenceNodeId(record, lens.pattern)), prefix(`record:${record.event_id}`)]))] : undefined });
      const record = lens.snapshot.evidence.filter((item) => orbEvidenceNodeId(item, lens.pattern) === node.id).at(-1);
      selections.set(prefix(node.id), { runId: run.run_id, ...(record ? { eventId: record.event_id } : {}) });
    }
    for (const edge of graph.edges) edges.push({ ...edge, id: prefix(edge.id), source: prefix(edge.source), target: prefix(edge.target) });
    const entry = graph.nodes.find((node) => node.entry) ?? graph.nodes[0];
    if (entry) edges.push({ id: `${header}:membership`, source: header, target: prefix(entry.id), label: "Run lens", relation: "contains" });
    if (level === "stations") continue;
    const occurrences = new Map<string, Evidence[]>();
    for (const record of lens.snapshot.evidence) {
      const id = occurrenceNodeId(record, lens.pattern);
      const members = occurrences.get(id) ?? [];
      members.push(record); occurrences.set(id, members);
    }
    for (const [occurrenceId, members] of occurrences) {
      const latest = members.at(-1)!;
      const id = prefix(occurrenceId);
      nodes.push({ id, label: latest.occurrence_id ?? "Occurrence not supplied", detail: `${members.length} loaded records · ${latest.subject_key ?? "unknown subject"}`,
        kind: latest.occurrence_id ? "occurrence" : "unknown", count: members.length, group: run.run_id, members: level === "occurrences" ? members.map((record) => prefix(`record:${record.event_id}`)) : undefined });
      selections.set(id, { runId: run.run_id, eventId: latest.event_id });
      edges.push({ id: `${id}:membership`, source: prefix(orbEvidenceNodeId(latest, lens.pattern)), target: id, label: latest.occurrence_id ? "Recorded occurrence" : "Unspecified occurrence", relation: "contains" });
      if (level !== "records") continue;
      for (const record of members) {
        const eventId = prefix(`record:${record.event_id}`);
        nodes.push({ id: eventId, label: record.summary, detail: `#${record.seq} · ${record.kind} · ${record.event_id}`,
          kind: "event", state: record.phase ?? "unknown", group: run.run_id });
        selections.set(eventId, { runId: run.run_id, eventId: record.event_id });
        edges.push({ id: `${eventId}:membership`, source: id, target: eventId, label: "Retained record", relation: "contains" });
      }
    }

  }
  for (const [name, observation] of animators) nodes.push({
    id: `animator:${encodeURIComponent(name)}`, label: name, kind: "animator", group: "animators",
    count: observation.count, accent: animatorAccent(name), attention: observation.attention ? "latest" : undefined,
    detail: `${observation.count} loaded grant${observation.count === 1 ? "" : "s"} across ${observation.runs.size} Run${observation.runs.size === 1 ? "" : "s"} · recorded selection; call activity and availability are not supplied`
  });
  return { projection: { identity: "orb-field", nodes, edges }, selections };
}
