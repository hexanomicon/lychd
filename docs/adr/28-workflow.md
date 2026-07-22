---
title: 28. Workflow
icon: material/tournament
---

# :material-tournament: 28. Workflow: The Weaver

!!! abstract "Context and Problem Statement"
    Cognitive labor involving multiple asynchronous **[Workers (ADR 14)](./14-workers.md)** and specialized **[Agents (ADR 20)](./20-agents.md)** often devolves into execution chaos without a centralized executive function to govern tempo and sequence. While the machine possesses the raw topology of the **[Graph (ADR 24)](./24-graph.md)**, tactical movement between synapses remains uncoordinated, leading to fragmentation and logic drift. A mechanism is necessary to translate authenticated operator and application intent into synchronized, verifiable, stateful workflow and semantic capability demand while respecting the physical constraints of the iron.

## Requirements

- **Absolute Sequencing:** Mandatory enforcement of task order and temporal pacing for multi-stage processes spanning across the asynchronous worker substrate.
- **The Archivist Pattern:** Implementation of "Memory Weaving"—the automated execution of semantic scrying prior to agent invocation to hydrate the **[Context (ADR 21)](./21-context.md)** with relevant historical truth.
- **Associative Logic:** Integration of memory-filling rituals directly into the execution flow, transforming raw database artifacts into associative links within the reasoning cortex.
- **Interception and Cleansing:** Provision of a "Censor" middleware to perform anonymization or verification of data as it transitions between internal and external synapses.
- **Transactional Consistency:** Mandatory utilization of the **[Archive (ADR 27)](./27-memory.md)** and the Graph persistence boundary to record committed state transitions, enabling recovery from the last valid boundary without assuming every checkpoint already lives in Postgres.
- **Composition Assimilation:** One Weaver must accept shaped, explicitly selected Pattern and
  [Reference Composition](../compositions/index.md) contributions through the broader
  **[Extension Protocol (ADR 5)](./05-extensions.md)** without spawning competing workflow
  engines or hardwiring every application into the Core.
- **Strategic Alignment:** Coordination with the **[Orchestrator (ADR 23)](./23-orchestrator.md)** to ensure tactical pacing respects the physical constraints of the local iron.

## Considered Options

!!! failure "Option 1: Static Procedural Logic"
    Defining workflows as hardcoded Python function chains using standard loops and conditionals.
    - **Pros:** Immediate execution; familiar development pattern.
    - **Cons:** **Cognitive Fragility.** These chains are volatile and opaque to the **[Smith (ADR 35)](./35-assimilation.md)**, preventing the machine from autonomously refactoring its own rituals. They fail to support declared recovery boundaries, so state is lost when the process terminates or a durable wait is required.

!!! failure "Option 2: External Orchestration Engines (Temporal / Airflow)"
    Adopting enterprise-grade workflow platforms to manage task state and distribution.
    - **Pros:** Robust error handling; native support for long-running processes.
    - **Cons:** **Architectural Bloat.** These systems introduce significant resource overhead and external dependencies, violating the **[Single-Node Sovereignty (ADR 01)](./01-doctrine.md)**. They bifurcate the machine's "Mind" from its "Tactics," creating latency that destroys the responsiveness of the machine.

!!! success "Option 3: One Weaver with Contributed Patterns"
    Implementing one workflow jurisdiction whose immutable Patterns govern the stateful movement
    of intent through functional graph steps and whose Portfolio organizes complete applications.
    - **Pros:**
        - **Total Synchronization:** Natively utilizes the **[Graph (ADR 24)](./24-graph.md)** engine to manage persistence and reanimation.
        - **Recursive Evolution:** The Smith may eventually generate, verify, and promote new
          Pattern or Composition contributions, allowing the machine to learn new ways of working
          without multiplying workflow authorities.
        - **Deep Integration:** Allows for "Memory Weaving" to be performed as a first-class citizen of the execution loop, ensuring agents are never born into a void.

## Decision Outcome

