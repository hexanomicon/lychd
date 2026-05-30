---
title: 29. Observability
icon: material/telescope
---

# :material-telescope: 29. Observability: The Oculus

!!! abstract "Context and Problem Statement"
    The operation of an autonomous cognitive engine bridges the deterministic world of infrastructure and the probabilistic world of AI agents. Maintaining operational coherence requires instrumented perception of both physical health (VRAM pressure, thermal limits) and cognitive drift (hallucinations, logical loops). Traditional monitoring tools capture network requests but remain blind to the "Thought Trace"—the causal link from prompt to tool to output. Observability is the instrumented perception layer of the agentic runtime: structured evidence for diagnosis, routing, evaluation, and repair without mandatory overhead on the core runtime.

## Requirements

- **Extension Assimilation:** Implementation as an optional coupled extension; the Core kernel must not possess hard dependencies on observability SDKs, ensuring zero overhead for users who do not summon the Oculus.
- **Thought Traceability:** Mandatory visualization of the full execution tree for every **[Agent (ADR 20)](./20-agents.md)** run. It must capture structured events: the flickers of movement through the agentic graph (**Vṛttis**), including tool arguments, validation retries, and the raw "Whispers" exchanged with providers.
- **Dual-Layer Scrying:** Separation of concerns into the "Mind" (Agent reasoning traces) and the "Body" (Host hardware and container status).
- **Runtime Evidence:** Traces, metrics, and structured events must remain available to the runtime as evidence for diagnosis, routing, evaluation, and repair while remaining readable to the Magus.
- **Physical Integration:** Mirroring of critical hardware metrics (GPU memory pressure) into the **[Orchestrator (ADR 23)](./23-orchestrator.md)** to inform scheduling decisions.
- **Privacy Enforcement:** Integration with the global `LYCHD_SECURE_MODE` to redact sensitive prompt and completion content from telemetry before it leaves the application memory.
- **Protocol Adherence:** Compliance with OpenTelemetry (OTLP) standards to ensure interoperability with external collectors if the Magus chooses a cloud backend.
- **A2A Tracing:** Need to support Distributed Tracing, propagating W3C Trace Context headers across A2A handshakes to visualize multi-node cognitive rituals - read the `traceparent` headers from incoming A2A requests.

## Considered Options

!!! failure "Option 1: The Cloud Native Suite (Prometheus / Grafana / Jaeger)"
    Deploying the standard enterprise observability stack.
    - **Pros:** Maximum power and industry standard.
    - **Cons:** **Extreme Default Overhead.** Requires 3-4 heavy containers and meaningful RAM allocation just to monitor a single node. The complexity of PromQL, LogQL, dashboarding, and retention policy is disproportionate to the needs of a personal daemon before it has many active Animators or Legion nodes.

!!! failure "Option 2: Persistence-Layer Logging"
    Storing all traces and metrics directly as JSONB rows in the **[Phylactery (ADR 06)](./06-persistence.md)**.
    - **Pros:** Zero extra infrastructure; unified backups.
    - **Cons:** **Wrong Tool.** Relational databases are inefficient for high-frequency time-series events. Building a specialized Trace UI within the Altar is a massive development diversion from core AI capabilities.

!!! success "Option 3: The Oculus (Phoenix + Cockpit)"
    A hybrid strategy utilizing specialized GenAI tracing and native host monitoring.
    - **Pros:**
        - **Arize Phoenix:** Specialized for LLM workflows and Pydantic AI; provides a local, high-fidelity scrying pool for cognitive traces.
        - **Logfire SDK:** Native integration with Pydantic models ensures zero-boilerplate instrumentation.
        - **Cockpit:** Zero-overhead host monitoring for "Body" metrics (GPU/CPU/RAM).

## Decision Outcome

**The Oculus** is adopted as the Observability Extension. Phoenix is the current scrying pool, but the architectural requirement is the trace itself: structured evidence that connects intent, graph movement, tool use, runtime pressure, and outcome while leveraging host-native tools for hardware telemetry.

