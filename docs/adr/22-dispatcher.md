---
title: 22. Dispatcher
icon: material/directions-fork
---

# :material-directions-fork: 22. Dispatcher: The Switchboard

!!! abstract "Context and Problem Statement"
    Cognitive and operational labor in a sovereign system requires abstract intents: reasoning, visual analysis, vocal perception, tool execution, telemetry queries, browsing, and peer delegation. The physical infrastructure is fragmented across discrete local containers (**Soulstones**), remote APIs (**Portals**), and peer-to-peer nodes (**The Legion**).

    A single provider often offers overlapping services, creating a complex many-to-many mapping between logical intent and physical substrate. Furthermore, on a single-node architecture, provider availability is volatile; a vision model may be "sleeping" to save VRAM. The lack of an intelligent switchboard leads to resource contention, inefficient model loading, and a failure to maintain the **[Sovereignty Wall (09)](09-security.md)**. The machine requires a **Semantic Cortex** to resolve abstract desire into executable power.

## Requirements

- **Provider-Pair Discovery:** Resolution of intents into concrete capability providers rather than hardcoded model identifiers. Cognitive calls may still resolve a `model_provider` + `tool_provider` pair, but the underlying abstraction is a capability-bearing Animator.
- **The Animator Protocol:** Mandatory implementation of the **Animator** interface to bind disparate local, remote, and swarm services to the **[Agents (20)](20-agents.md)** runtime, Graph, Orchestrator, and extension surfaces.
- **The Stasis Handshake:** Mandatory coordination with the **[Orchestrator (23)](23-orchestrator.md)**. The Dispatcher must query the physical state of the required **[Coven (08)](08-containers.md)** before binding logic. If the required hardware is "Cold," it must raise a `HardwareTransitionRequired` signal to trigger the **Stasis Protocol**.
- **Asynchronous Deferral:** The mechanism must support "The Long Sleep." It must be capable of serializing the calling thread and suspending it until the physical body reconfigures itself.
- **Modality Zipping:** Capability to "weave" deferred sensory tools into a text-only reasoning agent if the selected provider lacks native multimodal support.
- **Syntax Standardization (Pydantic Covenant):** Adoption of Python type hints and Pydantic schemas as the definitive internal grammar for tool definitions, eliminating the "Middleware Tax" of legacy proxy translation layers.
- **Sigil-Based Filtering:** Integration with **[The Ward (38)](38-iam.md)** to physically hide privileged tools/models from an Agent based on the active identity's scope.
- **Economic Arbitration:** Integration with **[The Toll (41)](41-x402.md)** to select the most cost-effective provider (local power vs. remote cost) based on the ritual's priority.
- **Privatization-Aware Routing:** Context with elevated privatization weight must not be sent to Portals unless anonymization policy succeeds.
- **Sovereignty Wall Enforcement:** The policy boundary is defined in **[Security (09)](09-security.md)** and enforced here in the Dispatcher's routing decisions. The **[Orchestrator (23)](23-orchestrator.md)** manages hardware state and container transitions; it does not own egress or privacy policy.

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

**The Dispatcher** is adopted as the system's Semantic Cortex. It functions as the switchboard that assembles the machine's working runtime grant from canonical capability records.

!!! note "Capability Binding Cartography"
    Current source names such as `CapabilitySpec`, `CapabilityState`, and `CapabilityGrant` are implementation handles, not final ontology. The durable boundary is the flow from declared intent, to discovered capability, to live substrate state, to late-bound runtime grant, to physical transition when required, to graph or worker recovery boundary. Future R&D may rename, split, or collapse classes as long as the authority boundaries remain intact.


### 1. The World Model (Provider Indexing)

At initialization, the Dispatcher constructs an in-memory index of the Sepulcher’s potential. It loads Animator Runes from the Codex anchors (`runes/animator/`, `runes/animator/soulstones/`, `runes/animator/portals/`) and tracks the runtime animators/connectors currently manifest in the system.

