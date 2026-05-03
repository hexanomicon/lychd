---
title: 21. Context
icon: material/text-box-multiple-outline
---

# :material-text-box-multiple-outline: 21. Context: The Active Cognitive Field

!!! abstract "Context and Problem Statement"
    In the era of large-scale context windows (128k+ tokens), reliance on fragmented retrieval creates a reasoning bottleneck by destroying the semantic relationships between disconnected data chunks. While retrieval facilitates discovery, it fails to provide the systemic understanding required for complex, interconnected datasets. Full-context ingestion offers superior comprehension but introduces prohibitive latency and computational costs regarding KV cache management and re-processing overhead. A fundamental gap exists in balancing the depth of total context with the physical constraints of local hardware and inference efficiency.

## Requirements

- **Typed State Persistence:** Mandatory utilization of a Pydantic-based `RunContext` to ensure all metadata (identity, environment, and history) is strictly validated before entering the cognitive loop.
- **Deep Contextual Ingestion:** Provision of a mechanism to ingest entire datasets into the "Working Memory" (Context Window) to maintain systemic coherence.
- **Prefix Stability:** Mandatory enforcement of a deterministic prompt structure to enable inference engine prefix caching (KV Cache reuse).
- **Dynamic Artifact Injection:** Support for loading massive codebase trees or documentation scrolls into an Agent's dependencies via the `RunContext`.
- **Environmental Grounding:** Inclusion of real-time hardware state data (e.g., VRAM pressure, connectivity status, low-power modes) within the context to inform reasoning.
- **Identity Scopes:** Mandatory inclusion of the active **Sigil** and its associated permission scopes to facilitate secure tool filtering.
- **Karma Integration:** Prioritization of verified interaction traces and feedback as hot context for subsequent reasoning rituals.
- **Heuristic Arbitration:** Implementation of logic to autonomously switch between Retrieval-Augmented Generation (RAG) and Context Aware Generation (CAG) based on token volume and model limits.
- **Governance Limits:** Mandatory enforcement of hard boundary limits (CTC Governor) to prevent VRAM spikes and substrate instability.
- **Prompt Density Optimization:** Support for Meta-Reasoning rituals to condense instructional prompts without loss of logical density.

## Considered Options

!!! failure "Option 1: Pure Vector-Based RAG"
    Relying exclusively on small-chunk retrieval for all reasoning tasks.
    -   **Cons:** **Semantic Blindness.** The Agent loses the ability to perceive the "Big Picture," such as cross-file dependencies in a codebase or the overarching narrative of a document. Reasoning becomes fragmented and shallow.

!!! failure "Option 2: Naive Full Context Ingestion"
    Passing entire datasets into the prompt for every request without optimization.
    -   **Cons:** **Extreme Resource Exhaustion.** Processing 100k+ tokens from scratch for every turn of a conversation introduces unacceptable latency (minutes per request) and exhausts GPU cycles, potentially paralyzing the machine.

!!! success "Option 3: Hybrid CAG with Prefix Caching (Unified RunContext)"
    Utilizing a strictly ordered prompt structure to maximize KV Cache capabilities alongside a typed dependency injection system.
    -   **Pros:**
        -   **Near-Instant Response:** Once the static "floor" (Identity/Codex) is processed, subsequent queries are served in milliseconds via cache reuse.
        -   **Holistic Understanding:** The Agent retains the full semantic relationship of the data within the **[Agents (ADR 20)](./20-agents.md)** framework.
        -   **Sovereign Safety:** Permissions and hardware reality are baked into the context, ensuring the mind is grounded in the laws of the machine.

## Decision Outcome

**Context Aware Generation (CAG)** is adopted as the primary strategy for deep reasoning, enabled by a strict **Prompt Caching** discipline and a heuristic **Context Manager**. The implementation utilizes Pydantic AI's `RunContext` as the universal primitive for all cognitive rituals.

Context is the temporary active field of cognition. It functions as the **Aisthēsis** (The Simulacrum)—the unified holograph where the **Ahamkara** (Identity) perceives the world. It is a bounded surface where identity, world-model artifacts, prior outcomes, and the current request are made simultaneously visible for one reasoning cycle.

### 1. The Cache Protocol (The Stable Floor)

To exploit KV Cache capabilities, a deterministic ordering of message blocks is enforced. The Working Memory is structured to ensure the most static data remains at the beginning of the prompt. This ordering is not only a caching optimization; it also defines the epistemic layering of the active field:

