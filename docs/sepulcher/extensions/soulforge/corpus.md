---
title: Corpus
icon: material/database-lock
---

# :material-database-lock: Corpus Admission and Compilation

> _The first gate of the forge is a ledger of what it refused._

Before a trainer receives anything, Soulforge must turn a Training Intent and exact nominated
records into an admitted immutable snapshot, then a Dataset Manifest. Both passages are
**Designed**; neither runs. [State of Work](../../../state-of-the-work.md#soulforge-training) owns
delivery, while
[ADR 33](../../../adr/33-training.md#corpus-admission) owns admission law and the complete record
schemas.

## Admit one snapshot

Nomination requests review. A Riddle Case or Outcome, Mirror attribution, HitL decision, Archive
row, success, refusal, repetition, storage consent, or database access never grants training
eligibility. Runtime data requires opt-in. A failed or refused Run may supply useful evidence;
success may be noise or one duplicated error.

Training Intent records the Principal, exact purpose, target capability, base digest, allowed data
classes, and authority boundary.

Corpus Admission freezes one snapshot. It binds sources, Runs, artifacts, producers, times,
transformations, and generated descendants to purpose, retention, derivative use, consent,
license or other authority, and approving Principal. It records privacy minimization, secret
removal, reviewable redaction limits, target behavior, objective, expected lift, regression
limits, and lineage groups spanning duplicates, revisions, sibling trajectories, and generated
variants. Train, development, and sealed-holdout membership become immutable before
training-facing generation.

Accepted members travel with a negative ledger of rejected, redacted, and duplicate member ids;
retry or another compiler cannot restore exclusions. Refuse admission and name the failed
condition when provenance, training authority, privacy clearance or minimization, relevance,
lineage-safe splits, or a viable uncontaminated sealed holdout is missing.

## Compile without leakage

Compilation reads only the admitted snapshot and emits one immutable Dataset Manifest. Every field
traces to a source or versioned deterministic transformation. The manifest preserves role, tool,
workflow, and authority context; distinguishes observation, human label, evaluator judgment,
augmentation, truthful non-completion, and failure; and records filtering, redaction, truncation,
normalization, sampling, lineage, splits, and audit statistics.

Sealed-holdout answers, benchmark solutions, evaluator rationales, and target artifacts cannot
enter prompts, retrieval, augmentation, preference construction, trainer metadata, or selection.
A benchmark used to select the corpus must be disclosed; without an untouched control, it cannot
serve as independent promotion evidence. Schema conformance alone does not establish truth.

Only the Dataset Manifest crosses to the trainer; nominations and ambient stores remain outside
the corpus.

## Refusal and return

Before a manifest exists, repair missing evidence, authority, minimization, grouping, or holdout,
then submit a new immutable Corpus Admission. Existing history remains unchanged.

If privacy, authority, license, contamination, or leakage fails later, quarantine the snapshot and
manifest, block reuse, follow lineage through derived Runs, candidates, and claims, and build a
clean admission and manifest. ADR 33 owns the full descendant policy. Deletion cannot remove
influence from weights already trained.

The immutable Dataset Manifest is Soulforge's sole corpus handoff into a future Training Run.
