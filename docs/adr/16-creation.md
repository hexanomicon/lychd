---
title: 16. Creation
icon: material/creation
---

# :material-creation: 16. Creation: The Workflow of Autopoiesis

!!! abstract "Context and Problem Statement"
    The LychD architecture is designed for Autopoiesis (self-creation)—the capability for the system to autonomously expand its own logic and manifest new capabilities. However, allowing a probabilistic process to modify its own live source code presents a fundamental stability dilemma. A single syntax error or logical loop introduced during self-modification results in an immediate system lobotomy, causing a crash that prevents self-recovery and violates the doctrine of immutability. A formal ritual is required to govern the transition from "Idea" to "Reality."

## Requirements

- **Hermetic Isolation:** Physical prevention of live system file modification during the experimental phase.
- **Speculative Sandbox:** A protected environment (The Shadow Realm) that mirrors the production substrate but lacks the authority to impact Primary Reality.
- **The Verification Ritual:** Mandatory success of a formal verification suite (e.g., Unit Testing, Linting, Type Checking) before logic transitions from experiment to reality.
- **Atomic Promotion:** Transactional migration of code; broken or untested artifacts must be discarded rather than merged.
- **History Preservation:** Mandatory VCS version control (Git/JJ) from the moment of inception to ensure a permanent audit trail of the system's evolution.
- **Magus Oversight:** Integration with the **Human-in-the-Loop** protocol to ensure that no structural change occurs without the Magus's subjective verification.

## Considered Options

!!! failure "Option 1: Live Hot-Reloading"
    Allowing the Agent to modify the `.py` files currently being executed by the Vessel.
    - **Cons:** **Systemic Lobotomy.** A single syntax error or indentation mistake by a probabilistic model results in an immediate, unrecoverable crash. The machine kills itself before it can finish the change.

!!! failure "Option 2: Manual Pull-Request Workflow"
    Forcing the Agent to submit a VCS PR/Change that a human must manually merge on the host.
    - **Cons:** **Operational Stagnation.** It destroys the "Autonomous" nature of the Daemon. The Lych becomes a glorified "Code Assistant" rather than a sovereign entity capable of self-directed growth.

!!! success "Option 3: The Shadow Realm (Lab -> Test -> Promote)"
    Modifying code in an isolated `lab/` directory, verifying it with Ghouls, and only promoting it to the Crypt upon success.
    - **Pros:** **Crash Immunity.** The "Primary Reality" (The Crypt) is Read-Only. Evolution happens in the "Shadow Realm" (The Lab). The machine handles the "Nigredo" (Darkness/Errors) internally, only presenting the "Albedo" (Whitened Truth) for promotion.

## Decision Outcome

A formal **Creation Workflow** is adopted, governing how new intents are manifested into the system's body. The workflow is a linear path through the system's domains.

### 1. Invocation (Genesis)

When a Magus or an authorized process initiates a change, the system creates a new coordinate in the **Lab** region of the **[Crypt (13)](13-layout.md)**.

- **Freedom:** This directory is the site of conception. The process can break things here, install experimental dependencies, and generate files without affecting the active Daemon.
- **Context:** The process is provided with the current state of the Core and the **[lychd.lock (07)](07-snapshots.md)** to ensure the new creation is compliant with the system's existing laws.

### 2. Speculation (The Shadow Realm / Manas)

The initial labor is performed using a divergent VCS revision. This state of "Speculative Execution" allows for the exploration of multiple branching paths for a given problem. It is the domain of **Manas** (the divergent router), where the machine is permitted to generate "Vrittis" (fluctuations and parallel branches) to navigate the **Possibility Space**. The fruits of this speculation are presented to the Magus as "Visions" at the **[Altar (15)](15-frontend.md)**.

Using **Jujutsu (jj)**, this speculative state is even more natural: every modification in the working copy is automatically a "change" (revision) in the graph, providing implicit checkpointing without the friction of manual commits.

The agent graph orchestrating the speculation runs in the **Vessel**. Raw execution payloads (code edits, test suites, linter invocations) are dispatched to **The Tomb** container via SAQ for sandboxed execution. The Tomb returns `stdout` only; it does not run agent logic or LLM calls.

### 3. Creation (The Sequential Deep-Dive / Buddhi)

Once a valid path is found in the Shadow Realm, the machine must transition from exploration to execution. This is the domain of **Buddhi** (the convergent intelligence). 

When writing core logic with causal dependencies, the agent must operate in a **Single-Threaded, Deep Sequential** mode. Massive parallelism here is a "hallucination trap." Because of **Computational Irreducibility**, the agent cannot predict the end state of a complex logical loop; it must walk the path step-by-step. By enforcing **Stillness** (Metabolic Discipline) during the actual creation phase, the system maximizes logic-per-watt and prevents the introduction of recursive errors.

### 4. Verification (The Rite of Albedo)

Before leaving the Lab, every creation must undergo the **Verification Ritual**.

- **The Strike:** The system enqueues a job for the **[Ghouls (14)](14-workers.md)**.
- **The Test:** The Ghouls execute the verification suite (e.g., `ruff`, `pytest`) against the new code in isolation.
- **The Verdict:** If the tests fail, the process must iterate within the Lab. No human intervention is requested for technical errors; the machine must solve its own syntax.
- **Migration Isolation:** Verification rituals must utilize a transient, ephemeral database instance. The creator of the new logic must prove that all new relational models and migrations are valid against this empty shell before the logic is ever promoted to the Primary **[Phylactery](../sepulcher/phylactery/index.md)**.

### 5. Promotion (The Rite of Passage)

Once a creation is deemed "Stable" (passes all verification) and is consecrated by the Magus via **[Consent](25-hitl.md)**, it undergoes **[Assimilation](./35-assimilation.md)**.

1. **The Lock:** The new logic is formally added to the system's federated lockfile.
2. **The Move:** The directory is moved from the **Lab** (Read-Write) to the **Crypt** (Read-Only).
3. **The Rebirth:** The system signals a **[Packaging (17)](17-packaging.md)** ritual to forge the new physical body.

### 6. Conflict Sovereignty (The Magus Always Wins)

In the event of a "Temporal Collision"—where a file in Primary Reality has been modified by the Magus while an Agent was speculating on a change in the **Shadow Realm**:

- **Banishment of the Dream:** The system enforces a "Fail-Fast" merge policy. If a VCS merge conflict is detected during the **Promotion Ritual**, the Shadow Timeline is immediately banished.
- **Sovereign Authority:** The machine possesses no authority to overwrite manual changes made by the Magus.
- **Resynchronization:** The Agent must be re-awakened to the new reality, internalizing the Magus's changes before it is permitted to initiate a new cycle of creation.

### Consequences

!!! success "Positive"
    - **Crash Immunity:** Syntax errors are trapped in the Lab, making it physically impossible for an autonomous process to lobotomize the running Daemon.
    - **Auditability:** Every evolution of the system is a VCS revision (commit/change), allowing the Magus to trace the "Chain of Thought" that led to a specific code change.
    - **Disciplined Autonomy:** The system handles the labor of debugging and testing, only presenting the Magus with a "Verified Truth."

!!! failure "Negative"
    - **Operational Latency:** Creating even a simple script requires the full ceremony of "Create -> Test -> Promote."
    - **Storage Accumulation:** The Lab may accumulate abandoned experiments if not pruned by a maintenance ritual.
