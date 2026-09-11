---
title: Discernment Training
icon: material/anvil
---

# Teaching Discernment Through Soulforge

“Ask before proceeding” is a poor lesson when the missing fact is already in the supplied
material. “Act without asking” is equally poor when the next effect needs authority the caller
has not given. A useful example shows the condition that distinguished these situations, the
evidence available at the time, and the consequence of choosing well or badly.

This **Designed** passage explains how approved experience from the
[agentic software lifecycle](../weaver/sdlc.md) and
[Ouroboros improvement cycle](../weaver/ouroboros.md) could become training material under
[ADR 33](../../../adr/33-training.md). It provides no installed harvesting, trainer, benchmark,
or serving path. [State of Work](../../../state-of-the-work.md#soulforge-training) owns delivery.
Soulforge prepares a candidate; independent Riddle evidence and an externally owned decision
stand between that candidate and use.

## Choose what should change

First locate the demonstrated limitation. A forgotten current fact calls for a different remedy
from an inability to apply a stable distinction across unfamiliar tasks. The four routes leave
different things behind:

| Route | What changes | Appropriate use |
| --- | --- | --- |
| Memory | An admitted, attributable record with correction and retention rules | Preserve a fact, preference, correction, or experience that should remain inspectable |
| Retrieval and Context | Which authorized material enters this invocation, within its budget | Supply current knowledge or remove distracting material when a decision needs it |
| Durable procedural artifact | A versioned instruction, prompt, schema, or workflow score | Make an explicit, reviewable procedure reliably available to later work |
| Learned model competence | Parameters in an exact model or adapter candidate | Test whether a learned distinction transfers when examples or explicit guidance are insufficient |

[Memory](../../../adr/27-memory.md) owns admission and correction of retained records;
[Context](../../../adr/21-context.md) owns what reaches a model call; the relevant artifact or
workflow owner controls a procedural revision. None of these silently updates weights.
Conversely, a trained model does not become the authoritative store of mutable facts or current
permission.

Prefer a context, prompt, schema, or workflow fix when the
[workflow comparison](../riddle/workflow-improvement.md) shows that it adequately solves the
problem. Training needs its own hypothesis: what capability remains deficient, why parameters
might improve it, what benefit would justify the cost, and which regressions would make the
attempt unacceptable. Fine tuning or LoRA can be a Recipe choice under that hypothesis; neither
is a mandatory destination for every correction.

## Preserve the lesson before compiling examples

[Discernment within exploration](../../lich/blade.md#discernment-within-exploration) supplies
a candidate learning objective: identify which uncertainty deserves a probe and let its result
change the plan. An example should show why that probe was consequential, paired with a case
where the evidence already suffices and further exploration would waste effort. The
[handoff comparison](../riddle/workflow-improvement.md#handoff-reception) first tests whether
an explicit procedure solves the problem; only a remaining transferable skill gap motivates
training. Sefirotic names are interpretive context, not correctness labels for the Dataset.

Nominate exact, authorized traces and artifacts with their human explanations. A teaching example
should retain the task and available evidence, relevant constraints, the observed decision and
result, the correction, the reason for it, and the conditions under which that correction applies.
Keep a counterexample where following the same superficial rule would be wrong. Distinguish
human preference, factual label, authority decision, measured result, and evaluator judgment.

For instance, a corrected workflow may have asked the same approval twice. The lesson needs the
earlier authorization and its scope, the later proposed action, and why that action still fell
inside the grant. Pair it with a case where changed recipients, effects, or data classes require
new admission. A dataset of “approved” versus “rejected” replies without these conditions would
teach social imitation rather than evidence-sensitive choice.

Retain successes, failures, justified refusals, and truthful non-completion where the objective
supports them. Completion alone is not quality; repeated agreement can repeat one misconception.
Use visible explanations and observable evidence. Hidden chain-of-thought is not required, and
an invented rationale cannot be presented as a recovered account of why the original model acted.

A minimal correction example keeps this inspectable shape within the owned Dataset schema:

```text
source / task or Run / artifact revisions
→ available evidence and authority → observed action and result
→ human correction → reason → applicability conditions → counterexample
→ label provenance and uncertainty → permitted uses → lineage group and split
```

For the first experiment, pair examples of acting under sufficient existing authority with
examples where changed effects or a decisive missing fact require a question. Use separate task
families for development and sealed transfer checks. Reuse the proposed
[starter Cases](../riddle/workflow-improvement.md#starter-cases-for-the-first-comparison) as a
design template, never as both tuning answers and unseen proof. A useful evaluation example may
remain excluded from training because its permitted uses differ.

## Obtain training authority over one snapshot

Storage, evaluation, and training are separate uses. Permission to retain a Run or to accept its
artifact does not permit training on it. A Training Intent names the Principal, purpose, target
capability, exact base digest, allowed data classes, resource envelope, and promotion authority.
[Corpus admission](./corpus.md#admit-one-snapshot) then establishes training-specific consent,
license, or other authority over the exact nominated material and derivative uses.

The review must expose a concrete choice: which examples and fields would enter, why they are
useful, who may receive them, how long they are retained, and the consequence of learned
influence. Reuse valid authorization within that declared scope; do not ask the operator to
approve every compiler operation. Missing or expanded authority still blocks the affected use.

Minimize private material and preserve provenance through redaction and transformation. An
anonymized explanation may still reveal its source or encode a distinctive private fact. Keep
the source classification, transformation limits, and derivative lineage attached. Admission
freezes membership and exclusions; a negative ledger prevents rejected or duplicate material from
returning through a later compilation attempt.

## Separate practice from examination

Group duplicates, revisions, sibling trajectories, and generated variants before splitting the
corpus. Freeze train, development, and sealed-holdout membership before training-facing generation.
Otherwise a corrected trace can enter training while its lightly reworded sibling appears to
test generalization.

Compile one immutable Dataset Manifest from that admitted snapshot. Version the schema and
compiler; retain labels, transformations, source references, split digests, and balance and
contamination statistics. Human explanations are attributable training inputs where admitted,
not an excuse to smuggle test answers into metadata.

Held-out benchmark tasks, answers, evaluator rationales, and downstream target artifacts stay
outside training, retrieval, augmentation, preference construction, and candidate selection.
Disclose any benchmark used to select the corpus; an untouched control is then needed for an
independent promotion claim. A development result can guide another attempt, but repeatedly
tuning against a sealed evaluation result consumes its independence.

## Train a bounded candidate

The [Training Run](./training-run.md) receives the exact Manifest, base and tokenizer/configuration
digests, objective, and versioned Recipe. Pin the method, dependencies, hyperparameters,
randomness, resource budget, expected improvement, regression limits, and stops. Orchestrator
admits physical resources; an idle window supplies neither corpus authority nor a reason to
disturb unrelated work.

Execute inside the admitted filesystem, credential, network, process, and resource boundaries,
with fresh Run-owned outputs and retained receipts. The trainer cannot enlarge its corpus with
ambient history or replace serving weights. Failure or cancellation preserves logs, terminal
truth, completed checkpoints, and quarantined partials. A retry receives a new Training Run.

Freeze candidate bytes and lineage into a Candidate Bundle. For an adapter, bind the exact base
digest and serving compatibility. Loss and development metrics help diagnose training; they do
not establish that the candidate is useful, safe, or ready to activate.

## Let the candidate leave its teacher

Independent [Riddle evaluation](../riddle/index.md) compares the frozen candidate with the base
or currently promoted baseline under matched serving conditions and budgets. Use the sealed
target holdout, deterministic contract gates, independently judged qualitative criteria, named
regression suites, and authority-boundary Cases. Test transfer to unfamiliar tasks and distinguish
appropriate refusal from blanket hesitation. Include quality, latency, memory, cost, human
attention, and recovery; retain uncertainty and failed or blocked trials.

The trainer cannot change the candidate or choose easier evaluation after seeing results. An
iteration stops according to its declared budget and thresholds. It never continues training
until its own judge likes the answer. An unresolved result may justify a separately bounded
investigation; it cannot silently become a favorable verdict.

Through [Candidate handoff](./candidate-handoff.md), the owning policy and required Magus/HitL
authority decide on the exact Bundle, evidence, capability envelope, compatible serving engine,
rollout observations, stops, and rollback target. Present the expected gain, remaining tradeoff,
and fallback together so approval names a reviewable candidate. The serving owner registers and
activates that exact revision for admitted work.

Observe the promoted revision within its approved envelope. Regression, contamination, or a
later privacy or authority failure can require stopping use, invalidating affected claims, and
routing new work to a prior digest. Preserve the Dataset, Run, Bundle, evaluation, decision, and
descendant lineage under their retention rules. Rollback cannot undo completed effects; deleting
a source record cannot remove its influence from already produced weights. A clean replacement
requires clean admission and another evidenced passage through the forge.