**The Weaver** is adopted as the singular logical workflow-application control plane. The
**Pattern** is its immutable executable primitive. Weaver manages application enablement and the
sequence, context, pacing, and continuity of admitted labor. The living [Reference Composition
Portfolio](../compositions/index.md) maps evolving application designs above Patterns.

The Weaver preserves temporal continuity of cognition across asynchronous steps. It prepares and synchronizes the field in which reasoning occurs, but it does not itself determine truth or identity.

Workflow is the backbone of the Ouroboros. It is the structure that lets a generated fluctuation return as usable state rather than vanish as a loose transcript. Shadow supplies candidate motion, Mirror supplies identity gravity, and Riddle supplies measurement; the Weaver binds their appearances into a repeatable Pattern with checkpoints, pauses, joins, and rehydration boundaries.

!!! note "Persistence foundation"
    The production-wired durable store targets one run-keyed Postgres `run_checkpoint` row carrying
    the complete Pydantic Graph snapshot document in JSONB. Focused memory-profile tests prove the
    resume and terminal-before-cleanup semantics; a real Postgres Consent-plus-Checkpoint restart
    receipt is still absent. Transactional submit/resume outbox, checkpoint-schema migration, and
    full cross-host recovery remain later Phylactery work. Weaver doctrine targets the persistence
    port rather than issuing direct database writes.

This is why workflows are not merely scripts. A script runs forward and forgets. A Weaver Pattern records where each step came from, which memory was woven into it, which identity owned it, which evidence measured it, and where it may safely resume. That temporal continuity is what lets self-reference become coherence rather than recursion for its own sake.

### 1. The Maestro Pattern (Tactical arm of the Will)

The Weaver translates authenticated Magus or Composition intent into admitted Invocations,
Pattern steps, gates, budgets, dependencies, and semantic capability demand. The
**[Orchestrator (ADR 23)](./23-orchestrator.md)** travels in the opposite direction of authority:
it receives capability demand and decides how physical services become ready. It never authors
the workflow's purpose.

New Pattern and Composition contributions follow the **[Smith (ADR 35)](./35-assimilation.md)** and
the **[Lab→Test→Promote rite (ADR 16)](./16-creation.md)** without exception. A generated way of
working enters through shaped contribution and immutable revision; it does not become a second
Weaver or acquire the jurisdictions of Graph, Dispatcher, Orchestrator, Phylactery, or HitL.

### 2. The Archivist (Memory Weaving)

When a Pattern explicitly declares memory preparation, the future Archivist performs a bounded
“Scry” ritual through the typed Archive port:

- It submits a classified, budgeted **[Vector Search (ADR 27)](./27-memory.md)** request rather than
  hidden SQL.
- It transforms raw database rows into Associative Links.
- These links are injected into the "Karma" block of the **[RunContext (ADR 21)](./21-context.md)**.
- By the time the **[Agent (ADR 20)](./20-agents.md)** receives control, the relevant memory is already part of its active reality.

The Archivist therefore activates attributable impressions before a requesting reasoning step.
It is neither ambient behavior on every node nor current delivery; the present Bridge Context has
reserved but empty memory chambers.

### 3. The Censor (Data Integrity)

To maintain the "Privacy Veil," the Weaver provides a Censor interceptor:

- Data moving between synapses is subjected to mandatory verification or anonymization.
- For external rituals (e.g., calling a remote peer), the Censor scrubs sensitive artifacts before they exit the **[Sovereignty Wall (ADR 09)](./09-security.md)**.
- Re-identification or de-anonymization is performed only upon the result's return to the internal substrate.

