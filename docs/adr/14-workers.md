---
title: 14. Workers
icon: material/excavator
---

# :material-excavator: 14. Workers: The Ghouls

!!! abstract "Context and Problem Statement"
    The LychD Vessel is designed to be a high-performance, non-blocking interface. However, many tasks required of an autonomous daemon—waiting for long generative responses, performing recursive file operations, or executing complex verification rituals—are inherently slow and blocking. Running these tasks inside the primary web process presents a critical stability risk: a system crash wipes the volatile state, a container restart kills the active thought, and heavy CPU-bound operations can block the event loop, causing the application to fail health checks.

## Requirements

- **Labor Offloading:** Slow graph work must leave the request-handler lifecycle and execute through
  queue-backed worker loops. Operating-system process isolation is required before the untrusted
  execution plane lands, not for the v1 trusted in-process topology.
- **Persistence beyond Death:** Pending jobs must live in Postgres, while graph state is recoverable
  only at an explicitly committed checkpoint or terminal run boundary.
- **Transactional Integrity:** The foundation must compensate and reconcile the run-row/enqueue
  split; a true transactional outbox is the stronger target.
- **Anatomical Partitioning:** The queue tables share the unified database in v1. A separately
  owned `queue` schema/role is required before a semi-trusted Tomb worker receives credentials.
- **Orchestrated Discipline:** The labor force must be subject to the commands of the **[Orchestrator (23)](23-orchestrator.md)**, allowing for the pausing of specific queues during state transitions.
- **Reflex Arc Support:** The worker system must provide the infrastructure for the "Long Sleep"—the ability to rehydrate the state of a **[Graph (24)](24-graph.md)** and resume reasoning after an interruption.
- **Bounded Async Concurrency:** Each queue must expose an explicit concurrency bound and avoid
  blocking the event loop; capacity claims require measurement rather than an assumed job count.
- **Infrastructure Minimalism:** To adhere to the single-node doctrine, the system must not require a heavy external broker (e.g., Redis).

## Considered Options

!!! failure "Option 1: In-Memory Async (`asyncio.create_task`)"
    Spawning background tasks directly within the web server process.

    -   **Cons:** **Ephemeral.** All pending work is lost on restart. No backpressure management. It introduces the risk of the entire Vessel failing if a background task causes a segmentation fault or Out-of-Memory error.

!!! failure "Option 2: Heavyweight Durable Execution (Temporal)"
    The industry standard for reliable, long-running workflows.

    -   **Cons:** **Architectural Overkill.** Requires maintaining a Java or Go cluster and additional database engines. The operational complexity contradicts the goal of a self-contained, lightweight daemon.

!!! success "Option 3: Async Database Queue (SAQ)"
    Utilizing a lightweight, async-native queue backed by Postgres `SKIP LOCKED` and integrated into the backend framework.

    -   **Pros:**
        -   **Minimalism:** Reuses the existing database infrastructure; no new services to manage.
        -   **Atomicity Horizon:** A Postgres-backed queue can eventually participate in a designed
            transactional outbox. The current SAQ integration uses its own autocommit pool, so run
            creation and enqueue are compensated and reconciled rather than one transaction.
        -   **Efficiency:** The `SKIP LOCKED` mechanism provides high-performance job claiming without the polling overhead of legacy database queues.

## Decision Outcome

**SAQ** is adopted as the engine for the background workers, referred to as **Ghouls**.

