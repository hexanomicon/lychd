---
title: 22. Dispatcher
icon: material/directions-fork
---

# :material-directions-fork: 22. Dispatcher: The Switchboard

!!! abstract "Context and Problem Statement"
    Cognitive labor in a sovereign system requires abstract intents—reasoning, visual analysis, vocal perception—but the physical infrastructure is fragmented across discrete local containers (**Soulstones**), remote APIs (**Portals**), and peer-to-peer nodes (**The Legion**).

    A single provider often offers overlapping services, creating a complex many-to-many mapping between logical intent and physical substrate. Furthermore, on a single-node architecture, provider availability is volatile; a vision model may be "sleeping" to save VRAM. The lack of an intelligent switchboard leads to resource contention, inefficient model loading, and a failure to maintain the **[Sovereignty Wall (09)](09-security.md)**. The machine requires a **Semantic Cortex** to resolve abstract desire into executable power.

## Requirements

- **Provider-Pair Discovery:** Resolution of intents into a concrete `model_provider` + `tool_provider` pair rather than hardcoded model identifiers.
- **The Animator Protocol:** Mandatory implementation of the **Animator** interface to bind disparate providers (Local/Cloud/Swarm) to the **[Agents (20)](20-agents.md)** runtime.
- **The Stasis Handshake:** Mandatory coordination with the **[Orchestrator (23)](23-orchestrator.md)**. The Dispatcher must query the physical state of the required **[Coven (08)](08-containers.md)** before binding logic. If the required hardware is "Cold," it must raise a `HardwareTransitionRequired` signal to trigger the **Stasis Protocol**.
- **Asynchronous Deferral:** The mechanism must support "The Long Sleep." It must be capable of serializing the calling thread and suspending it until the physical body reconfigures itself.
- **Modality Zipping:** Capability to "weave" deferred sensory tools into a text-only reasoning agent if the selected provider lacks native multimodal support.
- **Syntax Standardization (Pydantic Covenant):** Adoption of Python type hints and Pydantic schemas as the definitive internal grammar for tool definitions, eliminating the "Middleware Tax" of legacy proxy translation layers.
- **Sigil-Based Filtering:** Integration with **[The Ward (38)](38-iam.md)** to physically hide privileged tools/models from an Agent based on the active identity's scope.
- **Economic Arbitration:** Integration with **[The Toll (41)](41-x402.md)** to select the most cost-effective provider (Local Power vs. Cloud Tokens) based on the ritual's priority.
- **Privatization-Aware Routing:** Context with elevated privatization weight must not be sent to Portals unless anonymization policy succeeds.

## Considered Options

!!! failure "Option 1: Static Model Registry"
    Utilizing a hardcoded mapping that binds reasoning tasks to specific model strings at agent construction.

    - **Pros:** Zero resolution latency; predictable behavior.
    - **Cons:** **Functional Rigidity.** Fails to account for hardware state. If a local model is not resident, the Agent crashes. It cannot autonomously switch to a Portal if the user is offline or if the GPU is occupied.

!!! failure "Option 2: Network-Layer Load Balancers (LiteLLM)"
    Deploying standard proxies to route traffic based on service name strings.

    - **Pros:** Broad compatibility with standard OpenAI SDKs.
    - **Cons:** **Semantic Blindness.** These tools operate at the network layer. They remain blind to VRAM pressure, model tiers, or provider/tool routing policy. They cannot perform the **Stasis Handshake**, meaning a request to a cold model simply times out rather than triggering a state swap.

!!! success "Option 3: The Switchboard (Semantic Resolution)"
    A two-stage resolution engine that treats hardware states as functional providers, utilizing a generic binding protocol and dynamic toolset composition.

    - **Pros:**
        -   **Dynamic Pathfinding:** Resolves an abstract intent against available physical configurations in real-time.
        -   **Logical Parallelism:** Enables the **Stasis Protocol**, allowing the mind to pause while the body changes.
        -   **Substrate Efficiency:** Maximizes the utility of limited local silicon by preferring multimodal containers.

## Decision Outcome

**The Dispatcher** is adopted as the system's Semantic Cortex. It functions as the switchboard that assembles the machine's "Mind" by resolving provider pairs into **Mind-Bundles**.


### 1. The World Model (Provider Indexing)

At initialization, the Dispatcher constructs an in-memory index of the Sepulcher’s potential. It loads animator rune configs from the Codex anchors (`runes/animator/`, `runes/animator/soulstones/`, `runes/animator/portals/`) and tracks the runtime animators/connectors currently manifest in the system.

Policy resolution still targets a provider-route contract (model/tool identity for the requested task), while the current runtime binding path is connector-based (`base_url`, discovered/default model ids, and connector toolsets). This index updates as the **Orchestrator** manifests or banishes hardware covens.

### 2. The Animator Handshake (The Stasis Protocol)

The **Animator** serves as the metaphysical bridge between the Code and the Model. However, an Animator cannot exist without a Body.

