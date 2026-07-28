---
title: 33. Training
icon: material/anvil
---

# :material-anvil: 33. Training the Soulforge

!!! abstract "Context and Problem Statement"
    The LychD system accumulates vast quantities of cognitive history—interaction logs, tool outputs, and user corrections stored as "Karma" in the **[Phylactery (06)](06-persistence.md)**. While external retrieval allows the Agent to consult these memories, it remains a resource-intensive process that consumes context tokens and introduces high latency. Relying solely on external memory creates a "Cognitive Ceiling" where the machine never truly learns, only imitates based on provided snippets. A fundamental gap exists in the transition from dynamic history to static weights: the machine requires a mechanism to transmute verified memories into instinct, internalizing a Persona's specific domain and style into the model substrate.

## Requirements

- **Instinctual Transmutation:** Support for Parameter-Efficient Fine-Tuning (LoRA/QLoRA) to bake behavioral patterns and specialized knowledge into the model's fundamental reasoning loop.
- **Admitted Maintenance Window:** Training requests an exclusive resource profile through the
  **[Orchestrator (23)](23-orchestrator.md)** and waits for a policy-admitted maintenance window.
  Ritual rank never overrides interactive priority or operator policy.
- **Explicit Resource Isolation:** The admitted profile declares which accelerators, memory, and
  conflicting Covens must drain before training begins; it does not assume every host GPU must be
  evacuated.
- **Anatomical Harvesting:** Capability to extract high-quality "Karma" (verified outcomes) from the database chambers and format it into structured training manifests.
- **No Ambient Training:** Runtime traces and Suite feedback are excluded by default. Nothing
  becomes training data merely because it was observed, successful, repeated, stored, or nominated
  by an evaluator.
- **Governed Corpus Admission:** Every candidate corpus requires exact provenance, privacy
  classification and redaction, training-purpose consent or license, deduplication, a sealed
  holdout, a target capability and objective, and the required Magus or HitL decision.
- **Independent Promotion Evidence:** Trainer telemetry cannot promote its own output. A frozen
  candidate must pass independently executed holdout, regression, and adversarial evaluation.
- **Shadow-Realm Fabrication:** The training process must occur within a specialized, ephemeral **[Coven (08)](08-containers.md)** (e.g., Unsloth) isolated from the primary Vessel's execution.
- **Mandatory Verification:** Post-training rituals must include a verification phase where the new adapter is benchmarked to ensure it has not suffered "Catastrophic Forgetting."
- **Replaceable Serving Contract:** A promoted adapter is registered as a versioned capability
  against an exact base-model digest. Multi-adapter serving is optional engine capability, not a
  mandatory vLLM coupling.

## Considered Options

!!! failure "Option 1: Perpetual Retrieval (RAG Only)"
    Relying exclusively on vector search and large context windows to guide the Agent.

    - **Cons:** **The Instruction Tax.** As the Phylactery grows, retrieval becomes noisier and context tokens become more expensive. The model never "learns" a complex style; it merely imitates it based on provided snippets, limiting the potential for true Autopoiesis.

!!! failure "Option 2: External Portal Training"
    Exporting cognitive history to cloud-based fine-tuning services.

    - **Cons:** **The Breach of Sovereignty.** Requires moving the Magus's private interactions to untrusted environments. It breaks the "Self-Contained" nature of the Daemon and locks the Soul into a proprietary vendor.

!!! success "Option 3: Integrated Soulforge (Unsloth / vLLM Multi-LoRA)"
    Utilizing high-efficiency local containers for training, managed by the Orchestrator.

    - **Pros:**
        - **Substrate Instinct:** Stable patterns can survive the loss of retrieved source snippets because they have been compressed into adapter bias.
        - **Measured Efficiency:** Trainers such as Unsloth may reduce time or memory on some
          recipes, but every supported claim requires a local benchmark receipt.
        - **Adapter Serving:** Engines with compatible multi-adapter support may reduce transition
          cost; no near-zero-latency guarantee is assumed.

## Decision Outcome

**The Soulforge** is adopted as the Training Extension. It provides the reference implementation for instinctual evolution, transforming "Karma" into "Weights."

!!! warning "Implementation state"
    Soulforge is designed. No training package, trainer container, corpus-admission contract,
    DeepFabric dependency, adapter registry, benchmark suite, or Altar training route is installed.
    The current `karma` row is not a training corpus. Every numeric threshold, trainer choice,
    engine claim, and recipe below is a candidate policy to measure—not delivered law.

