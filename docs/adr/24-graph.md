---
title: 24. Graph
icon: material/graph-outline
---

# :material-graph-outline: 24. Graph

!!! abstract "Context and Problem Statement"
    Reasoning via single agents provides atomic intelligence but proves insufficient for complex architectural tasks such as recursive self-modification or multi-stage strategic planning. Standard procedural scripts and nested function calls lack formal memory of the reasoning process, fail to navigate the physical constraints of hardware resources, and cannot be gracefully suspended across system restarts. A stateful, asynchronous, and non-linear engine is necessary to model complex workflows as directed graphs capable of surviving the "Long Sleep" of hibernation and facilitating parallel exploration of solution spaces.

## Requirements

- **Type Safety as the Cortex:** Mandatory passage of workflow memory as strongly typed `StateT`
  objects between nodes so declared state is validated by Pydantic at every synapse. This validates
  data shape, not hidden chain-of-thought or factual truth.
- **Orchestrated Handshakes:** Capability-consuming nodes submit requirements through the physical
  arbiter and wait until the substrate can satisfy the logical intent.
- **Durable Persistence:** Mandatory support for committing graph state at declared boundaries—including message history, typed state, deferred waits, and completed step outputs—to the persistent substrate.
- **Commit-Ordered Cleanup:** A checkpoint remains recoverable until the authoritative run ledger has committed a terminal status; graph iteration or resume success may never delete it early.
- **Functional Topology:** The future GraphBuilder adapter should use functional Steps to reduce
  boilerplate without invalidating the current typed `BaseNode` execution contract.
- **Logical Parallelism:** Future provision of primitives for **Broadcasting** (same data to
  multiple paths) and **Spreading** (fanning out elements of an iterable) to enable concurrent
  reasoning.
- **Join and Reduce Synchronization:** Implementation of specialized synchronization points to
  aggregate parallel results into one candidate or typed aggregate. A join determines graph shape;
  it does not establish factual truth by consensus.
- **Opaque Delegated Labor:** A Pattern may contain a typed delegated-agent macro-node whose
  foreign runtime can plan and use tools internally without importing that hidden topology into
  the LychD Graph.
- **Visible Topology and Evidence:** Pattern topology must remain inspectable independently of the
  correlated runtime events that say which stations an Invocation actually entered.

!!! warning "Implementation state"
    The deployed engine is the installed serial `BaseNode` API. It provides typed serial execution,
    declared checkpoint boundaries, hardware Live Stasis, and the supported consent-resume path.
    Functional GraphBuilder Steps, broadcasting, spreading, joins, and parallel execution remain
    future adapter work. Requirements for that target do not prove those primitives are delivered.

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
        - **Parallel Vocabulary:** The newer GraphBuilder API supplies map, broadcast, and join
          primitives, but the deployed legacy `BaseNode` runner does not execute nodes in parallel.
        - **Persistence Seam:** The v1 `BaseStatePersistence` interface lets LychD adapt graph
          snapshots to its own Postgres checkpoint store. The library supplies an interface, not
          production durability or recovery authority.

## Decision Outcome

**pydantic-graph** is adopted as the engine for the machine's cortex. The current runtime models
reasoning as a stateful asynchronous graph of typed `BaseNode` transitions. A future
`WorkflowRuntime` adapter may admit functional GraphBuilder Steps only after it preserves LychD's
checkpoint and evidence law.

The graph topology models cognitive process and fluctuation patterns, not identity. It captures how candidate paths branch, compete, and converge without assigning ownership of outcomes.


### 1. The Cognitive Units: Nodes and State

The cortex is built on the installed `pydantic_graph` **`BaseNode`** API — the mind is a set of typed nodes composed into a `Graph`:

- **Nodes:** Subclasses of `BaseNode[StateT, DepsT, ...]` implementing an async `run(self, ctx)` that returns the next node (or `End`) to determine the next station of thought. A `Workflow` binds such a graph to its routing metadata.
- **The State (`StateT`):** A mutable, JSON-serializable Pydantic model representing declared
  working state. It carries only the committed fields represented by its schema; it does not ensure
  total recall. Per-run handles (grants, models, toolsets) live in `deps`, never in state, so durable
  snapshots stay clean.

