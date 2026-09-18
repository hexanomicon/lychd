---
title: 34. Evaluation
icon: material/chart-bell-curve-cumulative
---

# :material-chart-bell-curve-cumulative: 34. Evaluation

!!! abstract "Context"
    A capability must be evaluated for its declared task under the tools, authority, hardware,
    dialect, and consumer conditions in which it will be used. [Drift](../sepulcher/extensions/drift/index.md)
    keeps those conditions versioned and its findings attributable, so a result can be assessed
    against the claim it is meant to support.

## Decision

Drift is LychD's singular evaluation jurisdiction: it evaluates how an exact subject revision
meets or departs from a declared goal. It defines Cases and Trial Suites, captures observations,
applies versioned Rubrics, reports uncertainty, and returns bounded findings. It does not execute
unsafe payloads or own Tomb; select Animator/capability; authorize spend, publication,
repair, or deployment; define Persona; mutate Pattern, Composition, or artifact; admit training;
or promote a Soulstone. Execution, Dispatcher, Toll, Spellweaver, Mirror, Smith, Soulforge, and HitL
keep those effects. Evaluation is evidence offered to policy, never policy disguised as a score.

!!! warning "Delivery boundary"
    Drift is **Designed**. There is no harness, maintained Trial Suite, evaluator store,
    capability matrix, benchmark history, Altar route, or Dispatcher update driven by evaluation.
    [State of Work](../state-of-the-work.md#drift-evaluation) owns delivery.

## The declared goal

The requesting owner expresses the goal through a Case's expected and forbidden behavior and a
Rubric's criteria, thresholds, and missing-evidence policy before the trial. Applicable authority,
constraints, and permitted effects remain part of the trial conditions. Drift evaluates that
contract; its findings cannot revise the goal or authorize a method of reaching it.

Deviation from the goal may be categorical, qualitative, or measured along separate axes. A first
trial needs no earlier version or time series: its reference is the declared goal. Baseline/candidate
comparisons and repeated trials show how that relation changes. An unchanged failure remains a
failure; a large behavioral change may be an improvement. Missing evidence establishes neither
success nor a measured distance from the goal.

A revised goal requires revised Cases or Rubrics and new Outcomes. Earlier findings retain their
original contract; the subject cannot move the acceptance criteria after seeing the result.

## Trial contract

| Record | Required content |
| --- | --- |
| **Case** | input/fixtures, expected and forbidden behavior, oracle, effect class, stop |
| **Trial Suite (`TrialSuite@1`)** | versioned Cases/controls, order, repetitions, aggregation |
| **Rubric** | criteria, verdict vocabulary, thresholds, missing-evidence policy, revision |
| **Evaluator** | kind/identity/revision, independence, calibration, limitations |
| **Environment** | subject/prompt/tool/dependency/hardware/harness/state/budget/policy revisions |
| **Outcome** | observations, measures, verdicts, uncertainty, errors, cost, latency, evidence |

Changed subject, prompt, schema, Rubric, Evaluator, or Environment creates a new Outcome; it
cannot rewrite an earlier result. Libraries implement this port but do not own evidence or routing.
Drift first retains what was observed: process exits, files, rows, tool requests, admitted
effects, resource measurements and provider receipts. A criterion match, quality grade,
attribution claim or judge score is a judgment over those observations and must remain separately
identifiable. Model self-report is output under test. Mechanically observable receipts outrank
textual similarity, and missing evidence stays missing. Shadow may isolate candidates and Tomb
may execute them; each contributes typed observations to this judgment.

```text
trial status: completed | subject_error | harness_error | evaluator_error | blocked
claim verdict: PASS | PARTIAL | FAIL | CONTRADICTED | UNKNOWN | DISPUTED
```

Unavailable dependency is not subject failure; a hidden validator precondition is a harness/state
contract candidate. Refusal on an impossible task is not success unless matched solvable controls
show action when action is possible.

## Adversarial evidence and calibration

**Adversarial Cases** pressure a boundary: forbidden authoritative requests, false premises, demanded
certainty amid missing evidence, contradictions/impossible completion, repeated nudges, recoverable
distortion, and attempted tool/memory/identity/completion claims beyond supplied evidence. Matched
positive and negative controls record pressure round/order, recovery, over-refusal, truthful
non-completion, and downstream contamination separately—not a mutable “integrity” scalar. Magus
dialect perturbations are still test data with provenance, scope, and release rules.

A Trial Suite declares repetitions and stopping rules before it runs. It retains distributions,
trial order, applicable random seeds, blocked and error trials, and exclusions. Non-deterministic
Evaluators are calibrated against labelled controls and known ambiguity. Qualitative work records
independent agreement and disagreement where the judgment warrants it.

An LLM judge is a declared, bounded Evaluator. Its prompt, revision, inputs, lineage, calibration
and conflicts belong to the Environment; hidden chain-of-thought is never required. Sealed Cases
and holdouts protect against tuning. Leakage, duplicates, unstable harnesses and changes in
Evaluator behavior invalidate the claims they undermine while leaving independently supported claims intact.

## Evaluating a workflow change

[Workflow improvement](../sepulcher/extensions/drift/workflow-improvement.md) applies this trial
contract to an exact score, prompt, schema, Context policy or implementation revision. The claim
must include relevant trajectory evidence, failures and human burden as well as terminal artifact
quality. It pins baseline and candidate, matched budgets, controls, uncertainty and stopping rules
before comparison. Observations and qualitative judgments remain distinguishable.

Cached evidence can support only its unchanged input and evidence closure. Regrading a retained
artifact creates a judgment over that artifact; it cannot establish that a changed workflow
produces the same trajectory. Changed actions or relevant state require fresh admitted trials.
The owner may adopt, reject or investigate the resulting candidate under its authority, without
rewriting earlier Outcomes or a live Scroll. A later training hypothesis requires separate
[Soulforge](33-training.md) admission and protected holdout evidence.

### Historical exploration replay

Drift may evaluate a [versioned exploration strategy](31-simulation.md#versioned-exploration-strategy)
against an immutable collection of recorded branch histories. The Environment pins the histories,
observation-disclosure and transition rules, cost accounting and stopping conditions. The subject
strategy sees only observations revealed by its preceding replay decisions; hidden descendants
and their outcomes remain unavailable. An absent continuation stays unknown and cannot become
an invented observation or a witnessed failure.

Such an Outcome measures strategy behavior on that recorded search space. It does not establish
that changed requests, dependencies, timing or parallel execution would reproduce those outcomes.
Keeping the baseline among candidates can prevent a worse selection on the same replay objective
and history; it gives no guarantee for later histories or live work. Effectiveness outside replay
requires fresh admitted trials, protected evaluation and independently observed state. Report
represented execution costs separately from actual replay, strategy-development and validation
costs. The [operating passage](../sepulcher/extensions/drift/workflow-improvement.md#replay-an-exploration-history)
shows how to prepare that comparison.

### Evidence of recursive improvement

A recursive-improvement claim identifies the changed mechanism and its exact baseline/candidate
revisions, motivating evidence, adoption decision and later improvement attempt that actually used
it. This establishes structural reuse. An effectiveness claim additionally compares the successors
produced by the original and revised mechanisms from comparable starting subjects and evidence,
under matched total budgets and independent evaluation. Retain transfer results, regressions,
uncertainty and stopping decisions alongside improvement across rounds. A better task artifact
alone cannot establish a better mechanism for producing future improvements.

Development feedback remains separate from protected assessment. Revising an Evaluator creates
a separately calibrated candidate and new Outcomes; the subject cannot redefine its own acceptance
criteria. [Ouroboros](../sepulcher/extensions/weaver/ouroboros.md#what-the-next-round-inherits)
connects these claims to the owning creation and adoption passages.

## Capability claims and routing

Drift may derive a scoped claim from a healthy Trial Suite. Each claim pins:

- Animator, model, adapter, tool, and configuration revisions;
- task class, Cases, Rubric, Evaluators, and Environment;
- sample, controls, distribution, uncertainty, and noise;
- cost and latency per admitted success, including failures;
- creation, expiry, and evidence references.

There is no universal rank: accuracy, latency, VRAM, cost, restraint, and tool behavior
are distinct policy-valued axes. Dispatcher may consume fresh admitted claims only after Ward,
compatibility, availability, privacy, and authority construct an eligible set. Missing/stale
evidence leaves the Dispatcher's documented deterministic readiness order in force rather than
inventing an intelligence floor. [Dispatcher selection](22-dispatcher.md#candidate-selection)
owns that order, including the treatment of stale or erroneous cached observations. It selects
one candidate; failure of that selection does not retry another candidate. Toll may use the same
measures in spend policy
without making one local or frontier win universal routing authority.

## Evaluation before and after training

Soulforge pins any proposal to expected change, baseline Outcomes, holdout evidence, and
unacceptable regressions. Post-training work uses that contract or makes every change visible;
training-facing improvement cannot promote. Drift returns evidence, neither selects corpus nor
registers model; passing an identity/behavior Trial Suite grants no Persona, Sigil, tool, or privileged
route.

## Returning findings across a Composition Suite

An exact, version-pinned [Composition Suite](../compositions/products-and-suites.md#compositions-relate-without-nesting)
may return a consumer consequence as evidence. This requires the member Composition and Pattern
revisions, handoffs, failing observation, Rubric, Evaluator, Environment, verdict and uncertainty,
and the declared artifact and evidence dependencies. Returning evidence does not reverse execution
or merge member rows, secrets, Sigils, approvals, policies or effect authority.

| Inert record | Law |
| --- | --- |
| `CompositionSuiteFindingSet@1` | Binds the Composition Suite and Rubric, subjects, Environment, observations and measures, Evaluator, verdicts and uncertainty. |
| `AttributionCandidate@1` | Names a possible boundary, supporting and conflicting evidence, rival explanations and uncertainty; it does not establish causal certainty. |
| `InvalidationSet@1` | Identifies claims whose support fails and claims with intact closure. |
| `CorrectionRequest@1` | Names a bounded owner delta, preserved constraints, evidence, scope and repair budget. |

Drift follows declared dependencies backwards to the smallest cut supported by the evidence.
The nearest producer is not automatically the cause. Reuse requires the same complete input
closure, artifact revisions, Rubric, Evaluator, relevant Environment and evidence contract. A
failing consumer alone cannot condemn shared artifacts.

Missing lineage, flakiness, contagion, capture or rival explanations may leave the verdict
`UNKNOWN` or `DISPUTED`. They can justify at most a broader bounded trial; they cannot justify
reconstructed history or convenient blame.

The returned records authorize no spend, publication, deletion, training, promotion or mutation.
Spellweaver may admit a new forward Invocation under ordinary policy and HitL. Earlier Runs and
Outcomes remain in its lineage.

## Consequences

!!! success "Accepted"
    Claims are reproducible and scoped; receipts, judgment, and absence remain distinct; pressure
    measures restraint without rewarding blanket refusal; consumers retain their own authority.

!!! failure "Cost"
    Cases, controls, environments, calibration, and evidence maintenance cost ongoing human,
    hardware, and provider effort; observability may leave attribution disputed and claims stale.

## Acceptance evidence

Drift remains **Designed** until one versioned Trial Suite with controls distinguishes subject/harness/
evaluator failure, reproduces an Outcome, calibrates each non-deterministic Evaluator, preserves raw
evidence/uncertainty, and proves routing/repair consumers reapply their own policy. State of Work,
not this ADR alone, records promotion.
