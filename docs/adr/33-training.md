---
title: 33. Training
icon: material/school-outline
---

# :material-school-outline: 33. Training

!!! abstract "Context"
    Retained material can shape later acts through Context and Recall; training changes model
    parameters. **Soulforge** governs which nominated evidence may enter that training, how a
    candidate is formed, and what must reach independent judgment. A useful trace still needs
    corpus admission; trainer loss cannot authorize promotion; an adapter needs exact base-model
    compatibility. The [Soulforge guide](../sepulcher/extensions/soulforge/index.md) follows the
    passage from corpus admission to candidate handoff.

## Decision

Soulforge owns corpus admission, dataset compilation, training-job contracts, candidate lineage,
and handoff to independent evaluation/promotion. It never harvests runtime traces by default,
equates Karma/consent/repetition/a positive Riddle verdict with corpus admission, mutates serving
weights in place, treats trainer telemetry as promotion evidence, selects production routing, or
turns Trial Suite feedback into gradients/automatic repair.

```text
nominated evidence → admitted immutable corpus → compiled dataset + sealed holdout
→ isolated Training Run → frozen Candidate Bundle → independent Riddle evaluation
→ explicit promotion decision → versioned serving observation
```

Every arrow is attributable and may refuse; there is no ambient online self-training.

!!! warning "Delivery boundary"
    Soulforge is **Designed**. No training package, corpus service, compiler, trainer plane,
    candidate registry, evaluation integration, or Altar route is installed. The `karma` table is
    not a corpus. [State of Work](../state-of-the-work.md#soulforge-training) owns delivery.

## Training discernment from work

The [discernment training passage](../sepulcher/extensions/soulforge/discernment-training.md)
applies this law to nominated SDLC traces and human corrections. Preserve the distinction that
changed a decision, its evidence and conditions, and a counterexample to the superficial rule.
Preference, fact, authorization, measured result and evaluator judgment remain distinguishable.
First test whether Context or a versioned procedural correction solves the limitation; changing
weights requires a separate objective and transfer claim. Meeting capture, retained history,
accepted work and evaluation consent do not imply training admission. The passage participates in
[Ouroboros](../sepulcher/extensions/weaver/ouroboros.md) through settled records, with no ambient
harvesting or self-certified promotion.

## Records

| Record | Required content |
| --- | --- |
| **Training Intent** | Pins Principal, purpose, target capability, base digest, allowed data classes, resources, and promotion authority. |
| **Corpus Admission** | Freezes members and exclusions, provenance, transforms, privacy, consent/license, splits, objective, and approval. |
| **Dataset Manifest** | Pins examples, lineage groups, split digests, compiler, schema, statistics, and contamination checks. |
| **Recipe** | Pins trainer, dependencies, method, hyperparameters, randomness, precision, budgets, stops, and expected change. |
| **Training Run** | Pins exact inputs, environment, resources, logs, checkpoints, terminal state, and artifact digests. |
| **Candidate Bundle** | Binds base, candidate bytes, tokenizer and configuration changes, corpus/Recipe lineage, receipt, and compatibility. |
| **Promotion Decision** | Binds independent evidence, capability envelope, serving constraints, approver, rollout, rollback, and retirement. |

Names never replace digests. Every repeated execution receives a new Training Run identity and
receipt. Reproducibility must be proved by the execution contract; matching inputs or candidate
bytes cannot substitute for the later Run’s own lineage.

## Corpus admission

Riddle Cases/Outcomes, Mirror attribution, HitL decisions, Archive rows, success, refusal,
repetition, storage consent, and database access may nominate material; none grants training
rights. Before trainer access, admission proves:

- source, Run, artifact, producer, time, and transform lineage;
- exact purpose, subject, derivative and retention use, and approving Principal;
- training-specific consent, license, or authority;
- privacy minimization and retained redaction limits;
- target relevance and label quality;
- lineage-aware grouping of duplicates, revisions, sibling trajectories, and generated variants;
- immutable train, development, and sealed-holdout splits;
- base target, learning signal, unacceptable change, expected lift, regression limits, and stops.

The sealed holdout is fixed before training-facing generation and withheld from trainer,
augmentation, selection, and model judges used to tune. A negative ledger retains rejected,
redacted, and duplicate ids so retry/compiler cannot restore them. Missing provenance, authority,
privacy clearance/minimization, relevance, safe split, or uncontaminated holdout blocks admission.
Runtime data is opt-in: completion is not quality, and a blocked/refused Run can be useful if
objective and evidence support it. Redaction never erases source influence; privatization labels and
lineage remain attached through any narrower disclosure separately admitted by
[Security](09-security.md#portal-privatization-and-egress).

## Dataset compilation

The compiler receives one admitted corpus snapshot and produces an immutable Dataset Manifest.
Every field traces to a source or a versioned deterministic transform. Compilation preserves:

- role, tool, workflow and authority context;
- the distinction between observations, human labels, evaluator judgments and augmentations;
- truthful non-completion and split or lineage-group membership;
- filtering, redaction, truncation, normalization and sampling decisions; and
- audit statistics for balance, concentration, length, duplication and exclusion.

Schema-valid generation still requires evidence for its claims. Holdout answers, benchmark
solutions, evaluator rationales and downstream targets must remain outside prompts, retrieval,
augmentation, preference construction, trainer metadata and selection. A benchmark used to choose
the corpus must be disclosed and needs an untouched control before it can support independent
promotion. Only the admitted Manifest crosses to training.

## Training execution

The execution boundary receives one immutable Manifest, the exact base-model, tokenizer and
configuration digests, the Training Intent and Recipe, admitted secrets and network access, and
fresh Run-owned output locations. Its resource request names exact accelerators, memory,
storage, network and duration requirements together with the declared conflict domains it may
affect. Orchestrator resolves the affected set and owns readiness, affected-lease drain, conflict
resolution and restoration. Corpus meaning and trainer success remain with their owners.
Training has no universal priority: unused devices stay undisturbed, and policy may postpone or
refuse the request.

Filesystem, credential, network, process and resource controls must enforce the execution
boundary and leave receipts. A container or Coven label alone establishes none of these controls.
Local work has no privacy exemption. Remote work additionally records egress, provider custody
and retention, secret and network handling, returned artifacts and receipts. The trainer receives
no authority to enlarge its corpus with live traces, replace serving, widen resources or promote
its own result.

LoRA, QLoRA, full tuning, preference optimization, distillation and later methods remain
replaceable Recipe ports. Each adapter pins its base digest and runtime compatibility.

Failure or cancellation preserves terminal truth, logs, checkpoints and quarantined partials
for diagnosis. A completed checkpoint may be evaluated only as pinned candidate material through
the same independent handoff; it never becomes serving state by surviving the job. A partial is
never a Candidate Bundle. Retrying creates a new Training Run and receipt.

## Independent evaluation

A frozen Bundle enters [Riddle](34-evaluation.md) as an exact, immutable subject. Riddle may
neither alter the candidate nor change its corpus, Recipe or lineage. Its evidence must include:

- the sealed target holdout and matched Outcomes from the base or currently promoted baseline;
- named regression Trial Suites and adversarial or authority-boundary Cases; and
- quality, latency, memory and cost measured in a compatible serving Environment.

Errors, exclusions, uncertainty and evaluator calibration accompany those results. Loss,
development improvement, trainer-authored examples and self-grading remain diagnostics. A visible
Trial Suite establishes only the capability and safety claims its Environment can support.

## Promotion, serving, and rollback

Passing Riddle makes a candidate eligible for a decision. Owning policy and Magus/HitL decide
whether to promote it. Their decision binds the exact Bundle and Outcomes, admitted capabilities
and denied uses, compatible engine and base relation, rollout observations and stops, fallback
and rollback, and retention, quarantine and retirement rules.

Dispatcher consumes a registered capability; files alone cannot create one. Revisions remain
immutable, and supersession requires a new Bundle and decision. Rollback routes new work to an
earlier digest and quarantines the suspect candidate while preserving completed effects.

A later privacy, authority, license, contamination or leakage failure must be traced through the
exact Dataset, Run, Bundle, claims and promotion descendants. Policy may block serving or reuse,
quarantine or delete controlled artifacts, invalidate affected claims, and require clean
admission and rebuilding. Source deletion cannot untrain produced weights.

Retrieval remains appropriate for current, mutable, attributable knowledge. Exporting all history
to a provider, or allowing a trainer to select, evaluate and deploy itself, collapses the separate
authority this contract requires.

## Consequences

!!! success "Accepted"
    Corpus and weights gain auditable lineage; observation cannot silently become model bias;
    trainer and serving remain replaceable; holdouts/regressions separate optimization from release.

!!! failure "Cost"
    Review, grouping, sealed holdouts, large artifact custody, representative evaluation, and
    reproducibility consume substantial operator, hardware, and storage capacity; weight influence
    cannot be reliably removed by source deletion.

## Acceptance evidence

Soulforge remains **Designed** until one bounded recipe proves admissions/exclusions, lineage-safe
splits, sealed holdout, isolated immutable-input execution, candidate custody, independent Riddle
evaluation, explicit promotion, compatible serving, and rollback to a prior revision. State of Work
records the transition.