- **"The Substrate Check:"** When an Agent requires a provider route (for example, a vision-capable animator), the Dispatcher checks the **Orchestrator**. If the required Coven is not in a "Warm" state, the Dispatcher invokes the **Stasis Protocol**. It emits a deferred-transition signal (ADR contract), allowing the Agent state to be serialized to the **Phylactery** while the body reconfigures.
- **The Physical Check:** Before granting the Animator, the Dispatcher queries the **Orchestrator**: *"Is the `vision.coven` active?"*
- **The Stasis Signal:** If the answer is **NO**, the Dispatcher does not fail. It raises a `HardwareTransitionRequired` signal.
    - This signal propagates up to the **[Graph (24)](24-graph.md)**.
    - The Graph triggers the **Stasis Protocol**: the current thread is serialized and saved to the **[Phylactery (06)](06-persistence.md)**.
    - Time effectively stops for the Agent while the **Orchestrator** performs the heavy lifting of swapping VRAM contents.
- **The Reanimation:** Once the Orchestrator confirms the new Coven is "Warm," the Dispatcher releases the lock, and the Agent resumes execution as if no time had passed.

!!! note "Agent State vs. VRAM Swap"
    The Agent's cognitive state (Pydantic AI graph runner, in-flight tool calls) lives in **Vessel process memory**, not inside the VLLM/llama.cpp container. When VLLM restarts, the Vessel continues running and the Agent simply waits for the next LLM response. No serialization to the Phylactery is required for VRAM swaps. Phylactery serialization serves a different concern — **Long Sleep** durability (surviving reboots, multi-day waits for human approval, or deferred A2A results).

The handshake is implemented as a strict adapter contract:

1. **`resolve(animator_name)`** -> resolve provider pair and runtime mode (`single`, `router`, or OpenAI-compatible).
2. **`prepare(animator_name)`** -> produce executable runtime plan (container args/env/mounts).
3. **`bind_model(resolved)`** -> hydrate `OpenAIChatModel` (or provider-specific model) from resolved provider.
4. **`bind_toolset(resolved)` / `bind_toolsets(resolved)`** -> hydrate toolsets from the resolved animator connector.
5. **`health(resolved)`** -> optional pulse endpoint before grant (policy/runtime dependent).

This keeps Orchestrator, Dispatcher, and Animator code decoupled while preserving deterministic resolution.

#### Execution Plane Scope (Current Phase)

- **Now (trusted execution):** Model/tool binding and provider calls run in the Vessel control plane. All agent graph runners, LLM orchestration, and Dispatcher resolution execute exclusively in the Vessel.
- **Secrets:** Secret-bearing provider credentials remain in trusted units only, per **[Security (09)](09-security.md)**.
- **The Tomb phase:** Untrusted arbitrary execution is delegated to **The Tomb** via SAQ. The Tomb receives only serialized script payloads (Python code, CLI commands) — never graph state, agent definitions, or LLM credentials. It returns `stdout` only. The full doctrine is defined in **[Workers (14)](14-workers.md)**.
- **Layout dependency:** This split follows the trust geography in **[Layout (13)](13-layout.md)** and is intentionally phased to avoid partial trust assumptions.

### 3. The Resolution Algorithm (Matchmaking)

When a reasoning step submits a requirement, the Dispatcher executes a multi-stage resolution:

1. **Candidate Selection:** All physical (Soulstone) and logical (Portal) Animators declaring an active `Capability` matching the requested type are identified. The canonical capability taxonomy is defined in the **[Animator index](../sepulcher/animator/index.md)**.
2. **Context Filtering:** **[The Ward (38)](38-iam.md)** verifies the Sigil's scopes. Providers not visible to the user are pruned.
3. **Privatization Gate:** The context envelope is scored. If target is a Portal and the payload exceeds configured thresholds, raw routing is blocked and anonymization workflow is required.
4. **Economic Arbitration:** If multiple candidates exist, **[The Toll (41)](41-x402.md)** calculates the cost. It prefers "Free" (Local) over "Paid" (Cloud) unless the ritual is marked `high_fidelity`.
5. **Sovereignty Gate:** If `LYCHD_SECURE_MODE` is active, all Cloud Portals are physically purged from the list.

### 4. The Mind-Bundle (The Grant)

The Dispatcher does not return a raw model; it returns a **Mind-Bundle**. This is a configuration package containing:

- **The Animator:** The selected model implementation.
- **The Arsenal:** A `CombinedToolset` containing all permitted functions and sensory tools.
- **The Archive Lens:** Memory recall tools are injected only when embedding/retrieval substrate is warm and Sigil policy allows archive access.
- **The Limits:** Strictly defined `UsageLimits` derived from the system's economic laws.
- **Late-Bound Binding:** The Mind-Bundle is a temporary hydration of a Persona from the currently selected runtime animator/connector. Policy may still be expressed in provider-route terms, but binding is granted against the active physical substrate at the moment of thought.

### 5. The Modality Zip (Joint Intelligence)

