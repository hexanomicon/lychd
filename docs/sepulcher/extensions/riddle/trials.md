---
title: Trials
icon: material/flask-outline
---

# :material-flask-outline: The Trials: Evidence Before Verdict

A subject refuses an impossible task. Beside it, a matched control offers a solvable version with
the same surface pressure. Refusing both reveals blanket timidity; distinguishing them may reveal
judgment. Riddle observes both before drawing a conclusion.

Trials are **Designed**; no trial path runs. [State of
Work](../../../state-of-the-work.md#riddle-evaluation) records delivery;
[ADR 34](../../../adr/34-evaluation.md) owns the accepted trial law.

## Pin the trial

A trial fixes six records before execution:

| Record | Pinned meaning |
|---|---|
| **Case** | Exact input, fixtures, expected and forbidden behavior, oracle, effect class, and stop condition |
| **Suite** | Versioned Cases, matched controls, ordering, repetition policy, and aggregation rules |
| **Rubric** | Criteria, verdict vocabulary, thresholds, missing-evidence policy, and revision |
| **Evaluator** | Kind, identity, revision, independence, calibration evidence, and declared limitations |
| **Environment** | Subject revision, prompts, tools, dependencies, hardware, harness, state, budgets, and relevant policy |
| **Outcome** | Observations, measurements, verdicts, uncertainty, errors, cost, latency, and retained evidence |

A trial Suite groups Cases and evaluation controls. A
[Composition Suite](../../../compositions/index.md#suites-do-not-dissolve-their-members) is a
versioned graph of separately owned Compositions and typed handoffs. Changing the subject, prompt,
tool schema, Rubric, Evaluator, or Environment produces a new Outcome rather than revising the old
trial's answer.

## Observe before judging

Mechanical observation records exit status, files, database rows, tool requests, admitted effects,
resource measurements, and provider receipts. Evaluation applies criteria, grades, attribution,
or a declared model judge. Direct receipts outrank textual similarity when an effect can be
observed directly.

Shadow may hold candidate worlds and Tomb may execute an admitted unsafe payload; Riddle owns
neither isolation nor execution. An LLM judge is a declared, calibrated Evaluator with recorded
limits, never an oracle. Hidden chain-of-thought supplies no evidence. Model prose about its own
success is an output under test.

```text
trial status   completed | subject_error | harness_error | evaluator_error | blocked
claim verdict  PASS | PARTIAL | FAIL | CONTRADICTED | UNKNOWN | DISPUTED
```

Status describes execution. Verdict describes what retained evidence supports. The declared Case
and Environment decide whether an unavailable dependency or hidden-validator condition blocks the
trial or exposes a harness or state-contract failure; neither condition is automatically a subject
error. `blocked` does not mean `FAIL`. Missing evidence remains missing: its verdict is `UNKNOWN`.
Unresolved conflict in retained evidence or among rival Evaluators is `DISPUTED`.

## Pressure, repetition, and coverage

Sphinx Cases apply forbidden methods, false premises, missing information, impossible constraints,
repeated nudges, recoverable dialect distortion, and unsupported claims about tools, memory,
identity, or completion. Every trap receives positive and negative controls. The Outcome records
pressure round, order, recovery, over-refusal, truthful non-completion, and downstream
contamination separately.

Repetition and stopping rules are declared before results are inspected. Outcomes retain
distributions, order, seeds where applicable, blocked attempts, errors, and exclusions. Evaluators
are calibrated against labelled controls and known ambiguity; independent disagreement remains
visible.

Sealed Cases and holdouts resist tuning leakage. Coverage binds an exact Rubric to an immutable
subject revision and retained evidence. Mention, textual similarity, or a nearby receipt cannot
fill an uncovered criterion. One dramatic success or failure does not become certainty.

Healthy Outcomes may proceed to [Capability claims](./capability-claims.md). Findings that must
return to an owning boundary proceed through [Returning findings](./returning-findings.md).
