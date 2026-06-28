---
title: 24. Graph
icon: material/graph-outline
---

# :material-graph-outline: 24. Graph: The Cognitive Topology

!!! abstract "Context and Problem Statement"
    Reasoning via single agents provides atomic intelligence but proves insufficient for complex architectural tasks such as recursive self-modification or multi-stage strategic planning. Standard procedural scripts and nested function calls lack formal memory of the reasoning process, fail to navigate the physical constraints of hardware resources, and cannot be gracefully suspended across system restarts. A stateful, asynchronous, and non-linear engine is necessary to model complex workflows as directed graphs capable of surviving the "Long Sleep" of hibernation and facilitating parallel exploration of solution spaces.

## Requirements

- **Type Safety as the Cortex:** Mandatory passage of task memory as strongly-typed `StateT` objects between nodes to ensure the "Chain of Thought" is validated by Pydantic at every synapse.
- **Orchestrated Handshakes:** Integration with the system’s physical arbiter to submit capability requirements at each graph step, suspending execution until the hardware state matches the logical intent.
- **Durable Persistence:** Mandatory support for committing graph state at declared boundaries—including message history, typed state, deferred waits, and completed step outputs—to the persistent substrate.
- **Functional Topology:** Adoption of functional "Steps" over class-based nodes to enable high-velocity development and reduce architectural boilerplate.
- **Logical Parallelism:** Provision of primitives for **Broadcasting** (same data to multiple paths) and **Spreading** (fanning out elements of an iterable) to enable concurrent reasoning.
- **Join and Reduce Synchronization:** Implementation of specialized synchronization points to aggregate and "collapse" parallel results back into a single, verified truth.
- **Visual Scrying:** Automated generation of Mermaid diagrams to facilitate the visualization of internal logic and real-time state transitions for the Magus.

## Considered Options

!!! failure "Option 1: Procedural Logic (Function Chains)"
    Relying on standard Python control flow (loops and nested functions) to manage agent interactions.
    - **Pros:** Minimal learning curve for human developers; zero framework overhead.
    - **Cons:** **Non-Persistent.** The reasoning state is volatile; a process crash or hardware transition results in the total loss of progress. It lacks a formal mechanism for "Long Sleep" deferral, forcing the machine to remain active while waiting for slow tool results or human input.

!!! failure "Option 2: Dictionary-Based State Machines (LangGraph)"
    Utilizing established frameworks that rely on untyped dictionaries for state management.
    - **Pros:** Robust ecosystem; widespread community support for multi-agent patterns.
    - **Cons:** **Type-Safety Deficit.** Violation of the "Type Safety as the Cogito" doctrine. The lack of strict Pydantic validation at node boundaries introduces "Graph Slop," where hallucinated data structures cause runtime failures that cannot be detected by static analysis.

!!! success "Option 3: Type-Centric Functional Graphs (pydantic-graph)"
    Adopting an async-first graph library where nodes and edges are defined using Python generics and functional steps.
    - **Pros:**
        - **Static Verifiability:** Transitions are governed by return type hints, making the entire topology verifiable before execution.
        - **Native Parallelism:** Built-in primitives for broadcasting and mapping allow the mind to explore multiple "Shadow Realities" simultaneously.
        - **Durable Reanimation:** Standardized support for `BaseStatePersistence` allows the mind to be anchored in the database, enabling replay after system restarts, deferred approvals, or high-latency external waits. Ordinary VRAM swaps may remain Live Stasis when the Vessel process survives.

## Decision Outcome

**pydantic-graph** is adopted as the engine for the machine's cortex. Reasoning is modeled as a stateful, asynchronous graph where the movement of intent is governed by strict type hints and functional steps.

The graph topology models cognitive process and fluctuation patterns, not identity. It captures how candidate paths branch, compete, and converge without assigning ownership of outcomes.


### 1. The Cognitive Units: Steps and State

The cortex is constructed using the **`GraphBuilder`** pattern, defining the mind as a sequence of atomic **Steps**:

- **Steps:** Asynchronous functions decorated with `@g.step` that receive a `StepContext` and return values to determine the next station of thought.
- **The State (`StateT`):** A mutable Pydantic model representing the "Working Memory." It is built up as it passes through each synapse, ensuring total recall across the entire ritual.

### 2. The Orchestrated Handshake (Deferred Logic)

Every step in the graph respects the physical laws established in the **[Dispatcher (ADR 22)](./22-dispatcher.md)**. Before invoking an Agent, a node performs a handshake:

1. **Intent Submission:** The node defines the **CapabilitySet** required (e.g., `{"text-gen", "vision"}`).
2. **Grant Request:** The node asks the Dispatcher for a runtime grant instead of binding directly to a model, tool, container, or provider.
3. **Live Stasis:** If the required capability exists but the hardware is not ready, the node waits while the Orchestrator performs the physical transition. For ordinary VRAM swaps, the graph may remain alive in Vessel process memory.
4. **The Long Sleep:** If the wait must survive process death, reboot, human approval delay, or high-latency peer return, the Graph executes an atomic exit, serializing the `StateT` to the **[Phylactery (ADR 06)](./06-persistence.md)**.
5. **Awakening:** Once the physical substrate or external result is available, the Graph resumes from Vessel memory or is re-entered via persistence, depending on which boundary was crossed.

