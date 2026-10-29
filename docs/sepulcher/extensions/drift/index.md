---
title: Drift
icon: material/compass-outline
---

# :material-compass-outline: Drift: Evaluation Against a Declared Goal

> _By which star will you judge the wandering?_

To judge a result, first say what the work was meant to achieve. **Drift** makes that declared
goal testable through Cases and Rubrics, then binds each trial to the exact subject revision
being examined. Declared Evaluators compare retained observations with those criteria and return
only findings the evidence supports. Their findings say where actual behavior and outcomes met or departed from the goal, and preserve
what remains uncertain. [ADR 34](../../../adr/34-evaluation.md#the-declared-goal) owns this
evaluation jurisdiction.

That office carries no authority to execute unsafe work, select or grant an Animator, authorize
spending, repair or mutate a subject, publish, train, or promote. Its findings become input to
other owners, never their decision.

Drift is **Designed**; no runnable evaluation path is delivered. [State of
Work](../../../state-of-the-work.md#drift-evaluation) records its maturity boundary.

## Make the goal testable

A workflow may deliver the right artifact while exceeding its declared budget or omitting a
required check. Its Case and Rubric must name those obligations before execution. Drift then
reports where behavior met, missed, or left the criteria unresolved, retaining the evidence for
each finding. A later candidate can improve one dimension while regressing on another.

The same method applies to a first attempt: the declared goal supplies the reference. Historical
comparison is optional, and several criteria need not collapse into one distance or score.
[Trials](trials.md#pin-the-trial) shows how to fix that reference before the result is known.

## Execution is not verdict

A trial can be blocked by policy before it produces the evidence needed to judge its subject.
Its execution status records that block; it cannot turn the absence of a trial into claim
failure. [Trials](trials.md) supplies the separate status and verdict vocabularies, including
how to distinguish infrastructure, subject, and evaluator failures.

A **Trial Suite** (`TrialSuite@1`) groups Cases and evaluation controls; a
[Composition Suite](../../../compositions/products-and-suites.md#compositions-relate-without-nesting) coordinates
separately owned applications. These remain separate contracts.

A favorable verdict supplies no permission, routing authority, causal proof, or automatic promotion.

## Choose the evidence passage

Start with [Trials](./trials.md) when constructing versioned Cases, controls, observations,
Rubrics, calibration, repetition, and immutable Outcomes.

When healthy Outcomes must become scoped, expiring evidence for Dispatcher, Toll, or Soulforge to
consider under their own authority, continue to
[Capability claims](./capability-claims.md).

Use [Returning findings](./returning-findings.md) to trace a downstream failure across an exact
Composition Suite and return inert evidence to the smallest supported boundary, without initiating
reverse execution.

Drift locates the departure from the goal only as far as evidence reaches. The receiving owner
decides whether and how to correct it.

Evaluation can inform Creation before promotion and after use. A trial of the software candidate
asks whether it meets its goal; a trial of the workflow asks whether the method produces better
work. [Workflow improvement](workflow-improvement.md#evaluate-at-two-scales) separates those
subjects and follows the evidence into an owner decision. [Ouroboros](../weaver/ouroboros.md)
places both passages beside memory and training.
