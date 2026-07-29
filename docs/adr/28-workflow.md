---
title: 28. Workflow
icon: material/tournament
---

# :material-tournament: 28. Workflow: The Weaver

!!! abstract "Context and Problem Statement"
    Cognitive labor involving multiple asynchronous **[Workers (ADR 14)](./14-workers.md)** and specialized **[Agents (ADR 20)](./20-agents.md)** often devolves into execution chaos without a centralized executive function to govern tempo and sequence. While the machine possesses the raw topology of the **[Graph (ADR 24)](./24-graph.md)**, tactical movement between synapses remains uncoordinated, leading to fragmentation and logic drift. A mechanism is necessary to translate authenticated operator and application intent into synchronized, verifiable, stateful workflow and semantic capability demand while respecting the physical constraints of the iron.

## Requirements

- **Absolute Sequencing:** Mandatory enforcement of task order and temporal pacing for multi-stage processes spanning across the asynchronous worker substrate.
- **The Archivist Pattern:** Implementation of "Memory Weaving"—the automated execution of semantic retrieval prior to agent invocation to hydrate the **[Context (ADR 21)](./21-context.md)** with relevant historical truth.
- **Associative Logic:** Integration of memory-filling rituals directly into the execution flow, transforming raw database artifacts into associative links within the reasoning cortex.
- **Interception and Cleansing:** Provision of a "Censor" middleware to perform anonymization or verification of data as it transitions between internal and external synapses.
- **Transactional Consistency:** Mandatory utilization of the **[Archive (ADR 27)](./27-memory.md)** and the Graph persistence boundary to record committed state transitions, enabling recovery from the last valid boundary without assuming every checkpoint already lives in Postgres.
- **Composition Assimilation:** One Weaver must accept shaped, explicitly selected Pattern,
  [Reference Composition](../compositions/index.md), and Suite contributions through the broader
  **[Extension Protocol (ADR 5)](./05-extensions.md)** without spawning competing workflow
  engines or hardwiring every application into the Core.
- **Typed Semantic Return:** Downstream evaluation may return versioned findings, attribution
  candidates, invalidated support, and bounded correction requests to the rightful owner without
  creating reverse execution edges, implicit mutation, ambient training, or a second scheduler.
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
          Pattern, Composition, or Suite contributions, allowing the machine to learn new ways of
          working without multiplying workflow authorities.
        - **Deep Integration:** Allows for "Memory Weaving" to be performed as a first-class citizen of the execution loop, ensuring agents are never born into a void.

## Decision Outcome

**The Weaver** is adopted as the singular logical workflow-application control plane. The
**Pattern** is its immutable executable primitive. Weaver manages application enablement and the
sequence, context, pacing, and continuity of admitted labor. The living [Reference Composition
Portfolio](../compositions/index.md) maps evolving application and Suite designs above Patterns.

The Weaver preserves temporal continuity of cognition across asynchronous steps. It prepares and synchronizes the field in which reasoning occurs, but it does not itself determine truth or identity.

Workflow is the backbone of the Ouroboros. It is the structure that lets a generated fluctuation return as usable state rather than vanish as a loose transcript. Shadow supplies candidate motion, Mirror supplies identity gravity, and Riddle supplies measurement; the Weaver binds their appearances into a repeatable Pattern with checkpoints, pauses, joins, and rehydration boundaries.

!!! note "Persistence foundation"
    The production-wired durable store targets one run-keyed Postgres `run_checkpoint` row carrying
    the complete Pydantic Graph snapshot document in JSONB. Focused memory-profile tests prove the
    resume and terminal-before-cleanup semantics; a real Postgres Consent-plus-Checkpoint restart
    receipt is still absent. Transactional submit/resume outbox, checkpoint-schema migration, and
    full cross-host recovery remain later Phylactery work. Weaver doctrine targets the persistence
    port rather than issuing direct database writes.

!!! note "Implemented Pattern identity floor"
    Each registered workflow now carries an immutable semantic manifest: URL-safe Pattern identity
    and revision, checkpoint schema, station declarations, permitted edges, and
    a deterministic digest. Run admission stores that exact validated snapshot, and execution
    rejects a stored snapshot whose checksum or current registered identity no longer agrees.
    Loom uses the same exact revision; the Orb links back only while the pinned snapshot validates.

    The current registry accepts only one workflow for a given name, and the worker resolves the
    current registered definition by that name. Historical revisions do not remain executable
    merely because a Run pinned their snapshot. If the revision is unavailable or drifted, the
    worker fails honestly. Multi-revision registration, publication, drain, and migration remain
    future Weaver work.

    This is a version/pinning and inspection floor, not the future round-trippable Pattern IR.
    Station and edge declarations are authored beside the executable Python Graph and are not yet
    mechanically derived from every return path. The digest therefore fingerprints the declared
    score; executable/manifest parity remains a review and test responsibility until Weaver owns a
    canonical declarative compiler.

