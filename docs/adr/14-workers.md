---
title: 14. Workers
icon: material/robot-dead
---

# :material-robot-dead: 14. Workers: The Ghouls

!!! abstract "Context and Problem Statement"
    The LychD Vessel is designed to be a high-performance, non-blocking interface. However, many tasks required of an autonomous daemon—waiting for long generative responses, performing recursive file operations, or executing complex verification rituals—are inherently slow and blocking. Running these tasks inside the primary web process presents a critical stability risk: a system crash wipes the volatile state, a container restart kills the active thought, and heavy CPU-bound operations can block the event loop, causing the application to fail health checks.

## Requirements

- **Labor Offloading:** Mandatory offloading of slow or blocking tasks to resilient, persistent background processes that operate independently of the web server.
- **Persistence beyond Death:** Pending tasks must be stored in the **[Phylactery (06)](06-persistence.md)** and resumed automatically if the process restarts.
- **Transactional Integrity:** The enqueuing of labor must be atomic with database state changes; a job should only become visible to a worker if the associated database transaction commits successfully.
- **Anatomical Partitioning:** The background task system must utilize the dedicated `queue` chamber (schema) of the unified database to ensure operational isolation.
- **Orchestrated Discipline:** The labor force must be subject to the commands of the **[Orchestrator (21)](21-orchestrator.md)**, allowing for the pausing of specific queues during state transitions.
- **Reflex Arc Support:** The worker system must provide the infrastructure for the "Long Sleep"—the ability to rehydrate the state of a **[Graph (22)](22-graph.md)** and resume reasoning after an interruption.
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

### 2. Orchestrated Labor (The Sovereign's Command)

The Ghouls operate under the strict discipline of the **[Orchestrator (21)](21-orchestrator.md)**.

- **The Pause:** When the Orchestrator initiates a **[Coven (08)](08-containers.md)** swap, it issues a signal to the Ghoul process to pause the claiming of new jobs from the queue. This ensures that no tasks are dispatched to Runes that are about to be banished.
- **The Drain:** Once a new Coven is manifested, the Orchestrator unpauses the Ghouls, allowing them to resume their labor with the newly available hardware capabilities.

### 3. The Reflex Arc and Memory Rituals

The Ghouls are the primary drivers of the Daemon's long-term cognitive processes.

- **The Reflex Arc:** The Worker process is responsible for the rehydration of complex state machines. When a cognitive process pauses to await an external event, its state is persisted. The Ghoul is the entity that wakes the mind, rehydrates the **[Graph (22)](22-graph.md)** state, and steps the logic forward.
- **Ingestion Rituals:** The Ghouls perform the heavy lifting of **[Memory (24)](24-memory.md)**. They execute the partitioning of documents and the communication with the **[Dispatcher (20)](20-dispatcher.md)** to generate embeddings, ensuring the primary interface remains responsive during ingestion.

### 4. Extension Rites

The architecture allows extensions to register their own background functions (Rites). This ensures that heavy logic added by extensions (e.g., document processing or code compilation) does not degrade the performance of the core Vessel.

### Consequences

!!! success "Positive"
    - **Operational Resiliency:** The Daemon is crash-proof; work resumed after a failure picks up from the last successfully committed task in the Phylactery.
    - **Physical Synchronization:** By linking job claiming to the Orchestrator, the system prevents "Task Blindness" where a worker attempts to use a dormant container.
    - **Unified Logic:** Using the same framework and database for both web and background tasks eliminates the "Dual Schema" problem.

!!! failure "Negative"
    - **Database Churn:** High-volume queues generate significant dead tuples. The `queue` chamber requires aggressive Autovacuum tuning within the persistence layer.
    - **Polling Latency:** While sub-second, a database-backed queue has slightly higher job-pickup latency compared to an in-memory or raw-socket broker.
