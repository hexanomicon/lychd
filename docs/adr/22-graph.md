The updates to the **Agents ADR (19)** were very substantial. We successfully moved from a "conceptual" agent to a "technical" agent that understands **VRAM-dependent toolsets**, **recursive error correction (`ModelRetry`)**, and rich **multimodal artifacts (`ToolReturn`)**.

The most critical addition was **Section 8**, which established that **Embedders are Infrastructure**. This is the bridge between the "Mind" (Agent) and the "Body" (Runes).

Now, we move to **ADR 22. Graph: The Cognitive Topology**. This needs a massive enrichment from the Pydantic AI `pydantic-graph` documentation to show how the "Cortex" handles state, parallel thought, and the "Long Sleep" reanimation.

---

### File: `adr/22-graph.md` (Reworked)

---

title: 22. Graph
icon: material/graph-outline
---

# :material-graph-outline: 22. Graph: The Cognitive Topology

!!! abstract "Context and Problem Statement"
    A single Agent is an atomic neuron, capable of discrete reasoning, but complex architectural tasks—such as **Autopoiesis (16)**, recursive refactoring, or multi-stage strategic planning—require a "Cortex." Standard procedural scripts and nested functions are fundamentally brittle: they lack formal memory of the reasoning process, cannot be gracefully paused across system reboots, and fail to negotiate for limited hardware resources (VRAM) at each logical step. To transition from a simple tool into a pervasive Daemon, the system requires a **Cognitive Topology**—a stateful, asynchronous, and non-linear engine capable of modeling complex workflows as directed graphs that can survive the "Long Sleep" of hibernation.

## Requirements

- **Type Safety as the Cortex:** Mandatory passage of task memory as strongly-typed `StateT` objects between nodes, ensuring that the "Chain of Thought" is validated by Pydantic at every synapse.
- **Orchestrated Handshakes:** Every graph step must act as a client of the system sovereign, submitting capability requirements and suspending execution until the physical hardware state matches the logical intent.
- **Durable Persistence (The Long Sleep):** Mandatory support for serializing the entire graph state—including message history and node progress—to the **[Phylactery (06)](06-persistence.md)**, allowing reanimation after interruptions.
- **Logical Parallelism (Broadcasting/Spreading):** Support for "Fanning Out" reasoning paths to explore multiple solutions simultaneously, either by sending the same data to multiple paths or mapping an iterable across parallel tasks.
- **Join and Reduce Synchronization:** Provision of specialized nodes to aggregate, synchronize, and "collapse" parallel results back into a single, verified truth.
- **Conditional Branching (Decision Logic):** Support for high-fidelity routing based on type matching, literal values, or custom predicates to determine the next reasoning path.
- **Visual Scrying:** Support for the automated generation of Mermaid diagrams to allow the Magus to visualize the Daemon's internal logic and state transitions.

## Considered Options

!!! failure "Option 1: LangGraph"
    A popular framework for stateful multi-agent systems.
    - **Cons:** **Type-Safety Deficit.** LangGraph relies heavily on untyped dictionaries for state management, violating LychD's "Type Safety as the Cogito" principle. Its dependency on the broader ecosystem introduces architectural bloat and conflicts with the goal of a lean, sovereign kernel.

!!! failure "Option 2: Bespoke Finite State Machine (FSM)"
    Implementing a custom graph runner using standard Python `asyncio`.
    - **Cons:** **Operational Fragility.** Re-implementing complex features like cycle detection, partial persistence, and parallel reduction introduces massive technical debt and diverts resources from core AI development.

!!! success "Option 3: pydantic-graph"
    An async-first graph and state machine library where nodes and edges are defined using Python generics and type hints.
    - **Pros:**
        - **Typed Nodes (`BaseNode`):** Transitions are defined by return type hints, making the topology statically verifiable.
        - **Contextual Unity:** Provides a unified `GraphRunContext` for accessing mutable state, dependencies, and inputs.
        - **Native Parallelism:** Built-in primitives for **Broadcasting** (same data to N paths) and **Spreading** (N items to N paths).
        - **Durable Persistence:** Standardized protocol for `BaseStatePersistence` to anchor the mind in the database.

## Decision Outcome

**pydantic-graph** is adopted as the engine for the Daemon’s cortex. Reasoning is modeled as a stateful, asynchronous graph where transitions are governed by strict type hints and Pydantic validation.

### 1. The fundamental Units: Nodes and Steps

