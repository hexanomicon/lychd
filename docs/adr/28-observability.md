---
title: 28. Observability
icon: material/eye-outline
---

# :material-eye-outline: 28. Observability: The Oculus

!!! abstract "Context and Problem Statement"
    LychD operates as a hybrid of deterministic infrastructure and probabilistic AI agents. Maintaining operational coherence requires visibility into both physical health (VRAM/CPU) and cognitive drift (Hallucinations/Loops). Traditional monitoring tools fail to capture the nuance of agentic execution; they see the network request but are blind to the reasoning path that generated it. A unified observability stack is required to illuminate the "Thought Trace"—the causal link from prompt to tool to output—without violating the principle of a lightweight, sovereign kernel.

## Requirements

- **Extension Sovereignty:** The observability stack must be strictly optional; the Core must not possess hard dependencies on `logfire` or `opentelemetry` SDKs.
- **Thought Traceability:** Mandatory visualization of the full execution tree for every **[Agent (19)](19-agents.md)** run, including tool arguments and validation retries.
- **Dual-Layer Monitoring:** Separation of monitoring concerns into the "Mind" (Agent logic) and the "Body" (Host hardware and container status).
- **Physical Integration:** Visibility into hardware utilization, specifically GPU memory pressure, to inform the **[Orchestrator's (21)](21-orchestrator.md)** scheduling decisions.
- **Privacy Enforcement:** Integration with the global `LYCHD_SECURE_MODE` to allow for the redaction of prompt and completion content from telemetry.

## Considered Options

!!! failure "Option 1: The Cloud Native Suite (Prometheus / Grafana / Jaeger)"
    Deploying the standard enterprise observability stack.
    - **Pros:** Maximum power and industry standard.
    - **Cons:** **Extreme Overhead.** Requires 3-4 heavy containers and massive RAM allocation just to monitor a single node. The complexity of PromQL and Grafana dashboarding is disproportionate to the needs of a personal daemon.

!!! failure "Option 2: Persistence-Layer Logging"
    Storing all traces and metrics directly as JSONB rows in the **[Phylactery (06)](06-persistence.md)**.
    - **Pros:** Zero extra infrastructure; unified backups.
    - **Cons:** **Wrong Tool.** Relational databases are inefficient for high-frequency time-series events. Building a specialized Trace UI within the Altar is a massive development diversion from core AI capabilities.

!!! success "Option 3: The Oculus (Phoenix + Cockpit)"
    A hybrid strategy utilizing specialized GenAI tracing and native host monitoring.
    - **Pros:**
        - **Arize Phoenix:** Specialized for LLM workflows and Pydantic AI; provides a local, high-fidelity scrying pool for cognitive traces.
        - **Logfire SDK:** Native integration with Pydantic models ensures zero-boilerplate instrumentation.
        - **Cockpit:** Zero-overhead host monitoring for "Body" metrics (GPU/CPU/RAM).

Here is the consolidated **Decision Outcome** for **ADR 28 (Observability)**. I have merged the "Body Monitoring" sections into a single, authoritative block.

---

### Decision Outcome

**The Oculus** is adopted as the **Observability Extension**, serving as the reference implementation for system introspection. It transforms the invisible ghost of intent into a structured, scryable record while leveraging host-native tools for hardware telemetry.

### 1. The Extension Registration (The Retina Hook)

To satisfy the requirement of sovereignty, the Oculus is implemented as an Extension.

- **The Hook:** Inside its `register(context)` function, it invokes `context.add_litestar_plugin(OculusTelemetryPlugin())`.
- **The Injection:** This plugin implements the **[Backend's (11)](11-backend.md)** `InitPluginProtocol`. During the "Deep Awakening" (Server Mode), it configures the global OpenTelemetry providers.
- **The Scope:** Because the Vessel and the **[Ghouls (14)](14-workers.md)** share the same boot logic, the Oculus automatically observes both the scrying at the Altar and the labor in the background.

### 2. The Thought Trace (Logfire & Phoenix)

The extension configures the process to emit signals following the Generative AI Semantic Conventions:

- **Instrumentation:** It invokes `logfire.instrument_pydantic_ai()` and `logfire.instrument_httpx()`. This captures the reasoning loop of the Agent and the raw "Whispers" exchanged with the **[Soulstones (20)](20-dispatcher.md)**.
- **The Collector:** It registers a specialized container (Oculus Soulstone) running **Arize Phoenix**.
- **The Routing:** Telemetry is exported via OTLP to `http://localhost:4318`, keeping all cognitive data within the Pod's private network.

### 3. Physical Body Monitoring (Cockpit)

For hardware monitoring, the architecture rejects containerized metrics to avoid the "Prometheus Tax" (high CPU/RAM overhead). Instead, LychD utilizes the host's native **Cockpit** service.

- **VRAM Visualization:** Users are encouraged to install the `cockpit-pcp` and NVIDIA-SMI/AMD plugins. This provides the Magus with high-fidelity, real-time GPU utilization and VRAM tracking via a dedicated dashboard.
- **Metric Mirroring:** Critical hardware metrics (OOM events, thermal throttling, and memory pressure) are mirrored from the host into the **[Orchestrator (21)](21-orchestrator.md)**.
- **Grounded Logic:** These metrics inform the "Tipping Point" algorithms, ensuring that the Daemon's "Will" (Intent) is always grounded in the "Body's" actual physical capacity.

### 4. Privacy Control

The Oculus respects the global `LYCHD_SECURE_MODE` toggle.

- **Redaction:** When active, the telemetry provider is configured with `include_content=False`.
- **Structure Over Substance:** This ensures that the *structure* of the trace (latency, success, token counts) is preserved for debugging, while the *substance* (sensitive prompts or secrets) is physically redacted before leaving the application memory.

### Consequences

!!! success "Positive"
    - **Zero-Cost Purity:** Users who do not install the Oculus extension incur zero instrumentation overhead or resource bloat.
    - **Specialized Visualization:** Arize Phoenix provides native rendering for "Retrieved Chunks" and "Tool Calls," providing far superior scrying compared to generic logging tools.
    - **Pluggable Eyes:** Any extension can register a telemetry plugin. The Magus can swap the local Oculus for a cloud provider (e.g., Logfire Cloud) simply by changing the extension configuration.

!!! failure "Negative"
    - **Fragmented Dashboard:** Correlating a slow Agent response (Mind) with high GPU utilization (Body) requires the Magus to look at both the Oculus and Cockpit interfaces.
    - **Startup Latency:** The initialization of the OpenTelemetry exporters adds a measurable delay (~500ms) to the application boot sequence when the extension is active.