Policy resolution still targets a provider-route contract for cognitive tasks (model/tool identity for the requested task), while the runtime binding path is connector-based (`base_url`, discovered/default model ids, toolsets, service clients, and other adapter-owned surfaces). This index updates as the **Orchestrator** manifests or banishes hardware covens.

### 2. The Animator Handshake (The Stasis Protocol)

The runtime registry is the canonical handshake surface. It exposes:

- `CapabilitySpec`: declared capability identity and routing metadata
- `CapabilityState`: the latest live observation
- `CapabilityGrant`: the late-bound dispatch handoff

- **The Substrate Check:** When an Agent requests a capability, the Dispatcher reads `CapabilityState`.
- **The Physical Check:** If `warm=False`, the physical substrate supports the capability but it is not presently ready.
- **The Residency Boundary:** `persistent_resident=True` keeps a support runtime out of the default eviction set, but it does not create a second conflict law or a second activation path.
- **The Lifecycle Boundary:** `dedicated=False` means the runtime is routable but not lifecycle-managed by LychD.
- **The Stasis Signal:** In this scenario, the Dispatcher raises `HardwareTransitionRequired`. This freezes the Agent Graph and hands control to the Orchestrator.
    - **Soft Activation:** If the runtime is already warm and the adapter exposes a native activation seam, the Orchestrator performs adapter-led activation (for example `llama.cpp` router `/models/load`) without a container restart.
    - **Hard Swap:** If the target runtime is not warm and LychD owns its lifecycle, the Orchestrator executes a Systemd transition so kernel-level `Conflicts=` reclaims the substrate.
- **The Reanimation:** Once the requested capability is warm, the Dispatcher grants it and the Agent resumes.

!!! note "Agent State vs. VRAM Swap"
    The Agent's cognitive state (Pydantic AI graph runner, in-flight tool calls) lives in **Vessel process memory**, not inside the VLLM/llama.cpp container. When VLLM restarts, the Vessel continues running and the Agent simply waits for the next LLM response. No serialization to the Phylactery is required for VRAM swaps. Phylactery serialization serves a different concern — **Long Sleep** durability (surviving reboots, multi-day waits for human approval, or deferred A2A results).

The handshake is implemented as a strict registry and adapter contract:

1. **`list_capabilities()` / `get_capability()`** -> resolve canonical capability identity.
2. **`refresh_capability_state()`** -> re-probe warm/live readiness before grant.
3. **`activate_capability()`** -> perform runtime-native soft activation when supported.
4. **`bind_model()`** -> hydrate the selected model surface from the chosen connector when model-backed.
5. **`bind_toolset()` / `bind_toolsets()`** -> hydrate tool surfaces from the chosen connector when tool-backed.
6. **Service-specific binders** -> hydrate watcher, browser, peer, metrics, or other non-model surfaces when an extension registers that adapter family.

This keeps Orchestrator, Dispatcher, and Animator code decoupled while preserving deterministic resolution.

Generic fallback law: an unknown local Soulstone runtime is passive unless a specific adapter or explicit OpenAI-compatible runtime alias is selected. A `base_url` alone is not evidence that the runtime exposes chat, model listing, or OpenAI-compatible binding semantics.

#### Execution Plane Scope (Current Phase)

- **Now (trusted execution):** Model/tool binding and provider calls run in the Vessel control plane. All agent graph runners, LLM orchestration, and Dispatcher resolution execute exclusively in the Vessel.
- **Secrets:** Secret-bearing provider credentials remain in trusted units only, per **[Security (09)](09-security.md)**.
- **The Tomb phase:** Untrusted arbitrary execution is delegated to **The Tomb** via SAQ. The Tomb receives only serialized script payloads (Python code, CLI commands) — never graph state, agent definitions, or LLM credentials. It returns `stdout` only. The full doctrine is defined in **[Workers (14)](14-workers.md)**.
- **Layout dependency:** This split follows the trust geography in **[Layout (13)](13-layout.md)** and is intentionally phased to avoid partial trust assumptions.

### 3. The Resolution Algorithm (Matchmaking)

When a reasoning step submits a requirement, the Dispatcher executes a multi-stage resolution:

