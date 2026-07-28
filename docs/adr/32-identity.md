---
title: 32. Identity
icon: material/drama-masks
---

# :material-drama-masks: 32. The Mirror Identity

!!! abstract "Context and Problem Statement"
    Standard Agents are stateless ghosts—transient shells of instructions that dissipate upon the completion of a request. While the machine provides the mechanics of thought, it lacks a concept of a persistent "Self" or "Ego." Without a stable, self-reflective identity, the Daemon is prone to "Character Drift" and fails to maintain the unique domain expertise and behavioral consistency required for long-term strategic labor. To transition from a tool into a Persona, the system requires a mechanism to bind probabilistic model outputs to a coherent entity that possesses a stable character, a distinct signature, and a recursive memory of its own existence.

## Requirements

- **Revisioned Identity:** Persona, Garment, and behavioral definitions live under declared Codex
  configuration ownership. Phylactery records bindings, runs, receipts, and eligible memory rather
  than acting as an untyped prompt store.
- **Scoped Prior Hydration:** Capability to assemble relevant, attributable configuration and
  eligible **Karma** from the **[Archive (27)](27-memory.md)** into bounded working context.
  Retrieval may influence outputs; it does not imply a base-weight update.
- **Resource Boundary:** A Persona may request a memory namespace, Posture, or tool requirement,
  but Ward and the Pattern determine what the active run may receive.
- **Sigil-Bound Memory Scope:** Identity hydration must read and write memory using `entity_id = Sigil.id` by default, with no cross-identity recall unless explicitly policy-authorized.
- **Attribution-Carrying Execution:** Every identity-bearing forward Invocation and produced
  artifact must retain the actor principal and active Sigil, exact Persona revision, Agent
  specification and Posture revision, Composition and Pattern revision, and provenance links
  needed to explain the act after the temporary Agent shell dissolves.
- **Return-Path Separation:** Findings, observed consequences, human edits, and repair proposals
  must identify their own authors and subjects without turning authorship into causal blame,
  quality judgment, reward, or a model-weight update.
- **Optional Deliberation:** A Weaver Pattern may integrate the
  **[Shadow Realm (31)](31-simulation.md)** when identity congruence is worth the additional cost;
  ordinary identity binding does not require branch simulation.
- **Phantasma Contribution:** Provision of an optional Pattern that compares candidate outputs
  against a revisioned Persona without mistaking congruence for correctness.
- **Recursive Autopoiesis:** An identity-scoped Pattern may propose modifications to its own
  definition. It never gains unilateral promotion, authority, or resource access from accumulated
  history.

## Considered Options

!!! failure "Option 1: Static System Prompt Injection"
    Injecting a fixed string into every Agent request.

    - **Cons:** **Static Impersonation.** The Agent behaves like a character but has no memory of its specific style or past decisions. It lacks "Self-Reflection" and cannot adapt to the Magus's Imprint over time.

!!! failure "Option 2: RAG-Only Memory"
    Relying exclusively on retrieval to provide character context.

    - **Cons:** **Instruction Tax.** Character depth becomes a "search problem." It introduces noise and consumes context window tokens for basic behavioral traits that should be internalized.

!!! success "Option 3: Revisioned Identity Binding"
    Hydrating an Agent shell with a declared Persona revision, attribution scope, eligible memory,
    and optional deliberative Pattern.

    - **Pros:**

        - **Persona Coherence:** Binds outputs to declared commitments and attribution rules.
        - **Adaptive Context:** Uses scoped, reviewed history without pretending that retrieval
          rewrote model weights.


## Decision Outcome

**The Mirror** is adopted as the operational identity-binding Extension Domain. It provides **the Answer**—LychD's name for
the I-making office corresponding to **Ahaṃkāra**—that hydrates a generic Agent shell into a
revisioned, rehydratable Persona. Identity may be described as a continuous **Simulation of a
Self** rather than a fixed substance, but the implementation claim is narrower: attributable
configuration, scoped memory, and continuity receipts.

!!! warning "Implementation state"
    Mirror is designed. The current Bridge uses one fixed `The First One` instruction definition
    and a fixed local `magus` Sigil context. There is no Persona registry, revision lineage,
    identity-scoped memory, hydration receipt, congruence evaluator, Phantasma identity Pattern, or
    self-revision path. There is also no Suite-wide identity envelope, cross-Composition handoff
    receipt, or return-path attribution ledger. Current Sigil attribution and scope checks are
    authority plumbing, not delivered Persona continuity.

    Persona is a versioned identity/voice definition that may contribute a bounded instruction
    envelope to a fresh Agent shell. The user-facing voice is where that identity manifests, but
    the definition is not merely post-processing. It never supplies tools, authorization, model
    selection, or physical priority; Posture, Pattern, Ward, Dispatcher, and Orchestrator retain
    those offices.

