import type { ObservedActivity, OrbRuntimeSnapshot } from "$lib/api/models";

export function runtimeEvent(seq = 1, changes: Partial<ObservedActivity> = {}): ObservedActivity {
  return { event_id: `event-${seq}`, operation_id: "op-a", attempt_id: "attempt-a", seq,
    observed_at: "2026-11-02T00:00:00Z", received_at: "2026-11-02T00:00:01Z", producer_id: "edge", source: "edge", target: "endpoint",
    operation: "request", kind: "transport_attempt", phase: "started", capture: "process_local", source_id: "fixture", source_generation: "generation-a", registrant_id: "builtin:fixture",
    http_status: null, error_category: null, elapsed_ms: null, run_id: null, station_attempt_id: null, request_id: null, job_id: null, receipt_id: null,
    effect_outcome: null, pattern_id: null, pattern_revision: null, ...changes };
}
export function runtimeSnapshot(events: ObservedActivity[] = [runtimeEvent()]): OrbRuntimeSnapshot {
  const generation = events[0]?.source_generation ?? "generation-a";
  return { schema_version: 1, read_at: "2026-11-02T00:00:02Z", sources: [{ source_id: "fixture", registrant_id: "builtin:fixture", generation,
    profile_id: "test", profile_revision: "1", generated_at: "2026-11-02T00:00:01Z", status: "current", generation_changed: false,
    coverage: { capture: "process_local", completeness: "not_established", first_seq: events[0]?.seq ?? null, last_seq: events.at(-1)?.seq ?? null,
      dropped: 0, gaps: 0, omitted_components: 0, omitted_relations: 0, omitted_activities: 0, omitted_patterns: 0, limitations: ["gateway_not_instrumented"] } }],
    components: ["edge", "endpoint", "resource"].map(key => ({ key, label: key, kind: key === "endpoint" ? "external" as const : "service" as const,
      revision: "1", owner: "fixture", instance_id: null, lifecycle: "configured", activity_coverage: "unavailable", icon: "component", icon_asset: null,
      source_id: "fixture", source_generation: generation, registrant_id: "builtin:fixture" })),
    relations: [{ key: "attached", source: "edge", target: "endpoint", relation: "attached", source_id: "fixture", source_generation: generation }],
    activities: events, patterns: [], coverage: { source_limit: 9, selected_source_limit: 8, component_limit: 128, relation_limit: 256, activity_limit: 256, pattern_limit: 32,
      omitted_sources: 0, omitted_components: 0, omitted_relations: 0, omitted_activities: 0, omitted_patterns: 0 } };
}
