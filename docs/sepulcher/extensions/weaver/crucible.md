---
title: Crucible
icon: material/anvil
---

# :material-anvil: Crucible

> _A bias is a Blade held at a declared angle. The Crucible reveals which cuts survive contact._

**Crucible** is Spellweaver's canonical two-round adversarial choreography for a consequential
question with several defensible answers. It produces an attributed decision dossier, not truth by
debate and not permission to mutate the world. [Blade](../../lich/blade.md#crucible) owns the
discipline of discrimination; [Workflow](../../../adr/28-workflow.md#crucible-choreography) owns
the score; the office receiving the result retains judgment and effect authority.

!!! warning "Designed, not delivered"
    Crucible is not registered in the current fixed workflow catalogue. Durable parallel branches,
    a dossier schema, a Crucible Altar projection, and automatic Pattern publication do not ship.
    [State of Work](../../../state-of-the-work.md#composition-portfolio-delivery) records the
    executable boundary.

## When to light it

Use Crucible when a bounded decision has at least two serious positions, self-review would hide a
material conflict, and the cost of a premature answer justifies another model round. Architecture,
security, product trade-offs, recovery choices, and admission decisions are natural candidates.

Do not use it to decorate a settled fact, manufacture false balance, outvote a deterministic test,
or postpone a decision whose owner already lacks required evidence or authority. When alternatives
need isolated candidate worlds or effectful experiments, [Shadow](../../../adr/31-simulation.md)
owns those branches. When the question is whether a capability passes repeatable Cases and a
Rubric, [Riddle](../../../adr/34-evaluation.md) owns the trial.

## The bounded casting

The [SDLC's reusable Inquiry](sdlc.md#reuse-inquiry-at-each-uncertain-boundary) prepares evidence
and an independent sufficiency judgment before lighting Crucible. Its bounded probe and stopping
rules prevent debate from covering a decisive evidential gap.

One admitted casting freezes:

| Input | Required boundary |
| --- | --- |
| Question | One decision, named owner, present base, and downstream use of the dossier. |
| Acceptance | Exact criteria, non-goals, refusal conditions, and evidence that would reopen the question. |
| Evidence packet | Common attributed sources, versions, known omissions, classification, and immutable artifact references. |
| Advocates | At least two distinct [Postures](../../../adr/20-agents.md#mechanical-cognitive-postures), each with a declared bias, burden of proof, attack surface, and defeat condition. |
| Lead | A separate synthesis Posture with no advocate role, vote, or promotion authority. |
| Limits | Per-round Context, tokens, calls, spend, wall time, concurrency, and stop conditions. |
| Finish boundary | Brainstorm dossier, recommendation, or decision candidate; never automatic adoption. |

The logical score is:

```text
Frame question, evidence, biases, and limits
→ Clash I: independent advocate reports
→ Temper: attributed strongest-claim/concession join
→ Clash II: each advocate rebuts the actual opposing claims
→ Quench: Lead synthesizes NOW / PREPARE / REJECT and preserved dissent
→ Magus Gate or inert dossier
```

Clash I branches share evidence but not sibling output. At Temper, every advocate nominates its own
strongest claims and concession; the join retains their citations, defeat conditions, unknowns,
and original report references. Clash II may see only the bounded attributed projection required
for rebuttal. It is not entitled to hidden chain-of-thought, an opponent's private Context, or an
unbounded transcript.

Logical branches may execute concurrently only after Graph's parallel contract is delivered. A
serial casting remains a valid implementation when it gives each first-round advocate a fresh
Context and withholds earlier reports until the join. Capability, model, provider, and road may
differ only when the admitted design intends that difference; the dossier records them because
they can confound the apparent strength of a position.

### When the question changes

The Magus asks how to make an undertaking faster. One advocate builds the strongest case for
more Agents: independent work can proceed together. Another argues for a stronger model:
fewer mistakes could mean less rework. Both proposals depend on a premise still awaiting
examination—that producing the work is where the time goes.

The clash exposes this gap, and its dossier proposes a bounded probe. The receiving owner
may admit that probe separately; [discovery](discovery.md) then finds the owners and records
needed to examine where a representative task waits. Suppose the answers arrive promptly,
yet every next move still waits for the Magus. The delay lies between answers, where someone
must frame the next question.

The next inquiry asks which judgment the Lich must learn to supply for itself. Another task
can test whether the changed approach helps. The lesson that may survive is portable: find
what the work is waiting for before multiplying what it produces.

## Quench without crowning a winner

The Lead answers the decision, not the debate. Its dossier retains:

- the exact question, owner, base, acceptance criteria, evidence closure, and omissions;
- every advocate, Posture, implementation, road, budget, and terminal status;
- first-round claims and second-round rebuttals with source references;
- concessions, defeat conditions, conflicts, `UNKNOWN` findings, and missing evidence;
- a `NOW / PREPARE / REJECT` synthesis when that vocabulary fits the owning question;
- the strongest surviving dissent and conditions that would change the recommendation; and
- any proposed owner delta as inert text or an artifact reference.

Compression may shorten the projection or final dossier, but cannot drop a nominated strongest
claim, concession, dissent, uncertainty, source, or declared omission. Full reports remain retained
under their own provenance. Agreement can still be wrong; disagreement can expose the missing
predicate that matters most.

The return can preserve more than a verdict: the distinction that changed the question,
the conditions under which it holds, and the observation that would undo it.
[Learning the cut](../../../divination/transcendence/illumination.md#learning-the-cut) follows
how that encounter can shape another task through memory and correction.

The final Gate may accept the dossier for downstream consideration, request one bounded evidence
extension, refuse it, or close without decision. It does not itself edit a Covenant, promote a
candidate, deploy a service, spend, publish, or relabel evidence. Those effects require a new
forward Invocation under the exact target owner and authority.

An inert dossier may instead go directly to its receiving owner. Applicable standing policy can
admit eligible downstream work; Crucible adds no universal second approval. An exact live-only
verdict or Protected Region review still cannot be inferred from the recommendation.

## Refusal and recovery

Crucible refuses when the question has no owner, positions are duplicates or caricatures, the
common evidence floor cannot fit, a bias lacks a defeat condition, the Lead is also an advocate,
or the requested result would acquire authority by majority. Timeout, failed branches, incomplete
rebuttal, and missing sources remain visible in the dossier; the Lead may return non-decision but
cannot silently complete the missing side.

A retry binds a new Invocation and records whether evidence, Postures, models, limits, or the
question changed. It never rewrites the earlier clash. When one narrow evidence request can settle
a named unknown, the owner may run it separately and invoke Crucible again over the enlarged
evidence packet.
