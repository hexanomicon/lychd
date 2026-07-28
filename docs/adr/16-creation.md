---
title: 16. Creation
icon: material/creation
---

# :material-creation: 16. Creation: The Workflow of Autopoiesis

!!! abstract "Context and Problem Statement"
    The LychD architecture is designed for Autopoiesis (self-creation)—the capability for the system to autonomously expand its own logic and manifest new capabilities. However, allowing a probabilistic process to modify its own live source code presents a fundamental stability dilemma. A single syntax error or logical loop introduced during self-modification results in an immediate system lobotomy, causing a crash that prevents self-recovery and violates the doctrine of immutability. A formal ritual is required to govern the transition from "Idea" to "Reality."

## Requirements

- **Hermetic Isolation:** Physical prevention of live system file modification during the experimental phase.
- **Speculative Sandbox:** A protected environment (The Shadow Realm) that mirrors the relevant
  production substrate without receiving promotion or host authority. Shared-resource and
  external effects must still be declared, bounded, and reconciled.
- **The Verification Ritual:** Mandatory success of a formal verification suite (e.g., Unit Testing, Linting, Type Checking) before logic transitions from experiment to reality.
- **Controlled Promotion:** Code and lock state move only through an attributable, verified
  promotion coordinate. Database, package, and external effects retain their own transaction and
  recovery boundaries; the composition does not pretend they are one atomic write.
- **History Preservation:** Jujutsu-backed VCS tracks candidate source and reviewable change
  history according to retention policy. VCS is artifact provenance, not a record of hidden model
  reasoning.
- **Promotion Authorization:** Integration with the **Human-in-the-Loop** protocol and Codex autonomy policy so structural promotion requires live Magus consent unless an explicitly bounded preauthorization class applies.

## Considered Options

!!! failure "Option 1: Live Hot-Reloading"
    Allowing the Agent to modify the `.py` files currently being executed by the Vessel.
    - **Cons:** **Systemic Lobotomy Risk.** A syntax error or logical failure can crash the active
      process before the candidate is reviewed and may leave recovery to an external operator.

!!! failure "Option 2: Manual Pull-Request Workflow"
    Forcing the Agent to submit a VCS PR/Change that a human must manually merge on the host.
    - **Cons:** **Operational Stagnation.** It destroys the "Autonomous" nature of the Daemon. The Lich becomes a glorified "Code Assistant" rather than a sovereign entity capable of self-directed growth.

!!! success "Option 3: The Shadow Realm (Lab -> Test -> Promote)"
    Modifying code in an isolated `lab/` directory, verifying it with Ghouls, and only promoting it to the Crypt upon success.
    - **Pros:** **Contained Candidate Failure.** The active Crypt stays outside the candidate-write
      path. Lab failures remain attributable and reviewable before promotion, while shared
      resources and later lifecycle effects still require explicit controls.

## Decision Outcome

A formal **Creation Workflow** is adopted as the target governing how new intents are manifested
into the system's body.

!!! warning "Doctrine ahead of execution"
    The current foundation does not implement the Shadow/Smith creation graph, Tomb executor,
    Jujutsu lock manifest, automated verification database, promotion transaction, or Rebirth
    command. The Vessel has a bounded Lab mount for trusted control-plane work, but no safe surface
    for autonomous arbitrary-code execution or self-promotion. Until the complete Tomb/nono and
    consent/promotion path exists, this ADR is workflow law—not an enabled autopoiesis feature.

### 1. Invocation (Genesis)

When a Magus or an authorized process initiates a change, the system creates a new coordinate in the **Lab** region of the **[Crypt (13)](13-layout.md)**.

- **Freedom:** This directory is the site of conception. The process can generate and revise files
  without directly mutating the active Crypt. Dependency installation, subprocesses, ports,
  databases, and network effects remain separately sandboxed or declared; a directory boundary
  alone does not contain them.
- **Context:** The process is provided with the current state of the Core and the **[Crypt lockfile (13)](13-layout.md)** to ensure the new creation is compliant with the system's existing laws.

### 2. Speculation (The Shadow Realm / The Call)

The initial labor is performed using a divergent VCS revision. This state of "Speculative
Execution" allows the exploration of multiple branching paths for a given problem. It is the domain
of **the Call** (Manas correspondence), where the machine may open movements within **the Flux**
to navigate the **Possibility Space**. The fruits of this speculation are presented to the Magus
as "Visions" at the **[Altar (15)](15-frontend.md)**.

Using **Jujutsu (jj)**, this speculative state is even more natural: every modification in the working copy is automatically a "change" (revision) in the graph, providing implicit checkpointing without the friction of manual commits.

The agent graph orchestrating the future speculation flow belongs in the **Vessel**. Safe
control-plane creation work may remain there: planning, graph routing, policy checks, structured
diff preparation, review packaging, and promotion decisions. Once the Tomb plane is implemented,
raw execution payloads (code edits, test suites, linter invocations, arbitrary scripts, or risky
tool calls) must be dispatched to it through a dedicated queue for sandboxed execution. The Tomb
will return bounded, untrusted results only; it must not run agent logic or LLM calls.

### 3. Creation (The Sequential Deep-Dive / The Blade)

Once a valid path is found in the Shadow Realm, the machine must transition from exploration to
execution. This is the domain of **the Blade** (Buddhi correspondence), the convergent
intelligence.

For tightly coupled core edits, the workflow favors a bounded sequential critical path with focused
checks after each causal change. Independent discovery, static analysis, and isolated candidate
experiments may still run in parallel when their merge boundary is explicit. **Stillness**
(Metabolic Discipline) means limiting concurrent mutation and context pressure; it reduces
coordination risk but cannot prevent logical error.

### 4. Verification (The Rite of Speculation)

Before leaving the Lab, every creation must undergo the **Verification Ritual**.

- **The Strike:** The system enqueues a job for the **[Ghouls (14)](14-workers.md)**.
- **The Test:** The Ghouls execute the verification suite (e.g., `ruff`, `pytest`) against the new code in isolation.
- **The Verdict:** If checks fail, policy may grant a bounded correction budget in the Lab. When
  that budget or a required premise is exhausted, the workflow returns truthful noncompletion and
  evidence instead of demanding unlimited self-repair.
- **Migration Isolation:** Verification uses disposable databases to exercise empty bootstrap and
  every supported upgrade path relevant to the candidate, including declared forward/rollback or
  recovery behavior. Those receipts prove the tested paths only; production promotion still
  requires the owning **[Phylactery](../sepulcher/phylactery/index.md)** lifecycle gate.

### 5. Promotion (The Rite of Passage)

Once a creation is deemed "Stable" (passes all verification) and is authorized through **[Consent](25-hitl.md)** or a Codex-defined preauthorization class, it undergoes **[Assimilation](./35-assimilation.md)**. High-stakes creation, schema changes, secrets, host lifecycle authority, and destructive actions still require live Magus consent.

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
    - **Reduced Active-Body Risk:** Syntax and focused verification failures can be caught before
      promotion. Shared resources, migrations, packaging, and restart still carry residual risk.
    - **Auditability:** Retained VCS changes, candidate artifacts, and verification receipts let the
      Magus trace what changed and why it was proposed without claiming access to hidden
      chain-of-thought.
    - **Disciplined Autonomy:** The system handles bounded debugging and testing labor, presenting
      the Magus with the surviving candidate, its evidence, and any unresolved limits.

!!! failure "Negative"
    - **Operational Latency:** Creating even a simple script requires the full ceremony of "Create -> Test -> Promote."
    - **Storage Accumulation:** The Lab may accumulate abandoned experiments if not pruned by a maintenance ritual.
