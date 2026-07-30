---
title: Candidate Handoff
icon: material/transit-transfer
---

# :material-transit-transfer: Candidate Handoff

> _The candidate leaves the forge frozen, not crowned._

A frozen Candidate Bundle crosses from a [Training Run](./training-run.md) into independent
judgment. Riddle may establish eligibility; only an externally owned decision may promote the
exact digest, bind its serving envelope, or refuse it.

Candidate handoff is **Designed**; neither independent evaluation nor promotion runs. [State of
Work](../../../state-of-the-work.md#soulforge-training) owns delivery, and
[ADR 33](../../../adr/33-training.md#independent-evaluation) owns the handoff law.

## Independent trial

Entry accepts one exact Candidate Bundle revision with its trainer receipt. Riddle names that
revision as the subject and operates separately from the trainer. Evaluation cannot alter
candidate bytes, corpus, Recipe, or lineage.

An expected-change contract recorded before training defines sought lift and tolerated regression.
Any post-training change to that contract remains visible rather than silently reshaping the
trial.

Riddle records compact promotion evidence under
[ADR 34](../../../adr/34-evaluation.md#evaluation-before-and-after-training):

- sealed target-capability holdout results;
- matched baseline Outcomes for the base model or currently promoted revision;
- named regression Suites plus adversarial and authority-boundary Cases; and
- quality, latency, memory, and cost in a compatible serving Environment, with uncertainty,
  errors, exclusions, and Evaluator calibration.

Trainer loss, development improvement, trainer-authored samples, and candidate self-grading remain
diagnostics. Success on one visible Suite cannot establish general capability or safety outside
its measured Environment.

## Eligibility is not promotion

Passing Riddle establishes eligibility only. The owning policy and required
Magus/[HitL](../../../adr/25-hitl.md) authority choose whether to promote and which capability
envelope may be exposed.

The external Promotion Decision binds the exact Candidate Bundle and independent Outcomes;
eligible capabilities and denied uses; compatible engines and base relationship; rollout
population, observation window, and stop conditions; fallback and rollback; and retention,
quarantine, or retirement terms.

The serving owner registers and routes the exact promoted digest. Files appearing in a directory
create no capability, and Dispatcher cannot infer eligibility from their presence. Soulforge
neither promotes nor serves its output. Promoted revisions remain immutable; supersession requires
a new Candidate Bundle and Promotion Decision.

## Observe, roll back, invalidate

Versioned serving observation belongs to the declared evidence window. A stop condition or
regression routes new work to an earlier promoted digest and quarantines the suspect revision.
Rollback cannot erase completed effects or remove learned examples from produced weights.

Later discovery of privacy, authority, license, contamination, or holdout failure follows lineage
through the Dataset Manifest, Training Run, Candidate Bundle, Outcomes and evaluation claims, and
Promotion Decision. Policy may block reuse or serving, quarantine or delete controlled artifacts,
invalidate evidence, and require clean admission and rebuild. Deleting a source record does not
untrain derived weights.

Custody ends in one durable state: the exact digest remains promoted within its bounds, is
superseded by a new immutable decision, or is quarantined and blocked with lineage intact.
