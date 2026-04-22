---
title: 28. Workflow
icon: material/tournament
---

# :material-tournament: 28. Workflow: The Weaver

!!! abstract "Context and Problem Statement"
    Cognitive labor involving multiple asynchronous **[Workers (ADR 14)](./14-workers.md)** and specialized **[Agents (ADR 20)](./20-agents.md)** often devolves into execution chaos without a centralized executive function to dictate tempo and sequence. While the machine possesses the raw topology of the **[Graph (ADR 24)](./24-graph.md)**, the tactical movement of data between synapses remains uncoordinated, leading to fragmentation and logic drift. A mechanism is necessary to translate the strategic intent of the machine's physical will into a synchronized, verifiable, and stateful ritual—ensuring that every step of a litany is provided with woven context and purified data.

## Requirements

- **Absolute Sequencing:** Mandatory enforcement of task order and temporal pacing for multi-stage processes spanning across the asynchronous worker substrate.
- **The Archivist Pattern:** Implementation of "Memory Weaving"—the automated execution of semantic scrying prior to agent invocation to hydrate the **[Context (ADR 21)](./21-context.md)** with relevant historical truth.
- **Associative Logic:** Integration of memory-filling rituals directly into the execution flow, transforming raw database artifacts into associative links within the reasoning cortex.
- **Interception and Cleansing:** Provision of a "Censor" middleware to perform anonymization or verification of data as it transitions between internal and external synapses.
- **Transactional Consistency:** Mandatory utilization of the **[Archive (ADR 27)](./27-memory.md)** to mirror every state transition, enabling reanimation from the point of failure.
- **Extension Sovereignty:** Implementation as a pluggable primitive, allowing specialized executive functions (e.g., a "Research Maestro") to be registered via the **[Extension Context (ADR 5)](./05-extensions.md)**.
- **Strategic Alignment:** Coordination with the **[Orchestrator (ADR 23)](./23-orchestrator.md)** to ensure tactical pacing respects the physical constraints of the local iron.

## Considered Options

!!! failure "Option 1: Static Procedural Logic"
    Defining workflows as hardcoded Python function chains using standard loops and conditionals.
    - **Pros:** Immediate execution; familiar development pattern.
    - **Cons:** **Cognitive Fragility.** These chains are volatile and opaque to the **[Smith (ADR 35)](./35-assimilation.md)**, preventing the machine from autonomously refactoring its own rituals. They fail to support the "Long Sleep" reanimation routine, as state is lost the moment a process terminates or a hardware swap is triggered.

!!! failure "Option 2: External Orchestration Engines (Temporal / Airflow)"
    Adopting enterprise-grade workflow platforms to manage task state and distribution.
    - **Pros:** Robust error handling; native support for long-running processes.
    - **Cons:** **Architectural Bloat.** These systems introduce significant resource overhead and external dependencies, violating the **[Single-Node Sovereignty (ADR 01)](./01-doctrine.md)**. They bifurcate the machine's "Mind" from its "Tactics," creating latency that destroys the responsiveness of the machine.

!!! success "Option 3: The Weaver (Executive Graph Extensions)"
    Implementing workflows as specialized extensions that govern the stateful movement of intent through functional graph steps.
    - **Pros:**
        - **Total Synchronization:** Natively utilizes the **[Graph (ADR 24)](./24-graph.md)** engine to manage persistence and reanimation.
        - **Recursive Evolution:** The Smith possesses the capability to generate and install new Weavers, allowing the machine to learn new "Ways of Working."
        - **Deep Integration:** Allows for "Memory Weaving" to be performed as a first-class citizen of the execution loop, ensuring agents are never born into a void.

## Decision Outcome

**The Weaver** is adopted as the definitive workflow primitive. It functions as the Maestro of the machine's internal processes, managing the sequence, context, and pacing of labor.

The Weaver preserves temporal continuity of cognition across asynchronous steps. It prepares and synchronizes the field in which reasoning occurs, but it does not itself determine truth or identity.

### 1. The Maestro Pattern (Tactical arm of the Will)

The Weaver translates the strategy of the **[Orchestrator (ADR 23)](./23-orchestrator.md)** into tactical steps. It manages the temporal execution of nodes, coordinating between immediate reflexes and long-term rituals. By registering via the extension hook, the Weaver grafts itself onto the core, ensuring all multi-stage labor follows a disciplined litany.

### 2. The Archivist (Memory Weaving)

Before a reasoning step wakes in the cortex, the Weaver performs the "Scry" ritual:

- It executes a background SQL and **[Vector Search (ADR 27)](./27-memory.md)** based on the current state.
- It transforms raw database rows into Associative Links.
- These links are injected into the "Karma" block of the **[RunContext (ADR 21)](./21-context.md)**.
- By the time the **[Agent (ADR 20)](./20-agents.md)** receives control, the relevant memory is already part of its active reality.

The Archivist therefore activates latent impressions before reasoning starts, weaving memory into fluctuation so downstream steps receive prepared associations rather than raw storage.

### 3. The Censor (Data Integrity)

To maintain the "Privacy Veil," the Weaver provides a Censor interceptor:

- Data moving between synapses is subjected to mandatory verification or anonymization.
- For external rituals (e.g., calling a remote peer), the Censor scrubs sensitive artifacts before they exit the **[Sovereignty Wall (ADR 09)](./09-security.md)**.
- Re-identification or de-anonymization is performed only upon the result's return to the internal substrate.

### 4. The Litany (Pacing and Joins)

The Weaver utilizes the functional primitives of the graph to enforce the rhythm of thought:

- **Broadcasting:** Synchronizing the same input across multiple specialist agents for parallel analysis.
- **Spreading:** Distributing a list of tasks across the background worker force.
- **Joins:** Aggregating parallel results into a single "White Truth" before proceeding to the next station of the litany.

The Weaver governs tempo and synchronization of these movements; validity and selection remain the responsibility of the workflow's evaluators and approval gates.

### 5. Interaction with HITL

Every workflow includes a "Decision Point" that triggers the **[Sovereign Consent (ADR 25)](./25-hitl.md)** protocol. When a litany reaches a high-order synapse (e.g., system promotion), the Weaver initiates the stasis event and manifests the scried "Vision" at the interface, awaiting the Magus's signal to resume the tempo.

## Consequences

!!! success "Positive"
    - **Disciplined Labor:** Cognitive rituals are executed with absolute temporal and logical precision.
    - **Rich Working Memory:** The Archivist ensures that every agent thought is perpetually enriched by the machine's historical experience.
    - **Safe Interoperability:** The Censor allows the machine to participate in external swarms without risking the Magus's secrets.
    - **Stateful Resilience:** Rituals survive the physical reanimation of the machine through mandatory database mirroring.

!!! failure "Negative"
    - **Synapse Latency:** The rituals of scrying and cleansing add a sub-millisecond overhead to every transition between steps.
    - **Architectural Rigor:** Extension authors must adhere to the strict Litany structure, requiring higher initial engineering effort compared to simple scripts.
