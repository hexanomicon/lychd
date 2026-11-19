/** Worked import-retry policy for local exploration on the Loom Affect tab. */
export const evidenceCases = {
  key: {
    label: "A new receipt lookup key",
    emotion: "Curiosity",
    observation: "The storage log identifies a previously unknown receipt key for the timed-out write.",
    appraisal: "Useful novelty. One read could distinguish a lost acknowledgement from a failed write.",
  },
  repeat: {
    label: "The same timeout, reported again",
    emotion: "Frustration",
    observation: "A second log repeats the timeout and supplies no other reference.",
    appraisal: "Saturated. The repeated observation leaves both explanations open.",
  },
  conflict: {
    label: "Conflicting receipt identities",
    emotion: "Concern",
    observation: "Two receipts claim the same document with different write identities.",
    appraisal: "Disputed attribution. Neither receipt alone establishes which write took effect.",
  },
  confirmed: {
    label: "A matching committed receipt",
    emotion: "Satisfaction",
    observation: "The receipt identifies this document, write and committed result.",
    appraisal: "Decision settled. The acknowledgement was lost after the write succeeded.",
  },
} as const;

export type EvidenceCase = keyof typeof evidenceCases;
export type ProbeAllowance = "one" | "spent";
export type LookupPermission = "permitted" | "needs_review";

export function exampleDisposition(
  evidence: EvidenceCase,
  allowance: ProbeAllowance,
  permission: LookupPermission,
) {
  if (evidence === "confirmed")
    return {
      kind: "stop",
      title: "Stop probing",
      reason: "The receipt settles the question. Carry the known outcome to Join.",
    };
  if (allowance === "spent")
    return {
      kind: "stop",
      title: "Stop probing",
      reason: "The parent allowance is spent. Return the unresolved evidence to the decision owner.",
    };
  if (evidence === "repeat")
    return {
      kind: "stop",
      title: "Stop probing",
      reason: "Another copy of the same timeout would add no evidence. Preserve the unknown write outcome.",
    };
  if (evidence === "conflict")
    return {
      kind: "review",
      title: "Request owner review",
      reason: "Return both receipt references to the decision owner to resolve the conflict.",
    };
  if (permission === "needs_review")
    return {
      kind: "review",
      title: "Request owner review",
      reason: "Ask whether the store owner authorizes one read for this receipt key.",
    };
  return {
    kind: "probe",
    title: "One bounded probe is eligible",
    reason:
      "Read the receipt once using the new key. Return the observation to Join and preserve any remaining uncertainty.",
  };
}
