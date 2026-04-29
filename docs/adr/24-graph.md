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
- **Durable Persistence:** Mandatory support for serializing the entire graph state—including message history and node progress—to the persistent substrate after every step completion.
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
        - **Durable Reanimation:** Standardized support for `BaseStatePersistence` allows the mind to be anchored in the database, enabling reanimation after system restarts or VRAM swaps.

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
2. **Stasis:** If the hardware is not ready, the node invokes a **Deferred Tool**.
3. **The Long Sleep:** The Graph executes an atomic exit, serializing the `StateT` to the **[Phylactery (ADR 06)](./06-persistence.md)** and liberating VRAM.
4. **Awakening:** Once the physical substrate is manifested, the Graph is re-entered via `iter_from_persistence()`, resuming at the exact point of suspension.

### 3. Parallel Reasoning: Broadcasting and Spreading

The architecture treats the mind as a multi-threaded organism, where graph traversals represent active fluctuations (**Vrittis**):

- **Broadcasting:** Identical data is sent to multiple steps simultaneously (e.g., requesting three different **[Personas (ADR 32)](./32-identity.md)** to critique a single plan).
- **Spreading (Mapping):** Elements of an iterable are fanned out to parallel paths (e.g., analyzing 50 files in parallel). These parallel paths represent competing Vrittis traversing the state space.
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

- **Mermaid Diagrams:** The graph produces `stateDiagram-v2` code for the **[Altar (ADR 15)](./15-frontend.md)**.
- **State Streaming:** Transitions are pushed via Server-Sent Events (SSE), allowing the Magus to monitor the Daemon navigating the complex topology of a task.

## Consequences

!!! success "Positive"
    - **Cognitive Resilience:** Thoughts survive system reboots and hardware failures through mandatory persistence.
    - **Physical Discipline:** The graph acts as a "polite citizen," negotiating for hardware at every synapse to prevent VRAM thrashing.
    - **Neural Scaling:** Logical parallelism allows the Daemon to scale its attention across multiple sub-tasks without manual intervention.
    - **Type Sovereignty:** The entire cortex is statically verifiable, preventing systemic slop.

!!! failure "Negative"
    - **Initialization Latency:** Constructing a graph-based workflow requires significant upfront architectural effort compared to procedural scripts.
    - **I/O Pressure:** High-frequency serialization of large states increases the load on the persistence layer.