!!! important "Admission ordering"
    Admit one Run by committing the Run and its pinned Pattern snapshot, retaining the
    caller-owned initiating record under the canonical Run identity, and only then publishing work
    to the broker. Failure before or during publication must compensate the queued Run. This
    ordering closes the fast-worker race without pretending the current broker boundary is a
    transactional outbox.

!!! note "Implemented Bridge continuity floor"
    A Bridge session now owns serialized completed Pydantic AI message history separately from
    optimistic display turns. Settlement appends the visible agent reply and `new_messages()`
    suffix under one session-store operation. Provider hops are normalized to the owning LychD run,
    so the next run selects newest whole completed turns within turn and character bounds rather
    than splitting consent calls from their returns. It validates them through Pydantic AI's
    message adapter and reassembles Context after the actual Dispatcher grant so the environment
    and context window are grant-bound. A paused current-turn chain is indivisible and charged
    before older history on resume. This is completed-session continuity, not Archive retrieval or
    arbitrary full-session replay.

This is why workflows are not merely scripts. A script runs forward and forgets. A Weaver Pattern
records immutable score identity, topology, checkpoint schema, and permitted continuation. A future
Invocation record may correlate that Pattern with memory, identity, and evidence records owned by
their respective offices; the Pattern does not absorb those authorities. That temporal continuity
lets self-reference become coherence rather than recursion for its own sake.

### 1. The Maestro Pattern (Tactical arm of the Will)

The Weaver translates authenticated Magus or Composition intent into admitted Invocations,
Pattern steps, gates, budgets, dependencies, and semantic capability demand. The
**[Orchestrator (ADR 23)](./23-orchestrator.md)** travels in the opposite direction of authority:
it receives capability demand and decides how physical services become ready. It never authors
the workflow's purpose.

New Pattern, Composition, and Suite contributions follow the
**[Smith (ADR 35)](./35-assimilation.md)** and the
**[Lab→Test→Promote rite (ADR 16)](./16-creation.md)** without exception. A generated way of
working enters through shaped contribution and immutable revision; it does not become a second
Weaver or acquire the jurisdictions of Graph, Dispatcher, Orchestrator, Phylactery, or HitL.

### 2. The Archivist (Memory Weaving)

When a Pattern explicitly declares memory preparation, the future Archivist performs a bounded
**Recall** ritual through the typed Archive port:

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

The current Weaver executes serial `BaseNode` Patterns. A future GraphBuilder-backed runtime may
use these functional primitives only after it preserves the same admission, persistence, and
evidence law:

- **Broadcasting:** Synchronizing the same input across multiple specialist agents for parallel analysis.
- **Spreading:** Distributing a list of tasks across the background worker force.
- **Joins:** Aggregating parallel results into one typed candidate or shared state before
  proceeding to the next station. The join synchronizes topology; workflow evaluators and owning
  gates establish what is supported, permitted, and promotable.
- **Outcome Rubrics:** Carrying explicit success criteria through a multi-stage run so Riddle, Oculus, HitL, and the Magus can evaluate the final artifact against the same declared target.

The Weaver governs tempo and synchronization of these movements; validity and selection remain the responsibility of the workflow's evaluators and approval gates.