!!! warning "Doctrine ahead of code"
    LychD stays on the installed v1 `BaseNode` API. The dependency is explicitly constrained to
    `pydantic-ai-slim==1.25.1`: current upstream 2.x adds promising durability capabilities,
    deferred stream events, enqueued messages, and runtime model hooks, but also crosses the legacy
    graph/message boundary on which Stasis depends. The exact pin is a temporary migration fence,
    not a rejection of v2. An isolated upgrade must first prove deferred consent resume, serialized
    message/checkpoint compatibility, AgentForge/toolset behavior, and the streaming event union.
    GraphBuilder remains a beta execution adapter until LychD's own durable step ledger can govern it.

    The staged route is `1.25.1` → exact final-v1 bridge
    ([`1.107.1`](https://github.com/pydantic/pydantic-ai/releases/tag/v1.107.1), tag `54d51dbf`)
    with deprecations as errors → versioned LychD checkpoint/cursor and legacy parked-run migration
    → a `WorkflowRuntime` port → exact audited v2. The `1.107.1` patch is mandatory over `1.107.0`:
    it fixes the AG-UI `sanitize_messages` trailing-message authorization bypass; `1.107.0` lies in
    the affected range. Parallel GraphBuilder branches and external durability engines are separate
    experiments; neither may ride inside the checkpoint-format migration.

### 2. The Orchestrated Handshake (Deferred Logic)

Every capability-consuming node respects the physical laws established in the
**[Dispatcher (ADR 22)](./22-dispatcher.md)**. Before invoking an Agent, that node performs a
handshake:

1. **Intent Submission:** The node defines the required family and request traits (for example, `chat` with `image` input and tool support).
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

### Checkpoint Ownership and Terminal Commit

!!! note "Commit before cleanup"
    `GraphRunner` may create or resume snapshots, but it does not own their deletion. A returned
    graph result is not yet durable run truth: the process can still die before `RunStatus.DONE`
    reaches the ledger. The run worker therefore commits `DONE`, `FAILED`, or another terminal
    status first and only then asks the persistence boundary to remove the run-owned checkpoint row.
    If cleanup fails, the row remains for reconciliation. Consent and hardware parks remain
    non-terminal and keep their checkpoint.

    This ordering forbids the loss window `resume completes → checkpoint deleted → process dies →
    terminal status never committed`. Reanimation always prefers a retained committed boundary over
    silently restarting a run from its original intent.

!!! note "Run Events Are Observation, Not Recovery"
    A graph run may expose lanes and append-only events for the Altar and Oculus: node movement,
    child-agent branches, Tomb jobs, approval requests, hardware Stasis, and completion. These
    streams are the Magus's observation surface. They do not replace graph checkpoints, queue
    records, or Phylactery recovery boundaries.

    The event surface must support backfill plus live tail: stable `run_id`, `lane_id`, `step_id`,
    and `event_id` values allow the Altar, Oculus, and agent reviewers to resume observation
    without inventing state. Every relation declares whether it is containment, Pattern
    permission, correlation, explicit causal parentage, waiting, or another owned relation.
    Temporal adjacency, one trace identifier, or client layout cannot invent a causal edge or total
    order across independent producers. Approval appears as correlated request/result events,
    while the durable reanimation boundary remains the Graph checkpoint and queue record.

    The current single-process foundation gives every event a stable `event_id` and producer-local
    sequence. Each executable node attempt receives one occurrence identity shared by its
    entered/settled/waiting/failed phases. The Dispatcher emits a separate grant event only after
    acquisition and binds that occurrence to the issued grant/lease; automatic Orchestrator
    transitions retain the same run and occurrence. Lane, child-agent, tool-call, and multi-producer
    partial-order records remain later work.

!!! note "Implemented persistence floor vs Phylactery horizon"
    The current durable tier uses one Postgres `run_checkpoint` row per run. Its JSONB document is
    the complete, type-validated Pydantic Graph snapshot history and is foreign-key-owned by `run`.
    It supports process-death recovery for consent waits, with terminal-commit-owned cleanup. The
    live tier uses in-memory persistence for resident hardware waits; a process death during
    ordinary Live Stasis is reconciled as a failed run rather than silently replayed.

    `INSERT … ON CONFLICT … UPDATE` replaces the row atomically. The present topology has one
    in-process worker and a ledger claim fence per run; it is not a distributed execution protocol.
    A transactional submit/resume outbox, durable event stream, blob/artifact materializer,
    checkpoint schema migration, and cross-host lease recovery remain later Phylactery work.
    SAQ enqueue compensation and reconciliation narrow the current failure windows, but they are
    not a transactional outbox and must not be documented as one.

### 3. Delegated Agent Macro-Nodes

A **`DelegatedAgentNode`** is one typed Graph station that delegates a bounded task to an isolated
foreign agent runtime. Codex CLI, Claude Code, OpenCode, and later compatible runtimes are adapter
possibilities, not node kinds. The Graph sees one macro-node with declared inputs, outcomes, and
evidence. The runtime's private planner, tool loop, subagents, and provider-specific session format
remain opaque.

This boundary is deliberate:

- a delegated runtime is not a native LychD [Agent](./20-agents.md), Emissary, or child-agent lane;
- its hidden execution graph is not imported, inferred, or redrawn as LychD topology;
- provider JSONL is testimony from an adapter, not chain-of-thought or authoritative inner state;
  and
- multiple delegated jobs may execute concurrently only where the Pattern topology and admitted
  provider capacity both allow it. Internal foreign parallelism creates no implicit Graph edges.

The stable ownership is:

| Concern | Owner |
| :--- | :--- |
| Why the labor occurs, typed inputs and outcomes, and downstream routing | Pattern and Graph |
| Compatible `delegated_agent` capability and secret-free execution grant | [Dispatcher](./22-dispatcher.md) |
| Admitted provider capacity and configured quota posture | [Orchestrator](./23-orchestrator.md) |
| CLI/protocol invocation and provider-event normalization | [Extension adapter](./05-extensions.md) |
| Durable occurrence, idempotency, terminal adoption, and cancellation | `AgentJob` ledger |
| Filesystem, process, resource, and provider-egress containment | [Coffin and Provider Gate](./09-security.md) |
| Retained evidence and operator projection | [Oculus and Orb](./29-observability.md) |

#### The `AgentJob` Covenant

Every admitted macro-node occurrence creates or recovers one **`AgentJob`**. Its request binds an
idempotency key to the Run, Pattern station occurrence, attempt, delegated capability, input and
revision references, containment profile, allowed actions, timeout, resource and spending
ceilings, output schema, and capture policy. Prompts and artifacts are bounded values or references;
the job is not an ambient grant to the repository, home directory, network, or provider account.

The terminal result contains a terminal status, typed output, artifact or candidate-patch
references, normalized evidence, measured usage where available, and an explicit error or
unresolved condition. Blob bytes and credentials do not ride in the result. A returned patch is an
untrusted candidate artifact; it cannot promote itself or mutate the authoritative checkout.

The durable target state machine is:

```text
QUEUED → ADMITTED → PREPARING → RUNNING → SUCCEEDED
                                      ↘ FAILED
                                      ↘ TIMED_OUT
                                      ↘ CANCELLED
                                      ↘ LOST
```

An implementation may collapse preparatory states in its first internal model, but it may not
collapse the distinction between non-terminal and terminal truth. Transport is treated as
at-least-once. Submission, claim, terminal adoption, and resumption are therefore idempotent by the
stable Run/node-occurrence/attempt identity. A repeated id with different content fails closed.
`LOST` is terminal indeterminate truth: the external job can no longer be observed safely, so the
same occurrence is never started again automatically. It requires explicit reconciliation or a
new Pattern-authorized attempt with a new identity.

Once external labor is admitted, the Graph checkpoints and enters Durable Stasis with the reason
`AWAITING_DELEGATE`; the worker is free to exit. The `AgentJob` outlives that worker. Only an
idempotently committed terminal result correlated to the same occurrence and grant may request
Reanimation. Cancellation and timeout must stop the whole delegated process tree, revoke its Gate
capability, settle the job exactly once, and resume or terminate the Graph according to the
Pattern's declared route.

An in-memory coordinator, typed request/result models, or a parked-run signal proves only the
domain seam. It does not prove durable restart recovery, an effectful Coffin supervisor, provider
credential containment, or a working provider adapter. [State of
Work](../state-of-the-work.md#delegated-agent-execution) owns that delivery distinction.

#### Provider Trace Boundary

Adapters may retain a bounded, redacted raw trace as an artifact and must project stable semantic
events for lifecycle, admitted tools, file or artifact effects, usage, denials, and terminal
outcome. Every field is labelled either **LychD-observed** or **provider-reported**. Neither label
licenses storage of hidden chain-of-thought. Unsupported or malformed provider events remain
untrusted input: they may be quarantined or represented as an explicit gap, never executed or
silently promoted into system truth.

### 4. Parallel Reasoning: Broadcasting and Spreading

This section defines the future GraphBuilder target; none of these parallel primitives is delivered
by the current serial `BaseNode` engine. The architecture may later treat concurrent graph
traversals as movements within **the Flux** (Vṛtti correspondence):

- **Broadcasting:** Identical data is sent to multiple steps simultaneously (e.g., requesting three different **[Personas (ADR 32)](./32-identity.md)** to critique a single plan).
- **Spreading (Mapping):** Elements of an iterable are fanned out to parallel paths (e.g.,
  analyzing 50 files in parallel). These parallel paths represent competing movements traversing
  the state space.
- **Lens-Spreading:** For open-ended strategy work, Graph may spread the same intent across different operational lenses rather than different input items. The branches remain isolated during expansion and join only at a reducer or review step, preserving divergent range before convergence.
- **Joins and Reducers:** Parallel results are synchronized using `g.join` nodes and
  `ReducerFunctions` to synthesize one downstream candidate or aggregate. A join establishes graph
  shape and convergence, not factual truth; the selected value remains answerable to its owning
  evidence, identity, and authorization boundaries.
- **The First-Value Race:** In scenarios where speed and resource conservation are paramount, the
  cortex utilizes **`ReduceFirstValue`**. This mechanism is the moment **the Blade** takes over
  from **the Call**. Upon the first branch satisfying the reducer's declared success predicate,
  the system executes an immediate **Logical Banishment** of all sibling tasks. This pruning
  ritual ensures that VRAM is reclaimed and cognitive energy is focused on the selected timeline.
  The predicate proves only what it declares; `ReduceFirstValue` is a convergent cut expressed as
  graph topology, not a universal Pramāṇa gate.

### 5. Deterministic Routing & The Halting Problem

The current `BaseNode` runtime routes through typed return values. A future GraphBuilder adapter may
also use:

- **`g.decision()`:** Specialized nodes evaluate data against a set of branches.
- **Pattern Matching:** Branches utilize `g.match()` to route intent based on Type, Literal values, or custom predicates.
- **The Halting Problem:** An agent trapped in an unguided `while True` loop cannot predict its own outcome. To prevent infinite cognitive loops (Samsara), routing decisions frequently employ an "LLM as a judge." This ensures that a convergent, qualitative evaluation breaks the cycle, forcing the process toward resolution.

Topology is cognition without ownership: the graph determines process flow, while identity and promotion authority are handled elsewhere.

### 6. Pattern Topology and Runtime Observation

The two visual contracts must not be conflated:

- **Pattern score:** Weaver registers an immutable semantic manifest containing the Pattern
  identity/revision, checkpoint schema, station declarations, permitted edges, and digest. An
  admitted run pins that exact validated snapshot. `graph.mermaid_code()` (surfaced as
  `Workflow.mermaid()`) is a secondary `stateDiagram-v2` lens for the
  **[Loom](../divination/altar/loom.md)**. The manifest is presently author-declared beside the
  executable graph; its digest proves the declared score snapshot, not mechanical parity with
  every Python return path.
- **Invocation evidence:** The **[Orb](../divination/altar/orb.md)** now joins one Run to
  its valid pinned Pattern manifest and displays bounded producer-local status, node occurrence,
  dispatch grant, wait, and transition evidence. It labels retained coverage and gaps. It does not
  yet provide a live trace tail, graph-shaped evidence view, durable Oculus read model, child-agent
  lanes, or a cross-producer total order.

The semantic manifest and outline are the current score projection; Mermaid is an optional
plain-text/diagram lens. Neither is a runtime event contract, a future round-trippable Pattern IR,
or evidence that an Invocation entered or completed a node.

A manifest terminal station such as `end` is a declarative outcome, not an executable occurrence.
Pydantic Graph returns `End` directly; runtime evidence therefore records the final executable
node settlement and authoritative run terminal status. The Orb must not fabricate a synthetic
terminal-node occurrence.

## Consequences

!!! success "Positive"
    - **Bounded Resilience:** Declared durable boundaries can preserve committed graph state; current
      hardware Live Stasis remains process-local and a complete reboot receipt is still absent.
    - **Physical Discipline:** Capability-consuming nodes request grants through Dispatcher and
      Orchestrator instead of binding physical runtimes directly.
    - **Parallelism Seam:** GraphBuilder leaves a typed route to later fan-out and joins after the
      persistence adapter proves them.
    - **Type Sovereignty:** Typed state and return contracts catch shape errors; they do not prove
      complete topology, factual truth, or total static correctness.

!!! failure "Negative"
    - **Initialization Latency:** Constructing a graph-based workflow requires significant upfront architectural effort compared to procedural scripts.
    - **I/O Pressure:** High-frequency serialization of large states increases the load on the persistence layer.
