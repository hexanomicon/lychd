---
title: 14. Workers
icon: material/excavator
---

# :material-excavator: 14. Workers: The Ghouls

!!! abstract "Context and Problem Statement"
    The LychD Vessel is designed to be a high-performance, non-blocking interface. However, many tasks required of an autonomous daemon—waiting for long generative responses, performing recursive file operations, or executing complex verification rituals—are inherently slow and blocking. Running these tasks inside the primary web process presents a critical stability risk: a system crash wipes the volatile state, a container restart kills the active thought, and heavy CPU-bound operations can block the event loop, causing the application to fail health checks.

## Requirements

- **Labor Offloading:** Mandatory offloading of slow or blocking tasks to resilient, persistent background processes that operate independently of the web server.
- **Persistence beyond Death:** Pending tasks must be stored in the **[Phylactery (06)](06-persistence.md)** and resumed automatically if the process restarts.
- **Transactional Integrity:** The enqueuing of labor must be atomic with database state changes; a job should only become visible to a worker if the associated database transaction commits successfully.
- **Anatomical Partitioning:** The background task system must utilize the dedicated `queue` chamber (schema) of the unified database to ensure operational isolation.
- **Orchestrated Discipline:** The labor force must be subject to the commands of the **[Orchestrator (23)](23-orchestrator.md)**, allowing for the pausing of specific queues during state transitions.
- **Reflex Arc Support:** The worker system must provide the infrastructure for the "Long Sleep"—the ability to rehydrate the state of a **[Graph (24)](24-graph.md)** and resume reasoning after an interruption.
- **Massive Concurrency:** A single worker process must be capable of juggling thousands of concurrent IO-bound tasks utilizing an asynchronous event loop.
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
        -   **Atomic Workflows:** Allows a "Save and Enqueue" operation to occur within a single SQL transaction.
        -   **Efficiency:** The `SKIP LOCKED` mechanism provides high-performance job claiming without the polling overhead of legacy database queues.

## Decision Outcome

**SAQ** is adopted as the engine for the background workers, referred to as **Ghouls**.

### 1. The Architecture of Labor

The Worker (Ghoul) is executed as a separate operating system process from the Web Server (Vessel), though they share the same codebase, dependencies, and database connection.

- **The Engine:** The worker utilizes the `SAQPlugin` provided by the **[Backend (11)](11-backend.md)** to ensure identical configuration and dependency injection.
- **The `queue` Chamber:** Jobs are serialized into the dedicated `queue` schema within the **[Phylactery (06)](06-persistence.md)**. This ensures that background labor is subject to the same **[Snapshot (07)](07-snapshots.md)** and persistence laws as the rest of the system.
- **Async Efficiency:** Because the Ghouls run on an asynchronous event loop, a single process can manage thousands of concurrent tasks (e.g., awaiting a response from a remote A2A peer or a slow local model) without exhausting system threads.
      - - **Worker Profile Binding (Topology Split):** To enforce the Dual-Plane Trust Delta, queue *definitions* are maintained globally, but worker *execution loops* are conditionally bound.
            - Utilizing environment variables (e.g., `LYCHD_WORKER_PROFILE`), the binding of specific queues to specific processes is dictated at boot time.
            - The Vessel container boots under the `core` profile, spawning background loops that exclusively claim trusted orchestration tasks.
            - The Tomb container boots under the `tomb` profile, spawning loops that exclusively claim untrusted code-execution tasks.
            - This separation ensures a malicious payload cannot jump execution queues by overwhelming a worker situated in the trusted plane.

### 2. The Doctrine: Brain in the Vessel, Hands in the Tomb

All cognitive labor—agent graph runners, LLM inference orchestration, Dispatcher resolution, memory curation—executes exclusively in the Vessel. The Tomb is a **brainless executor**. It receives serialized script payloads (Python code, CLI commands) via SAQ, runs them inside the `nono` sandbox, and returns `stdout`. It does not run agent logic, graph state machines, or make LLM provider calls.

This doctrine exists because:

- **State locality:** Agent graph state lives in Vessel process memory. Keeping it there eliminates the need to serialize complex graph state across process boundaries.
- **Security:** The Tomb never needs LLM provider credentials, Dispatcher access, or graph runner dependencies. Its attack surface is minimal.
- **Routing simplicity:** The Vessel's Dispatcher and Orchestrator have instant visibility into all agent state because it never leaves Vessel memory. Tomb returns are just strings.
- **Latency irrelevance:** The SAQ queue hop (~50ms DB read) is negligible compared to multi-second LLM inference times.

