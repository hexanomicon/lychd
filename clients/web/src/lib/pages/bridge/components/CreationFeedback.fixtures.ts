import type { components } from "$lib/api/openapi";

export type FeedbackView = components["schemas"]["FeedbackView"];
type FeedbackEntry = components["schemas"]["FeedbackEntry"];
type ExternalAssessment = components["schemas"]["ExternalAssessment"];
type OwnerDecision = components["schemas"]["OwnerDecision"];

export const ids = {
  a: "00000000-0000-4000-8000-000000000001",
  b: "00000000-0000-4000-8000-000000000002",
  assessment: "00000000-0000-4000-8000-000000000011",
  newerAssessment: "00000000-0000-4000-8000-000000000012",
  decision: "00000000-0000-4000-8000-000000000021"
} as const;

const target: components["schemas"]["FeedbackTarget"] = {
  request_digest: "a".repeat(64), profile_digest: "b".repeat(64),
  candidate_digest: "c".repeat(64), verdict_digest: "d".repeat(64),
  sources_digest: "e".repeat(64), criteria_digest: "f".repeat(64)
};
export const retainedReport = "Current external report: answer remains partially supported.";
export const retainedReason = "Current owner reason: retain the partial result for review.";
export const newerReport = "New external report: the earlier result is rejected.";

function assessment(
  id: string = ids.assessment,
  disposition: ExternalAssessment["disposition"] = "partial",
  report = retainedReport,
  sequence = 1
): FeedbackEntry {
  const body: ExternalAssessment = {
    assessment_id: id, target: { ...target }, reviewer_label: "Independent reviewer",
    reviewer_revision: "public-review-1", disposition, report,
    exposure: ["Supplied public source only."], limitations: ["Semantic correctness is not established."],
    submitter_annotations: []
  };
  return {
    id, sequence, body_digest: "1".repeat(64), body: { ...body },
    attribution: { principal: "fixture-local-operator", role: "local-operator" },
    created_at: "2026-10-17T12:00:00+00:00", report_digest: "2".repeat(64),
    criterion_coverage: { answer: "not_assessed" }
  };
}

export function held(caseId: string = ids.a): FeedbackView {
  const external = assessment();
  const body: OwnerDecision = {
    decision_id: ids.decision, assessment_id: external.id, assessment_digest: external.body_digest,
    target: { ...target }, action: "hold", reason: retainedReason, distinguishing_observation: null
  };
  return {
    case_id: caseId, native_status: "accepted",
    native_verdict: { disposition: "accepted", findings: [], contradictions: [] },
    target: { ...target }, status: "hold", current_assessment_id: external.id,
    current_decision_id: ids.decision, assessments: [external], decisions: [{
      id: ids.decision, sequence: 2, body_digest: "3".repeat(64), body: { ...body },
      attribution: { principal: "fixture-local-operator", role: "local-operator" },
      created_at: "2026-10-17T12:01:00+00:00", report_digest: null, criterion_coverage: {}
    }]
  };
}

export function reviewRequired(): FeedbackView {
  const view = held();
  const newest = assessment(ids.newerAssessment, "rejected", newerReport, 3);
  return { ...view, status: "review_required", current_assessment_id: newest.id,
    current_decision_id: null, assessments: [...view.assessments, newest] };
}

export function unassessed(): FeedbackView {
  return { ...held(), status: "unassessed", current_assessment_id: null, current_decision_id: null,
    assessments: [], decisions: [] };
}

export function explicitlyNotAssessed(): FeedbackView {
  const current = assessment(ids.assessment, "not_assessed", "Reviewer explicitly did not assess semantics.");
  return { ...unassessed(), status: "review_required", current_assessment_id: current.id, assessments: [current] };
}