!!! note "Trace Correlation Contract"
    Runtime evidence must preserve correlation keys across layers: `run_id`, `step_id`, `tool_call_id`, `lane_id`, peer task IDs, and relevant hardware lease IDs. This lets an incident, Riddle failure, HitL decision, or A2A callback be followed from visible surface to graph movement to provider call without granting the trace authority over the underlying state.

    Failed tool calls must also preserve the validator-known rejection shape: `failure_class`, `required_state`, `observed_state`, and retryability when available. This keeps "the model ignored the state" distinct from "the state surface omitted a hidden precondition" during later Riddle, Reaper, or Magus review.

### 1. The Extension Registration (The Retina Hook)

To satisfy the requirement of sovereignty, the Oculus is implemented as an Extension:

- **The Rune:** `observability/phoenix` registers `PhoenixSettings`, a
  `RuneConfig` under `runes/observability/phoenix/`. Phoenix image and host
  ports are extension-owned TOML, not fields on the core `Settings` model.
- **The Store:** Vessel telemetry registration is reserved for a future shaped
  `context.vessel` bundle; it must not become another flat ExtensionContext
  method.
- **The Injection:** Once shaped, that Vessel bundle may install the
  **[Backend's (ADR 11)](./11-backend.md)** `InitPluginProtocol`. During the
  "Deep Awakening" (Server Mode), it configures the global OpenTelemetry
  providers.
- **The Scope:** Because the Vessel and the **[Ghouls (ADR 14)](./14-workers.md)** share the same boot logic, the Oculus automatically observes both the scrying at the Altar and the labor in the background.

### 2. The Thought Trace (Mind)

The extension configures the process to emit signals following the Generative AI Semantic Conventions:

- **Instrumentation:** It invokes `logfire.instrument_pydantic_ai()` and `logfire.instrument_httpx()`. This captures the reasoning loop of the Agent and the raw prompts exchanged with the **[Dispatcher (ADR 22)](./22-dispatcher.md)**'s providers.
- **The Collector:** An active `PhoenixSettings` rune manifests a local
  `lychd-oculus` service running **Arize Phoenix**.
- **The Routing:** Telemetry is exported via OTLP to `http://localhost:4318`. Because the composed runtime shares the `lychd.pod` network namespace, all containers can natively push traces over TCP without requiring complex network bridging or custom proxies.

### 3. Physical Body Monitoring (Body)

For hardware monitoring, the architecture rejects containerized metrics to avoid the "Prometheus Tax." Instead, LychD utilizes the host's native **Cockpit** service.

- **VRAM Visualization:** Users are encouraged to install the `cockpit-pcp` and NVIDIA-SMI/AMD plugins. This provides the Magus with high-fidelity, real-time GPU utilization and VRAM tracking via a dedicated dashboard.
- **Metric Mirroring:** Critical hardware metrics (OOM events, thermal throttling) are mirrored from the host into the **[Orchestrator (ADR 23)](./23-orchestrator.md)**.
- **Grounded Logic:** These metrics inform the "Tipping Point" algorithms, ensuring that the Daemon's "Will" is always grounded in the "Body's" actual physical capacity.

### 4. Performance & SDLC Metrics (The Pulse)

The third observability layer captures the **service body's own vital signs**: model runtime performance, local service health, and the data that Prometheus traditionally collects, harvested without the Prometheus Tax.

- **Per-Request Metrics:** Model-backed **[Animators](../sepulcher/animator/index.md)** piggyback performance data on every inference response: `tokens_generated`, `tokens_per_second`, `time_to_first_token`, `prompt_processing_time`. OpenAI-compatible APIs (vLLM, llama.cpp) already include `usage` fields and timing headers; the Animator adapter extracts and normalizes them.
- **Engine System Metrics:** The **[Orchestrator (ADR 23)](./23-orchestrator.md)** periodically polls each active Soulstone's `/metrics` endpoint for system-level data: KV cache utilization, request queue depth, active batch size, GPU memory pressure, or service-family equivalents. These are standard Prometheus exposition format, trivially parseable without requiring a Prometheus server.
- **Agentic SDLC Quality Telemetry:** The system logs its own software engineering performance to prove competence over time.
    - **Attempts:** The number of self-correction loops (`ModelRetry`) needed before a task succeeds.
    - **Presence:** Whether a task was merged autonomously (Zero-Touch Engineering) or required human intervention (HitL).
    - **Streak:** The consecutive count of flawless, autonomous ZTE merges. This serves as the Confidence Threshold to unlock frictionless promotion.
- **Trajectory and Cost Observability (The Grist):** To reason about its own metabolic efficiency, the system maintains an append-only Trajectory Log directly in the PostgreSQL Phylactery. For every agent invocation, it captures the raw economics of the thought: `[Phase, Command, Model, Tokens_In, Tokens_Out, Cost_USD, Success]`. This ensures the Lich retains durable historical data to auto-tier cheaper models for mechanical chores, independent of external visualizers like Phoenix.
- **Phylactery Storage:** All metrics are written to a dedicated `metrics` schema in the **[Phylactery (ADR 06)](./06-persistence.md)**. PostgreSQL handles single-node time-series scale effortlessly. This eliminates the need for a dedicated time-series database.
- **Scheduling Fuel:** The Orchestrator consumes these metrics directly from Postgres to inform the **Whim** algorithm — routing decisions, model tiering, Thrall delegation, and thermal throttling are all driven by real tok/s and cache pressure, not heuristics.
- **Legion Scaling:** Each Thrall's Orchestrator scrapes its own local Soulstones and writes to the Master's Phylactery. The Master sees all nodes' performance in one query — no federation, no aggregation layer.
- **Agent-Consumed Analysis:** Trends and anomalies are surfaced by agents reading the metrics table directly. The Magus asks "how's the GPU doing?" and gets a reasoned answer with the trace available for inspection.

#### Optional Watcher Coven Boundary

The rejection of the Cloud Native Suite is a default-runtime decision, not a permanent ban. Prometheus, Grafana, Loki, Alloy, or similar tools may become **Watcher-class Animators** when the Magus needs fleet-style operations:

- many Soulstone, Portal, browser, watcher, or tool Animators running at once;
- Legion/Thrall nodes emitting service metrics from multiple machines;
- historical dashboards, alert rules, and cross-service correlation beyond what Cockpit, Phoenix, Postgres metrics, and agent queries comfortably provide;
- log volume where `journalctl` and structured application logs stop being ergonomic.

When summoned, these tools must be optional Soulstones or Portals under the Oculus/Watcher family. They must not become Core dependencies, must not replace the Phylactery metrics used as Orchestrator fuel, and must expose explicit capabilities such as `metrics_query`, `logs_query`, `trace_search`, `dashboard_render`, or `alert_state` rather than masquerading as cognitive Animators.


### 5. Privacy Control

The Oculus respects the global `LYCHD_SECURE_MODE` toggle:

- **Redaction:** When active, the telemetry provider is configured with `include_content=False`.
- **Structure Over Substance:** This ensures that the *structure* of the trace (latency, success, token counts) is preserved for debugging, while the *substance* (sensitive prompts or secrets) is physically redacted before leaving the application memory.

## Consequences

!!! success "Positive"
    - **Zero-Cost Purity:** Users who do not enable the Oculus extension incur zero instrumentation overhead or resource bloat.
    - **Specialized Visualization:** Arize Phoenix provides native rendering for "Retrieved Chunks" and "Tool Calls," providing far superior scrying compared to generic logging tools.
    - **Pluggable Eyes:** Any extension can register a telemetry plugin. The Magus can swap the local Oculus for a cloud provider (e.g., Logfire Cloud) simply by changing the extension configuration.

!!! failure "Negative"
    - **Fragmented Dashboard:** Correlating a slow Agent response (Mind) with high GPU utilization (Body) requires the Magus to look at both the Oculus and Cockpit interfaces.
    - **Startup Latency:** The initialization of the OpenTelemetry exporters adds a measurable delay (~500ms) to the application boot sequence when the extension is active.
