---
title: 13. Unified Postgres
icon: material/database
---

# :material-database: 13. Unified Postgres Backend for State and Task Queuing

!!! abstract "Context and Problem Statement"
    A modern AI application like LychD presents three distinct persistence requirements: relational storage for application state, vector storage for high-dimensional embeddings, and a reliable job queue for asynchronous task processing.

## Decision Drivers

- **Single-Node Architecture:** The architectural strategy must satisfy these needs within the strict constraints of a self-contained daemon.
- **Operational Simplicity:** The architecture must minimize the number of moving parts. Ideally, a single backend service should handle all persistence needs to simplify backups and deployment.
- **Transactional Integrity:** The system should support atomic operations across domains—allowing background jobs to be enqueued within the same database transaction that commits the application state change.
- **Ecosystem Synergy:** The backend must integrate natively with the chosen web framework (Litestar) and observability tooling (Arize Phoenix).

## Considered Options

!!! failure "Option 1: Polyglot Stack (Postgres + Qdrant + Redis/Celery)"
    Deploy best-in-class specialized services for each persistence domain.

    - **Pros:** Each component offers maximum performance and specialized features for its domain.
    - **Cons:** **Operational Burden.** While scalable, this architecture introduces immense operational complexity. It requires deploying, monitoring, and backing up three separate stateful services. This complexity is a direct contradiction to the project's goal of creating a simple, robust daemon.

!!! success "Option 2: Unified Stack (Postgres-Only)"
    Leverage modern Postgres capabilities and extensions to handle all three persistence domains.

    - **Pros:**
        - **Vector Storage:** The `pgvector` extension provides high-performance vector search capabilities sufficient for single-node workloads, eliminating the need for a dedicated vector database.
        - **Task Queuing:** **SAQ (Simple Asynchronous Queue)** utilizes Postgres as a broker. The `litestar-saq` integration allows for robust background processing without Redis.
        - **Observability:** Arize Phoenix provides native instrumentation for Postgres, ensuring seamless tracing across standard queries and vector searches.
    - **Cons:** At extreme scale (millions of concurrent users), specialized services would outperform this consolidated approach. This scale is outside the project's scope.

## Decision Outcome

**Postgres** is selected as the unified backend service for the entire LychD system, consolidating relational state, vector storage, and task queuing.

This decision is implemented through a cohesive technology stack:

- **`SQLAlchemyAsync`:** Manages relational data via the standard ORM.
- **`pgvector`:** The Postgres extension is mandated for storing and querying AI embeddings.
- **`SAQ`:** The `litestar-saq` plugin is utilized to manage background jobs, treating Postgres as a reliable, transactional message broker.

### Consequences

!!! success "Positive"
    - **Radical Simplicity:** The operational footprint is reduced to a single container. Backing up the system requires only a single `pg_dump` or Btrfs snapshot, ensuring total data consistency.
    - **Transactional Reliability:** The architecture enables atomic reliability patterns impossible in polyglot stacks. A database transaction can commit a user creation, insert their embedding vector, and enqueue a welcome email job simultaneously—guaranteeing that either all happen or none do.
    - **Tooling Synergy:** The architecture aligns perfectly with the stack. Litestar, Arize Phoenix, and SQLAlchemy all possess first-class support for this Postgres-centric model.

!!! failure "Negative"
    - **Database Coupling:** The application is tightly coupled to Postgres features. Porting to another database engine would require a complete rewrite.
    - **The Vacuum Tax (Maintenance):** Consolidating high-churn workloads (Job Queues) and high-cost indexing (Vector Search) onto a single node requires aggressive tuning of the Postgres Autovacuum daemon. Failing to tune this will lead to index bloat and performance degradation over time.