The cortex is composed of atomic units of work called **Steps**, which are orchestrated within a **Graph**.

- **Steps:** Async functions decorated with `@g.step` that receive a `StepContext` and return values to move the mind forward.
- **Nodes:** Subclasses of **`BaseNode`** that represent a specific station of reasoning.
- **The State (`StateT`):** A mutable Pydantic model representing the "Working Memory." It is build up as it passes through each node, ensuring total recall across the entire ritual.

### 2. The Orchestrated Node Handshake

Every step in the graph must respect the physical laws of the machine. Before invoking an **[Agent (19)](19-agents.md)**, a node performs a handshake with the sovereign dispatcher:

1. **Submit Intent:** The node defines the **CapabilitySet** required for the task (e.g., `{"text-generation", "vision"}`).
2. **Wait for Manifestation:** The graph execution suspends until the Sovereign manifests the required **[Coven (08)](08-containers.md)**.
3. **Execute Thought:** Once granted a `Model` and `FunctionToolset`, the node proceeds with the reasoning.

### 3. Durable Execution (The Long Sleep)

To handle tasks that span days or require human intervention, the Graph implements the **`BaseStatePersistence`** protocol.

- **Hibernation:** When a node raises a **`CallDeferred`** (external labor) or **`ApprovalRequired`** (Human-in-the-loop) signal, the `Graph` instance serializes its entire `StateT` and message history into the **[Phylactery (06)](06-persistence.md)**.
- **Reanimation:** The background **[Ghouls (14)](14-workers.md)** use `graph.iter_from_persistence()` to rehydrate the mind and resume execution exactly where it halted, ensuring zero context loss.

### 4. Parallel Execution: Broadcasting and Spreading

The architecture treats the mind as a multi-threaded organism capable of parallel thought:

- **Broadcasting:** Sending identical data to multiple nodes simultaneously to perform varied analyses on the same input.
- **Spreading (Mapping):** Fanning out elements from an iterable (e.g., a list of files or search results), processing each in parallel.
- **Async Streaming:** The system utilizes `@g.stream` to process values dynamically as they are yielded from an API, creating parallel tasks on-the-fly.

### 5. Joins and Reducers (The Collapse)

Parallel paths must eventually synchronize into a single decision. The system uses **Join Nodes** and **Reducers**:

- **Aggregation:** A `g.join` node waits for all parallel tasks to complete.
- **Reduction:** It uses a `ReducerFunction` (e.g., `reduce_list_append`, `reduce_dict_update`) to combine multiple outputs into a single object.
- **The First-Value Race:** In scenarios where speed is paramount, the system uses **`ReduceFirstValue`**, returning the first successful result and immediately canceling all other sibling tasks in the fork to reclaim VRAM.

### 6. Decision Nodes and Routing

Routing through the cortex is deterministic and type-safe.

- **`g.decision()`:** A specialized node that evaluates incoming data against a set of branches.
- **Pattern Matching:** Branches use **`g.match()`** to route data based on its Type, Literal values, or custom logic.
- **Priority:** Branches are evaluated in order; the first match is taken, allowing for "Catch-all" fallback paths using `object` or `Any`.

### 7. Scrying the Topology

To provide transparency to the Magus, the system generates real-time visualizations of its own thoughts.

- **Mermaid Diagrams:** The graph can generate `stateDiagram-v2` code to visualize the nodes, edges, and current state.
- **Altar Integration:** These diagrams are pushed to the **[Altar (15)](15-frontend.md)** via SSE, allowing the Magus to watch the Daemon navigate the complex topology of a task.

## Consequences

!!! success "Positive"
    - **Cognitive Resilience:** Thoughts survive system reboots and hardware failures through mandatory persistence.
    - **Physical Awareness:** The graph is a "polite citizen," negotiating for hardware at every step to prevent system-wide VRAM thrashing.
    - **Neural Scaling:** Logical parallelism allows the Daemon to scale its attention across multiple sub-tasks without manual intervention.
    - **Type Sovereignty:** The entire cortex is statically verifiable, preventing common "Agent slop" errors found in untyped frameworks.

!!! failure "Negative"
    - **Initialization Latency:** Setting up a graph-based workflow is more complex than a simple agent prompt, requiring upfront architectural discipline.
    - **Persistence Overhead:** Frequent serialization of large states can increase I/O pressure on the Phylactery.
    - **Recursion Limits:** Deeply nested parallel operations require careful monitoring to prevent "Cognitive Deadlocks" in the swarm.
