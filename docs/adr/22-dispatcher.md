---
title: 22. Dispatcher
icon: material/directions-fork
---

# :material-directions-fork: 22. Dispatcher: The Switchboard

!!! abstract "Context and Problem Statement"
    Cognitive and operational labor in a sovereign system requires abstract intents: reasoning, visual analysis, vocal perception, tool execution, telemetry queries, browsing, and peer delegation. The physical infrastructure is fragmented across discrete local containers (**Soulstones**), remote APIs (**Portals**), and peer-to-peer nodes (**The Legion**).

    A single provider often offers overlapping services, creating a complex many-to-many mapping between logical intent and physical substrate. Furthermore, on a single-node architecture, provider availability is volatile; a vision model may be "sleeping" to save VRAM. The lack of an intelligent switchboard leads to resource contention, inefficient model loading, and a failure to maintain the **[Sovereignty Wall (09)](09-security.md)**. A resolution layer is required to translate an abstract capability intent ("chat with tool support") into a concrete, warm endpoint. That layer is the **Dispatcher** — the Semantic Cortex.

## Requirements

- **Provider-Pair Discovery:** Resolution of intents into concrete capability providers rather than hardcoded model identifiers. Cognitive calls may still resolve a `model_provider` + `tool_provider` pair, but the underlying abstraction is a capability-bearing Animator.
- **Semantic Selection Only:** The Dispatcher selects a declared capability and issues a scoped grant only when it is `WARM`; it never starts, stops, swaps, or activates a runtime.
- **Explicit Requirements:** Family, model preference, required input modalities, and tool support must be named in the dispatch request and filtered before a provider can be selected.
- **The Animator Protocol:** Mandatory implementation of the **Animator** interface to bind disparate local, remote, and swarm services to the **[Agents (20)](20-agents.md)** runtime, Graph, Orchestrator, and extension surfaces.
- **The Stasis Handshake:** Mandatory coordination with the
  **[Orchestrator (23)](23-orchestrator.md)**. The Dispatcher reads the selected capability's live
  Animator state before binding. If managed substrate is not ready, it raises
  `HardwareTransitionRequired` to trigger the **Stasis Protocol**; it never interprets Coven or
  conflict-domain topology itself.
- **Asynchronous Deferral:** HTR and grant requirements must be serializable/park-safe so the Graph can own Live or Durable Stasis. The Dispatcher never serializes an execution frame itself.
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

### Capability Binding Cartography

The capability ontology is frozen. Earlier drafts left the class names provisional across the Dispatcher, **[Orchestrator (23)](23-orchestrator.md)**, and **[Graph (24)](24-graph.md)**; for v1 that instability ends. Three classes carry the binding lifecycle, and their authority boundaries are canonical:

- **`CapabilitySpec`** — declared capability identity. Immutable per bind; the routing metadata a candidate advertises.
- **`CapabilityState`** — the live physical projection. The latest observation of warm/live readiness against real substrate.
- **`CapabilityGrant`** — the late-bound cognitive binding. A temporary hydration handed to a reasoning step at the moment of thought.

The canonical capability key is `{animator}:{family}:{model_id}`. The rune names the Animator (**[Configuration (12)](12-configuration.md)**); the family and model id complete the identity, so a single multi-model Animator yields several Specs.

#### `is_dynamic` and Phase

A `CapabilitySpec` carries an `is_dynamic: bool`; a `CapabilityState` projects a `CapabilityPhase`. The two are orthogonal: `is_dynamic` is a *fixed property of the runtime* (how it becomes ready), phase is the *live observation* (whether it is ready now).

- **`is_dynamic`** — `False` (resident whenever the Animator unit is up — the server binds its port only after the model loads, so a reachable endpoint is warm) or `True` (the unit is up but the model needs an in-runtime activation step, e.g. the `llama.cpp` router `/models/load` or ExLlamaV3 through TabbyAPI `/v1/model/load`). These are the canonical doctrine values; an earlier `FIXED/AWAITED` proposal was rejected, and the legacy `dynamic_soft` string normalizes to `is_dynamic=True`.
- **`CapabilityPhase`** — the six-value readiness ladder: `COLD` (unit down / endpoint unreachable), `ACTIVATABLE` (unit up, an `is_dynamic=True` model not yet loaded), `WARMING` (activation in flight), `WARM` (requests accepted now), `ERROR`, and `UNKNOWN`. Intent resolution drives its decision table off the phase, not a boolean.

