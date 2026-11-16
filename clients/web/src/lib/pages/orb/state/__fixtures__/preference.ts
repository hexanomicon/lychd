import type { OrbRunSnapshot } from "$lib/api/models";

/** Synthetic admission observations only; never probes or selects a runtime. */
export const coldPreferredRoute: NonNullable<OrbRunSnapshot["bridge_preference"]> = {
  policy_schema_version: 1,
  policy_digest: "a".repeat(64),
  batch_started_at: "2026-10-17T12:00:00Z",
  batch_finished_at: "2026-10-17T12:00:01Z",
  selected_capability_key: "local-ready:chat:model-b",
  routes: [
    { capability_key: "local-preferred:chat:model-a", weight: 1000, phase: "cold", observed_at: "2026-10-17T12:00:00Z", admission_open: true, exclusion_code: "not_warm" },
    { capability_key: "local-ready:chat:model-b", weight: 10, phase: "warm", observed_at: "2026-10-17T12:00:01Z", admission_open: true, exclusion_code: null }
  ]
};