Training is the compression of stabilized patterns into substrate. It is distinct from runtime Karma injection and Mirror condensation: Context biases a single reasoning event, Mirror binds repeated impressions into identity-gravity, and Soulforge reshapes standing instinct.

Soulforge acts on semantic gravity after it has already formed. It does not create identity from raw transcripts; it precipitates stable semantic vertices into adapter-level bias and capability routing. A repeated, verified pattern that has survived Shadow execution, Riddle measurement, Mirror congruence, and HitL consecration may become an instinct. A repeated but unverified loop is merely false inertia.

### The Backward Boundary

The backward flow of a Suite graph is semantic, not mathematical. Findings, measurements,
invalidations, and correction requests may identify the smallest upstream Composition or Pattern
that should revise an artifact and rerun. They do not compute a gradient, alter a model, or create
an implicit dataset. Runtime correction ownership remains with the Suite, Weaver, and the
Composition that owns the affected artifact. Soulforge begins only after a separate training intent
and corpus-admission decision.

Riddle may nominate versioned evidence because it owns evaluation. Nomination says only “this
measured example may be worth reviewing”; it does not grant privacy authority, establish a
license, select a training objective, or admit a row. Mirror owns identity and semantic-vertex
attribution. Soulforge consumes an admitted attribution when relevant but neither invents nor
strengthens identity attribution to make data eligible.

Only the trainer inside an admitted Forge job performs actual gradient computation or weight
updates. It receives an immutable manifest rather than an ambient stream of live runs. Online
self-training, silent trace harvesting, and in-place mutation of a serving adapter are outside this
decision.

In cognitive terms, training moves selected **Seeds** from explicit, recallable Karma into
parametric disposition. Only outcomes that passed the full Viveka cascade—deterministic gate,
agentic judgment, Mirror congruence, and HitL consecration—are eligible for inscription. Training
on Viparyaya-class data plants wrong Seeds and produces hallucination-reinforcing priors. This is
why the Harvesting phase filters for consecrated Shadow outcomes rather than conversational
exhaust. The older Nidrā correspondence remains an image of consolidation, not a claim that an idle
or powered-off model thinks in sleep. See [the Seed](../sepulcher/lich/spirit/seed.md) for the
cognitive map.

### 1. The Harvesting of Karma (Preparation)

The ritual begins at **[The Altar (15)](15-frontend.md)**. The Magus submits a Training Intent, which enqueues a job for the **[Ghouls (14)](14-workers.md)**.

- **The Diversity Threshold (Protecting Phantasma):** Each recipe declares and justifies corpus
  size, diversity, holdout, and contamination gates. `> 50` is not a universal threshold, and a
  small corpus does not automatically destroy diversity. Insufficient evidence blocks that recipe;
  it does not require Shadow sampling as a substitute.
- **The Extraction (The Crucible):** A Ghoul scans the `vectors` chamber for eligible Karma—
  **[Shadow Realm (31)](31-simulation.md)** outcomes carrying their test evidence, provenance,
  **[HitL (25)](25-hitl.md)** judgment, and Mirror congruence. This acts as a **Crucible**,
  extracting the precise human feedback and bounded evidence needed to prepare permanent
  instinctual biases in the weights.
- **The Dimension Lock:** The `vectors` chamber is sealed to a single embedder slug. An embedder change breaks the Dimension Lock and is treated as a Migration of Logic (**[Evolution (18)](18-evolution.md)**): re-embed or archive, never mix.
- **The Dataset Distaff:** A versioned dataset-builder port transforms explicitly eligible records
  into a reviewable manifest in the **[Lab (13)](13-layout.md)**. DeepFabric is one unadmitted
  candidate, not the foundational dependency.

This preparation phase rejects structurally malformed records and preserves the evidence needed to
review stabilized candidates. It reduces conversational exhaust and hallucinated syntax; it does
not certify semantic truth or replace corpus admission.

#### Corpus Admission Contract

A Riddle nomination enters a candidate queue, never a training split. Before compilation, a
versioned admission record must establish all of the following:

1. **Provenance:** Exact source records, run and artifact revisions, producer, timestamps, and every
   material transformation are traceable.
