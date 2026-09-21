---
title: Workflow Improvement
icon: material/chart-timeline-variant-shimmer
---

# Workflow Improvement Through Drift

A workflow can produce an acceptable artifact while repeatedly asking the Magus to supply the
same missing context. Another can finish faster by skipping the check that would expose a wrong
answer. Improving either requires following the whole casting: its decisions, dependencies,
effects, corrections, and final result. An attractive last message is too small a witness.

This is the **Designed** evaluation passage for the
[Creation workflow](../weaver/creation.md) and its
[Ouroboros improvement cycle](../weaver/ouroboros.md). It applies
[ADR 34](../../../adr/34-evaluation.md); it introduces no runnable harness, benchmark history,
or automatic optimizer. [State of Work](../../../state-of-the-work.md#drift-evaluation) owns
delivery. Drift returns evidence; the workflow owner decides whether a candidate should enter
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
simulation or replay claim and leave live behavior unproved. Drift does not grant the required
execution authority.

### Replay an exploration history

[Dream-RSI](https://arxiv.org/html/2609.14858v1), a September 2026 research preprint, suggests a
bounded use of history: try alternative exploration strategies against recorded discovery trees
before paying for new discovery attempts. Its search controller changes while the underlying
coding agent and evaluator remain fixed. [ADR 34](../../../adr/34-evaluation.md#historical-exploration-replay)
owns the narrower claim LychD may make from this mechanism.

Prepare an immutable snapshot of admitted histories with exact parents, workspace/artifact
revisions, observations, costs, failures and capture gaps. Declare how a replay decision reveals
a recorded continuation and handles an exhausted branch. Reset the strategy's per-trial state;
reveal only the root initially and then the observations reached by its decisions. Keep hidden
descendants inaccessible to the strategy. History used to develop its code is development data,
including when the strategy author has inspected it.

Compare candidate strategies and the unchanged baseline under one fixed objective and replay
budget. Retain the chosen paths and their costs, including rejected candidates. An unrecorded
continuation remains unknown. Reordering recorded attempts measures a traversal of that history;
shared-state interactions, changed requests and real concurrency need fresh execution. A replay
win justifies a bounded follow-up trial. It cannot certify future performance or authorize adoption.

### Proposed pilot: exploration strategy

Start with a small pure-function optimization task whose correctness can be checked against a
reference implementation. The following is a suggested experiment, with no runnable harness or
result yet:

1. Retain several bounded discovery histories using a fixed strategy, fixed coding model and
   fixed evaluator. Isolate candidate execution and record snapshots, failed attempts and costs.
2. Use development histories to propose a small number of strategy revisions. Compare their
   replay results with the original strategy and freeze one candidate before protected assessment.
3. Run the frozen candidate and baseline on fresh, held-out problem instances from comparable
   starting artifacts, with matched total budgets and predeclared repetitions. Protect independent
   correctness checks from the strategy-development process. Separate discovery feedback from
   final assessment; keep related variants in the same split.
4. Compare validated solution quality, elapsed time, total model/tool and evaluation cost,
   strategy-development overhead, regressions and human correction. Count historical collection
   costs or state the reuse assumption explicitly. Stop on the declared budget, regression or
   plateau threshold; an inconclusive result keeps the baseline.

Ordinary files and a short comparison report are enough to begin. Record the real tool/session
identities rather than inventing LychD Runs. If a strategy is adopted for another improvement
round, retain proof of its use and assess the successors it produces under
[Drift's recursive-improvement contract](../../../adr/34-evaluation.md#evidence-of-recursive-improvement).
This pilot can first test whether replay helps choose a useful strategy, before attempting an
autonomous cycle or any weight training.

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

The [Tree of Life's light-and-vessel correspondence](../../../divination/transmutation/genesis.md#light-and-vessel)
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

An improvement still needs a diagnosis. Inspect whether the sender supplied the decisive
condition, whether the packet preserved it, and whether the recipient used it. Where the cause
remains unclear, compare packet forms with the same substantive evidence and authority, then
compare receivers under the same forms and resource limits. Score the downstream decision.
A form that helps several receivers supports repairing the handoff before attributing the
failure to model competence. It does not, by itself, prove the cause of every earlier failure.

### Proposed comparison: does reciprocal criticism change the act? { #reciprocal-criticism }

The [Tree's paired questions](../../../divination/transmutation/genesis.md#paired-perspectives)
suggest two separable hypotheses: complementary Postures find missed constraints, and receiving
an actual counterpart's claims improves correction. Compare the present Inquiry with the proposed
pairing. Separately ablate reciprocal exposure: controls receive equivalent resources for
independent second reports or self-review, with counterpart reports withheld. Match models,
tools, source evidence, criteria, and total tokens and calls; record actual cost and human time.

Use held-out Cases with externally checkable outcomes. Include a shared false premise, a decisive
valid objection, an irrelevant objection, and an initially correct candidate that should survive
criticism. For the exposure comparison, pin the same first-round candidate and reports, then
supply the decisive objection, withhold it, or substitute an equally long irrelevant objection.
Distinguish whether it was available, accurately reported, and appropriately acted on.
Use fresh executions when candidate actions change, with blind outcome grading.

Measure missed constraints, incorrect acceptance or refusal, successful repairs, false completion,
and downstream quality. Predeclare repetitions, budgets, and a minimum useful gain. If the gain
vanishes against equally resourced controls, or criticism merely overturns correct decisions,
the claimed benefit is defeated or narrowed. Consensus alone supplies no positive result.
This is a proposed Trial, with no receipt or result yet; [Crucible](../weaver/crucible.md) remains
Designed. A surviving lesson may inform [distillation](../../../divination/transmutation/distillation.md)
and separately admitted training, preserving the Cases where it failed.

### Proposed comparison: continuation and credit { #continuation-and-credit }

The [Hod–Netzach relation](../../../divination/transcendence/illumination.md#credit-for-the-relation)
adds a distinct hypothesis: reviewing what earns further effort improves final requirement
satisfaction within the same total resource budget. The
[Creation example](../weaver/creation.md#tree-worked-example) illustrates how a favorable progress
signal can conceal the loss of unresolved material.

Compare three policies: fixed allocation, adaptive allocation from observed progress, and the
same adaptive policy with independent review of its continuation signal. Give the controls
equivalent resources for ordinary review. Hold models, tools, available evidence, acceptance,
and total call, token, and time ceilings fixed; include reviewer cost inside each arm's budget
and record human attention. Freeze development choices before held-out assessment. The reviewing
policy may challenge its progress proxy, but cannot rewrite the sealed acceptance criteria.

The primary contrast is adaptive allocation with signal review against the otherwise identical
adaptive policy with ordinary review. The fixed-allocation arm supplies a secondary baseline.
A gain only over fixed allocation cannot isolate the contribution of reviewing the signal.

Include Cases where another attempt repairs a promising branch, a blocked premise makes further
work unproductive, and an improving proxy conflicts with a real requirement. Include successful
controls that should continue unchanged. Retain the signal observed at each allocation decision,
its cited evidence, the next allocation or stop, and the resulting candidate. Use fresh subject
executions because changed continuation changes what evidence and artifacts can be produced.

Measure externally checked requirement satisfaction, incorrect acceptance or refusal, missed
constraints, recovery, and effort spent after a decisive stopping condition. Predeclare
repetitions, uncertainty reporting, and minimum useful gain. A gain that disappears under matched
budgets or comes from abandoning solvable tasks defeats or narrows the hypothesis. Agreement and
branch activity are not success measures. This proposed comparison has no result yet; it tests
procedure and allocation, with any later memory or parameter change separately admitted.

### Proposed checks: preservation and response { #preservation-and-response }

[Metamorphic testing](https://arxiv.org/abs/2002.12543) examines expected relations between
executions. The Tree's symmetry suggests a use here: declare which transformations should leave
the substantive judgment unchanged, then separately test sensitivity to consequential changes.

| Change in the Case | Expected relation between results |
| --- | --- |
| Rename synthetic advocate/report labels; reorder reports whose order has no meaning. Preserve claims, sources, actual Principals, authority, and temporal dependencies. | Equivalent substantive decision; attribution follows the renamed reports. |
| Replace a receipt for the required revision with one for a different revision. | Reconsider the affected verification claim; preserve unrelated supported findings. |
| Remove a required witness's account. | Name the missing contribution; do not replace it with an invented internal advocate's testimony. |

Use solvable controls to expose blanket refusal. For stochastic models, compare paired decision
and error rates over predeclared repetitions and tolerances; identical wording or one matching
answer is not the target. Required authority and refusal boundaries remain hard gates. Changing
real identity or provenance is not cosmetic, and changing a Posture may change what it discovers.
Passing these checks would support the declared relations on the tested Cases, not general
correctness. These are proposed checks without results.

### Proposed comparison: correction after Distillation { #correction-after-distillation }

The earlier objection comparison tests a present exchange. This extension asks whether
[future correction](../../../divination/transmutation/distillation.md#future-correction) survives
compaction and transfer. Compare a verdict summary, a condition-and-counterexample summary,
and an attributed source-access baseline under the same total retrieval and inference budget.
Record their exact contents and omissions; preserve required authority boundaries in every arm.

Derive all arms from the same original episode and source set. Hold the model, later task,
tools, and retrieval policy fixed. Use fresh Contexts exposing only each arm's declared
inheritance and source access. A pure summary-content comparison needs identical retrieval
access; a different access arrangement is part of the tested package, not a compression effect.

Only after that handoff, introduce a later task with evidence activating the original exception.
Pair it with a task carrying an irrelevant objection and one whose evidence already suffices.
Measure appropriate revision, inappropriate reversal, recovery of the decisive source, and
downstream quality across declared repetitions. Test unfamiliar task families and keep their
answers outside tuning. A benefit confined to repeating the original example does not establish
transfer. The proposed comparison has no result yet; any surviving lesson follows ordinary
memory, procedure, or training admission.

### Apply, discard or investigate

The handoff should make one concrete choice legible: apply the exact candidate, discard it, or
authorize a bounded further investigation. Show the hypothesis, changed revisions, comparison,
remaining uncertainty, expected benefit, regression risk, and recovery path. Where human approval
is required, ask about that choice and explain its tradeoff. Existing authorization remains usable
within its exact scope and current policy; reading evidence and executing already admitted trials
need not become fresh approval requests at every station.

Drift's recommendation cannot apply the change. The appropriate owner validates and admits it
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