#### The Two-Axis Law

A capability is described along two orthogonal axes, and conflating them is forbidden:

- **Family** names a routable *service kind*: `chat`, `vision`, `embedding`, `stt`, `tts`, `tool_execution`, `rerank`.
- **Modalities** name what a capability *admits and emits* on a request.

There is no AUDIO family. A chat model that hears is `chat` with `audio ∈ modalities_in`; a chat model that sees is `chat` with `image ∈ modalities_in`. The `vision` family (the dedicated Eye of **[Vision (36)](36-vision.md)**) is reserved for dedicated vision-analysis providers, not for a multimodal chat model that happens to accept images. Intent resolution matches on `(family, required_modalities, requires_tools)`, where the required modalities must be a subset of the capability's `modalities_in` and a tool-bearing request admits only `supports_tools=True`. When no admitting capability is available, the **Modality Zip** (§5) is the sanctioned degradation path — never a silent family substitution.

#### The Declare-then-Verify Doctrine

Declared capability hints (the `[[models]]` blocks of a Soulstone rune, per **[Configuration (12)](12-configuration.md)**) are authoritative for routing intent. Live probes — `llama-server` `/props` modalities, the `multimodal` flag on `/v1/models` — may only *downgrade*: they mark a declared capability unavailable with a reason. They never invent capability a rune did not declare. Verification tightens; it never loosens. This is the deliberate mirror of the tighten-only Policy Ward in **[Configuration (12)](12-configuration.md)**.

#### The Grant Lease Doctrine

A `CapabilityGrant` is a lease scoped to the step that acquired it. Steps re-acquire per use; a
grant is never cached across steps. Before any mutable-runtime transition, the Orchestrator closes
admission and waits for every affected lease to release: the complete evictee set for a hard swap,
or the target Animator itself for an in-process model load. The second barrier matters because a
router load may unload an older model and invalidate a different capability grant from the same
process. Generation/epoch-based stale-grant rejection remains a later distributed-recovery
refinement; the foundation prevents the local stale-grant race through admission closure and drain.
This ties to the Swarm Lease of the **[Orchestrator (23)](23-orchestrator.md)**.

!!! note "Rulings: the grant/lease surface"
    - **HTR decoupling (seam S5).** `HardwareTransitionRequired` is now handle-free — it carries only `capability_key`, `animator_name`, and a nullable `estimated_ready_ms`. It is JSON-loggable and park-safe; consumers re-fetch the spec from the registry by key (the registry is the only truth for records).
    - **The lease context manager.** A grant is acquired through `Dispatcher.lease_grant(...)`, an async context manager that resolves family/model/modality/tool requirements and reads the phase decision table. `WARM` registers a GrantLease and yields the grant; managed readying phases (`COLD`, `ACTIVATABLE`, `WARMING`) raise HTR *before* lease acquisition; `ERROR`, unresolved `UNKNOWN`, and unavailable shared runtimes fail closed. The lease is released on every exit. `lease_grant_key(key, ...)` is the key-addressed form for CLI, tests, and manual paths — same machinery, spec resolved by explicit key.
    - **Concurrent drain admission.** An open Animator is preferred over an otherwise equivalent draining candidate. Admission may still close during the asynchronous WARM preflight or grant assembly; that typed refusal is converted to HTR before the grant enters the ledger, so GraphRunner parks and retries through the single readiness owner. Duplicate grant ids and other ledger defects remain hard failures rather than masquerading as stasis.
    - **`issue_grant` (formerly `resolve_capability_grant`).** Grant assembly for a WARM capability moved onto the AnimatorRegistry as `issue_grant` (mechanics only); the Dispatcher owns the phase decision, the registry owns the handoff assembly.

