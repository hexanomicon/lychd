import type { OrbRunSnapshot } from "$lib/api/models";
import type { GraphProjection } from "$lib/graph/model";

type Record = OrbRunSnapshot["evidence"][number];
export type LocalAppraisal = {
  source: string;
  eventId: string;
  seq: number;
  gain: string;
  emotion: string;
  next: string;
  finding: string;
  reason: string;
  at: string;
};

/** Bind the review to the exact source fields shown to the reviewer. */
export function appraisalSource(runId: string, record: Record): string {
  return JSON.stringify([
    runId,
    record.event_id,
    record.seq,
    record.occurrence_id,
    record.occurred_at,
    record.capture,
    record.kind,
    record.subject_key,
    record.phase,
    record.summary,
  ]);
}

export function markAppraisal(graph: GraphProjection, nodeId: string, note: LocalAppraisal): GraphProjection {
  const annotation = `Your ${note.emotion.toLowerCase()} · #${note.seq}`;
  return {
    ...graph,
    nodes: graph.nodes.map((node) => (node.id === nodeId ? { ...node, annotation } : node)),
  };
}
