---
title: Health care planning
icon: material/clipboard-pulse-outline
---

# Health care planning

`health.plan_care@1` turns one reviewed case and its externally established facts or explicitly
declared diagnostic assumptions into treatment options. `health.follow_up@1` records what the
person or qualified professional says happened. A proposal is not a prescription, a verdict is
not administration, and a plan is not evidence of adherence or benefit.

## Compare care options

`CareProposal@1` binds the person, profile and case revisions, clinical basis and unresolved
assumptions, goal, option, evidence scope, expected benefit, material risks, contraindications and
interactions checked, unknown interactions, alternatives including no action, required clinician
or prescriber, monitoring, escalation and stop conditions, duration, review date, and expiry.
Unsupported dose conversion, incomplete medication or allergy review, or missing authority blocks
the affected option.

The Composition may explain externally issued instructions and prepare questions for a clinician.
It cannot issue or renew a prescription, alter a dose, recommend stopping prescribed medication,
claim an interaction check is complete beyond its admitted sources, or convert patient consent
into professional authorization. Low-risk self-care, clinician-supervised treatment, medication,
procedure, rehabilitation, and watchful waiting remain distinct effect classes with distinct
policy.

## One exact human verdict

When an option is eligible for HitL, its call binds the exact person and case; profile and evidence
revisions; diagnostic basis; intervention, medicine or device identity; dose, route, frequency,
duration and timing where applicable; prerequisites, monitoring and stop conditions; actor and
required qualification; disclosures and destination; cost ceiling; policy revision; and expiry.
Any clinically relevant change creates a new call. Approval of one option does not approve its
alternatives, refills, substitutions, later cycles, purchases, sharing, or administration.

The Altar should show the evidence for and against the option, unresolved fields, likely and severe
risks, alternatives, reversibility, required professional role, and what approval can and cannot
cause. Denial closes that proposal without effect. Revision returns to planning. Approval only
authorizes an eligible next effect to be rechecked by its owner; it does not attest safety or
outcome.

Prescription, test ordering, dispensing, booking, payment, device control, and treatment delivery
remain external effects until separately governed owners are accepted and integrated. A
human-entered confirmation or attributable external receipt may record one of them. Missing
acknowledgement remains unknown and must be reconciled before retry.

## Follow up without inventing success

`HealthFollowUp@1` can record a confirmed start, dose or session, skip, deviation, symptom change,
measurement, adverse event, patient reflection, clinician assessment, stop, or unknown outcome,
each with source, time, uncertainty, and linked proposal. A reminder, purchase, dispensation,
schedule, silence, or model inference proves none of these.

Adverse events and red flags stop ordinary progression and return the applicable professional or
emergency handoff. Follow-up may propose a review; it cannot automatically escalate a dose,
continue an expired plan, punish non-adherence, or suppress contradictory testimony. Restart
recovers exact receipts and pending unknown effects without duplicating a treatment event or
reusing an obsolete verdict.

---

[Health](index.md) · [Consultation](consultation.md)