#### Portal Capability Synthesis

A Portal yields `CapabilitySpec`s from its declared model list in the Codex or, when explicitly enabled, from a live `/v1/models` probe performed at bind. Portal-born specs are `dedicated=False` and `is_dynamic=False`: LychD has no activation or lifecycle authority over them. Their live state must still be `WARM` before grant.

!!! note "Ruling: Portal synthesis is live"
    Portal capability synthesis is built. A Portal now yields one `CapabilitySpec` per declared `[[models]]` block — key `{portal}:{family}:{model_id}`, always `is_dynamic=False`. A Portal with zero declared models yields zero specs (honest: reachable but unadvertised). The live `/v1/models` probe is opt-in per rune (`probe = true`, default `false`) so binding a Portal performs no egress by default. Request-time Portal Egress, Sovereignty, and Economic (**[The Toll (41)](41-x402.md)**) gates remain policy integrations described below.


### 1. The World Model (Provider Indexing)

At initialization, the Dispatcher constructs an in-memory index of the Sepulcher’s potential. It loads Animator Runes from the Codex anchors (`runes/animator/`, `runes/animator/soulstones/`, `runes/animator/portals/`) and tracks the runtime animators/connectors currently manifest in the system.

Policy resolution still targets a provider-route contract for cognitive tasks (model/tool identity
for the requested task), while the runtime binding path is connector-based (`base_url`,
discovered/default model ids, toolsets, service clients, and other adapter-owned surfaces). This
index updates as the **Orchestrator** readies or retires managed Animators.

### 2. The Animator Handshake (The Stasis Protocol)

The runtime registry is the canonical handshake surface. It exposes:

- `CapabilitySpec`: declared capability identity and routing metadata
- `CapabilityState`: the latest live observation
- `CapabilityGrant`: the late-bound dispatch handoff

- **The Substrate Check:** When an Agent requests a capability, the Dispatcher reads `CapabilityState.phase`.
- **The Physical Check:** Any managed phase below `WARM` (`COLD`, `ACTIVATABLE`, `WARMING`) means the substrate supports the capability but it is not presently ready. The Dispatcher emits HTR without choosing or executing the remedy.
- **The Residency Boundary:** `persistent_resident=True` excludes a support runtime from conflict
  participation at bind and from managed eviction. It does not create a second activation path.
- **The Lifecycle Boundary:** `dedicated=False` means the runtime is routable but not lifecycle-managed by LychD.
- **The Stasis Signal:** In this scenario, the Dispatcher raises `HardwareTransitionRequired`. This freezes the Agent Graph and hands control to the Orchestrator.
    - **Soft Activation:** If the unit is already running and the adapter exposes a native
      activation seam, the Orchestrator closes admission for that whole Animator, pauses new queue
      claims, drains all of its leases, and only then performs adapter-led activation (for example
      `llama.cpp` router `/models/load`) without a container restart. If activation/readiness fails,
      admission remains deliberately closed because v1 has no trustworthy model-level inverse.
    - **Hard Swap:** If the target runtime is cold and LychD owns its lifecycle, the Orchestrator
      derives the exact active conflict neighborhood from validated Rune intent, closes and drains
      it, and stale-validates the world. After the actuator attests the loaded target graph, one
      Animator-target start asks systemd to perform the complete stop/switch/start transaction.
      Readiness and one exact compensation toward the captured prior compatible target set remain
      Orchestrator responsibilities. An uncertain transaction or failed compensation keeps
      admission closed and rejects later transitions—including a warm-looking NO_OP. Direct mode
      holds this containment only for the Vessel process lifetime; mediated mode persists a
      `.contained` marker across restart until operator recovery.
- **The Reanimation:** Once the Orchestrator converges the requested capability on `WARM`, the Graph retries dispatch; only that fresh dispatch may issue the grant.

!!! note "Agent State vs. VRAM Swap"
    An ordinary VRAM swap is **Live Stasis**: the Agent's cognitive state lives in Vessel process memory and simply waits for the substrate. The Live/Durable Stasis definitions and default table are law in **[Graph (24)](24-graph.md)**.