To resolve the complexity of multi-modal provider routing on disparate hardware, the Dispatcher implements the **Modality Zip**.

- **Native Pass:** If the Animator is a multimodal VisionLLM, the image data is passed directly in the prompt.
- **Decomposed Pass:** If the Animator is text-only (e.g., Llama-3), the Dispatcher injects a **Deferred Sensory Tool** (e.g., `call_ocr_container`).
- **The Trigger:** When the text model calls this tool, it triggers the **Stasis Protocol**, causing the text model to sleep while the OCR container is summoned.

### 6. The Pydantic Covenant (The Internal Law)

The Dispatcher rejects intermediate translation protocols (UTCP). It adopts **Python Type Hints** and **Pydantic AI Generics** as the definitive contract for all cognitive labor.

- **Type-Safe Sovereignty:** Tools are defined as standard Python functions. The Dispatcher uses the model's native schema generation to present these to the Animator.
- **Zero Translation:** By using Pydantic models as the "Word," the system eliminates the CPU tax and hallucination risk associated with converting between disparate JSON schemas.

### 7. The Agent Registry & Emissary Protocol

The Dispatcher functions as the sole keeper of the **Agent Registry**—a system-wide directory of all manifest minds.

- **The Registry:** An in-memory index mapping agent intents to provider-route policy (`model_provider` and `tool_provider`). Extensions register their agents here during the boot sequence.
- **The Emissary Pattern:** Remote agents are represented in the registry as **Emissaries**. To the local Agent, invoking a remote node is identical to calling a local tool—the domain boundary is invisible at the reasoning layer.
- **Legion Routing:** If the target node shares the **Master Sigil** (a Thrall), the Dispatcher signs the intent with `INTENT_UPDATE_SYSTEM` authority and transmits it via direct Vessel HTTP. The receiving Thrall validates the Sigil and willingly executes infrastructure-level commands.
- **Necropolis Routing:** If the target node is a foreign Sovereign, the Dispatcher routes through the **[A2A Intercom (26)](26-a2a.md)** and the **Workload Pool** path, attaching a **[Toll (41)](41-x402.md)** bounty. No infrastructure authority is granted — only the declared task intent.
- **The Handover:** When the Dispatcher resolves an intent to an Emissary, it does not execute code locally. It serializes the Pydantic intent and manages the transport — direct HTTP for **[Legion (42)](42-legion.md)** Thralls, A2A for Necropolis peers. This triggers the **Stasis Protocol**: the local Agent freezes, VRAM is freed, and the Agent rehydrates when the peer returns the result.

### 8. Health and Pulse

Before granting a Mind-Bundle, the Dispatcher performs a **Stateless Pulse**.
It pings the assigned provider endpoint (for OpenAI-compatible connectors, typically `/v1/models`; other connectors may define provider-specific probes). If the pulse fails (timeout/error), the Dispatcher triggers an **Autonomous Repair Signal** to the Orchestrator to investigate or restart the container, protecting the Agent from "Zombie" providers.

### 9. Portal Egress Gate (Privatization Enforcement)

Before any intent is dispatched to a Cloud Portal, the volatility of the context payload is evaluated based on the explicit schema-level classification established by the **[Phylactery (06)](06-persistence.md)**.

- **Context Weighting:** As data is extracted from the persistence layer, the SQLAlchemy `info={"privatization_weight": X}` tags attached to the ORM models are read. The entire prompt inherits the highest weight present within the payload.
- **The Egress Policy:**
    - If the weight is below `portal_threshold` (e.g., public documentation): Dispatch to Cloud Portals is permitted.
    - If the weight is between `portal_threshold` and `forbidden_threshold`: An Anonymization Ritual (local scrubbing) is required, and only sanitized output is used for the dispatch.
    - If the weight is at or above `forbidden_threshold` (e.g., internal system passwords, private memory): **Raw portal egress is strictly forbidden.**
- **The Fallback:** If a Portal route is forbidden, routing is forced to a Local Soulstone (e.g., vLLM), or the request is failed closed. This ensures the Dispatcher acts as an unbypassable firewall against prompt injection exfiltration.

## Consequences

!!! success "Positive"
    -   **Hardware Resonance:** The system maximizes the utility of limited local VRAM by intelligently selecting multimodal animators or zipping text-models with Sensory Soulstones.
    -   **Logical Parallelism:** The "Stasis Signal" allows logical parallelism in the Graph (multiple branches waiting for different hardware) without violating the physical seriality of the single GPU.
    -   **Late-Binding Security:** Logic never possesses permanent access to tools; it is granted a temporary Mind-Bundle filtered by the user's Sigil at the moment of thought.

!!! failure "Negative"
    -   **Resolution Latency:** The calculation of the optimal Mind-Bundle adds a small overhead (10-50ms) to the initiation of every step.
    -   **Registry Complexity:** Maintaining a synchronized map of providers, provider-route policy, and hardware states requires robust handling of extension registration edge-cases.