!!! note "The Gate-and-Censor Doctrine"
    The Censor shares the Sovereignty Wall with the **[Dispatcher's (ADR 22)](./22-dispatcher.md)** egress gate, and the two authorities must never be confused. The Dispatcher **gates**: it decides whether egress happens at all (privatization thresholds, fail-closed, `LYCHD_SECURE_MODE`). The Censor **transforms**: it anonymizes what has been permitted to cross and re-identifies on return. The Censor runs strictly downstream of the gate and may only narrow what crosses; it can never widen what the gate admits. The Censor's concrete algorithm remains future work, but its position is now law.

### 4. The Pattern (Pacing and Joins)

The Weaver utilizes the functional primitives of the graph to enforce the rhythm of thought:

- **Broadcasting:** Synchronizing the same input across multiple specialist agents for parallel analysis.
- **Spreading:** Distributing a list of tasks across the background worker force.
- **Joins:** Aggregating parallel results into a single "White Truth" before proceeding to the next station of the pattern.
- **Outcome Rubrics:** Carrying explicit success criteria through a multi-stage run so Riddle, Oculus, HitL, and the Magus can evaluate the final artifact against the same declared target.

The Weaver governs tempo and synchronization of these movements; validity and selection remain the responsibility of the workflow's evaluators and approval gates.

At each join, the workflow can close a loop: generated branches return to a shared state, failed branches become evidence, and the surviving continuation carries both measurement and identity forward. This is the practical shape of the semantic vortex in execution time.

A Reference Composition may collect several Patterns under one operator-visible purpose. Weaver
governs the Portfolio, immutable Pattern selection, logical priority, dependencies, overlap, and
schedule semantics. Workers own durable occurrence delivery and retry. Orchestrator owns model
residency, lease drain, prewarming, eviction, and swaps. Several Invocations may therefore remain
logically active while finite iron serializes their physical inference.

### 5. Interaction with HitL

A Pattern declares a Decision Point only where authority, uncertainty, or effect policy requires
the **[Sovereign Consent (ADR 25)](./25-hitl.md)** protocol. Read-only and fully preauthorized
Patterns need no ceremonial pause merely to satisfy topology. When a governed step does require a
decision—such as source promotion, public publication, deletion, or world restore—Weaver enters
Durable Stasis and projects the bounded choice for the Magus.

### 6. The Demarcation of Weaver and Shadow

The Weaver and **[Shadow Simulation (ADR 31)](./31-simulation.md)** both fan out parallel agent labor—the Weaver through Broadcasting, Spreading, and Joins; Phantasma through the Expansion of $N$ timelines. A Pattern author therefore requires an absolute rule for which fan-out belongs where. That rule is the **Demarcation Law**:

!!! important "The Demarcation Law"
    A branch that may commit an effect into the live Run belongs to the Weaver. A branch that may only produce a Vision belongs to the Shadow. The Weaver consumes Simulation results solely as consecrated Visions or as evidence in joins—never as direct state writes. The Dual-Gate governs only the Shadow's output.

Weaver branches execute inside the live Run, and their joins commit into real state. Shadow branches live in Jujutsu workspaces under `lab/shadow/` and can only ever emit Visions—promotion candidates—never direct effects. The Weaver never treats a Simulation result as an authority to write; it either receives that result already consecrated (ADR 25) or folds it into a join as measured evidence.

## Consequences

!!! success "Positive"
    - **Disciplined Labor:** Validated Patterns make temporal order, gates, budgets, and outcomes
      explicit rather than leaving them in an uninspectable script loop.
    - **Rich Working Memory:** When the Archivist is implemented, requesting steps can receive
      bounded, attributable historical context through the typed Archive port.
    - **Narrower Interoperability Risk:** When the Censor is implemented, it can minimize already
      authorized egress. It does not eliminate provider, peer, or re-identification risk.
    - **Stateful Resilience:** The typed Stasis port and memory-profile tests prove declared durable
      resume semantics, while production wiring targets the run-keyed Postgres checkpoint adapter.
      A real Postgres restart receipt, transactional submit/resume outbox, and broader recovery
      remain later consolidation.

!!! failure "Negative"
    - **Synapse Cost:** Scrying, cleansing, checkpointing, and gates add work that must be measured
      per Pattern; no universal latency bound is assumed.
    - **Architectural Rigor:** Pattern authors must satisfy the typed contribution and continuity
      contract, requiring more initial work than a simple script.