The handshake is implemented as a strict registry and adapter contract:

1. **`list_capabilities()` / `get_capability()`** -> resolve canonical capability identity.
2. **`refresh_capability_state()`** -> re-probe warm/live readiness before grant.
3. **`issue_grant()`** -> hydrate a grant only from a `WARM` record.
4. **`activate_capability()` / `await_warm()`** -> Orchestrator-owned readiness operations, never Dispatcher-owned selection operations.
5. **`bind_model()`** -> hydrate the selected model surface from the chosen connector when model-backed.
6. **`bind_toolset()` / `bind_toolsets()`** -> hydrate tool surfaces from the chosen connector when tool-backed.
7. **Service-specific binders** -> hydrate watcher, browser, peer, metrics, or other non-model surfaces when an extension registers that adapter family.

This keeps Orchestrator, Dispatcher, and Animator code decoupled while preserving deterministic resolution.

Generic fallback law: an unknown local Soulstone runtime is passive unless a specific adapter or explicit OpenAI-compatible runtime alias is selected. A `base_url` alone is not evidence that the runtime exposes chat, model listing, or OpenAI-compatible binding semantics.

#### Execution Plane Scope (Current Phase)

- **Now (trusted execution):** Model/tool binding and provider calls run in the Vessel control plane. All agent graph runners, LLM orchestration, and Dispatcher resolution execute exclusively in the Vessel.
- **Secrets:** Secret-bearing provider credentials remain in trusted units only, per **[Security (09)](09-security.md)**.
- **The Tomb phase:** Untrusted arbitrary execution is delegated to **The Tomb** via SAQ. The Tomb receives only serialized script payloads (Python code, CLI commands) — never graph state, agent definitions, or LLM credentials. It returns `stdout` only. The full doctrine is defined in **[Workers (14)](14-workers.md)**.
- **Layout dependency:** This split follows the trust geography in **[Layout (13)](13-layout.md)** and is intentionally phased to avoid partial trust assumptions.

### 3. The Resolution Algorithm (Matchmaking)

The full policy algorithm is staged as follows. The foundation implements capability admission and
deterministic readiness-aware ordering; later gates must be inserted before grant without creating a
parallel dispatch path:

1. **Candidate Selection:** All local (Soulstone) and remote (Portal) Animators declaring a `Capability` matching the requested family, optional model, required modalities, and tool requirement are identified. The canonical capability taxonomy is defined in the **[Animator index](../sepulcher/animator/index.md)**.
2. **Context Filtering:** **[The Ward (38)](38-iam.md)** verifies the Sigil's scopes. Providers not visible to the user are pruned.
3. **Privatization Gate:** The context envelope is scored. If target is a Portal and the payload exceeds configured thresholds, raw routing is blocked and anonymization workflow is required.
4. **Economic Arbitration:** If multiple candidates exist, **[The Toll (41)](41-x402.md)** calculates the cost. It prefers "Free" (local) over "Paid" (remote) unless the ritual is marked `high_fidelity`.
5. **Sovereignty Gate:** If `LYCHD_SECURE_MODE` is active, external Portals are physically purged from the list unless an explicit policy permits sanitized egress.

### 4. The Capability Grant

The Dispatcher does not return a raw model. It returns a **CapabilityGrant** containing:

- **The Animator:** The selected runtime handle.
- **The CapabilitySpec:** The canonical declaration that was selected.
- **The CapabilityState:** The warm/live state observed immediately before grant.
- **The Resolved Generation Profile:** The runtime → Animator → model overlay, including
  `max_context` and `max_tokens` when declared. Context uses these grant-bound limits rather than a
  static model guess; see **[Context (ADR 21)](./21-context.md)**.
- **The Hydrated Runtime Surfaces:** The bound model, toolsets, service clients, or other adapter surfaces when the selected connector exposes them.
- **Late-Bound Binding:** The grant is a temporary hydration against the active physical substrate at the moment of thought.

Tool-only and service-only grants may have no model. Capability-bearing surfaces are carried by connectors, not by pretending every Portal has a default chat model. A Watcher, browser Animator, or remote service Portal follows the same law: it exposes its own capability families rather than masquerading as chat.

