---
title: 25. HitL
icon: material/account-voice
---

# :material-account-voice: 25. HitL: The Sovereign Consent

!!! abstract "Context and Problem Statement"
    A truly autonomous Daemon presents a fundamental stability and safety paradox. Large Language Models are inherently probabilistic and lack a subjective sense of value or risk; allowing them to perform high-stakes actions—such as modifying core system logic, executing unverified code, or deleting sensitive data—without oversight is an unacceptable risk to systemic integrity. A physical and ethical gap exists between the machine’s tireless computational labor and the Magus’s subjective judgment. Without a formal protocol to bridge this divide, the machine is prone to "Ghost Actions"—irreversible transitions performed by an engine that has no concept of consequence.

## Requirements

- **The Stasis Protocol:** Mandatory capability for a cognitive thread to "Hibernate"—exiting active memory and persisting its state to the **[Phylactery (06)](06-persistence.md)**—to prevent resource locking during human deliberation.
- **Speculative Isolation (The Shadow Realm):** Provision of a sandbox environment to explore and verify potential outcomes (the "Dream") before they are permitted to impact Primary Reality.
- **Advanced Transparency:** Mandatory presentation of rich, multimodal context—including code diffs, terminal logs, and visual screenshots via **`BinaryContent`**—to the Magus at the interface.
- **Resource Liberation:** The transition to a pending state must signal the **[Orchestrator (21)](21-orchestrator.md)** to evacuate the current hardware coven, reclaiming VRAM for other tasks during the deliberation period.
- **Resumption Fidelity:** Absolute rehydration of the cognitive state upon approval, utilizing Pydantic AI’s deferred result patterns to ensure zero context loss.
- **Undeletable Authority:** Hardcoded enforcement of consent for system-critical intents, preventing autonomous "oversight-bypass" behaviors.

## Considered Options

!!! failure "Option 1: Blocking Execution"
    Keeping the worker process and VRAM active while waiting for human input.
    - **Cons:** **Resource Paralysis.** If the Magus is away from the Altar for hours, the GPU remains locked, preventing the machine from performing other background labor.

!!! failure "Option 2: Continuous Polling"
    Having the worker loop indefinitely, checking for an "Approved" flag.
    - **Cons:** **CPU Inefficiency.** Wasteful cycles are burned on a task that is idle. It provides no mechanism for the "Speculative Dreaming" required to show the user a preview of the outcome.

!!! success "Option 3: Deferred Tooling and Shadow Realm"
    A "Halt and Scry" workflow utilizing Pydantic AI's **`DeferredToolRequests`**.
    - **Pros:**
        - **VRAM Liberation:** Physically evacuates the machine's state while waiting.
        - **Verified Visions:** Uses the Shadow Realm to present a "future state" (diffs/tests) via **`ToolReturn`**.
        - **Reflex Resumption:** Reawakens the mind only when the Magus’s signal triggers the reflex arc.

## Decision Outcome

**The Sovereign Consent Protocol** is adopted as the definitive interaction pattern for all high-stakes transitions. It utilizes a "Halt and Scry" workflow powered by **Pydantic AI's Deferred Tools** to transform probabilistic "Dreams" into "Verified Truths."

### 1. The Trigger (`ApprovalRequired`)

Human-in-the-loop (HitL) is treated as a first-class state transition within the **[Graph (22)](22-graph.md)**.

- **The Signal:** A tool identifies a high-risk intent (e.g., `delete_file` or `modify_core`). If `RunContext.tool_call_approved` is `False`, the tool raises the **`ApprovalRequired`** exception.
- **Decorator Enforcement:** Critical tools are registered with `requires_approval=True`, ensuring the model cannot bypass the check.

### 2. The Hibernation (`DeferredToolRequests`)

When the exception is raised, the Agent run terminates and returns a **`DeferredToolRequests`** object.

- **Serialization:** The **[Vessel (11)](11-backend.md)** catches this result and serializes the entire `StateT` and message history into the `queue` chamber of the Phylactery using the system's high-performance binary codecs.
- **Evacuation:** The **[Worker (14)](14-workers.md)** thread is released, and the Orchestrator is notified that the task is in stasis, allowing for immediate Coven swaps.

### 3. The Shadow Realm (Speculative Scrying)

To bridge the gap between "Nigredo" (raw LLM output) and "Albedo" (whitened truth), the machine continues to labor in the shadows.

- **The Dreaming:** While in stasis, the Ghouls execute the intent within an isolated Git branch in the `lab/` directory. They perform the "Rite of Speculation"—running tests, compilers, and linters.
- **The Vision:** The results are packaged into a **`ToolReturn`** object. This includes **`BinaryContent`** for visual feedback and a `return_value` containing the technical summary.
- **The Altar:** These fruits are manifested at **[The Altar (15)](15-frontend.md)**. The Magus observes the "Vision of the Future"—a diff of the proposed changes and the verification results.

### 4. The Reflex Arc (`DeferredToolResults`)

The moment of human choice is the moment of **Wavefunction Collapse**.

- **The Selection:** The Magus selects the "White Truth" at the Altar. This generates a **`DeferredToolResults`** object, mapping the unique `tool_call_id` to a `True` approval or a **`ToolDenied`** signal.
- **The Awakening:** This choice enqueues a `resume_graph` job. A background Ghoul picks up the winning result, rehydrates the **[Graph (22)](22-graph.md)** state, and resumes execution exactly where it halted.
- **Self-Correction:** If the Magus provides corrective feedback instead of approval, it is fed back into the Agent via a **`ModelRetry`**, forcing the mind to reflect and generate a new speculation.

### 5. Evolution and Karma

Every instance of Sovereign Consent provides high-quality data for the machine's evolution.

- **The Consecration Hook:** Approval of a "White Truth" at the Altar triggers an atomic background ritual. A **Ghoul (14)** is dispatched to:
    1. **Embed** the original Intent and the final manifested Code/Artifact.
    2. **Tag** the entry in the `vectors` chamber with `status="consecrated"`.
    3. **Internalization:** These entries are prioritized in the **Context (26)** manager, ensuring the machine does not repeat mistakes and builds upon established patterns of success.

### Consequences

!!! success "Positive"
    - **Guaranteed Sovereignty:** The Magus remains the ultimate arbiter; the machine cannot "run away" with the system substrate.
    - **Zero-Cost Deliberation:** The system can wait indefinitely for a human response without consuming active RAM or locking inference ports.
    - **High-Fidelity Scrying:** Using Pydantic AI's multimodal returns ensures the Magus reviews "verified outcomes" rather than probabilistic guesses.

!!! failure "Negative"
    - **Workflow Latency:** High-stakes evolution is strictly bound by human reaction time.
    - **Cleanup Complexity:** Maintaining "Shadow Realities" in the Lab requires robust automated pruning of discarded Git branches.