One station may be a
[`DelegatedAgentNode`](./24-graph.md#3-delegated-agent-macro-nodes). The Pattern declares why it is
needed, its typed inputs and outcomes, eligible containment profile, budget envelope, timeout,
failure/cancellation routes, and permitted downstream use. It does not name a CLI command, mount a
credential, choose quota posture, interpret provider JSONL, or expose the foreign runtime's private
subgraph. Provider adapters and pool policy are configuration and Extension concerns, not new
Compositions.

At each join, the workflow can close a loop: generated branches return to a shared state, failed branches become evidence, and the surviving continuation carries both measurement and identity forward. This is the practical shape of the semantic vortex in execution time.

A Reference Composition may collect several Patterns under one operator-visible purpose. A
**Suite** may arrange several separately owned Compositions and their typed artifact or intent
handoffs into one versioned operator-visible graph. Weaver governs the Portfolio, immutable
Pattern selection, logical priority, dependencies, overlap, and schedule semantics. Workers own
durable occurrence delivery and retry. Orchestrator owns model residency, lease drain, prewarming,
eviction, and swaps. Several Invocations may therefore remain logically active while finite iron
serializes their physical inference.

Suite is coordination and projection law, not a new super-application authority. Each member
retains its domain records, Patterns, effects, policy, and independent utility. A Suite descriptor
may pin eligible Composition and Pattern revisions, handoff schemas, shared correlation,
aggregate ceilings, and partial-completion policy. It cannot merge secrets or Sigils, grant a
downstream effect, reinterpret an artifact, or treat one member's HitL as consent for another.

Suite execution is Designed. Before an automated Suite edge may admit a child Invocation, Weaver
must define parent/child identity, exact revision selection, input/output closure, fan-out/join
semantics, budget reservation, cancellation, Stasis, retry, idempotent effect receipts,
compensation, and truthful partial completion. Until then, cross-Composition handoffs are explicit
artifact-backed admissions and Loom may project the graph without executing it.

The Call/Manas may open and route an Intent into one or more attributable charcoal Suite drafts
through bounded Agent, Graph, ReCall, or Shadow work. It is an office distributed across those
mechanisms, not a planner service and not promotion authority. The Blade and declared evaluators
discriminate among candidates; schema validation, policy, and the Magus govern publication; only
Weaver admits the resulting exact Pattern Invocations.

#### Semantic return across a Suite

Riddle may evaluate an observed downstream consequence against the exact pinned graph and publish
`SuiteFindingSet@1`, `AttributionCandidate@1`, `InvalidationSet@1`, and
`CorrectionRequest@1` records under **[ADR 34](./34-evaluation.md)**. They may be drawn against the
direction of production, but they are evidence and candidate intent—not executable Graph edges.

Weaver may admit a correction only as a new forward Invocation after resolving the addressed
Composition and Pattern revision, validating the typed input, reserving a bounded repair budget,
and applying ordinary authority and HitL policy. It never resumes an old producer at an arbitrary
node, mutates an accepted artifact in place, inherits downstream authority, or converts a finding
into a trainer job.

The repair plan starts from Riddle's smallest **supported** cut, not the nearest or cheapest node.
It preserves unrelated branches only when their complete declared input and evaluation closure
remain unchanged, pins regression sentinels, and stops on repeated findings or budget exhaustion.
Unresolved rival attribution may justify a broader bounded trial; it never justifies system-wide
blame or an infinite producer-consumer loop.

Mirror preserves the distinct actors, Sigils, Persona/Posture revisions, providers, tools, human
edits, evaluators, and correction authors across both faces of the Suite. That answers who and
whose, not what caused failure. Soulforge remains a separate training office: semantic return is
not a gradient, runtime traces are not an implicit corpus, and only an independently admitted
training Pattern may alter candidate weights.

### 5. Pattern Projection and Drafting

The **[Loom](../divination/altar/loom.md)** may project the Portfolio and an exact Pattern revision,
but a current Python `BaseNode` graph is executable source—not a round-trippable visual document.
Renderer nodes, edges, groups, and coordinates never become Weaver truth.

Loom distinguishes:

- **charcoal** — an attributable inert candidate pinned to an exact base revision; and
- **law** — a validated, reviewed, published immutable Pattern revision.

No browser or model gesture crosses that boundary implicitly. Before Loom can author an executable
draft, Weaver must own one canonical declarative Pattern intermediate representation that carries
stable identity, reusable step-type references, typed inputs and outputs, state transfer,
reachability, termination bounds, effects, gates, capability requirements, authority, provenance,
and checkpoint/resume compatibility. The Vessel validates the complete draft; publication creates
a new immutable revision; existing Invocations remain pinned.

Nested or callable Patterns are not accepted merely because a renderer can draw a frame around
nodes. A Suite does not bypass that boundary. Before a Sub-Pattern, automated Suite edge, or
extraction operation becomes executable, Weaver must define invocation identity, cut-set inputs
and outputs, state closure, effect ownership, cancellation, Stasis, resume, and checkpoint
compatibility. An arbitrary selection of Python nodes or Composition cards cannot be extracted
safely without that law.

### 6. Interaction with HitL

A Pattern declares a Decision Point only where authority, uncertainty, or effect policy requires
the **[Sovereign Consent (ADR 25)](./25-hitl.md)** protocol. Read-only and fully preauthorized
Patterns need no ceremonial pause merely to satisfy topology. When a governed step does require a
decision—such as source promotion, public publication, deletion, or world restore—Weaver enters
Durable Stasis and projects the bounded choice for the Magus.

### 7. The Demarcation of Weaver and Shadow

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
    - **Synapse Cost:** Retrieval, cleansing, checkpointing, and gates add work that must be measured
      per Pattern; no universal latency bound is assumed.
    - **Architectural Rigor:** Pattern authors must satisfy the typed contribution and continuity
      contract, requiring more initial work than a simple script.