When a Graph occurrence is bound in the current execution context, the Dispatcher emits the
authoritative dispatch observation only after the lease ledger has admitted the grant. That event
names the selected capability, Animator, family/model, observed warm phase, occurrence identity,
and exact grant/lease identity. Workflows do not emit a look-alike selection event: only the office
that actually acquired the grant may claim that relation.

#### Durable Content and `ArtifactRef`

Multimodal bytes do not belong inside an `Intent`, run row, queue payload, graph state, or
checkpoint. Durable content carries an immutable `ArtifactRef` containing an artifact identity,
SHA-256 digest, media type, byte size, and classification. The blob lives in an external artifact
store governed by Phylactery/security policy; Graph and Dispatcher pass only the reference.

The foundation implements the discriminated text/artifact content shape, digest validation, and
media-type-to-modality projection used by dispatch admission. The blob store, authorization-aware
materializer, retention/garbage collection, and provider-specific multimodal payload conversion
remain later work. Until that materializer exists, an `ArtifactRef` is durable metadata, not a
promise that every Animator can consume the referenced bytes.

### 5. The Modality Zip (Joint Intelligence)

To resolve the complexity of multi-modal provider routing on disparate hardware, this ADR defines the **Modality Zip** target.

- **Native Pass:** If the Animator is a multimodal VisionLLM, the image data is passed directly in the prompt.
- **Decomposed Pass:** If the Animator is text-only (e.g., Llama-3), the Dispatcher injects a **Deferred Sensory Tool** (e.g., `call_ocr_container`).
- **The Trigger:** When the text model calls this tool, it triggers the **Stasis Protocol**, causing the text model to sleep while the OCR container is summoned.

!!! warning "Doctrine ahead of the foundation"
    Native modality admission is implemented, but the full Modality Zip planner, deferred sensory
    tool materializer, and cross-Animator result join are not. A request that has no native
    admitting capability currently fails closed; it is not silently transformed.

### 6. The Pydantic Covenant (The Internal Law)

The Dispatcher rejects intermediate translation protocols (UTCP). It adopts **Python Type Hints** and **Pydantic AI Generics** as the definitive contract for all cognitive labor.

- **Type-Safe Sovereignty:** Tools are defined as standard Python functions. The Dispatcher uses the model's native schema generation to present these to the Animator.
- **Zero Translation:** By using Pydantic models as the "Word," the system eliminates the CPU tax and hallucination risk associated with converting between disparate JSON schemas.

### 7. The Agent Registry & Emissary Protocol

The Dispatcher is the intended semantic routing boundary for the **Agent Registry**—a system-wide directory of all manifest minds. The Emissary transport described here is not part of the current foundation.

- **The Registry:** An in-memory index mapping agent intents to provider-route policy (`model_provider` and `tool_provider`). Extensions register their agents here during the boot sequence.
- **The Emissary Pattern:** Remote capabilities are represented in the registry as
  **Emissaries**. They may present a tool-shaped reasoning surface, but the Dispatcher preserves
  the remote principal, authority, durability, cost, and failure boundary.
- **Legion Routing:** An enrolled Node Agent has a unique node-scoped identity. The Dispatcher may
  route only a typed semantic delegation admitted under **[Legion law (42)](42-legion.md)**; it
  never grants `INTENT_UPDATE_SYSTEM`, shares the Master Sigil, or transmits infrastructure
  commands.
- **Necropolis Routing:** If the target node is a foreign Sovereign, the Dispatcher routes through the **[A2A Intercom (26)](26-a2a.md)** and the **Workload Pool** path, attaching a **[Toll (41)](41-x402.md)** bounty. No infrastructure authority is granted — only the declared task intent.
- **The Handover:** When the Dispatcher resolves an intent to an Emissary, it records and parks
  the local Graph at the durable handoff boundary. The Intercom profile carries the delegation:
  owned-node authority and fencing for **[Legion (42)](42-legion.md)**, negotiated peer authority
  for the Necropolis. Local resources are released only through their own lease and Orchestrator
  law. The Graph resumes from an admitted, matching result—not from transport silence or an
  arbitrary callback.

