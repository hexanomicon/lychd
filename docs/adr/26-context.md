---
title: 26. Context
icon: material/text-box-multiple-outline
---

# :material-text-box-multiple-outline: 26. Context: The Deep Memory

!!! abstract "Context and Problem Statement"
    In the era of 128k+ context windows, reliance on fragmented retrieval—**[Memory (24)](24-memory.md)**—creates a reasoning bottleneck by destroying the semantic relationships between disconnected chunks. While retrieval facilitates discovery, it fails to provide the systemic understanding required for complex, interconnected datasets. Full-context ingestion offers superior comprehension but introduces prohibitive latency and computational costs, specifically regarding KV cache management and re-processing overhead. A fundamental gap exists in balancing the depth of total context with the physical constraints of local hardware and inference efficiency.

## Requirements

- **Deep Contextual Ingestion:** Provision of a mechanism to ingest entire datasets into the "Working Memory" (Context Window) to maintain systemic coherence.
- **Prefix Stability:** Mandatory enforcement of a deterministic prompt structure to enable inference engine prefix caching (KV Cache reuse).
- **Dynamic Artifact Injection:** Support for loading massive codebase trees or documentation scrolls into an Agent's dependencies via the **[RunContext (19)](19-agents.md)**.
- **Karma Integration:** Prioritization of "White Truths" and feedback from **[HitL (25)](25-hitl.md)** as hot context for subsequent reasoning rituals.
- **Heuristic Arbitration:** Implementation of logic to autonomously switch between RAG and Context Aware Generation (CAG) based on token volume and model limits.
- **Resource Synchronization:** Mandatory integration with the **[Orchestrator (21)](21-orchestrator.md)** to account for the heavy VRAM footprint of active KV caches during scheduling.
- **Prompt Density Optimization:** Support for Meta-Reasoning rituals to condense instructional prompts without loss of logical density.

## Considered Options

!!! failure "Option 1: Pure Vector-Based RAG"
    Relying exclusively on small-chunk retrieval.
    -   **Cons:** **Semantic Blindness.** The Agent loses the ability to see the "Big Picture," such as cross-file dependencies in a codebase or the overarching narrative of a document. It results in fragmented, shallow reasoning.

!!! failure "Option 2: Naive Full Context Ingestion"
    Passing the entire dataset into the prompt for every request without optimization.
    -   **Cons:** **Extreme Resource Exhaustion.** Processing 100k tokens from scratch for every turn of a conversation introduces unacceptable latency (minutes per request) and burns through GPU cycles and VRAM, paralyzing the machine.

!!! success "Option 3: Hybrid CAG with Prefix Caching"
    Utilizing a strictly ordered prompt structure to maximize the KV Cache capabilities of modern inference engines (e.g., vLLM).
    -   **Pros:**
        -   **Near-Instant Response:** Once the static "floor" (Codebase/Identity) is processed, subsequent queries are served in milliseconds.
        -   **Holistic Understanding:** The Agent retains the full semantic relationship of the data.
        -   **Intelligent Fallback:** The system automatically reverts to RAG when the dataset exceeds the hardware's physical limits.

## Decision Outcome

**Context Aware Generation (CAG)** is adopted as the primary strategy for deep reasoning, enabled by a strict **Prompt Caching** discipline and a heuristic **Context Manager**.

### 1. The Cache Protocol (The Stable Floor)

To exploit the KV Cache capabilities of modern inference servers, the system enforces a deterministic ordering of message blocks. The Working Memory is structured to ensure the most static data remains at the beginning of the prompt.

1. **The Identity:** (Immutable). System Prompt defining the Persona.
2. **The Codex:** (Static). The specific codebase, book, or technical manual being analyzed.
3. **The Karma:** (Prioritized). High-quality outcomes and corrections previously verified through the **[Shadow Realm (25)](25-hitl.md)**.
4. **The State:** (Dynamic). The current **[Graph (22)](22-graph.md)** state or multi-turn history.
5. **The Query:** (Volatile). The specific user request.

**The Result:** The inference engine hashes the prefix. As long as the Codex, Identity, and Karma remain unchanged, the Lych "remembers" the bulk of the data without re-processing it, collapsing the time-to-first-token for long-running conversations.