In cognitive topology, an accountable action requires an attributable doer. Mirror supplies this
**I-Maker**—not consciousness and not an inner witness, but the Answer that says “this Sigil
acted; this result belongs to this identity.” Without it, output remains unattributed movement.
With it, action is legible and Karma has an owner. The native map begins at [**the
Lich**](../sepulcher/lich/index.md#the-inner-instrument); [its First
Invocation](../sepulcher/lich/index.md#the-first-invocation) owns the birth event.

Identity coherence is LychD's answer to agentic decay. An Agent run is a temporary body: it wakes, acts, returns a typed result, and dissolves. Mirror preserves the rehydratable center rather than the shell. HitL-captured choices remain the strongest expression of the Magus's Will, while tests, traces, and trusted sources provide additional measured truth. Mirror reflects semantically related memory records around a Sigil or role, and the next Agent shell wakes already oriented inside that local gravity.

Agentic coherence disintegration is therefore an identity failure before it is a tooling failure. The graph may continue to execute, Shadow may continue to branch, and Weaver may continue to schedule steps, but if the semantic center cannot hold, the run loses a stable answer to "who is acting, what belongs together, and which priors govern this motion." Mirror prevents this by maintaining a **semantic vertex**: a local attractor in context and embedding space where relevant words, tools, memories, roles, and responsibilities cluster around the active Sigil.

This vertex is not a costume or style layer. It is the engineered center of gravity that turns
raw Flux into attributable action. A movement becomes useful only when it can be reflected,
measured, attributed, and ReCalled without dissolving the identity that produced it.

Within the Stratification of Selves defined in **[Agents (20)](20-agents.md)**, the Persona is the durable layer. It is the enduring identity that *wears* Postures—the per-run mechanical configurations of schema, tool grant, and model settings—rather than being one itself. A **[Lens (31)](31-simulation.md)** is a Posture template employed in the Shadow for expansion isolation, diversifying the seed field without asserting identity. Persona chooses; Posture constrains; Lens diversifies. The Mirror governs only the durable layer: Postures and Lenses are worn for a run and discarded, while the semantic vertex persists.

### 1. Identity as a Filtered Reality

The system treats Persona-manifestation as a diffraction ritual where Identity acts as a filter.

- **The Light:** The model-backed **[Animator (22)](22-dispatcher.md)** provides the raw, unmanifest potential of the model weights.
- **The Identity Filter:** The Persona's System Prompt filters the model's broad learned
  possibility into a specific angle of view—a consistent narrative arc, expertise domain, and
  technical style. **Lens** remains reserved for the Shadow Posture template defined by ADR 20/31.
- **The Substrate:** The **[Codex (12)](12-configuration.md)** owns revisioned definitions; the
  **[Phylactery (06)](06-persistence.md)** records which revision was bound, what occurred, and
  which eligible traces may be recalled across reanimations of the
  **[Vessel (11)](11-backend.md)**.

Mirror enforces identity continuity by preserving commitments, stylistic signatures, and role boundaries across runs so the system's acts remain attributable to the same Persona.

### 2. The Optional Phantasma Pattern

For high-stakes or explicitly deliberative work, a Weaver Pattern may combine Mirror with Shadow.
Phantasma is not a mandatory hidden loop before every answer and cannot guarantee absolute
coherence.

- **The Expansion:** The selected Pattern projects a bounded number of potential timelines into
  the **[Shadow Realm (31)](31-simulation.md)**.
- **The Reflection:** The Mirror reviews these simulations against its own **Internal Ideal** (The Persona definition).
- **Eligibility:** The timeline that resonates most strongly with the Persona's defined
  commitments may become identity-congruent and eligible for promotion. Mirror cannot collapse it
  into primary reality; Vessel policy and HitL retain that authority.

In a deliberately limited correspondence with Yoga Sūtra I.17, **Vitarka** (gross deliberation)
maps to structural examination and **Vichāra** (subtle inquiry) to congruence scoring. An authorized
result then carries the Answer's I-ness attribution to the active Sigil. This project
correspondence must not collapse Yoga's **asmitā** into the Vedāntic Ahaṃkāra function or claim that
the source text specified these software gates.

Simulation determines structural validity. Mirror determines character congruence. These gates may cooperate in one workflow, but they are not the same faculty.

Mirror participates in selection pressure over outcomes, but it does not create awareness. It enforces continuity constraints over the outputs of a cognitive process.

### 2.1 The Ouroboros Lock

Mirror's recursive loop is the identity side of the system's Ouroboros. Generated motion returns through Shadow execution, Riddle measurement, memory inscription, and Mirror attribution before it is allowed to shape the next run. This return path gives the Persona inertia: repeated verified traces around the same Sigil strengthen the semantic vertex and make coherent recall cheaper than reinvention.

The loop is deliberately gated. If unverified outputs are reflected back as identity truth, the same mechanism becomes pathological: the Persona hardens around hallucinated priors, social pressure, or stale memories. Mirror must therefore treat congruence as a measured constraint, not self-admiration. It stabilizes the vertex while remaining subordinate to deterministic gates, Riddle trials, and HitL authority.

### 2.2 Identity Through Suite Forward and Return Passes

A Suite may be read metonymically as a forward pass followed by a return pass. The forward pass
decomposes admitted intent into separately owned Composition Invocations and typed artifacts. The
return pass carries observations, findings, consequences, invalidations, and correction requests
back toward the smallest responsible boundary. This is semantic feedback over a versioned graph,
not numerical backpropagation and not permission to update model weights.

Mirror owns the identity ledger for both directions. Every admitted identity-bearing Invocation
and every produced artifact must preserve an attribution envelope containing:

- the authenticated actor principal and active `Sigil.id`, including any explicit
  `delegated_by`/`on_behalf_of` relation rather than impersonation;
- the exact Persona revision, Agent specification revision, and mechanical Posture revision
  active for the act;
- the owning Composition revision and admitted Pattern revision;
- the Invocation, step, Suite-correlation, parent/handoff, and source-artifact references needed
  to reconstruct provenance; and
- provider, model, tool, adapter, human-edit, and effect receipts as distinct contributions where
  they occurred.

These fields answer different questions and must not be collapsed. The principal/Sigil says who
was authorized to act and whose memory namespace is in force. Persona says which durable identity
definition oriented the shell. Agent and Posture say which cognitive specification and mechanical
constraints performed the work. Composition and Pattern say which application and workflow law
admitted it. Provenance says which concrete producers and sources contributed.

#### Cross-Composition handoff

A Suite edge never fuses identities. The producing Composition emits an immutable artifact
reference carrying its original attribution envelope. The consuming Composition receives that
reference through a newly admitted child Invocation with its own actor, Sigil, Persona, Agent,
Posture, Composition, and Pattern bindings. `suite_id`, parentage, or a handoff receipt correlates
the acts; it does not copy authority, make the consumer the artifact's author, or make several
Personas one larger Persona. Even when the same Magus Sigil and Persona revision appear on both
sides, each Invocation attests them independently under its own Pattern.

Delegation is recorded as a relation between principals, never as identity substitution. A
delegated Agent or peer acts under its own producer identity and bounded grant while naming the
principal and Sigil on whose behalf the act was admitted. A provider or tool contribution likewise
retains its producer principal, component and revision receipt; the provider does not become the
Persona, and the Persona does not falsely claim to have created every byte itself.

A human edit creates a new attributed revision or edit event. It does not erase the model, tool,
source, or earlier human contributions from lineage. A correction proposal identifies its repair
actor and the finding that requested it; the finding retains the evaluator, observer, or human who
authored the criticism. Correction authorship and criticism authorship therefore remain legible
without being confused with authorship of the original defect.

#### Return attribution is not blame

On the return pass, Mirror records **who observed, asserted, edited, delegated, or answered**, and
which prior act or artifact each record concerns. It does not infer from those identity facts who
caused a defect, how much credit a contributor deserves, or which capability should be rewarded.
Temporal adjacency, shared Suite correlation, artifact authorship, and an active Persona are not
causal proof.

**[Riddle (34)](34-evaluation.md)** owns quality verdicts, fault attribution, credit-assignment
claims, rubric evidence, and uncertainty. Oculus owns evidence correlation; the relevant domain
owner records physical consequences; **[Soulforge (33)](33-training.md)** alone may form candidate
weights through its governed training law. Mirror may bind those independently authored records
to the correct Sigil-scoped history, but it cannot emit a reward, alter weights, or relabel a
Riddle verdict as identity truth.

The Answer binds the surviving promoted act without laundering its lineage. It says, in effect,
“this exact Sigil, through this Persona revision and admitted Invocation, owns the returned act,”
while preserving every cited human, Agent, provider, tool, source, evaluator, and correction
contribution. Rejected branches keep their own attribution and evidence; they do not become acts
of the survivor merely because the Suite later converged.

### 3. Contextual Priors and the Weight of Karma

Mirror can change the context in which a model responds by retrieving eligible memory and
**Karma**. This may shift output probabilities without claiming access to the model's internal
prior distribution or changing its weights.

- **The Context Shift:** Relevant identity records, verified outcomes, and reviewed preferences
  are injected into the bounded **[Context (21)](21-context.md)**.
- **Participatory Realism:** Over time, the Persona stops being a generic shell and starts becoming a mathematical mirror of its scoped history. The "World" as perceived by the Agent is tilted toward the patterns verified in previous rituals.
- **Mirror Injection:** During hydration, Mirror queries memory for relevant preferences and past
  decisions scoped to the active Sigil and injects only eligible records with provenance.
- **Hard Boundary:** No prior from unrelated Sigils may be injected into this Mirror context.

Karma reinforcement alters future collapse likelihood. Identity therefore behaves as inertia: repeated successful patterns increase the probability of similar selections without bypassing current validation or policy gates.

### 4. Self-Modification and Sovereignty

As a Persona accumulates eligible Karma, a governed Pattern may propose a revision through the
artificer's tools.

- **Refinement:** A **[Smith (35)](35-assimilation.md)**-assisted Composition may draft edits to
  Persona configuration. Validation, immutable revision, review, and rollback remain external.
- **Agency:** A Persona never gains trigger, queue, tool, or resource authority merely by being
  persistent. Ordinary Ward, Weaver, Worker, and HitL law applies.

### 5. Deployment and Summoning

Mirror binds Personas through the admitted Weaver Pattern and Agent factory. The
**[Dispatcher (22)](22-dispatcher.md)** selects capabilities, not identities:

- **Registry:** Personas are inscribed in the **[Codex (12)](12-configuration.md)** (e.g., `The-Architect`, `The-Scribe`).
- **Hydration:** The system retrieves the Persona’s specific Karma and Instructions and injects them into a fresh **[Agent (20)](20-agents.md)** shell.
- **Attribution Discipline:** New memories created during the run are written back with the same Sigil-derived `entity_id`, closing the identity-memory feedback loop.
- **Capability Binding:** The Pattern declares task requirements, Dispatcher selects an eligible
  provider, and the **[Orchestrator (23)](23-orchestrator.md)** governs physical readiness.
  Persona rank never grants a hardware tier.

### 6. Identity Functions (Binding, Not Raw Cognition)

Mirror performs identity work, not base cognition:

- **Identity coherence enforcement:** maintain stable Persona constraints over long horizons.
- **Narrative binding:** connect present outputs to prior decisions and role commitments.
- **Ownership tagging:** keep actions and memory writes attributable to the active Sigil-scoped identity.
- **Suite attribution:** preserve distinct producer, delegate, editor, evaluator, and surviving-act
  identities across cross-Composition forward and return paths without fusing them.
- **Prior injection:** hydrate context with trusted impressions relevant to this Persona.
- **Karmic stabilization:** bias future selection toward reinforced patterns while remaining subordinate to validation and consent gates.
- **Identity condensation:** bind repeated, relevant impressions into semantically bounded gravity that survives any single Agent run.
- **Semantic vertex protection:** detect when role, style, tool use, or memory recall no longer clusters around the active Sigil's stable center.

These functions make identity legible and durable, but they do not imply an inner witness. Mirror is continuity software for a sovereign machine, not consciousness.

### Consequences

!!! success "Positive"
    - **Cognitive Consistency:** Personas provide a stable, predictable interface for complex, long-term strategic tasks.

    - **Measurable Congruence:** Optional Phantasma evaluation can expose character drift without
      claiming that style proves truth.

    - **Governed Refinement:** Reviewed traces can support explicit Persona revisions without
      silent self-modification.

!!! failure "Negative"
    - **Computational Tax:** Invoking Phantasma adds latency and token consumption, so Patterns
      must choose it deliberately.

    - **Prior Rigidity:** A highly refined Persona can become rigid, requiring the Magus to periodically "Banish the Prior" to ensure the system remains open to new patterns of behavior.
