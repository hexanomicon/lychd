---
title: 13. Unified Postgres
icon: material/database
---

# :material-database: 13. Unified Postgres Backend for State and Task Queuing

!!! abstract "Context and Problem Statement"
    A modern AI application like LychD has three core persistence needs: a relational database for application state, a vector database for embeddings, and a reliable job queue for asynchronous tasks. The conventional approach is to deploy a polyglot stack: Postgres for state, a dedicated service like Qdrant or Milvus for vectors, and a Redis/Celery combination for task queuing.

    This polyglot approach introduces immense operational complexity. It requires deploying, managing, and backing up three or more distinct services for a single-node application. This complexity is a direct contradiction to the project's goal of creating a simple, robust, and self-contained daemon. We require a solution that consolidates these functions without compromising core functionality.

## Decision Drivers

- **Operational Simplicity:** Minimize the number of moving parts to a single backend service.
- **Transactional Integrity:** Enable atomic enqueuing of background jobs within the same database transaction as the state changes that trigger them.
- **Sufficient Performance:** The solution must be "good enough" for a single-node, vertical-scaling application. Planet-scale, distributed performance is a non-goal.
- **Ecosystem Synergy:** The chosen backend must integrate seamlessly with our web framework (Litestar) and our observability tooling (Arize Phoenix).

## Considered Options

!!! failure "Option 1: Polyglot Stack (Postgres + Qdrant + Redis/Celery)"
    The conventional, distributed-first approach.

    - **Pros:** Each component is a best-in-class, specialized tool.
    - **Cons:** The operational overhead of managing three separate stateful services is an unacceptable burden and violates the principle of simplicity.

!!! success "Option 2: Unified Stack (Postgres-Only)"
    Leverage modern Postgres capabilities for all three persistence needs.

    - **Pros:**
        - **Relational State:** Handled by the core engine with SQLAlchemy as the ORM.
        - **Vector Storage:** The `pgvector` extension provides high-performance vector search capabilities, sufficient for our single-node needs, eliminating the need for a separate vector DB.
        - **Task Queuing:** Simple Asynchronous Queue (SAQ) is a lightweight, robust library that uses Postgres as its broker. It has a first-party `litestar-saq` plugin, making integration trivial.
        - **Observability Synergy:** Our chosen tracing tool, Arize Phoenix, has native support for instrumenting Postgres, creating a seamless observability experience.
    - **Cons:** At extreme scale, specialized services would outperform this consolidated approach. This is an accepted trade-off.

## Decision Outcome

We will use **Postgres** as the single, unified backend for the entire LychD system, consolidating relational state, vector storage, and task queuing into one robust service.

This decision is implemented through a cohesive set of technologies:

- **`SQLAlchemyAsync`:** Manages relational data via the SQLAlchemy ORM.
- **`pgvector`:** The Postgres extension used for storing and querying AI embeddings.
- **`SAQ`:** The `litestar-saq` plugin manages background jobs, using Postgres as a reliable, transactional message broker.

By unifying these functions, we create a system that is simpler to operate, inherently more reliable due to shared transactional integrity, and synergizes perfectly with our chosen observability tools.

### Consequences

!!! success "Positive"
    - **Simplicity:** The entire operational footprint is reduced to a single database service, simplifying deployment, monitoring, and backups.
    - **Reliability:** The system gains a powerful reliability guarantee: state changes, vector updates, and task enqueues can occur within a single atomic transaction.
    - **Cohesion:** The architecture is lean, with all major components (Litestar, Phoenix, Postgres) integrating seamlessly.

!!! failure "Negative"
    - **Vendor Lock-in:** This decision tightly couples the application to Postgres. This is a deliberate and accepted choice, valuing depth of integration and operational simplicity over backend agnosticism.
