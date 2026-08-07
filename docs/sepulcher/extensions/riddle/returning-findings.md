---
title: Returning Findings
icon: material/source-merge
---

# :material-source-merge: Returning Findings: The Smallest Supported Cut

An artifact passes its producer's checks and reaches two independent consumers. One succeeds; the
other fails under a different Environment. That failure neither condemns the artifact nor
identifies the producer through proximity. Riddle instead performs a bounded dependency walk
across the exact Suite and its retained evidence, stopping where observations can distinguish one
responsible boundary from its rivals.

Returning findings are **Designed**; no feedback path runs, and reverse execution is forbidden.
Maturity remains in
[State of Work](../../../state-of-the-work.md#riddle-evaluation);
[ADR 34](../../../adr/34-evaluation.md#returning-findings-across-a-suite) owns the evidentiary law,
while [Weaver](../../../adr/28-workflow.md#returning-findings) owns any later executable admission.

## Fix the graph under examination

Entry requires an exact, version-pinned
[Composition Suite](../../../compositions/index.md#suites-do-not-dissolve-their-members) graph;
each member Composition and Pattern revision; retained artifact and Intent handoffs; the downstream
failing observation; its Rubric, Evaluator, Environment, verdict, and uncertainty; and declared
dependencies between artifacts and evidence.

The Suite coordinates separately owned applications. It does not merge their domain rows, secrets,
Sigils, approvals, policies, or effect authority. A finding must therefore preserve which owner
produced each artifact, which consumer observed it, and which contract connected them.

Four inert records carry the result:

| Record | Contents |
|---|---|
| **`SuiteFindingSet@1`** | Binds Rubric, Suite, subjects, Environment, observations, measurements, Evaluator, verdicts, and uncertainty |
| **`AttributionCandidate@1`** | Names a possible responsible boundary, supporting and conflicting evidence, rivals, and uncertainty; never causal certainty |
| **`InvalidationSet@1`** | Names claims whose support no longer survives and claims whose complete evidence closure remains intact |
| **`CorrectionRequest@1`** | Gives one owner a bounded target delta, preserved constraints, evidence, proposed scope, and repair budget |

None can grant authority, authorize spending, delete, mutate, publish, promote, or train. Return
travels as evidence, not reverse Graph edges.

## Walk only as far as evidence supports

Riddle follows declared dependencies backward until evidence distinguishes the narrowest boundary.
The search stops at the smallest supported cut, not the nearest convenient producer. Earlier
evidence may be reused only when its complete input closure, artifact revisions, Rubric, Evaluator,
relevant Environment, and evidence contract still match.

One failing consumer does not condemn a shared artifact for independent consumers. The
`InvalidationSet@1` names claims whose complete support has broken while preserving every intact
closure. Missing lineage, flaky measurements, shared-input contagion, Evaluator capture, or
unresolved rival explanations produce `UNKNOWN` or `DISPUTED`. If policy permits recovery, the
next step is a broader bounded trial—not reconstruction of unobserved history or assignment of
blame.

A deterministic localized regression with complete lineage is the positive control: it may
support a narrow `AttributionCandidate@1` and `CorrectionRequest@1`. Negative controls vary the
downstream Environment, induce Evaluator failure, and compare independent consumers without
contaminating them. These comparisons defend against proximity attribution. Categorical
responsibility is refused when lineage or Evaluator independence is absent.
[Trials](./trials.md) owns the deeper control design.

## Return through ordinary forward admission

Weaver may admit a `CorrectionRequest@1` only as a new forward Invocation under ordinary
validation, budget, authority, consent, cancellation, and termination rules. It cannot resume an
old producer arbitrarily, mutate the retained artifact, or inherit authority from the failing
consumer. Prior Runs and Outcomes remain immutable lineage.

Branches qualify for reuse only while their complete evidence closure still matches. Exhausted
repair budgets, repeated unsupported findings, or unresolved attribution terminate honestly. Any
resulting capability claim follows [Capability claims](./capability-claims.md) and must earn
support from new retained evidence.
