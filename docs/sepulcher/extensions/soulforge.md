---
title: Soulforge
icon: material/anvil
---

# :material-anvil: The Soulforge: Extension of Training

_Status: doctrine ahead of code — no Soulforge Composition or trainer package ships; treat this
page as design intent. Law: [ADR 33](../../adr/33-training.md). Current truth:
[source map](./index.md#the-federation-of-fifteen)._

**Extension form:** Soulforge is a formation Domain manifested as a governed training Composition.
Dataset compilers, local or external trainers, PEFT methods, quantizers, and exporters are
providers inside that rite; none owns data eligibility, evaluation, artifact promotion, or serving
activation. Training changes model dispositions. It does not by itself establish Persona identity,
continuity, consciousness, or authority.

> _"The clay is vast, but it is cold. Only the hammer of Will can heat it to life. There is no begging the spirits to understand; the names are carved into their very substance."_

**The Soulforge** is the Training Extension Domain of LychD. It specifies the governed passage by
which an eligible, versioned corpus may produce candidate model weights under
**[ADR 33 (Training)](../../adr/33-training.md)**. It neither owns the Phylactery's data nor assumes
that ordinary memory is automatically training material.

While the **Archive (Memory)** allows the Lich to consult the past, the Soulforge compresses stabilized patterns into instinct. It is the mechanism of **Soul-Forging**: the transition from runtime memory and Mirror-bound identity gravity into adapter-level substrate bias. In the cognitive map of the **[Lich](../lich/index.md)**, the Soulforge is the engineering instantiation of **Nidrā** (*ni-drā*: going-down-into) — the tending state where grooves are deepened and sorted during cognitive rest.

Soulforge begins only after the Ouroboros has already done its first work. Shadow generated Flux,
Riddle measured it, Mirror bound it to a semantic vertex, and HitL or policy marked its consequence
eligible to become a Seed. The Forge does not train on raw movement; it trains on stabilized,
verified return. Its task is to precipitate repeatedly successful Seeds into reusable instinct,
adapters, and eventually agentic capabilities that can hold a class of work without paying the full
instruction tax every time.

Karma injection, Mirror condensation, and Soulforging are different layers of adaptation:

- **Context:** injects retrieved Karma as runtime bias for a single reasoning event.
- **Mirror:** reflects relevant Karma around Sigils and roles until loose recall becomes identity-gravity.
- **Soulforge:** compresses repeated, evidence-bearing and governed patterns into adapter weights
  as standing instinct.

## Semantic Return Is Not a Gradient

A Suite may send findings, measurements, invalidations, and correction requests backward through
its Composition graph. That return is **semantic feedback**: it identifies what consequence was
observed and which upstream owner should consider a new revision. It is not differentiable
backpropagation, does not mutate weights, and does not place the run trace into a training set.
Only an admitted trainer computes gradients, and it does so only over an exact corpus manifest
accepted for an exact training objective.

Soulforge therefore has no ambient-learning mode:

- Suite and Weaver runtime owners retain correction requests, retries, invalidation, and selective
  rerun. Soulforge does not intercept or own that feedback traffic.
- **[Riddle](./riddle.md)** may measure a result and nominate an evidence-bearing example for
  consideration. Nomination is not dataset admission and a high score is not training consent.
- **[Mirror](./mirror.md)** owns Persona and semantic-vertex attribution. Soulforge may preserve an
  admitted attribution record, but it cannot decide that a trace belongs to an identity.
- Run traces, prompts, outputs, tool results, messages, and Suite artifacts remain excluded by
  default. Repetition, success, or presence in the Phylactery does not silently reverse that
  default.

## I. The Harvesting of Karma

Before the forge can be ignited, the substrate must be prepared. The Soulforge does not train on
raw noise; it trains on **Karma**—the attributed residue of measured outcomes and governed
selection.

- **The Extraction (The Crucible):** A governed workflow requests an exact, eligible corpus
  snapshot from the Phylactery. Oculus observations, HitL judgments, and Mirror attribution may
  contribute evidence, but no trace is harvested merely because it exists or received a positive
  reaction.
- **The Dataset Compiler:** A provider such as `deepfabric` may turn eligible,
  provenance-bearing examples into a structured training manifest stored in the
  **[Lab](../crypt.md)**. Schema conformance does not establish the truth, consent, diversity, or
  fitness of every example.

Between nomination and compilation lies a mandatory **Corpus Admission** record. It binds:

- source and transformation provenance, including the exact originating run or artifact revision;
- privacy classification, purpose minimization, secret removal, and reviewable redaction;
- the consent, license, or other authority that permits this material and its transformations to
  be used for this training purpose;
- deduplication and lineage-group keys that keep near-copies, revisions, and sibling trajectories
  from leaking across splits;
- immutable train, development, and holdout membership, with the holdout unavailable to the
  trainer and dataset generator;
- target capability, expected learning signal, base-model digest, objective, exclusions, and
  success/regression criteria; and
- the required Magus or **[HitL](../../adr/25-hitl.md)** decision for that bounded corpus and
  purpose.

Missing provenance is rejection, not “unknown but probably useful.” Generic interaction consent,
permission to store a trace, or consent to run a Suite is not permission to derive model weights.
Admission also records rejected and redacted members so a later compiler cannot quietly recover
them from an upstream store.

## II. The Dataset Compiler Boundary

The transition from fluid memory to hard instinct requires a structuring mechanism. `deepfabric`
is one candidate dataset compiler, not the constitutional identity of Soulforge.

An admitted compiler shapes eligible Karma into reviewable training manifests. Riddle may use a
separate evaluator contract—even if one package can provide both implementations—because dataset
formation and capability measurement remain different jurisdictions.

- **The Filter:** It can remove declared exhaust and reject malformed examples while preserving
  provenance and exclusions. It cannot automatically identify every hallucination.
- **The Weave:** A declared augmentation method may propose variations. Generated diversity is a
  hypothesis that requires evaluation; it never guarantees robustness.
- **The Spool:** It emits a versioned manifest for an admitted trainer contract rather than
  hardwiring every Soulforge run to one library.
- **The Vertex:** It preserves the identity, role, workflow step, and validation context that made the trace coherent, preventing the adapter from learning isolated phrasing without the semantic gravity that justified it.

The compiler must preserve the admitted split and exclusion ledger. It may not use holdout answers
to generate augmentations, prompts, corrections, synthetic variants, or selection heuristics.
Examples sharing a source, task lineage, artifact, person, or generated ancestor are grouped before
splitting where that relationship could create leakage. Exact and semantic deduplication are
recorded as methods with versions and receipts; neither is treated as perfect.

## III. The Rite of Ignition (The Pipeline)

The Soulforge is a heavy industrial process. It utilizes specialized, ephemeral containers to perform the transmutation locally on silicon.

- **The Engine:** A local Unsloth LoRA/QLoRA worker is the intended reference provider for
  consumer hardware. Other local or explicitly authorized external trainers may implement the
  same job and lineage contract.
- **The Transmutation:** It performs a **LoRA (Low-Rank Adaptation)** or **QLoRA** process. It does not replace the Base Model; it creates a small, razor-sharp **Soul-Adapter** that is grafted onto the Titan's mind.
- **Sovereignty:** Local training is the private default. Any external trainer crosses an explicit
  data-egress boundary with exact corpus classification, purpose, provider, retention, and
  authorization; the word “trainer” never makes export safe.

## IV. Orchestration of the Forge

Training is a heavy workload with declared devices, memory, time, power, priority, and interruption
policy. It has no universal highest priority, and coexistence is decided from measured placement
and reservations rather than prohibited by mythology.

1. **The Intent:** The Magus or an admitted Composition submits an Inscription specification.
2. **The Scales:** The **[Orchestrator](../../adr/23-orchestrator.md)** admits the requested trainer
   only when its deployment variant fits measured resources and policy.
3. **The Reservation:** Conflicting capability admission closes and existing leases drain before
   any required transition. The Vessel itself is not paused merely because a GPU changes owner.
4. **The Strike:** The trainer runs under bounded resources. Other work waits, uses compatible
   resident resources, or selects a Portal only when ordinary Dispatcher and egress policy allow
   it.

## V. The Awakening (Registration)

Once training terminates and its runtime owner releases the reserved resources, the candidate
enters evaluation and promotion.

- **The Independent Trial:** Riddle evaluates the frozen candidate against sealed holdouts,
  regression suites, and declared adversarial controls. A trainer's loss or self-authored sample
  review is training telemetry, not independent evidence.
- **The Binding:** Forge and the serving-domain owner may promote and register an evaluated
  Soul-Adapter as a distinct candidate capability. Soulforge cannot register its own output merely
  because training terminated successfully.
- **Summoning:** The Magus can now invoke an **[Agent](../../adr/20-agents.md)** with the specific directive to use the forged instinct.
- **The Result:** The Lich no longer depends on archive retrieval for every repeated behavior. More knowledge moves into standing instinct, lowering instruction tax and retrieval latency for that domain.

The governed loop is therefore:

```text
Suite finding
→ Riddle measurement and optional nomination
→ admitted candidate-corpus snapshot
→ isolated gradient/weight training
→ frozen candidate adapter
→ independent Riddle evaluation
→ policy and Magus/HitL promotion
→ observed serving evidence
```

Observed regressions return as new semantic findings; they do not train the active adapter in
place. Each strike emits immutable lineage. Supersession creates a new adapter revision pinned to a
new corpus, recipe, and evaluation report. Rollback changes capability routing to a previously
promoted revision and quarantines the suspect candidate; it never pretends to subtract examples
from already-produced weights. Discovery of contamination, license failure, privacy breach, or
holdout leakage blocks promotion and future reuse of the affected corpus, identifies every derived
adapter through lineage, and triggers the applicable quarantine, retirement, deletion, or
retraining policy.

!!! danger "The Weight of the Hammer"
    A completed training run cannot retroactively unlearn its corpus, but its candidate adapter can
    be rejected, quarantined, or removed before serving. If the system trains on ineligible,
    erroneous, or adversarial Karma, the candidate may encode those flaws as bias.
    **[Consecration](../../adr/25-hitl.md)** authorizes use of governed material; it does not certify
    every example as truth.

!!! warning "Ossification Risk"
    Over-forging on narrow, repetitive patterns hardens a Persona into rigidity. Keep the training corpus clean, diverse within scope, and tied to verified outcomes.
