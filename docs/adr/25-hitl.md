---
title: 25. HitL
icon: material/account-voice
---

# :material-account-voice: 25. Human-in-the-Loop Consent

!!! abstract "Context and Problem Statement"
    The execution of autonomous reasoning presents a fundamental stability and safety dilemma. Large Language Models operate on probabilistic principles and lack an inherent sense of subjective value or systemic risk, creating a scenario where irreversible transitions—such as the modification of core system logic, the expenditure of significant Tithes, or the deletion of user data—could occur without oversight. A gap exists between the tireless computational labor of the machine and the subjective judgment of the Magus. The absence of a formal protocol to bridge this divide exposes the substrate to "Ghost Actions," where high-stakes intents are manifested by an engine that possesses no concept of consequence.

## Requirements

- **The Stasis Protocol:** Mandatory capability for a cognitive thread to hibernate and persist its state to the **[Phylactery (ADR 06)](./06-persistence.md)**, preventing resource locking during human deliberation. (An approval wait is Durable Stasis — definition in **[Graph (ADR 24)](./24-graph.md)**.)
- **Speculative Isolation (Shadow Realm):** Provision of a sandbox environment to explore and verify potential outcomes (the "Vision") before they are permitted to manifest in the Crypt.
- **Multi-Modal Transparency:** Mandatory presentation of rich, multimodal context—including code diffs, terminal logs, and visual screenshots—to the Magus at the primary interface.
- **Resource Liberation:** Signaling to the **[Orchestrator (ADR 23)](./23-orchestrator.md)** to evacuate hardware covens when a task enters a pending state, reclaiming VRAM for active user reflexes.
- **Undeletable Authority:** Hardcoded enforcement of consent for system-critical capabilities, preventing autonomous "oversight-bypass" behaviors.
- **Configurable Preauthorization:** Low-risk autonomous approval must be expressible only through explicit **[Codex (ADR 12)](12-configuration.md)** policy and must remain subordinate to hard HitL gates.
- **Reanimation Fidelity:** Phylactery-backed rehydration must resume from the declared recovery boundary upon approval, utilizing Pydantic AI's deferred result patterns without claiming every volatile frame survives.
- **Feedback Integration:** Support for corrective feedback that triggers internal agent reflection via self-correction loops.

## Considered Options

!!! failure "Option 1: Blocking Execution"
    Maintaining active worker threads and GPU VRAM while waiting for human input at a synchronous interface.
    - **Pros:** Immediate resumption; low implementation complexity.
    - **Cons:** **Resource Paralysis.** If the Magus is away from the interface, the GPU remains locked, preventing other background rituals or interactive reflexes. It creates a physical bottleneck that violates the efficiency laws of the machine's physical will.

!!! failure "Option 2: Continuous Polling"
    Having the worker process loop indefinitely, checking a database flag or file for an "Approved" status.
    - **Pros:** Allows for state persistence; simpler than a full asynchronous deferral system.
    - **Cons:** **Wasteful Cycles.** Consumes CPU resources and database I/O for an idle task. It provides no standard mechanism for "Shadow Scrying," making it difficult to present the user with a verified outcome before the choice is made.

!!! success "Option 3: Deferred Consecration (Stasis & Scrying)"
    Adopting a "Halt and Scry" workflow utilizing Pydantic AI's `DeferredToolRequests` and the Shadow Realm sandbox.
    - **Pros:**
        - **Hardware Agility:** Physically liberates the machine's body while the mind waits, allowing the **[Orchestrator (ADR 23)](./23-orchestrator.md)** to reallocate VRAM.
        - **Verified Visions:** Uses background labor to present a "future state" (e.g., a proposed code merge) before it is committed to the **[Crypt (ADR 13)](./13-layout.md)**.
        - **Reflex Reanimation:** Re-enters the mind at the declared decision boundary, triggered by a secure signal from the **[Altar (ADR 15)](./15-frontend.md)**.

## Decision Outcome

**The Magus Consent Protocol** is adopted as the definitive Conscience of the machine. It uses a
"Halt and Scry" workflow powered by Pydantic AI's native deferred tooling to transform a
probabilistic intent into an explicitly authorized or refused decision. Consent does not make a
factual claim true; Magus testimony counts as Pramāṇa only where the Magus is competent to witness
the matter.

There is a structural reason this protocol cannot be treated as optional polish. An autonomous agent left to loop without external grounding faces a known failure mode: context saturates, reasoning frays, and Viparyaya-generated outputs begin referencing each other as though they were Pramāṇa — each cycle compounding the drift. The system spirals into the noise of its own generation, losing coherence not through malice but through the mathematical inevitability of probabilistic reasoning without an external anchor. HitL is not a safety leash bolted on; it is the channel by which verified human judgment enters the loop at the only moment it matters — when a generated candidate is about to become permanent reality. See **[The Lich](../sepulcher/lich/index.md)** for the cognitive map underlying this architecture.

Within the broader simulation architecture, HitL is the final authority in a three-stage collapse sequence: structural validity is established in Shadow, identity congruence is evaluated by Mirror, and ontological promotion is authorized here through explicit Magus consent or Codex-governed Vessel preauthorization. High-stakes promotion remains live Magus authority.

