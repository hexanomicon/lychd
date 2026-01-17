---
title: 16. Observability
icon: material/eye-outline
---

# :material-eye-outline: 16. Arize Phoenix and Cockpit for Observability

!!! abstract "Context and Problem Statement"
    Observing a complex system like LychD requires monitoring two distinct layers: the physical health of the host system (CPU, GPU, RAM) and the abstract health of the agent's "mind" (LLM traces, performance metrics). The conventional cloud-native approach involves a heavy stack of specialized tools: Prometheus for metrics, Grafana for visualization, and a separate tracing tool.

    This stack is designed for distributed microservice fleets and is philosophically and technically misaligned with LychD's single-node, self-contained design. It introduces significant operational complexity and resource drain (3-4 additional services) for a level of granularity we do not need. We require a leaner, more integrated approach that prioritizes raw, structured data over pre-canned visualizations.

## Decision Drivers

- **Simplicity and Low Overhead:** The stack must be lightweight, minimize the number of running services, and avoid resource-heavy dependencies.
- **LLM-Centric Tracing:** We need a tool that provides deep insights into the traces and thought processes of the AI agent.
- **Backend Synergy:** The solution must leverage our existing, unified Postgres backend, avoiding the need for additional databases like ClickHouse.
- **LLM-Native Reporting:** We are entering an era where the LLM itself can be the primary analyst of its own performance. The priority is to capture clean, structured performance data (TTFT, tok/sec), not to render it in graphs for humans.

## Considered Options

!!! failure "Option 1: The Conventional Stack (Prometheus + Grafana)"
    Deploy a full Prometheus/Grafana stack for metrics and visualization, likely paired with a tracer like Langfuse.

    - **Pros:** Industry standard, powerful and flexible visualization capabilities.
    - **Cons:** This represents the "age of graphs," a paradigm we are moving beyond. It is operationally bloated for our needs. Tracing tools like Langfuse require a ClickHouse database, violating our "Unified Postgres Backend" principle. The entire stack is optimized for human consumption of dashboards, not for machine analysis of raw data.

!!! success "Option 2: The Lean, Integrated Stack"
    A curated set of tools (Cockpit + Arize Phoenix + Custom Metrics) that provides targeted insights without the overhead.

    - **Pros:**
        - **Cockpit for the "Body":** The host's system health (CPU, RAM, network) is monitored by the native Cockpit web interface. It is lightweight and can be extended for specific hardware like GPUs.
        - **Arize Phoenix for the "Mind":** Phoenix is a brilliant, lightweight tool specifically for LLM application tracing. Its killer feature is the ability to use Postgres as its backend, creating perfect synergy with our existing ADR #0007.
        - **LLM-Native Metrics:** Key performance indicators (TTFT, tokens/sec, latency) are not scraped by an external service. They are captured directly from API call results within our application code and saved as structured data to a dedicated table in our Postgres database.

## Decision Outcome

We explicitly reject the complexity of the Prometheus/Grafana ecosystem. Our observability philosophy is data-first and agent-centric.

1. **System Health:** Will be monitored via the host's **Cockpit** service.
2. **LLM Tracing:** Will be handled by **Arize Phoenix**, which will be configured to use our existing Postgres database as its data store.
3. **Performance Metrics:** All key LLM performance metrics will be captured programmatically within the application and persisted directly to Postgres.

This approach transitions observability from a passive, human-oriented task of watching graphs to an active, agent-oriented one. The historical performance data is now just another table in the database that the Lich can query, analyze, and report on, enabling it to answer questions like, "How has my token generation speed for summarization tasks changed over the last week?"

### Consequences

!!! success "Positive"
    - **Efficiency:** The operational stack is dramatically simplified, saving significant system resources.
    - **Cohesion:** The architecture remains cohesive, with all application data (state, traces, metrics) residing in a single Postgres database.
    - **Autopoiesis:** It unlocks a new, powerful paradigm of self-observability, where the agent becomes the primary analyst of its own performance.

!!! failure "Negative"
    - **No Dashboards:** We sacrifice the rich, pre-built dashboarding and alerting ecosystem of Grafana. If complex visualizations are needed, they will have to be built as part of our own web UI.
