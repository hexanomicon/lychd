---
title: Riddle
icon: material/help-rhombus-outline
---

# :material-help-rhombus-outline: The Riddle: Systemic Evaluation

> _“The Sphinx’s proper question is one for which the pleasing answer is wrong.”_

Riddle is **Designed**. [ADR 34](../../../adr/34-evaluation.md) defines one evaluation
jurisdiction: bind an exact subject revision to a versioned trial contract, keep observation
distinct from judgment, apply declared Rubrics through declared Evaluators, retain uncertainty,
and return only the evidence the trial can support.

That office carries no authority to execute unsafe work, select or grant an Animator, authorize
spending, repair or mutate a subject, publish, train, or promote. Its findings become input to
other owners, never their decision.

No runnable harness, maintained Case suite, evaluator or scorer store, capability matrix,
benchmark history, pass-at-k experiment, Altar route, or evaluation-driven Dispatcher update is
delivered. [State of Work](../../../state-of-the-work.md#riddle-evaluation) owns this maturity
boundary.

## Execution is not verdict

Riddle keeps trial health separate from evidentiary judgment:

```text
trial status   completed | subject_error | harness_error | evaluator_error | blocked
claim verdict  PASS | PARTIAL | FAIL | CONTRADICTED | UNKNOWN | DISPUTED
```

Trial status says what happened while attempting the evaluation. Claim verdict says what retained
evidence supports. A `blocked` trial never establishes claim failure; it records that the planned
trial could not produce the required observation.

This separation prevents infrastructure faults, subject errors, evaluator failures, and policy
blocks from masquerading as capability evidence. It also keeps a favorable verdict from becoming
permission, routing authority, causal proof, or automatic promotion.

A trial **Suite** groups Cases and their evaluation controls. A
[Composition Suite](../../../compositions/index.md#suites-do-not-dissolve-their-members) instead
forms a versioned graph of separately owned Compositions and typed handoffs. Sharing the word does
not merge their responsibilities.

## Choose the evidence passage

Start with [Trials](./trials.md) when constructing versioned Cases, controls, observations,
Rubrics, calibration, repetition, and immutable Outcomes.

<span id="vii-rubric-coverage-is-evidence-not-geometry"></span>

When healthy Outcomes must become scoped, expiring evidence for Dispatcher, Toll, or Soulforge to
consider under their own authority, continue to
[Capability claims](./capability-claims.md).

<span id="viii-the-returning-riddle-suite-feedback"></span>

Use [Returning findings](./returning-findings.md) to trace a downstream failure across an exact
Composition Suite and return inert evidence to the smallest supported boundary, without initiating
reverse execution.

Riddle names the wound only as far as evidence reaches. It does not take the knife.