!!! note "Consent and Preauthorization"
    "Approved" is a policy result, not a feeling produced by the model. It can mean live Magus approval at the Altar or a preauthorized Vessel policy class defined in **[Configuration (ADR 12)](12-configuration.md)**. ZTE chores may use the second path only when deterministic checks, scope limits, risk class, identity constraints, and confidence predicates all pass. Core mutation, schema migration, destructive deletion, secret changes, host lifecycle authority, and broad egress changes always require live HitL.


### 1. The Trigger (Stasis Initiation)

Consent is treated as a first-class state transition within the **[Graph (ADR 24)](./24-graph.md)**.

- Tools identified as high-risk (e.g., `modify_core`, `delete_artifact`) are configured with `requires_approval=True`.
- Upon invocation, the tool raises an `ApprovalRequired` exception.
- The Agent run terminates and returns a `DeferredToolRequests` object containing the tool name, validated arguments, and a unique `tool_call_id`.
- The Graph commits its typed snapshot history to the run-owned Postgres checkpoint row and parks
  before a verdict can re-enqueue it. This is the implemented durable consent boundary; a
  transactional checkpoint/outbox transaction remains later work.
- Tools identified as preauthorizable still pass through the same Vessel-side policy gate. They may skip a live Altar prompt only when Codex policy explicitly permits that action class.

When a recorded verdict admits a parked run, the ledger first performs one atomic status admission
and then publishes a fresh SAQ resume hop. Those two stores are not one transaction. Publication
failure or caller cancellation completes a shielded restoration to `AWAITING_CONSENT`; the
monotonic `enqueue_seq` is not rolled back, so a key that may have reached the broker is never
reused. Startup reconciliation can re-fire a durable decided verdict after process death.

### 2. The Shadow Realm (The Dreaming)

While the reasoning thread is in stasis, the system enters the state of **Albedo** (Purification):

1. A background **[Ghoul (ADR 14)](./14-workers.md)** executes the intent within an isolated Jujutsu workspace or change in the `lab/` directory.
2. The Ghoul performs the "Rite of Speculation"—running compilers, linters, and unit tests against the proposed change.
3. The results are packaged into a **Vision artifact**, containing a technical summary, code diffs, and visual feedback (e.g., screenshots or Mermaid diagrams).

This phase establishes structural validity evidence and prepares material for downstream identity and consent evaluation; it does not, by itself, authorize manifestation.

### 3. The Ritual of Consecration (Reanimation)

The moment of human choice is the site of ontological promotion collapse. The Magus scries the Vision at the **[Altar (ADR 15)](./15-frontend.md)**, with identity and scope established via the active Sigil context in **[Context (ADR 21)](./21-context.md)**.

- **The Blessing:** Approval enqueues a reanimation job. A Ghoul rehydrates the Graph, injects a `DeferredToolResults` object with the approval, and the mind resumes the thought.
- **The Preauthorized Blessing:** A configured low-risk policy may enqueue the same reanimation job without a live prompt only after all Codex predicates and verification gates pass.
- **The Refinement:** If denied, the Magus's feedback is delivered to the mind via a `ModelRetry`. The Agent reflects on the refusal and generates a new speculation within the Shadow Realm.

Denial is a calibration signal, not punishment. The returned context should name the violated constraint, missing evidence, or unacceptable risk clearly enough that the next Shadow pass can change shape rather than loop defensively around the same false premise. HitL therefore strengthens truthful correction without training the Agent to please authority at the expense of Pramāṇa.

HitL therefore does not replace simulation, identity evaluation, or Codex policy. It ratifies (or rejects) promotion after those earlier gates have already reduced the candidate space, and it remains mandatory wherever policy marks the action as high-risk or undeletably human.

### 4. Promotion to Karma (The Crucible Convergence)

Every instance of Consent provides high-quality data for the machine's evolution. Upon successful reanimation and manifestation, the interaction trace—the original Intent, the scried Vision, and the final Blessing—is promoted to the **Karma** partition of the **[Memory Archive (ADR 27)](./27-memory.md)**.

This human feedback forms a **Crucible**. HitL captures the Magus's Will; Karma stores its Imprint; Mirror binds that Imprint into identity-gravity; and, once the pattern is stable enough, **[Soulforge](../sepulcher/extensions/soulforge.md)** may compress it into substrate instinct. This converges the **Mirror** (Ego), **Shadow** (Simulation), and **HitL** (Consent) into a unified pipeline that fundamentally forges the machine's ongoing character.

## Consequences

!!! success "Positive"
    - **Absolute Sovereignty:** The machine remains bound to the Magus's Will; autonomous "runaway" behaviors are physically impossible for critical tasks.
    - **Zero-Cost Deliberation:** The system can wait indefinitely for a human signal without consuming active memory or locking inference ports.
    - **High-Fidelity Scrying:** By presenting "Verified Outcomes" (Visions) rather than raw text, the Magus makes decisions based on the projected reality of the change.

!!! failure "Negative"
    - **Operational Latency:** High-stakes self-modification is strictly bound by human reaction time, slowing the pace of Autopoiesis.
    - **Tomb Management:** Maintaining multiple "Shadow Realities" in the lab requires automated pruning to prevent storage accumulation.