!!! note "Ghoul vs worker — the animated labor and the engine"
    Code names the *mechanism*: `worker` (SAQ's own term — a persistent engine that claims jobs). **Ghoul** is the doctrinal name for the *animated labor* — one summoned, ephemeral unit of work (`perform_run`) that a worker raises, carries, and lets crumble. The engine persists; the Ghoul does not. One run may raise one *or more* Ghouls over its life (park → resume, fan-out).

### 1. The Architecture of Labor

In the v1 topology, the trusted `runs` and `rites` worker loops execute in the Vessel process on its
event loop. A separate operating-system worker process is the target topology for independently
scaled labor and remains mandatory for the future untrusted Tomb plane; both forms share the same
codebase and Postgres queue contract.

- **The Engine:** The worker utilizes the `SAQPlugin` provided by the **[Backend (11)](11-backend.md)** to ensure identical configuration and dependency injection.
- **The Postgres Substrate:** SAQ serializes jobs into its own `saq_*` tables in the configured
  Phylactery database. A separately owned `queue` schema and database role are a future isolation
  boundary, not part of the v1 wiring.
- **Async Efficiency:** The Ghouls wait asynchronously and use configurable per-queue concurrency;
  no current foundation guarantee claims thousands of simultaneous jobs on one process.
- **Worker Profile Binding (planned topology split):** A future explicit profile will decide which
  queues a process may claim, separating trusted Vessel work from a Tomb execution queue. No
  `LYCHD_WORKER_PROFILE`, Tomb queue, or Tomb worker process exists in the v1 foundation. The two
  implemented physical queues are `runs` and `rites`, and both execute inside the Vessel.

!!! note "Topology A (v1): one Vessel process with in-process ghouls"
    Both fixed v1 queues run **in-process** on the Vessel event loop with
    `QueueConfig.separate_process=False`. `SAQConfig.use_server_lifespan=False` disables SAQ's
    process-spawning server lifespan; each worker starts through the plugin's application-startup
    hook. The ghouls (`perform_run`) and SSE handlers therefore share the same process-local
    `InProcessRunEventBus`, so a run's tokens reach its open stream byte-for-byte.

    This topology requires exactly one ASGI/Granian worker process. Server startup rejects a
    `GRANIAN_WORKERS` or `--workers` value other than one. More processes would create isolated
    event buses: a Ghoul claimed in one process could publish events that an SSE connection in
    another process can never observe. Multi-process serving is forbidden until `RunEventBus` is
    backed by a shared transport such as `PostgresEventBus`.
    A separately isolated Tomb worker plane remains later work.

    Startup is fail-closed and ordered: both fixed v1 queues connect before the run substrate or
    web-facing service handle is published; registry loading and recovery complete before handlers
    can observe the runtime. A boot timestamp is captured before publication, so orphan recovery
    sweeps only runs from an earlier process rather than a run claimed during this startup. Shutdown
    stops in-process workers first, resets/closes their shared substrate second, and disconnects
    queues in reverse order last. A missing queue/plugin or partial connection cannot leave a
    healthy-looking engine that only black-holes work.

!!! warning "Implemented durability boundary"
    SAQ queue rows are durable, and startup reconciliation handles known stranded `RUNNING`, aged
    `QUEUED`, and decided-consent cases. Run-ledger creation and SAQ enqueue are not one atomic
    database transaction. If initial publication raises or its caller is cancelled, a shielded
    compensator finishes marking the run `FAILED`, emits/closes the live channel, then preserves the
    original error/cancellation. Consent re-admission atomically changes the row to `QUEUED` and
    allocates its next `enqueue_seq`, then restores that exact hop to `AWAITING_CONSENT` under a
    shield when resume publication fails or is cancelled. The sequence remains monotonic, is carried
    in the SAQ payload, and participates in the worker's claim CAS, so a possibly published stale job
    is never reused and cannot claim a later retry. Startup reconciliation narrows the remaining
    process-death windows. A transactional outbox remains later work. The process-local live event
    bus is also not durable; the ledger and graph checkpoint are the recovery truths.

    After a worker wins `QUEUED → RUNNING`, it snapshots that hop's monotonic `enqueue_seq`.
    Cancellation and failure may write `FAILED` only through a conditional update over both the
    active status and that exact sequence. An older consent-park delivery therefore cannot fail or
    clean the checkpoint/context of a newer resume hop that has already claimed the run.

    Terminal status commits are cancellation-shielded long enough to determine which writer owns
    the matching `DONE` event. Checkpoint/context cleanup is best-effort after terminal truth and may
    be retried from its retained pointer; cleanup failure cannot suppress terminal publication or
    strand an SSE stream.

    API cancellation is also completion-shielded. The `RunEngine` and in-process `RunSubstrate`
    share a loop-confined cancellation coordinator. It elects one terminal writer while concurrent
    cancel callers wait and re-read durable truth; an abort-triggered worker `CancelledError` waits
    for that writer's `CANCELLED` decision instead of racing it with `FAILED`. If the abort/status
    sequence itself fails, a waiting caller may retry and the exact-hop worker failure CAS remains
    the fallback. This fence is valid only for the declared one-process Topology A; a future
    multi-process worker plane requires a durable cancellation state/protocol rather than
    process-local coordination.

### 1a. The Run Substrate (Every Workflow Is a SAQ Job)

Every workflow run is a SAQ job, not a fire-and-forget in-process coroutine. The old `asyncio.create_task` submission path is gone; a single `RunEngine.submit(intent)` is the one entry for every surface (Bridge now; CLI and A2A later):

1. Route once via the `WorkflowRegistry`; resolve `(queue_name, priority)` via the `QueueRouter` (`[orchestration.routing]`).
2. Persist a `QUEUED` `Run` through the **`RunLedger`** — the run truth store (in-memory for DB-free tests; Postgres `run`/`step` tables in the durable substrate).
3. Open the run's channel on the **`RunEventBus`** and enqueue `perform_run` onto the `runs` queue.

The enqueue explicitly sets SAQ `timeout=0`: the broker does not impose its default short job wall
clock on an agent graph. This is not an unbounded-everything policy. Model calls, Orchestrator drain
and warm-up, consent/reanimation, and graph-specific operations own their explicit deadlines at the
layer that can interpret failure and recovery. SAQ owns claiming, retries, and job bookkeeping; it
must not kill a valid long-running graph simply because inference exceeds a queue default.

The ghoul (`perform_run`) claims the job, writes `RUNNING`, drives the graph, and writes the terminal status. Events are **semantic** `RunEvent`s (`STATUS/NODE/TOKEN/FRAGMENT/CONSENT/LOG/DONE`); the web `Projector` renders them. Non-`TOKEN` events tee into the `RunLedger` as `Step` rows (`TOKEN` is too chatty — settled text lands on the session turn). A `reconcile_runs` rite sweeps runs left `RUNNING` by a crash back to a safe state on restart.

### 2. The Doctrine: Brain in the Vessel, Hands in the Tomb (Target Topology)

All implemented cognitive labor—agent graph runners, LLM inference orchestration, Dispatcher
resolution, memory curation—executes exclusively in the Vessel. The **planned** Tomb is a brainless
executor: it will receive serialized script payloads through a dedicated execution queue, run them
inside the `nono` sandbox, and return bounded results. It must never run agent logic, graph state
machines, or LLM provider calls. The Tomb container, queue/profile split, narrow database role, and
executor loop are not implemented in this foundation.

The clever split is anatomical: agents live in the Vessel; when they need unsafe labor, only their hands enter the Tomb. A Tomb Ghoul is therefore an execution hand for a Vessel-side agent, not a second agent brain.

This doctrine exists because:

- **State locality:** Agent graph state lives in Vessel process memory. Keeping it there eliminates the need to serialize complex graph state across process boundaries.
- **Security:** The Tomb never needs LLM provider credentials, Dispatcher access, or graph runner dependencies. Its attack surface is minimal.
- **Routing simplicity:** The Vessel's Dispatcher and Orchestrator have instant visibility into all agent state because it never leaves Vessel memory. Tomb returns are just strings.
- **Latency irrelevance:** The SAQ queue hop (~50ms DB read) is negligible compared to multi-second LLM inference times.

#### Planned Tomb Execution Flow

1. A Vessel-side agent or Ghoul running a graph step needs code executed.
2. It serializes the payload (script text, environment, dependency list) and enqueues it to the `tomb` SAQ queue.
3. A Tomb executor loop claims the job using its narrow execution credential.
4. The Tomb executor uses `uv` to fast-install any required dependencies into a **job-scoped temporary workspace**.
5. The Tomb executor spawns `nono` with the enriched workspace. `nono` has zero network access and cannot read the container's environment variables.
6. `nono` executes the script, captures `stdout`/`stderr`.
7. The Tomb executor writes the result back to SAQ.
8. The Vessel Ghoul receives the result string and continues the graph step.

!!! warning "Untrusted Returns"
    Tomb `stdout` is **untrusted**. If the executed code processed data fetched through the Tomb loop's approved prefetch/proxy path, the output may contain adversarial content including prompt injection attempts. Tool outputs returning from the Tomb must be treated as untrusted when injected into agent context.

#### Planned Per-Job Workspace Isolation

When Tomb Ghouls land, multiple jobs may operate concurrently against the execution workspace and
artifact region. To prevent file collisions, every job must create a unique, isolated subdirectory
under the Tomb job root (e.g., `~/.local/share/lychd/tomb/jobs/<job_id>/`). The executor will own
bounded cleanup. This is a design requirement, not current runtime behavior.

### 3. Orchestrated Labor (The Command)

The Ghouls operate under the strict discipline of the **[Orchestrator (23)](23-orchestrator.md)**.

- **The Pause:** When the Orchestrator initiates a **[Coven (08)](08-containers.md)** swap, it issues a signal to the Ghoul process to pause the claiming of new jobs from the queue. This ensures that no tasks are dispatched to container services that are about to be banished.
- **The Drain:** Once a new Coven is manifested, the Orchestrator unpauses the Ghouls, allowing them to resume their labor with the newly available hardware capabilities.

!!! note "Queue and Recovery Boundary"
    Workers own durable queue state: claim, ack, retry, result recording, and crash pickup. The Orchestrator may pause and drain workers during physical transitions, but it does not decide replay semantics for every job. Ordinary hardware stasis stops new claims and lets active work reach a safe boundary; Long Sleep, reboot recovery, and failed job retry are queue and Phylactery concerns.

    A worker may hold non-authoritative in-memory state while it is actively laboring. After process death, that breath is lost and reconstructed from durable inputs: queued jobs, graph checkpoints, completed step outputs, traces, Codex configuration, and live capability probes. The testable invariant is not that every intermediate thought survives; it is that every declared recovery boundary can be replayed or safely abandoned.

### 4. The Reflex Arc and Memory Rituals

The Ghouls are the primary drivers of the Daemon's long-term cognitive processes.

- **The Reflex Arc:** The Worker process is responsible for the rehydration of complex state machines. When a cognitive process pauses to await an external event, its state is persisted. The Ghoul is the entity that wakes the mind, rehydrates the **[Graph (24)](24-graph.md)** state, and steps the logic forward.
- **Ingestion Rituals:** The Ghouls perform the heavy lifting of **[Memory (27)](27-memory.md)**. They execute the partitioning of documents and the communication with the **[Dispatcher (22)](22-dispatcher.md)** to generate embeddings, ensuring the primary interface remains responsive during ingestion.

#### Metabolic Ghoul Profile

Memory augmentation runs as a dedicated Ghoul specialization:

- Performs Memori "Advanced Augmentation" (facts, entities, triples) asynchronously.
- Applies attribution on every write (`entity_id`, `process_id`) before committing to the Phylactery.
- Never blocks user-facing response paths; ingestion is eventual and durable.
- Defers heavy embedding/vectorization to available embedding covens under Orchestrator discipline.

#### Curator Ghoul Profile

Memory curation runs as a separate periodic Ghoul specialization:

- Scores candidate memories using recency, reinforcement, confidence, and contradiction checks.
- Applies lifecycle transitions: `promote`, `keep`, `archive`, `prune`.
- Preserves anchored identity facts regardless of decay score.
- Emits audit traces for every destructive prune action to support rollback and policy tuning.

### 5. Extension Rites

The architecture allows extensions to register their own background functions (Rites). This ensures that heavy logic added by extensions (e.g., document processing or code compilation) does not degrade the performance of the core Vessel.

### 6. Dual-Plane Trust Delta (Target Topology)

The completed worker topology must span Trusted and Semi-Trusted planes. V1 currently implements
only the trusted Vessel side; every Tomb statement below is a required future boundary.

- Vessel workers remain fully trusted for control-plane tasks.
- Tomb workers will be **Semi-Trusted** execution hands. The main Python loop in the Tomb container
  must use a narrow queue-only SAQ/Postgres execution credential to claim, ack, and retry
  execution-plane jobs.
- **Untrusted Sub-steps:** Real unsafe labor (executing AI code) is spawned inside the `nono` sandbox by the Tomb worker loop. The sandbox has zero network access.
- If a `nono` sandbox escapes, the attacker reaches the Tomb container's real authority, including
  its narrow SAQ/Postgres execution credential and shared-Pod endpoints. Exact mounts still prevent
  direct reads of unmounted Vessel secrets, while database roles and every reachable service must
  enforce their own authorization. The current local-only LychD API is not a hostile-network
  authentication boundary.

### Policy Table

| Dimension | Vessel Workers (Trusted Control Plane) | Tomb Executors (Semi-Trusted Execution Plane) |
| :--- | :--- | :--- |
| Secrets | Accesses control-plane queue/database credentials and high-value API keys. | Narrow queue-only SAQ/Postgres execution credential. No provider keys, signing keys, Codex secrets, or control-plane credentials. |
| Mounts | Trusted mounts for queue processing and persistence orchestration. | Task workspace and temporary execution mounts; optional read-only/sanitized Codex projection only. |
| Network | Shared Pod network (Internet + Localhost). | Tomb loop may use shared Pod connectivity for queueing and approved prefetch/proxy work; sandboxed `nono` subprocesses have zero network. |
| Queue Ownership | Owns enqueue policy, durable scheduling, and retry lifecycle for core tasks. | Claims, acks, and retries untrusted execution jobs via the Semi-Trusted loop. |
| Authority Boundaries | Commits durable outcomes and controls retries. All agent/graph/LLM logic runs here. | Executes raw scripts/commands only. No agent logic, no graph runners, no LLM calls. Cannot mutate core infrastructure state. |

### Consequences

!!! success "Positive"
    - **Bounded Restart Recovery:** Durable SAQ rows, run-ledger reconciliation, and explicit graph
      checkpoints recover declared boundaries without pretending every in-memory thought survives.
    - **Physical Synchronization:** By linking job claiming to the Orchestrator, the system prevents "Task Blindness" where a worker attempts to use a dormant container.
    - **Unified Logic:** Using the same framework and database for both web and background tasks eliminates the "Dual Schema" problem.

!!! failure "Negative"
    - **Database Churn:** High-volume SAQ tables generate dead tuples and require measured
      Autovacuum tuning within the persistence layer.
    - **Polling Latency:** While sub-second, a database-backed queue has slightly higher job-pickup latency compared to an in-memory or raw-socket broker.
    - **No Transactional Outbox Yet:** Compensation and startup reconciliation narrow, but do not
      eliminate, the run-row/enqueue crash window.