### 2. The Context Manager (The Heuristic Switch)

Before an Agent run is initiated, a Context Manager service evaluates the intended payload against the current hardware state.

- **Evaluation:** The system tokenizes the target data.
- **Logic:**
    - If `tokens < (context_window * 0.7)`: **Use CAG.** The entire dataset is injected into the prompt as a static block.
    - Else: **Use RAG.** The Agent is granted the `query_archive` tool from **[Memory (24)](24-memory.md)** to search the Phylactery.
- **Tuning:** This threshold is configurable in the Codex, allowing the Magus to balance accuracy against VRAM pressure.

### 3. Karma Integration: Living Memory

The results of the **[Sovereign Consent (25)](25-hitl.md)** protocol are not merely stored in the database; they are promoted to the immediate Working Memory.

- **The Process:** When a "White Truth" is selected in the shadow realm, the resulting artifact is added to the "Karma" block of the prompt structure.
- **The Benefit:** Subsequent reasoning steps "see" the verified truth as part of their cached prefix, ensuring that the machine does not repeat mistakes and builds upon established patterns of success.

### 4. Prompt Optimization (Meta-Reasoning)

To minimize the "Instruction Tax" on VRAM, the system supports autonomous optimization rituals. A specialized Agent analyzes successful traces to generate condensed, "Lossless" versions of system prompts. This reduces the token cost of complex Personas while preserving their instructional density.

### 5. The Context Orchestrator

To bridge the gap between deterministic state and probabilistic reasoning, the system employs a **Context Orchestrator** service.

- **Deterministic Assembly:** The Orchestrator intercepts Agent requests to assemble the prompt block-by-block: **[Identity] → [Codex] → [Karma] → [State] → [Query]**.
- **Cache Shielding:** By ensuring the most static blocks (Identity and Codex) always lead the sequence, the Orchestrator enables the **[Dispatcher (20)](./20-dispatcher.md)** to maximize KV-cache reuse.
- **Dynamic Gating:** The Orchestrator monitors token pressure and autonomously switches from full-context injection to **[RAG (24)](../adr/24-memory.md)** when model limits are approached, ensuring the "Working Memory" remains functional.
- **The CTC (Cut The Crap) Governor:** To ensure substrate stability and prevent VRAM spikes, the manager enforces hard boundary limits:
    - **Character Cap:** Maximum raw character count for the total prompt.
    - **Message Depth:** A rolling window of the last $N$ turns to prevent "goldfish" drift.
    - **Verbatim Priority:** The governor aggressively prunes filler while preserving **[Verbatim)](./06-persistence.md)** facts and **[Consecrated)](./25-hitl.md)** entries.
- **VRAM Safety:** If the calculated cache size exceeds the available buffer in the active **Rune (08)**, the governor triggers a condensation ritual to prune non-essential traces before inference begins.

### 6. Pluggable Context Formatters

The **Context Orchestrator** utilizes a registry of **Formatters** to prepare the working memory.

- **Template Extension:** Extensions can register new `PromptTemplates` or `ArtifactInjectors`. This allows specialized Archons (like **[The Mirror (34)](../adr/34-identity.md)**) to inject unique behavioral constraints or "Karma" summaries into the prefix without modifying the core Orchestrator logic.

### Consequences

!!! success "Positive"
    - **Latency Collapse:** Successful prompt caching reduces the processing time of massive context from minutes to seconds.
    - **Systemic Reasoning:** CAG allows the Agent to maintain a coherent understanding of complex structures that chunked retrieval cannot provide.
    - **Hardware Alignment:** By acknowledging the "Weight" of context, the system prevents Out-of-Memory crashes during deep thinking rituals.

!!! failure "Negative"
    - **Cache Fragility:** A single character change in a static file invalidates the entire cached prefix, forcing a full re-computation.
    - **VRAM Competition:** Maintaining large KV caches for multiple concurrent Personas can starve the GPU, requiring strict limits and preemptive evacuation by the **[Orchestrator (21)](21-orchestrator.md)**.
