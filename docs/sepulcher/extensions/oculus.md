---
title: 28. Observability
icon: material/eye-outline
---

# :material-eye-outline: 28. Observability: The Oculus

!!! abstract "Context and Problem Statement"
    LychD operates as a hybrid of deterministic infrastructure and probabilistic AI agents. Maintaining operational coherence requires visibility into both physical health (VRAM/CPU) and cognitive drift (hallucinations or loops). Traditional monitoring tools fail to capture the nuance of agentic execution; they see the network request but remain blind to the reasoning path that generated it. A fundamental gap exists between the telemetry of the "Body" (hardware) and the "Mind" (agent logic), creating a risk where the Daemon thrashes or fails without leaving a causal trail for the Magus to diagnose.

## Requirements

- **Extension Sovereignty:** The observability stack must be strictly optional; the Core kernel must possess no hard dependencies on specific telemetry SDKs or cloud providers.
- **Thought Traceability:** Mandatory visualization of the full execution tree for every **[Agent](../../adr/19-agents.md)** run, including tool arguments, validation retries, and internal monologues.
- **Anatomical Integration:** Observability data must be persisted within the dedicated `traces` chamber of the **[Phylactery](../phylactery/index.md)** to ensure traces survive reanimation.
- **Coven-Based Infrastructure:** The observability engine (collector and UI) must be managed as a specialized **[Coven](../../adr/08-containers.md)**, allowing it to be Manifested or Banished based on hardware availability.
- **Physical Integration:** Visibility into hardware utilization, specifically real-time GPU memory pressure, to inform the **[Orchestrator's](../../adr/21-orchestrator.md)** scheduling decisions.
- **Privacy Redaction:** Mandatory integration with the system's security toggles to redact prompt and completion content from telemetry before it leaves memory.
- **Offline Sovereignty:** The reference implementation must function in isolated or air-gapped environments, requiring a local telemetry sink.

## Considered Options

!!! failure "Option 1: The Cloud Native Suite (Prometheus / Grafana / Jaeger)"
    Deploying the standard enterprise observability stack.
    -   **Cons:** **Extreme Overhead.** Requires multiple heavy containers and massive RAM allocation. The complexity of PromQL and dashboarding is disproportionate to the needs of a sovereign daemon.

!!! failure "Option 2: Persistence-Layer Logging"
    Storing all traces and metrics directly as JSONB rows without a specialized sink.
    -   **Cons:** **Architectural Diversion.** Relational databases are inefficient for high-frequency time-series events. Building a specialized Trace UI within the **[Altar](../../divination/altar.md)** is a massive development diversion from core AI capabilities.

!!! success "Option 3: The Oculus (Phoenix + Logfire SDK)"
    A hybrid strategy utilizing specialized GenAI tracing and native host monitoring.
    -   **Pros:**
        -   **Arize Phoenix:** Specialized for LLM workflows and Pydantic AI; provides a local, high-fidelity scrying pool for cognitive traces.
        -   **Native Sink:** Integrates with the existing Postgres backend, ensuring no new database engine is required.
        -   **Sovereign Trace:** The Logfire SDK provides zero-boilerplate instrumentation while supporting a local OTLP export path.

## Decision Outcome

**The Oculus** is adopted as the **Observability Extension**, serving as the reference implementation for system introspection. It transforms the invisible ghost of intent into a structured, scryable record.

### 1. The Extension Hook (The Retina)

The Oculus follows the doctrine of **[Extension Sovereignty (05)](../../adr/05-extensions.md)**. It possesses no authority until it is registered:

- **The Injection:** Upon registration, the Oculus invokes `context.add_litestar_plugin(OculusTelemetryPlugin())`.
- **Initialization:** This plugin implements the **[Backend's (11)](../../adr/11-backend.md)** initialization protocol. During the "Deep Awakening" (Server Mode), it hijacks the boot process to configure the global OpenTelemetry providers.
- **Scope:** Because the **[Vessel](../vessel/index.md)** and the **[Ghouls (14)](../vessel/ghouls.md)** share the same boot logic, the Oculus automatically observes both the scrying at the Altar and the labor in the background.

### 2. The Thought Trace (Logfire & Phoenix)

The extension configures the process to emit signals following the Generative AI Semantic Conventions:

- **Instrumentation:** It invokes `logfire.instrument_pydantic_ai()` and `logfire.instrument_httpx()`. This captures the reasoning loop of the Agent and the raw whispers exchanged with the **[Animator](../animator/index.md)**.
- **The Collector:** It registers a specialized container (**Oculus Rune**) running **Arize Phoenix**.
- **The Routing:** Telemetry is exported via OTLP to the local collector. Phoenix is configured to use the `traces` chamber of the **[Phylactery](../phylactery/index.md)** as its permanent storage.

### 3. The Body's Health (Physical Monitoring)

For hardware monitoring, the architecture rejects containerized metrics to avoid the "Prometheus Tax."

- **The Integration:** LychD utilizes the host's native monitoring tools (e.g., Cockpit).
- **The Handshake:** The **[Orchestrator](../../adr/21-orchestrator.md)** reads these physical metrics to calculate the "Tipping Point" for Coven swaps, ensuring that the machine's "Will" is grounded in the "Body's" actual capacity.

### 4. The Privacy Veil

The Oculus respects the global `LYCHD_SECURE_MODE` toggle. When active, the telemetry provider is configured to exclude content. This ensures that the *structure* of the thought (latency, tool success, token counts) is preserved for debugging, while the *substance* (sensitive prompts or secrets) is physically redacted before leaving the application memory.

### Consequences

!!! success "Positive"
    - **Zero-Cost Purity:** Users who do not manifest the Oculus extension incur zero instrumentation overhead or resource bloat.
    - **Specialized Scrying:** Arize Phoenix provides native rendering for retrieved chunks and tool calls, offering superior visibility compared to generic logging.
    - **Pluggable Eyes:** The Magus can swap the local Oculus for a cloud provider (e.g., Logfire Cloud) simply by changing the extension configuration.

!!! failure "Negative"
    - **Fragmented Dashboard:** Correlating a slow Agent response (Mind) with high GPU utilization (Body) requires the Magus to look at both the Oculus and host-native interfaces.
    - **Startup Latency:** The initialization of the OpenTelemetry exporters adds a measurable delay (~500ms) to the application boot sequence when the extension is active.
