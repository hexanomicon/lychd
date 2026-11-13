import type { LoomView, OrbRunSnapshot } from "$lib/api/models";
export const pattern: LoomView = {
  schema_version: 1, pattern_id: "review", revision: "1", title: "Review", description: "Declared review score",
  digest: "pinned-digest", publication: "published", entry_node: "inspect", checkpoint_schema: "state", implementation_revision: "source", trigger_hint: "manual", mermaid_source: "",
  nodes: [{ key: "inspect", label: "Inspect", kind: "step" }, { key: "revise", label: "Revise", kind: "step" }],
  edges: [{ key: "inspect-revise", source: "inspect", target: "revise", relation: "permits" }, { key: "revise-inspect", source: "revise", target: "inspect", relation: "permits" }]
};
export function fixtureRun(id = "run-a"): OrbRunSnapshot {
  return {
    schema_version: 1, snapshot_at: "2026-09-22T00:00:00Z", capture: "process_local", ledger_head_seq: 0, page_end_seq: 0,
    live_tail: "ledger_poll", next_after_seq: null, has_more: false, known_omissions: [], gaps: [], delegated_jobs: [], workflow: pattern,
    pattern: { pattern_id: pattern.pattern_id, revision: pattern.revision, digest: pattern.digest, exact: true, loom_path: "/loom/review/1" },
    run: { run_id: id, session_id: "session-a", workflow_name: "review", status: "running", created_at: "2026-09-22T00:00:00Z", started_at: "2026-09-22T00:00:00Z", finished_at: null, error_present: false, bridge_path: "/bridge/session-a" },
    evidence: [{ event_id: `${id}-event-0`, seq: 0, kind: "node", occurred_at: "2026-09-22T00:00:00Z", summary: "Inspect entered", subject_key: "inspect", phase: "entered", occurrence_id: "occurrence-a", capture: "process_local" }]
  };
}
