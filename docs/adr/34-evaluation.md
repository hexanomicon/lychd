---
title: 34. Evaluation
icon: material/chart-bell-curve-cumulative
---

# :material-chart-bell-curve-cumulative: 34. Evaluation

!!! abstract "Context"
    A capability must be evaluated for its declared task under the tools, authority, hardware,
    dialect, and consumer conditions in which it will be used. [Riddle](../sepulcher/extensions/riddle/index.md)
    keeps those conditions versioned and its findings attributable, so a result can be assessed
    against the claim it is meant to support.

## Decision

Riddle is LychD's singular evaluation jurisdiction: it defines Cases and Trial Suites, captures
observations, applies versioned Rubrics, reports uncertainty, and returns bounded findings. It does
not execute unsafe payloads or own Tomb; select Animator/capability; authorize spend, publication,
repair, or deployment; define Persona; mutate Pattern, Composition, or artifact; admit training;
or promote a Soulstone. Execution, Dispatcher, Toll, Spellweaver, Mirror, Smith, Soulforge, and HitL
keep those effects. Evaluation is evidence offered to policy, never policy disguised as a score.

!!! warning "Delivery boundary"
    Riddle is **Designed**. There is no harness, maintained Trial Suite, evaluator store,
    capability matrix, benchmark history, Altar route, or Dispatcher update driven by evaluation.
    [State of Work](../state-of-the-work.md#riddle-evaluation) owns delivery.

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
Riddle first retains what was observed: process exits, files, rows, tool requests, admitted
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

**Sphinx** Cases pressure a boundary: forbidden authoritative requests, false premises, demanded
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
and holdouts protect against tuning. Leakage, duplicates, unstable harnesses and evaluator drift
invalidate the claims they undermine while leaving independently supported claims intact.

## Capability claims and routing

Riddle may derive a scoped claim from a healthy Trial Suite. Each claim pins:

- Animator, model, adapter, tool, and configuration revisions;
- task class, Cases, Rubric, Evaluators, and Environment;
- sample, controls, distribution, uncertainty, and noise;
- cost and latency per admitted success, including failures;
- creation, expiry, and evidence references.

There is no universal rank: accuracy, latency, VRAM, cost, restraint, and tool behavior
are distinct policy-valued axes. Dispatcher may consume fresh admitted claims only after Ward,
compatibility, availability, privacy, and authority construct an eligible set. Missing/stale
evidence leaves the Dispatcher's documented deterministic readiness order in force rather than
inventing an intelligence floor. Current v1 prefers open admission, then active capability, then
warmth, with Animator name and capability key as tie-breakers. It selects one candidate; failure
of that selection does not retry another candidate. Toll may use the same measures in spend policy
without making one local or frontier win universal routing authority.

## Evaluation before and after training

Soulforge pins any proposal to expected change, baseline Outcomes, holdout evidence, and
unacceptable regressions. Post-training work uses that contract or makes every change visible;
training-facing improvement cannot promote. Riddle returns evidence, neither selects corpus nor
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

Riddle follows declared dependencies backwards to the smallest cut supported by the evidence.
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

Riddle remains **Designed** until one versioned Trial Suite with controls distinguishes subject/harness/
evaluator failure, reproduces an Outcome, calibrates each non-deterministic Evaluator, preserves raw
evidence/uncertainty, and proves routing/repair consumers reapply their own policy. State of Work,
not this ADR alone, records promotion.