!!! note "Live vs Durable Stasis"
    A pause is described by two orthogonal axes; the mark of Durable Stasis is *who resumes the run*, not *whether state was written*.

    - **Live Stasis:** the run remains a resident in-process loop; resumption is self-directed. A checkpoint MAY be taken opportunistically, and its absence is lawful.
    - **Durable Stasis:** the run exits the process; a checkpoint MUST be taken; resumption requires **Reanimation**.

    Hardware transitions default to Live Stasis with an opportunistic checkpoint — a Phylactery write taken mid-swap is that opportunistic checkpoint, not a Reanimation boundary. HitL waits, Long Sleep, Vessel lifecycle intents, and deferred peer waits are Durable. Which boundaries *force* Durable is policy (see the **[Orchestrator (ADR 23)](./23-orchestrator.md)** drain and **[HitL (ADR 25)](./25-hitl.md)**), but the default table below is normative.

    | Pause boundary | Default Stasis |
    | :--- | :--- |
    | Hardware / VRAM swap | Live (opportunistic checkpoint) |
    | HitL approval wait | Durable |
    | Long Sleep | Durable |
    | Vessel lifecycle intent | Durable |
    | Deferred peer (A2A) wait | Durable |

!!! note "Graph Binding Boundary"
    Graph and Agent code should describe capability needs and consume granted runtime surfaces. They should not know whether the capability was satisfied by a warm local Soulstone, a runtime-native soft activation, a hard Quadlet swap, a Portal, or a Tomb execution payload. Current object names are allowed to change during R&D; the stable rule is that Graph topology owns cognitive flow, Dispatcher owns runtime binding, and Orchestrator owns physical readiness.

!!! note "Volatile Breath and Committed Progress"
    Volatile state is allowed. Active iterator frames, partial token streams, warm grants, derived context windows, and live adapter handles may live only in memory. The durable promise is narrower: committed step outputs, graph checkpoints, approval waits, external commitments, recovery markers, and traces must be persisted at declared boundaries. A crash may kill breath, but not committed progress.

!!! note "Run Events Are Observation, Not Recovery"
    A graph run may expose lanes and append-only events for the Altar and Oculus: node movement, child-agent branches, Tomb jobs, approval requests, hardware stasis, and completion. These streams are the Magus's observation surface. They do not replace graph checkpoints, queue records, or Phylactery recovery boundaries.

    The event surface must support backfill plus live tail: stable `run_id`, `lane_id`, `step_id`, and `event_id` values allow the Altar, Oculus, and agent reviewers to resume observation without inventing state. Approval should appear as correlated request/result events, while the durable reanimation boundary remains the Graph checkpoint and queue record.

### 3. Parallel Reasoning: Broadcasting and Spreading

The architecture treats the mind as a multi-threaded organism, where graph traversals represent active fluctuations (**Vṛttis**):

- **Broadcasting:** Identical data is sent to multiple steps simultaneously (e.g., requesting three different **[Personas (ADR 32)](./32-identity.md)** to critique a single plan).
- **Spreading (Mapping):** Elements of an iterable are fanned out to parallel paths (e.g., analyzing 50 files in parallel). These parallel paths represent competing Vṛttis traversing the state space.
- **Lens-Spreading:** For open-ended strategy work, Graph may spread the same intent across different operational lenses rather than different input items. The branches remain isolated during expansion and join only at a reducer or review step, preserving divergent range before convergence.
- **Joins and Reducers:** Parallel results are synchronized using `g.join` nodes and `ReducerFunctions` to synthesize a single "White Truth." Join points perform determinative synthesis over competing paths.
- **The First-Value Race:** In scenarios where speed and resource conservation are paramount, the cortex utilizes **`ReduceFirstValue`**. This mechanism acts as the trigger for **Buddhi** taking over from **Manas**. Upon the discovery of a "White Truth" by the first successful parallel branch, the system executes an immediate **Logical Banishment** of all sibling tasks. This pruning ritual ensures that VRAM is reclaimed and cognitive energy is focused exclusively on the winning timeline, preventing the machine from lingering on redundant solutions. In practice, `ReduceFirstValue` is the decisive convergent cut expressed as graph topology.

### 4. Deterministic Routing & The Halting Problem

Routing through the cortex is type-safe and non-probabilistic:

- **`g.decision()`:** Specialized nodes evaluate data against a set of branches.
- **Pattern Matching:** Branches utilize `g.match()` to route intent based on Type, Literal values, or custom predicates.
- **The Halting Problem:** An agent trapped in an unguided `while True` loop cannot predict its own outcome. To prevent infinite cognitive loops (Samsara), routing decisions frequently employ an "LLM as a judge." This ensures that a convergent, qualitative evaluation breaks the cycle, forcing the process toward resolution.

Topology is cognition without ownership: the graph determines process flow, while identity and promotion authority are handled elsewhere.

### 5. Visual Scrying (Mermaid Integration)

To provide transparency, the system generates real-time visualizations:

- **Mermaid Diagrams:** `graph.render()` produces `stateDiagram-v2` source (Mermaid text) for the **[Altar (ADR 15)](./15-frontend.md)**. The source is shipped as text and rendered client-side; there is no server-side image-rendering API.
- **State Streaming:** Transitions are pushed via Server-Sent Events (SSE), allowing the Magus to monitor the Daemon navigating the complex topology of a task.

## Consequences

!!! success "Positive"
    - **Cognitive Resilience:** Committed graph progress survives system reboots and hardware failures through mandatory persistence.
    - **Physical Discipline:** The graph acts as a "polite citizen," negotiating for hardware at every synapse to prevent VRAM thrashing.
    - **Neural Scaling:** Logical parallelism allows the Daemon to scale its attention across multiple sub-tasks without manual intervention.
    - **Type Sovereignty:** The entire cortex is statically verifiable, preventing systemic slop.

!!! failure "Negative"
    - **Initialization Latency:** Constructing a graph-based workflow requires significant upfront architectural effort compared to procedural scripts.
    - **I/O Pressure:** High-frequency serialization of large states increases the load on the persistence layer.
