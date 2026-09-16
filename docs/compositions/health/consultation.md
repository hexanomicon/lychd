---
title: Health consultation
icon: material/stethoscope
---

# Health consultation

`health.review_case@1` answers one bounded health question against exact profile and source
revisions. The useful result may be a clearer history, a set of plausible explanations, the next
discriminating observation or test to discuss with a clinician, or an honest stop.

## Open one case

`HealthCase@1` binds the person's reviewed profile revision, question, symptom onset and course,
patient testimony, available measurements and records, unavailable evidence, purpose, urgency,
decision role, jurisdiction or provider context when relevant, and time and privacy bounds. It
does not absorb the whole profile by default. The patient reviews the case summary before it is
used or disclosed.

The consultation first checks declared emergency and escalation rules. A matched red flag returns
an emergency handoff with the triggering evidence and uncertainty. No match means only that the
finite check did not match; it is not clearance, monitoring, or a guarantee that waiting is safe.

## Propose diagnostic work without manufacturing a diagnosis

The review keeps observations, assertions, hypotheses, and established external diagnoses
separate. It can summarize supporting and contradicting evidence, ask focused questions, and rank
candidate explanations only under a pinned knowledge and policy revision. Missing evidence and
limits accompany every rank. Popularity, model confidence, and a clean-looking OCR result do not
establish a diagnosis.

`DiagnosticProposal@1` records the case and profile revisions, candidate explanations, rationale,
contradictions, information gaps, proposed examination or test, prerequisites, burdens and risks,
alternatives, expected discriminating value, urgency, stop conditions, required professional
role, and expiry. The proposal can end as self-observation, routine clinician discussion, urgent
handoff, exact blocker, refusal, or unresolved case. It cannot order a test, certify necessity,
interpret an unseen result, or promise access.

An accepted external test order remains the external clinician's act. A returned result enters
through [assimilation](assimilation.md) with its author and source intact, then opens a new case
revision; it never silently settles an earlier hypothesis. Consultation can finish while the
external diagnostic path remains pending.

## Stopping and recovery

Conflicting identity, an unreviewed high-impact field, inadequate evidence, exhausted budget,
unsupported population, unavailable qualified authority, or an emergency boundary can stop the
case. A proposed next step requires its own exact approval when it would disclose data, spend
money, create an appointment, order a test, or cause another effect.

Restart recovers the last committed case and proposal. A changed symptom, medication, allergy,
source, profile, policy, or knowledge revision invalidates the affected pending proposal instead
of borrowing its prior approval. Missing provider acknowledgement leaves the external action
unknown and blocks blind retry.

---

[Health](index.md) · [Care planning](care.md)