1. **The Identity (Immutable):** The System Prompt defining the Persona and its core constraints. This establishes structural bias.
2. **The Codex (Static):** The specific codebase, technical manual, or dataset being analyzed. This establishes the active world model.
3. **The Environment (Grounding):** Real-time hardware constraints (VRAM, Power) and the user's active Sigil scopes.
4. **The Karma (Prioritized):** High-quality interaction outcomes and semantic results retrieved from the **[Archive (ADR 27)](./27-memory.md)**. This activates high-salience impressions.
5. **The State (Dynamic):** The current reasoning history or multi-turn conversation thread.
6. **The Query (Volatile):** The specific user request. This is the transient perturbation.

**The Result:** The inference engine hashes the prefix. As long as the Codex, Identity, and Karma remain unchanged, the system "remembers" the bulk of the data without re-processing, collapsing time-to-first-token.

Prefix stability is the fundamental law of **not fucking up the KV cache**. In the cognitive map of the **[Lich](../sepulcher/lich.md)**, the context window is the active field of **Citta** (from *cit*: to perceive — the total LLM generation field). The static prefix layers — Identity, Codex, Karma — are the substrate: the settled Saṃskāras, the lake bed. The volatile layers — State, Query — are the active **Vṛttis** (from *vrt*: to whirl): they disturb only the surface. Keeping the bed still while the surface churns is both the KV cache strategy and the cognitive architecture of clear perception.

### 2. The Context Manager (The Heuristic Switch)

Prior to ritual initiation, a Context Manager evaluates the intended payload against the current hardware state:

- **Evaluation:** The system tokenizes the target data.
- **Logic:**
    - If `tokens < (context_window * 0.7)`: **Use CAG.** The entire dataset is injected into the prompt as a static block.
    - Else: **Use RAG.** The Agent is granted a tool to search the **[Archive (ADR 27)](./27-memory.md)**.
- **Tuning:** Thresholds are configurable in the **[Codex (ADR 12)](./12-configuration.md)**.

### 3. The Context Orchestrator

To bridge the gap between deterministic state and probabilistic reasoning, a **Context Orchestrator** service is employed:

- **Deterministic Assembly:** The Orchestrator intercepts Agent requests to assemble the prompt block-by-block according to the Cache Protocol.
- **Cache Shielding:** By ensuring the most static blocks lead the sequence, the Orchestrator enables the maximized reuse of KV caches.
- **Dynamic Gating:** The Orchestrator monitors token pressure and autonomously switches from full-context injection to RAG when model limits are approached.

### 4. The CTC (Context Truncation & Compression) Governor

To ensure substrate stability and prevent VRAM spikes, the manager enforces hard boundary limits:

- **Character Cap:** Maximum raw character count for the total prompt.
- **Message Depth:** A rolling window of the last $N$ turns to prevent context drift.
- **Verbatim Priority:** Aggressive pruning of filler while preserving **[Verbatim (ADR 06)](./06-persistence.md)** facts and consecrated entries.
- **VRAM Safety:** If the calculated cache size exceeds the available buffer in the active container, the governor triggers a condensation ritual to prune non-essential traces before inference begins.

### 5. Pluggable Context Formatters

The architecture supports a registry of **Formatters** to prepare the working memory. Extensions can register new `PromptTemplates` or `ArtifactInjectors` to inject unique behavioral constraints or memory summaries into the prefix without modifying the core kernel.

#### Quality Drift Injection (LLM Output Correction)

A formatter/injector may provide a compact "quality drift" block containing recent, high-frequency local failure patterns (for example: Ruff lint faults, BasedPyright typing faults, Markdown formatting mistakes) to reduce repeated agent errors during coding rituals.

- **Intent:** Pre-correct common local mistakes before code is produced.
- **Inputs:** Local lint/type outputs and curated fault indexes (for example an agent drift ledger).
- **Constraints:** Must be bounded by recency, frequency, and token budget to avoid polluting the stable floor.
- **Placement:** Inject after Identity/Codex and before volatile query content when used, so project conventions remain visible during generation.

This is a correction aid, not a replacement for Ruff/BasedPyright enforcement; the quality stack remains the authoritative judge after generation.

## Consequences

!!! success "Positive"
    - **Latency Collapse:** Successful prompt caching reduces the processing time of massive context from minutes to seconds.
    - **Systemic Reasoning:** CAG allows the Agent to maintain a coherent understanding of complex structures that chunked retrieval cannot provide.
    - **Hardware Alignment:** By acknowledging the "Weight" of context, the system prevents Out-of-Memory crashes during deep thinking rituals.

!!! failure "Negative"
    - **Cache Fragility:** A single character change in a static file invalidates the entire cached prefix, forcing a full re-computation.
    - **VRAM Competition:** Maintaining large KV caches for multiple concurrent Personas can starve the GPU, requiring strict limits and preemptive evacuation by the system's physical controller.