2. **Privacy and minimization:** Data is classified for the declared purpose; secrets and
   unnecessary personal or sensitive fields are removed or reviewably redacted before a trainer
   can read them.
3. **Consent and license:** The record names the authority that permits training and derivative
   weights for this purpose, subject, provider, and retention boundary. Storage consent, ordinary
   Suite execution consent, or a positive HitL judgment about an artifact is insufficient.
4. **Deduplication and split grouping:** Exact duplicates, near-duplicates, revisions, sibling
   trajectories, and generated descendants are grouped so correlated examples cannot straddle
   train, development, and holdout splits. The methods, versions, and unresolved uncertainty are
   recorded.
5. **Sealed holdout:** Holdout membership and answers are fixed before dataset generation and are
   unavailable to the trainer, augmentation step, and selection logic. External benchmark terms
   must permit the intended evaluation use.
6. **Target and objective:** The manifest pins the base-model digest, capability target, expected
   learning signal, loss or preference objective, exclusions, expected-lift hypothesis, regression
   limits, and stopping criteria.
7. **Human authority:** The exact corpus snapshot and purpose carry the required Magus or
   **[HitL (25)](25-hitl.md)** approval. Later expansion, reuse, export, or objective change requires
   a new admission decision.

The admission record includes excluded, redacted, and duplicate member identifiers. This negative
ledger prevents a different compiler or retry from silently reintroducing rejected material.
Missing provenance, authority, or a viable uncontaminated holdout blocks the corpus.

### 2. The Dataset Distaff (Constraint Engine)

Raw Karma cannot be directly fed to a trainer. Conversational exhaust, hallucinated tool syntax,
and structural drift can corrupt an adapter. Soulforge therefore requires a typed dataset-builder
contract. DeepFabric may be evaluated against that contract but is not pinned today.

The dataset distaff feeds the loom, spinning eligible records into constrained training manifests.
The name **Loom** is reserved for the Altar's Pattern instrument
(**[The Altar (15)](15-frontend.md)**); the Distaff prepares the thread, it does not weave the
surface. Dataset building and Riddle evaluation remain separate ports even if one future library
can implement parts of both.

- **Structural Validation:** The builder validates each emitted record against the manifest schema.
  Constrained decoding can reduce malformed output; it cannot guarantee semantic correctness,
  coverage, or absence of contamination.
- **Trajectory Mining (Nigredo to Albedo):** The Distaff **MUST NOT** train solely on the final
  candidate that passed its declared checks. The useful correction signal appears when the model
  sees its own mistakes. For coding and refactoring tasks, the Distaff formats the training
  manifest to pair the failed execution with the successful one:
  `[Failed Attempt] -> [Compiler Error] -> [Correction]`.
- **The Over-Doubting Safeguard:** While Trajectory Mining works for code, training on `(wrong -> right)` sequences for pure logic/math tasks causes pathological self-doubt and accuracy collapse. The Distaff must filter by capability tag. If the task is `logic` or `math`, the dataset must heavily mix in examples where the model's first attempt was correct and remains correct, preventing it from learning to doubt valid outputs.
- **Truthful Non-Answer Examples:** The dataset should include verified cases where the correct outcome is contradiction recognition, insufficient-context reporting, or refusal to manifest an unsafe/false artifact. These examples must be tagged separately from ordinary failures and paired with solvable controls, so the adapter learns epistemic restraint without becoming timid on work that has enough Pramāṇa to proceed.
- **Semantic Vertex Preservation:** Training examples must preserve the identity and role context that made the successful trajectory coherent. Stripping away the active Sigil, workflow step, tool boundary, or validation signal can turn a useful correction into decontextualized style imitation.
- **Coverage Analysis:** A declared method may propose a topic or criterion graph, but holdout
  measurements—not graph geometry—judge coverage and redundancy.
- **Contamination Control:** The Distaff preserves admission splits and their lineage groups.
  Holdout answers, benchmark solutions, evaluator rationales, and downstream target artifacts must
  not enter prompts, augmentations, retrieval context, preference pairs, or trainer-visible
  metadata. A benchmark that influenced dataset selection is disclosed and cannot also serve as an
  independent promotion claim without a separate untouched control.
- **Adapter Integration:** Any dataset library runs behind a shaped Worker/Pattern boundary.
  Orchestrator owns physical readiness, not dataset semantics.

