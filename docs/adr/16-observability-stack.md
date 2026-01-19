---
title: 16. Observability
icon: material/eye-outline
---

# :material-eye-outline: 16. Arize Phoenix and Cockpit for Observability

!!! abstract "Context and Problem Statement"
    The LychD system requires a comprehensive observability strategy to monitor its operations effectively without introducing the operational overhead typical of distributed microservice architectures.

## Decision Drivers

- **Dual-Layer Monitoring:** The solution must monitor two distinct layers: the physical health of the host infrastructure (CPU, GPU, RAM) and the abstract cognitive health of the agent (LLM traces, token throughput).
- **Operational Efficiency:** The stack must be lightweight, minimizing the number of running services and avoiding resource-heavy dependencies.
- **Backend Synergy:** The solution must leverage the existing, unified Postgres backend, strictly avoiding the introduction of additional database technologies (e.g., ClickHouse).
- **Machine-Readable Metrics:** The priority is capturing clean, structured performance data for programmatic analysis by the agent itself, rather than generating pre-canned visualizations for human operators.

## Considered Options

!!! failure "Option 1: The Conventional Stack (Prometheus + Grafana)"
    Deploy a full monitoring stack including Prometheus for metrics scraping, Grafana for visualization, and a dedicated tracing service.

    - **Pros:** Industry standard with powerful, flexible visualization capabilities.
    - **Cons:** **Architectural Mismatch.** This approach is architected for distributed microservice fleets. For a single-node daemon, it introduces significant operational complexity and resource overhead (3-4 additional services). It prioritizes human-centric dashboarding over the structured data capture required for agent self-analysis.

!!! success "Option 2: The Lean, Integrated Stack"
    A curated set of tools (Cockpit + Arize Phoenix + Custom Metrics) that provides targeted insights without the overhead.

    - **Pros:**
        - **Cockpit ("The Body"):** The host's system health is monitored by the native, lightweight Cockpit web interface.
        - **Arize Phoenix ("The Mind"):** Phoenix provides specialized LLM application tracing. Crucially, it supports Postgres as a backend, aligning perfectly with ADR 0013.
        - **Native Metrics:** Key performance indicators (TTFT, tokens/sec) are captured programmatically and persisted to the Postgres database, treating performance data as first-class application state.

## Decision Outcome

The complexity of the Prometheus/Grafana ecosystem is explicitly rejected in favor of a data-first, agent-centric observability philosophy.

1. **System Health:** Monitored via the host's native **Cockpit** service.
2. **LLM Tracing:** Handled by **Arize Phoenix**, configured to utilize the existing unified Postgres database as its storage backend.
3. **Performance Metrics:** All key LLM performance metrics are captured programmatically within the application logic and persisted directly to a dedicated schema in Postgres.

This approach transitions observability from a passive, human-oriented task of watching graphs to an active, agent-oriented capability. Historical performance data becomes queryable application state, enabling the agent to perform self-analysis.

### Consequences

!!! success "Positive"
    - **Resource Efficiency:** The operational stack is dramatically simplified, saving significant system resources by eliminating the need for a separate time-series database and visualization server.
    - **Architectural Cohesion:** All application data—relational state, vector embeddings, and observability traces—resides in a single Postgres database, simplifying backup and maintenance.
    - **Autopoietic Self-Reflection:** By storing performance metrics in the same database the agent can query, the system enables the agent to analyze its own operational history. This allows it to answer questions like "Is my summarization latency degrading?" and self-optimize without human intervention.

!!! failure "Negative"
    - **Visualization Deficit:** The rich, pre-built dashboarding and alerting ecosystem of Grafana is sacrificed. Any required complex visualizations must be implemented manually within the application's web UI.