#### Tomb Execution Flow

1. A Vessel Ghoul (running a graph step) needs code executed.
2. It serializes the payload (script text, environment, dependency list) and enqueues it to the `tomb` SAQ queue.
3. A Tomb Ghoul claims the job.
4. The Tomb Ghoul uses `uv` to fast-install any required dependencies into a **job-scoped temporary workspace**.
5. The Tomb Ghoul spawns `nono` with the enriched workspace. `nono` has zero network access and cannot read the container's environment variables.
6. `nono` executes the script, captures `stdout`/`stderr`.
7. The Tomb Ghoul writes the result back to SAQ.
8. The Vessel Ghoul receives the result string and continues the graph step.

!!! warning "Untrusted Returns"
    Tomb `stdout` is **untrusted**. If the executed code fetched data from the internet (via the Ghoul's pre-fetch, not `nono` itself), the output may contain adversarial content including prompt injection attempts. Tool outputs returning from the Tomb must be treated as untrusted when injected into agent context.

#### Per-Job Workspace Isolation

Multiple Tomb Ghouls may operate concurrently on the same mounted host directory. To prevent file collisions, every SAQ job must create a unique, isolated subdirectory inside the lab mount (e.g., `tomb/jobs/<job_id>/`). The spawning Ghoul is responsible for cleanup after result collection.

### 3. Orchestrated Labor (The Command)

The Ghouls operate under the strict discipline of the **[Orchestrator (23)](23-orchestrator.md)**.

- **The Pause:** When the Orchestrator initiates a **[Coven (08)](08-containers.md)** swap, it issues a signal to the Ghoul process to pause the claiming of new jobs from the queue. This ensures that no tasks are dispatched to container services that are about to be banished.
- **The Drain:** Once a new Coven is manifested, the Orchestrator unpauses the Ghouls, allowing them to resume their labor with the newly available hardware capabilities.

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

### 6. Dual-Plane Trust Delta

Worker ownership spans both the Trusted and Semi-Trusted planes.

- Vessel workers remain fully trusted for control-plane tasks.
- Tomb workers are **Semi-Trusted**. The main Python loop in the Tomb container claims, acks, and retries jobs from the SAQ queue.
- **Untrusted Sub-steps:** Real unsafe labor (executing AI code) is spawned inside the `nono` sandbox by the Tomb worker loop. The sandbox has zero network access.
- If a `nono` sandbox escapes, the attacker is trapped in the Tomb container. They may steal the SAQ database password from the environment, but Layer 7 Auth prevents them from accessing Vessel's master tables or secrets.

### Policy Table

| Dimension | Vessel Workers (Trusted Control Plane) | Tomb Executors (Semi-Trusted Execution Plane) |
| :--- | :--- | :--- |
| Secrets | Accesses queue/database credentials and high-value API keys. | Accesses queue/database credentials only (Least Privilege Role). No high-value keys. |
| Mounts | Trusted mounts for queue processing and persistence orchestration. | Task workspace and temporary execution mounts only. |
| Network | Shared Pod network (Internet + Localhost). | Shared Pod network. (Sandboxed `nono` subprocesses have zero network). |
| Queue Ownership | Owns enqueue/dequeue/retry lifecycle for core tasks. | Owns enqueue/dequeue/retry for untrusted tasks via the Semi-Trusted loop. |
| Authority Boundaries | Commits durable outcomes and controls retries. All agent/graph/LLM logic runs here. | Executes raw scripts/commands only. No agent logic, no graph runners, no LLM calls. Cannot mutate core infrastructure state. |

### Consequences

!!! success "Positive"
    - **Operational Resiliency:** The Daemon is crash-proof; work resumed after a failure picks up from the last successfully committed task in the Phylactery.
    - **Physical Synchronization:** By linking job claiming to the Orchestrator, the system prevents "Task Blindness" where a worker attempts to use a dormant container.
    - **Unified Logic:** Using the same framework and database for both web and background tasks eliminates the "Dual Schema" problem.

!!! failure "Negative"
    - **Database Churn:** High-volume queues generate significant dead tuples. The `queue` chamber requires aggressive Autovacuum tuning within the persistence layer.
    - **Polling Latency:** While sub-second, a database-backed queue has slightly higher job-pickup latency compared to an in-memory or raw-socket broker.