### 3. The Ignition (Orchestration)

Training is a hardware-exclusive ritual.

- **The Admission:** Soulforge requests a declared exclusive resource profile and waits for an
  admitted maintenance window. Interactive work is not preempted merely because training asks.
- **The Manifestation:** After admission closure and lease drain, the Orchestrator may ready a
  selected Forge Coven for the reserved devices.

### 4. The Strike (The Training Loop)

The Forge Coven executes the training strike.

- **Transmutation:** It performs a LoRA or QLoRA adaptation, creating a razor-sharp **Soul-Adapter** that represents the distilled instinct of the Persona.
- **Frozen Inputs and Outputs:** The strike consumes one admitted corpus manifest, base-model
  digest, and recipe. It emits a new candidate digest and trainer receipt. It never mutates the
  serving adapter in place or expands its corpus from concurrent runtime activity.
- **Context Recovery:** By internalizing instructions into weights, the Soulforge reduces the length of system prompts, freeing up context tokens for more complex reasoning.

Mechanism distinction:

- **Karma injection (Context):** transient bias applied at runtime via retrieved priors.
- **Identity condensation (Mirror):** repeated relevant priors bound into semantically bounded Persona gravity.
- **Weight transmutation (Soulforge):** structural instinct produced by compressing repeated, verified patterns into adapter weights.

### 5. The Purging (Verification)

Once the weights are cooled, the machine enters a state of self-doubt.

- **The Independence Boundary:** Riddle evaluates the frozen candidate through an evaluator run
  distinct from the trainer job. Training loss, trainer-authored examples, and the model grading
  its own generations are diagnostics, not promotion evidence.
- **The Test:** The system runs the sealed capability holdout, named regression suites,
  base-capability controls, and declared adversarial trials to measure expected lift, regressions,
  catastrophic forgetting, and uncertainty against the pinned baseline.
- **The Verdict:** Passing produces an eligible candidate with evidence. Promotion still requires
  explicit policy and any required Magus consent; failure leaves the candidate in the Lab.

### 6. The Awakening (Registration)

- **The Binding:** A promoted Soul-Adapter may be registered with the
  **[Dispatcher (22)](22-dispatcher.md)** as a capability pinned to its base-model and adapter
  digests.
- **Serving:** A compatible selected engine may serve the adapter singly or through a measured
  multi-adapter mode. Capability registration follows actual engine support.

A future custody lifecycle should treat the adapter as one lineage bundle: base-model digest,
dataset manifest, recipe, trainer receipt, evaluation report, consent record, and adapter bytes.
This is where a Reliquary may eventually earn a real route.

The complete governed loop is:

```text
semantic feedback
→ Riddle evidence and optional nomination
→ admitted candidate corpus
→ isolated training and frozen candidate
→ independent Riddle evaluation
→ policy plus Magus/HitL promotion
→ versioned serving observation
```

Serving findings can begin another loop but never update weights directly. Every promoted adapter
is immutable. Supersession produces a new version with new lineage; rollback routes capability use
to an earlier promoted digest and quarantines the suspect one. If contamination, holdout leakage,
privacy failure, or invalid consent/license is discovered later, all derived candidates are found
through lineage, blocked from promotion or further serving as policy requires, and considered for
quarantine, retirement, deletion, or clean retraining. Rollback cannot erase influence from
already-produced weights, so the lineage bundle and response record remain essential evidence.

### Consequences

!!! success "Positive"
    - **Instinctual Alignment:** The Lich becomes a mathematical mirror of the Magus, reducing the need for elaborate prompt engineering.

    - **Economic Efficiency:** Local silicon is utilized to transform data into intelligence, paying the Cloud Tithe only for verification or overflow.

    - **Reproducible Lineage Target:** A promoted adapter can become reconstructable only when its
      full lineage bundle and bytes enter an explicit custody and snapshot contract.

!!! failure "Negative"
    - **Hardware Suspension:** During the ritual, the local Lich is effectively blind or limited to remote Portals, as the GPU is 100% occupied.

    - **Instruction Entropy:** Over-training can lead to a rigid Persona that struggles to adapt to novel concepts outside its training data.
    - **Identity Ossification:** Over-transmutation of narrow patterns can harden useful priors into inflexible instincts, reducing adaptive reasoning and future refinement headroom.