### 8. Health and Pulse

Readiness comes from adapter-owned **Stateless Pulses** in the canonical registry (for
OpenAI-compatible connectors, typically `/v1/models`; other connectors define their own probes).
The foundation refreshes an `UNKNOWN` record once during dispatch and otherwise consumes the latest
observed state; it does not pretend to perform a network round trip before every grant. A failed
pulse makes the capability unavailable or non-WARM. State TTL/freshness policy, autonomous repair
signaling, and bounded restart policy remain later Registry/Orchestrator integration; dispatch does
not restart providers.

### 9. Portal Egress Gate (Privatization Enforcement)

Before any intent is dispatched to an external Portal, the volatility of the context payload is evaluated based on the explicit schema-level classification established by the **[Phylactery (06)](06-persistence.md)**.

- **Context Weighting:** As data is extracted from the persistence layer, the SQLAlchemy `info={"privatization_weight": X}` tags attached to the ORM models are read. The entire prompt inherits the highest weight present within the payload.
- **The Egress Policy:**
    - If the weight is below `portal_threshold` (e.g., public documentation): Dispatch to external Portals is permitted.
    - If the weight is between `portal_threshold` and `forbidden_threshold`: An Anonymization Ritual (local scrubbing) is required, and only sanitized output is used for the dispatch.
    - If the weight is at or above `forbidden_threshold` (e.g., internal system passwords, private memory): **Raw portal egress is strictly forbidden.**
- **The Fallback:** If a Portal route is forbidden, routing is forced to a Local Soulstone (e.g., vLLM), or the request is failed closed. This ensures the Dispatcher acts as an unbypassable firewall against prompt injection exfiltration.

### The Gate-and-Censor Doctrine

The Sovereignty Wall carries two distinct authorities that must not be confused. The Dispatcher **gates**: it decides *whether* content may egress at all, applying the privatization thresholds above and failing closed under `LYCHD_SECURE_MODE`. The Weaver's Censor (**[Workflow (28)](28-workflow.md)**) **transforms**: it anonymizes *what* has been permitted to cross and re-identifies results on return.

The two never substitute for one another. The Censor runs strictly downstream of the gate — only on content the gate has already admitted — and it may only narrow: it can never widen what the gate permitted. The gate answers "may this leave?"; the Censor answers "in what form does the permitted content leave?". The Censor's concrete algorithm remains future work; its position in the pipeline is now law.

!!! note "Implemented foundation vs policy horizon"
    The implemented Dispatcher foundation performs canonical family/model/modality/tool filtering,
    warm-first deterministic selection, WARM-only scoped lease grants, and handle-free HTR for
    managed readying candidates. The durable `Intent` schema can retain immutable artifact
    references and derive modality requirements, but the current Bridge/graph remains text-first and
    does not materialize those references into model content. Request-time Sigil visibility, privatization scoring,
    anonymization, economic arbitration, secure-mode Portal filtering, Emissary/A2A routing, and
    autonomous repair remain policy integrations described by this ADR. They must fail closed as
    they land; their doctrine here is not evidence that the current request path enforces them.

## Consequences

!!! success "Positive"
    -   **Hardware Resonance:** The system maximizes the utility of limited local VRAM by intelligently selecting multimodal animators or zipping text-models with Sensory Soulstones.
    -   **Logical Parallelism:** The "Stasis Signal" allows logical parallelism in the Graph (multiple branches waiting for different hardware) without violating the physical seriality of the single GPU.
    -   **Late-Binding Security:** Logic never possesses permanent access to tools; it is granted a temporary capability grant filtered by the user's Sigil at the moment of thought.

!!! failure "Negative"
    -   **Resolution Latency:** The calculation of the optimal capability grant adds a small overhead (10-50ms) to the initiation of every step.
    -   **Registry Complexity:** Maintaining a synchronized map of providers, provider-route policy, and hardware states requires robust handling of extension registration edge-cases.
