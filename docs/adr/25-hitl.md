---
title: 25. HitL
icon: material/account-voice
---

# :material-account-voice: 25. Human-in-the-Loop Consent

!!! abstract "Context and Problem Statement"
    The execution of autonomous reasoning presents a fundamental stability and safety dilemma. Large Language Models operate on probabilistic principles and lack an inherent sense of subjective value or systemic risk, creating a scenario where irreversible transitions—such as the modification of core system logic, the expenditure of significant Tithes, or the deletion of user data—could occur without oversight. A gap exists between the tireless computational labor of the machine and the subjective judgment of the Magus. The absence of a formal protocol to bridge this divide exposes the substrate to "Ghost Actions," where high-stakes intents are manifested by an engine that possesses no concept of consequence.

## Requirements

- **The Stasis Protocol:** Mandatory capability for a cognitive thread to hibernate and persist its state to the **[Phylactery (ADR 06)](./06-persistence.md)**, preventing resource locking during human deliberation.
- **Speculative Isolation (Shadow Realm):** Provision of a sandbox environment to explore and verify potential outcomes (the "Vision") before they are permitted to manifest in the Crypt.
- **Multi-Modal Transparency:** Mandatory presentation of rich, multimodal context—including code diffs, terminal logs, and visual screenshots—to the Magus at the primary interface.
- **Resource Liberation:** Signaling to the **[Orchestrator (ADR 23)](./23-orchestrator.md)** to evacuate hardware covens when a task enters a pending state, reclaiming VRAM for active user reflexes.
- **Undeletable Authority:** Hardcoded enforcement of consent for system-critical capabilities, preventing autonomous "oversight-bypass" behaviors.
- **Reanimation Fidelity:** Absolute rehydration of the cognitive state upon approval, utilizing Pydantic AI's deferred result patterns to ensure zero context loss.
- **Feedback Integration:** Support for corrective feedback that triggers internal agent reflection via self-correction loops.

## Considered Options

!!! failure "Option 1: Blocking Execution"
    Maintaining active worker threads and GPU VRAM while waiting for human input at a synchronous interface.
    -   **Pros:** Immediate resumption; low implementation complexity.
    -   **Cons:** **Resource Paralysis.** If the Magus is away from the interface, the GPU remains locked, preventing other background rituals or interactive reflexes. It creates a physical bottleneck that violates the efficiency laws of the machine's physical will.

!!! failure "Option 2: Continuous Polling"
    Having the worker process loop indefinitely, checking a database flag or file for an "Approved" status.
    -   **Pros:** Allows for state persistence; simpler than a full asynchronous deferral system.
    -   **Cons:** **Wasteful Cycles.** Consumes CPU resources and database I/O for an idle task. It provides no standard mechanism for "Shadow Scrying," making it difficult to present the user with a verified outcome before the choice is made.

!!! success "Option 3: Deferred Consecration (Stasis & Scrying)"
    Adopting a "Halt and Scry" workflow utilizing Pydantic AI's `DeferredToolRequests` and the Shadow Realm sandbox.
    -   **Pros:**
        -   **Hardware Agility:** Physically liberates the machine's body while the mind waits, allowing the **[Orchestrator (ADR 23)](./23-orchestrator.md)** to reallocate VRAM.
        -   **Verified Visions:** Uses background labor to present a "future state" (e.g., a proposed code merge) before it is committed to the **[Crypt (ADR 13)](./13-layout.md)**.
        -   **Reflex Reanimation:** Reawakens the mind exactly at the point of decision, triggered by a secure signal from the **[Altar (ADR 15)](./15-frontend.md)**.

## Decision Outcome

**The Magus Consent Protocol** is adopted as the definitive Conscience of the machine. It uses a "Halt and Scry" workflow powered by Pydantic AI's native deferred tooling to transform probabilistic intents into "Verified Truths."

Within the broader simulation architecture, HitL is the final authority in a three-stage collapse sequence: structural validity is established in Shadow, identity congruence is evaluated by Mirror, and ontological promotion is authorized here (via Vessel policy and Magus consent).


### 1. The Trigger (Stasis Initiation)

Consent is treated as a first-class state transition within the **[Graph (ADR 24)](./24-graph.md)**.

- Tools identified as high-risk (e.g., `modify_core`, `delete_artifact`) are configured with `requires_approval=True`.
- Upon invocation, the tool raises an `ApprovalRequired` exception.
- The Agent run terminates and returns a `DeferredToolRequests` object containing the tool name, validated arguments, and a unique `tool_call_id`.
- The Graph executes an atomic exit, serializing the `StateT` and message history into the `queue` chamber of the **[Phylactery (ADR 06)](./06-persistence.md)**.

### 2. The Shadow Realm (The Dreaming)

While the reasoning thread is in stasis, the system enters the state of **Albedo** (Purification):

1. A background **[Ghoul (ADR 14)](./14-workers.md)** executes the intent within an isolated Git branch in the `lab/` directory.
2. The Ghoul performs the "Rite of Speculation"—running compilers, linters, and unit tests against the proposed change.
3. The results are packaged into a **Vision artifact**, containing a technical summary, code diffs, and visual feedback (e.g., screenshots or Mermaid diagrams).

This phase establishes structural validity evidence and prepares material for downstream identity and consent evaluation; it does not, by itself, authorize manifestation.

### 3. The Ritual of Consecration (Reanimation)

The moment of human choice is the site of ontological promotion collapse. The Magus scries the Vision at the **[Altar (ADR 15)](./15-frontend.md)**, with identity and scope established via the active Sigil context in **[Context (ADR 21)](./21-context.md)**.

- **The Blessing:** Approval enqueues a reanimation job. A Ghoul rehydrates the Graph, injects a `DeferredToolResults` object with the approval, and the mind resumes the thought.
- **The Refinement:** If denied, the Magus's feedback is delivered to the mind via a `ModelRetry`. The Agent reflects on the refusal and generates a new speculation within the Shadow Realm.

HitL therefore does not replace simulation or identity evaluation. It ratifies (or rejects) promotion after those earlier gates have already reduced the candidate space.

### 4. Promotion to Karma

Every instance of Consent provides high-quality data for the machine's evolution. Upon successful reanimation and manifestation, the interaction trace—the original Intent, the scried Vision, and the final Blessing—is promoted to the **Karma** partition of the **[Memory Archive (ADR 27)](./27-memory.md)**. This ensures the machine internalizes the pattern of successful collaboration and Magus preference.

## Consequences

!!! success "Positive"
    - **Absolute Sovereignty:** The machine remains a strict extension of the Magus's will; autonomous "runaway" behaviors are physically impossible for critical tasks.
    - **Zero-Cost Deliberation:** The system can wait indefinitely for a human signal without consuming active memory or locking inference ports.
    - **High-Fidelity Scrying:** By presenting "Verified Outcomes" (Visions) rather than raw text, the Magus makes decisions based on the projected reality of the change.

!!! failure "Negative"
    - **Operational Latency:** High-stakes self-modification is strictly bound by human reaction time, slowing the pace of Autopoiesis.
    - **Shadow Management:** Maintaining multiple "Shadow Realities" in the lab requires automated pruning to prevent storage accumulation.
