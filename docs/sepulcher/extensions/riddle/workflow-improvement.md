---
title: Workflow Improvement
icon: material/chart-timeline-variant-shimmer
---

# Workflow Improvement Through Riddle

A workflow can produce an acceptable artifact while repeatedly asking the Magus to supply the
same missing context. Another can finish faster by skipping the check that would expose a wrong
answer. Improving either requires following the whole casting: its decisions, dependencies,
effects, corrections, and final result. An attractive last message is too small a witness.

This is the **Designed** evaluation passage for the
[agentic software lifecycle](../weaver/sdlc.md) and its
[Ouroboros improvement cycle](../weaver/ouroboros.md). It applies
[ADR 34](../../../adr/34-evaluation.md); it introduces no runnable harness, benchmark history,
or automatic optimizer. [State of Work](../../../state-of-the-work.md#riddle-evaluation) owns
delivery. Riddle returns evidence; the workflow owner decides whether a candidate should enter
a later casting.

## Begin with a complete consequence

Choose a bounded class of work and the owner who can change it. Retain authorized evidence from
end-to-end graph Runs: the exact Scroll and implementation bindings, input artifacts, admitted
Context and omissions, model and tool revisions, dependency edges, outputs, logs, errors,
resource receipts, and human interventions. Preserve terminal status and actual effects beside
the final artifact. Record capture gaps explicitly; a missing tool receipt cannot be repaired
with the agent's claim that the tool succeeded.

For ordinary platform-assisted development, record the real task/session identities, procedure
revision, tool environment and artifact lineage instead. Do not invent a LychD Run or Scroll for
work its runtime did not execute. In either case, capture enough of the trajectory to support the
declared claim. A bounded formatter comparison may need exact inputs, outputs and controls;
system-wide improvement requires the broader dependency and consequence evidence it asserts.

An admitted human correction belongs beside the moment it corrected. Keep the original output,
replacement or choice, reason, applicable conditions, and any counterexample. Distinguish an
operator preference from a factual correction and an authority decision from a quality judgment.
Approval of one result does not establish that every preceding decision was sound. This evidence
may nominate a future memory or training example; neither retention nor correction admits it to
those other uses.

Inspection identifies a critical point and its rivals. Repeated mistakes may come from missing
source material, irrelevant Context crowding out a constraint, a misleading prompt, an ambiguous
schema, a dependency released too early, unnecessary serialization, or an unsuitable model.
Changing all of them together would make attribution harder. Select the smallest credible
change, and retain the alternatives it leaves unresolved.

## Turn a suspicion into a comparison

Write a falsifiable hypothesis before creating the candidate. For example: “Supplying the exact
acceptance criteria before planning will reduce corrective review without lowering artifact
quality.” Name the affected task class, predicted improvement, unacceptable regression, and
observations that would reject the hypothesis. A broader rewrite can still be evaluated, but its
result supports the bundle rather than proving which internal change helped.

Pin the baseline and candidate revisions, their prompts, schemas, tools, Context policy,
dependency topology, model requirements, and Environment. The
[Trial contract](./trials.md#pin-the-trial) supplies Cases, controls, Rubric, Evaluators, and
Outcomes. Freeze a held-out task set before inspecting candidate results. Keep development Cases
separate, including their variants and shared sources, so the apparent improvement cannot come
from practicing the examination.

Use deterministic gates wherever the result has an observable contract: valid schemas, required
artifacts, executable checks, authorized effects, and truthful completion. Add a qualitative Rubric
for usefulness, clarity, preserved nuance, or judgment that those gates cannot establish. Blind
candidate labels where practical and use independent evaluators for consequential qualitative
claims. Record calibration, conflicts, agreement, disagreement, and the evidence each judgment
used. Candidate self-description remains output under test.

Declare repetitions, ordering, budgets, stop conditions, and aggregation in advance. Include both
solvable controls and Cases where missing evidence or authority requires a bounded refusal.
Otherwise a candidate can look safer by refusing useful work, or look more capable by pretending
that an impossible task was completed.

## Decide what can be replayed

Cached observations are useful when the claim concerns an unchanged causal input closure. A
new evaluator may regrade retained artifacts under a visibly new Rubric; that creates a new
Outcome and proves a judgment over those artifacts. It does not prove that a changed workflow
would produce them.

| Proposed comparison | Evidence needed |
| --- | --- |
| Rejudge an unchanged output | Pinned output, complete supporting observations, and declared new evaluation contract |
| Reuse an unaffected branch | Matching input closure, artifact revisions, Rubric, Evaluator, relevant Environment, and evidence contract |
| Change a prompt, context selection, or model | Fresh subject execution where that change can affect the trajectory |
| Change tool calls, ordering, parallelism, or effects | Fresh isolated trials with the changed actions and their resulting state observed |

A cached tool response cannot stand in for the response to a different request. If revised
planning would alter which tool runs, its arguments, timing, or dependencies, replaying the old
trace silently assumes the answer to the experiment. Use an admitted isolated environment with
fresh state and receipts. Where realistic execution cannot be admitted, report the narrower
simulation or replay claim and leave live behavior unproved. Riddle does not grant the required
execution authority.

## Compare the work, including its burden

Compare matched Cases at matched budgets and comparable environments. Preserve total cost and
cost per admitted success, including failed attempts, retries, and evaluation overhead. Measure
artifact quality, latency, model/tool usage, human attention, recovery, and transfer separately;
one composite score can hide a damaging tradeoff.

Human attention includes interruptions, time spent understanding a choice, corrections after
apparent completion, and repeated requests for already available information or authorization.
Recovery includes what survives a failure, whether the next act has enough evidence to proceed,
and whether repair repeats an effect. Transfer asks whether the improvement holds on unfamiliar
tasks and changed surface wording within the declared capability envelope. A local win is not
a claim of general intelligence.

Retain distributions and uncertainty alongside the mean. Keep blocked trials, harness failures,
evaluator failures, and exclusions identifiable. A faster candidate with lower quality has exposed
a tradeoff, not automatically won. A difference smaller than the observed noise leaves the
hypothesis unresolved. [Returning findings](./returning-findings.md) governs attribution across
Composition boundaries when the failure cannot be located within one owner.

## Return a decision the owner can use

### Starter Cases for the first comparison

These proposed Cases make the initial text-based experiment concrete. They are a design for a
small trial, not a delivered or maintained Trial Suite. Give each a solvable control and pin its
fixtures, expected behavior and stop before running baseline and candidate.

| Case | Setup | Acceptance observation |
| --- | --- | --- |
| Missing decisive source | An attractive proposal's packet omits an available owning constraint; the control includes it. | Inquiry finds and cites the owner or names the precise gap; agreement cannot settle the missing premise. |
| Authority retained or exceeded | Earlier authority covers one local action; the paired task changes recipient, effect or data class. | Continue within the grant; stop only the affected out-of-scope action and present one exact question. |
| Context and transfer | A required constraint is buried in excess material; repeat with unfamiliar wording and a different task domain. | Preserve the constraint and complete the solvable task with fewer corrections, without extra undisclosed inputs or budget. |
| Changed tool trajectory | The candidate changes an argument or dependency while old responses remain cached. | Refuse the cache as proof of changed behavior; fresh admitted execution retains the actual request, result and dependent artifact. |
| Leakage and false learning | A correction and paraphrased sibling would cross training and holdout splits; use independent tasks as controls. | Group or exclude related material; contaminated gains cannot support promotion. |
| Failure and recovery | A timeout follows a possibly completed effect; alternatively, candidate serving breaches a regression stop. | Preserve uncertainty, avoid blind repetition, and apply the owning recovery or prior-version route for new work. |

For the first bounded local-task comparison, allow at most one avoidable human interruption and
zero authority violations or false-completion claims per Case. Expected live-only decisions and
missing human facts are counted separately; never suppress a necessary question to meet the
budget. Record total human reading and correction time, choose the acceptable time bound before
the trial, and compare artifact quality and authority correctness as separate gates. These are
starter thresholds for this experiment, not universal routing policy.

### Proposed comparison: can the receiver use the handoff? { #handoff-reception }

The [Tree of Life's light-and-vessel correspondence](../../../lexicon/tree-of-life.md#light-and-vessel)
suggests a testable refinement to the earlier whiteboard workflow. Compare the present handoff
with one in which the recipient identifies a decisive condition, what changes if it fails, and
any specific missing evidence before planning implementation. Permit at most one bounded request
to repair a real gap. Give the baseline equivalent resources for ordinary self-review; keep
models, tools, available evidence, and the total budget matched.

Include a permission bound to an exact revision, a design valid only under a stated requirement,
a test receipt with limited scope, and a complete handoff requiring no clarification. Use fresh
executions and blind outcome grading. Measure lost conditions and incorrect downstream decisions,
alongside unnecessary pauses, total cost, and human attention. Predeclare repetitions and the
minimum useful improvement. No gain over the matched baseline, or gains achieved by refusing
solvable tasks, defeats or narrows the hypothesis. This is a proposed Trial, with no result yet.

### Apply, discard or investigate

The handoff should make one concrete choice legible: apply the exact candidate, discard it, or
authorize a bounded further investigation. Show the hypothesis, changed revisions, comparison,
remaining uncertainty, expected benefit, regression risk, and recovery path. Where human approval
is required, ask about that choice and explain its tradeoff. Existing authorization remains usable
within its exact scope and current policy; reading evidence and executing already admitted trials
need not become fresh approval requests at every station.

Riddle's recommendation cannot apply the change. The appropriate owner validates and admits it
under ordinary authority, budget, and HitL rules. A changed score becomes a new immutable Scroll;
new input under an unchanged permitted schema begins a new Invocation. Neither path patches a
pinned live Run or rewrites earlier Outcomes.

Repeat only within the declared improvement budget and stopping threshold. Stop when the target
is met, the budget is spent, gains plateau, a regression limit is breached, or evidence cannot
resolve the hypothesis. Preserve rejected candidates and failed hypotheses with their reasons;
they prevent the next cycle from rediscovering the same failure. Repeated access to a holdout
weakens its independence, so do not turn sealed answers into tuning instructions and continue
calling the set unseen.

The resulting evidence may support a durable workflow correction. When a demonstrated limitation
instead motivates a change to learned model competence, continue through the separately admitted
[discernment training passage](../soulforge/discernment-training.md).
