---
title: 6. Persistence
icon: material/database
---

# :material-database: 6. Persistence: The Phylactery

!!! abstract "Context and Problem Statement"
    The LychD Daemon requires a unified persistence layer to store disparate forms of reality: Relational State (User Data) and complex, nested Data Structures (State Snapshots). Furthermore, the system operates on a federated architecture where the database schema is not static; it is the aggregate of models defined by the Core and models defined by installed Extensions. The persistence layer must provide a mechanism to dynamically discover, register, and migrate these schemas into a single, cohesive database structure while optimizing for the throughput of massive serialized objects.

## Requirements

- **Single-Node Efficiency:** The architecture must minimize the number of moving parts. A single backend service should handle all persistence needs (Relational, Document, Concurrency).
- **Federated Schema Management:** The system must support the distributed definition of models, allowing Extensions to define their own tables which are then automatically detected and migrated by the Core.
- **Anatomical Partitioning:** The database must be organized into logical chambers (schemas) to maintain separation between Relational State, high-dimensional artifacts, execution traces, and background labor.
- **Concurrency Primitives:** The database must support row-locking mechanisms (e.g., `SKIP LOCKED`) to enable high-performance, atomic work distribution without external brokers.
- **High-Throughput Serialization:** The system expects to store large, deeply nested JSON objects (e.g., execution history or state machines). A mechanism for **Binary Transmutation** is required to bypass the CPU overhead of standard text-based serialization.

## Considered Options

!!! failure "Option 1: Polyglot Stack"
    Deploying Postgres (Relational), Mongo (Document), and Redis (Queue).
    -   **Cons:** **Operational Complexity.** Managing three separate services contradicts the goal of a simple, self-contained daemon. Coordinating atomic transactions across disparate services is mathematically difficult.

!!! failure "Option 2: Static Schema Definition"
    Requiring all database models to be defined in the Core codebase.
    -   **Cons:** **Extensibility Blocker.** Extensions would be unable to store their own persistent data without modifying the Core source code, violating the principle of deep modularity.

!!! success "Option 3: Dynamic Unified Postgres"
    Leveraging Postgres for all data types—Relational and Document (via `JSONB`)—governed by a strict binary serialization protocol and organized into logical chambers.
    -   **Pros:**
        -   **Transactional Integrity:** Guaranteed atomicity across all data types in a single commit.
        -   **Minimalism:** Reduces the infrastructure footprint to a single robust engine.
        -   **Flexibility:** Supports both structured relational data and unstructured artifacts within a single query context.

## Decision Outcome

**Postgres** is selected as the unified backend, equipment with the capability to handle relational, vector, and document data. The persistence logic is orchestrated via **SQLAlchemy (Async)**.

### 1. The Dynamic Registry (Federation)

The persistence layer implements a Schema Federation Protocol to support the system's recursive evolution:

1. **The Base:** All models inherit from a shared `UUIDBase` provided by the Core.
2. **Registration:** During the initialization phase, extensions call `context.register_model(MyModel)`.
3. **Aggregation:** The Core aggregates these references. When the migration tool (Alembic) runs, it imports all registered models, generating a single migration script that covers the entire Federation.

### 2. Binary JSONB Transmutation

To achieve maximum throughput for complex state objects and execution history, a **Zero-Copy Serialization** strategy is adopted via a custom `asyncpg` connection hook.

- **The Problem:** Standard ORMs serialize objects to JSON strings, pass them to the driver, which encodes them to UTF-8 bytes, which the database then decodes. This "Double Encoding" is unacceptable for large payloads.
- **The Solution:** The system injects a custom codec that accepts already-serialized bytes (from a high-performance serializer like `msgspec`), prepends the Postgres JSONB version header (`\x01`), and transmits the raw binary protocol directly.
- **The Result:** The application memory maps directly to the database storage engine, bypassing text processing entirely. This is critical for future rituals involving massive cognitive data dumps.

### 3. Anatomical Partitioning (The Chambers)

To maintain organizational purity, the Phylactery is divided into logical chambers:

- **`public` (State):** Relational data for user state, configuration, and extension registries.
- **`vectors` (Karma):** High-dimensional space for storing verified artifacts and long-term memory. Entries include a `status` metadata field (e.g., `speculative`, `consecrated`) to distinguish between experimental thoughts and verified truths.
- **`traces` (The Eye):** Specialized storage for execution traces and observability data.
- **`queue` (Labor):** The persistence layer for the background task distribution system.
- **`verbatim` (The Facts):** A high-priority Key-Value store (JSONB) for immutable facts (IP addresses, specific names, technical constants). The system is mandated to consult this chamber before semantic search to ensure 100% deterministic recall of critical data.

### 4. Concurrency and Labor

The database is configured to support atomic task distribution. By utilizing `SKIP LOCKED`, the system can manifest background ghouls that claim and execute pending labor without the risk of duplicate work or the need for an external broker.

### Consequences

!!! success "Positive"
    - **Atomic Reliability:** A single transaction can commit a user action and save a complex state snapshot simultaneously.
    - **Performance:** Binary Transmutation reduces the latency of saving large state objects by orders of magnitude compared to standard handling.
    - **Extension Sovereignty:** An extension author defines a standard Python class, and the system automatically handles the table creation and evolution within the unified body.

!!! failure "Negative"
    - **Migration Complexity:** If two extensions define models with conflicting table names, the migration will fail. The system relies on strict namespace conventions to prevent collisions.
    - **Vacuum Tuning:** High-volume chambers (like the task queue) require aggressive autovacuum tuning to prevent database bloat.
