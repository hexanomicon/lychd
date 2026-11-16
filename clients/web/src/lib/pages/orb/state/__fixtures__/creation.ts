import type { OrbRunSnapshot } from "$lib/api/models";

/** Synthetic metadata only; no provider, source or private evidence bodies. */
export const incompleteCreation: NonNullable<OrbRunSnapshot["creation"]> = {
  case_id: "c70a9526-fd5a-44df-b400-57a1066423cb",
  admission_id: "e8186a0b-ced8-4c3f-8cfe-5097e9521e3e", run_id: "run-a", admission_current: true,
  native_status: "incomplete", reason_code: "output_bytes", deadline: "2026-10-17T18:00:00Z",
  deadline_elapsed: true, slot_encumbered: false,
  constructor_present: true, constructor_adopted: false, verifier_present: false, verifier_adopted: false,
  candidate_present: false, verdict_present: false, native_disposition: null, external_disposition: null,
  feedback_status: "unassessed", current_assessment_id: null, current_decision_id: null
};