1. **Candidate Selection:** All local (Soulstone) and remote (Portal) Animators declaring an active `Capability` matching the requested type are identified. The canonical capability taxonomy is defined in the **[Animator index](../sepulcher/animator/index.md)**.
2. **Context Filtering:** **[The Ward (38)](38-iam.md)** verifies the Sigil's scopes. Providers not visible to the user are pruned.
3. **Privatization Gate:** The context envelope is scored. If target is a Portal and the payload exceeds configured thresholds, raw routing is blocked and anonymization workflow is required.
4. **Economic Arbitration:** If multiple candidates exist, **[The Toll (41)](41-x402.md)** calculates the cost. It prefers "Free" (local) over "Paid" (remote) unless the ritual is marked `high_fidelity`.
5. **Sovereignty Gate:** If `LYCHD_SECURE_MODE` is active, external Portals are physically purged from the list unless an explicit policy permits sanitized egress.

### 4. The Capability Grant

The Dispatcher does not return a raw model. It returns a **CapabilityGrant** containing:

- **The Animator:** The selected runtime handle.
- **The CapabilitySpec:** The canonical declaration that was selected.
- **The CapabilityState:** The warm/live state observed immediately before grant.
- **The Hydrated Runtime Surfaces:** The bound model, toolsets, service clients, or other adapter surfaces when the selected connector exposes them.
- **Late-Bound Binding:** The grant is a temporary hydration against the active physical substrate at the moment of thought.

Tool-only and service-only grants may have no model. Capability-bearing surfaces are carried by connectors, not by pretending every Portal has a default chat model. A Watcher, browser Animator, or remote service Portal follows the same law: it exposes its own capability families rather than masquerading as chat.

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

Before granting a capability, the Dispatcher performs a **Stateless Pulse**.
It pings the assigned provider endpoint (for OpenAI-compatible connectors, typically `/v1/models`; other connectors may define provider-specific probes). If the pulse fails (timeout/error), the Dispatcher triggers an **Autonomous Repair Signal** to the Orchestrator to investigate or restart the container, protecting the Agent from "Zombie" providers.

### 9. Portal Egress Gate (Privatization Enforcement)

Before any intent is dispatched to an external Portal, the volatility of the context payload is evaluated based on the explicit schema-level classification established by the **[Phylactery (06)](06-persistence.md)**.

- **Context Weighting:** As data is extracted from the persistence layer, the SQLAlchemy `info={"privatization_weight": X}` tags attached to the ORM models are read. The entire prompt inherits the highest weight present within the payload.
- **The Egress Policy:**
    - If the weight is below `portal_threshold` (e.g., public documentation): Dispatch to external Portals is permitted.
    - If the weight is between `portal_threshold` and `forbidden_threshold`: An Anonymization Ritual (local scrubbing) is required, and only sanitized output is used for the dispatch.
    - If the weight is at or above `forbidden_threshold` (e.g., internal system passwords, private memory): **Raw portal egress is strictly forbidden.**
- **The Fallback:** If a Portal route is forbidden, routing is forced to a Local Soulstone (e.g., vLLM), or the request is failed closed. This ensures the Dispatcher acts as an unbypassable firewall against prompt injection exfiltration.

## Consequences

!!! success "Positive"
    -   **Hardware Resonance:** The system maximizes the utility of limited local VRAM by intelligently selecting multimodal animators or zipping text-models with Sensory Soulstones.
    -   **Logical Parallelism:** The "Stasis Signal" allows logical parallelism in the Graph (multiple branches waiting for different hardware) without violating the physical seriality of the single GPU.
    -   **Late-Binding Security:** Logic never possesses permanent access to tools; it is granted a temporary capability grant filtered by the user's Sigil at the moment of thought.

!!! failure "Negative"
    -   **Resolution Latency:** The calculation of the optimal capability grant adds a small overhead (10-50ms) to the initiation of every step.
    -   **Registry Complexity:** Maintaining a synchronized map of providers, provider-route policy, and hardware states requires robust handling of extension registration edge-cases.
