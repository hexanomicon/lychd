---
title: 20. Agents
icon: material/robot-outline
---

# :material-robot-outline: 20. Agents: The Cognitive Atom

!!! abstract "Context and Problem Statement"
    To summon a Daemon capable of reason requires a computational primitive that bridges the gap between the probabilistic "Word" of current Large Language Models, future reasoning substrates, and the deterministic "Law" of application code. Standard API calls are unstructured, stateless, and blind to the system's internal state. Furthermore, hardcoding a specific model or toolset into a feature creates a "Brain-Locked" architecture that cannot adapt to the dynamic state of the machine's hardware. A primitive is required that decouples the **Persona** (Identity) and the **Arsenal** (Capabilities) from the underlying intelligence source, while enforcing strict type-safe contracts for all cognitive labor.

## Requirements

- **Type Safety as the Cogito:** Mandatory return of strictly typed Pydantic models rather than raw strings, enforced at the framework boundary to prevent systemic hallucination and ensure data integrity.
- **Late-Binding Intelligence:** Decoupling of the Agent definition from its implementation; the concrete cognitive backend, LLM `Model`, or specialized reasoning capability must be injected at execution time based on hardware availability and the Sovereign's current priorities.
- **Provider-Pair Hydration:** Mandatory support for dynamic toolsets bound by runtime provider identity; each run resolves a `model_provider` and `tool_provider` from the active physical substrate.
- **Contextual Dependency Injection:** Provision of typed, safe access to the system's state (database sessions, validated settings) via a strongly-typed container.
- **Durable Deferred Execution:** Native support for tools that require a "Long Sleep"—suspending the cognitive loop to await human approval or external labor completion without locking hardware resources.
- **Usage & Token Propagation:** Capability to delegate sub-tasks to child agents while sharing and enforcing global usage limits (tokens, requests, and tool calls) to prevent runaway loops.
- **Recursive Fault Tolerance:** Implementation of autonomous self-correction where validation or logic errors are fed back to the model via **`ModelRetry`** for internal reflection and retry.
- **Truthful Non-Completion:** Agent contracts must permit typed outcomes for contradiction, insufficient context, or structurally unresolvable tasks. A truthful stop is preferable to a polished false manifestation.
- **Multi-Modal Fluency:** The capability to handle and return non-textual artifacts (images, binary content, audio) as first-class components of the reasoning result.

## Considered Options

!!! failure "Option 1: LangChain / LlamaIndex"
    Relying on established "chains" or "orchestration" frameworks.

    - **Cons:** **Architectural Bloat and Type Blindness.** These frameworks often rely on untyped dictionaries and "Prompt Templates," violating the requirement for strict Pydantic validation. Their heavy dependency trees introduce "Framework Lock-in" and conflict with the goal of a lean, sovereign kernel.

!!! failure "Option 2: Agno (formerly Phidata) / CrewAI"
    Utilizing opinionated "Agentic Roles" or "Assistant" frameworks.

    - **Cons:** **Insufficient Substrate Control.** These systems are designed for cloud-first environments and lack the low-level hooks required for local hardware resource management and "Long Sleep" rehydration.

!!! success "Option 3: Pydantic AI"
    An agent framework built on Pydantic and Python generics.

    - **Pros:**
        - **Type Sovereignty:** Enforces strict data contracts for input dependencies and output results using Python type hints and generics.
        - **Stateless Primitives:** Designed for global agent definitions that are hydrated into runs, matching the "Late-Binding" requirement perfectly.
        - **Native Framework Support:** Provides first-class support for toolsets, deferred execution, and multi-agent delegation patterns.

## Decision Outcome

**Pydantic AI** is adopted as the atomic primitive for all reasoning. An `Agent` in LychD is defined as a static **Specification Class** that is hydrated into a living entity by the system's current state.

This is a runtime decision, not merely an implementation detail. Pre-v1 LychD agents are **model/provider agnostic**, but they are not **agent-framework agnostic** inside the Vessel. Pydantic AI supplies the blessed execution grammar for typed outputs, `RunContext`, toolsets, deferred execution, retries, usage propagation, and graph-friendly composition. Other agent frameworks may still participate by being wrapped as external-service Animators or A2A Emissaries, or by being assimilated into native Pydantic AI agents. They are not loaded as independent in-process agent runtimes unless a future versioned `lychd.extensions.api` explicitly defines that product surface.

This model/provider agnosticism is also a substrate horizon. LychD uses next-token LLMs as the current practical substrate for language, tool calls, and broad candidate generation, but the architecture does not declare autoregressive text generation to be the final form of machine reasoning. Future Animators may expose energy-based scorers, constraint optimizers, latent world-model rollouts, proof-search engines, or hybrid reasoning runtimes as typed tools, model-like grants, or graph steps. Such engines may compact inner loops that are explicit today, such as retry, branch scoring, repair, and heuristic judging. They do not replace the Graph, Dispatcher, Orchestrator, Phylactery, Mirror, HitL, or Vessel policy boundaries that make reasoning durable, governable, and sovereign.

An Agent is the execution atom of cognition, the fundamental unit of labor for both **Manas** (speculation) and **Buddhi** (creation). In the cognitive map of the **[Lich](../sepulcher/lich.md)**, Manas (*√man* — to oscillate, to receive) is the generating engine: it produces candidate responses, explores option-space, and never settles on its own. Buddhi (*√budh* — to discern, to wake) is the discriminative blade that cuts to one. An Agent spans both modes: its inference loop is Manas at work; its typed output contract is Buddhi's determination made concrete in a Pydantic model. It is not the full Persona identity and not the final authority of promotion. It acts, but it is not the "doer" — Identity continuity (the **Ahaṃkāra**) is provided by **[Mirror (ADR 32)](./32-identity.md)**; high-stakes manifestation remains governed by **[HitL (ADR 25)](./25-hitl.md)** and Vessel-side policy.

!!! note "Mechanical Cognitive Postures"
    Agent specialization may be expressed as mechanically separated postures, not merely as roleplay. An expander-only Agent opens candidate space and must not rank its own ideas. A reviewer-only Agent evaluates, groups related paths, flags hazards, and must not invent new branches unless explicitly routed into repair. A repair-only Agent receives measured failure traces and proposes corrections. A red-team Agent searches for breach paths and plausible-but-wrong proposals. These postures are enforced through separate runs, prompts, output schemas, tool grants, and `ModelSettings`, so Shadow and Graph can compose Manas and Buddhi without mixing evaluation into the expansion context.

    Each posture treats honest dead-end recognition as a valid cognitive act. If the field contains contradiction, missing variables, or impossible constraints, the Agent must name the bottleneck within its typed result instead of satisfying pressure by fabricating certainty. This prevents Manas from hardening Viparyaya into a confident answer merely because the prompt demands closure.

    This is not a relaxation of rigor. It is the typed expression of the Pramāṇa boundary: when direct measurement, sound inference, or trusted testimony is absent, the Agent preserves the state as Vikalpa or returns a bottleneck instead of laundering uncertainty into Pramāṇa-shaped prose. The contract gives uncertainty a valid output channel so status pressure cannot become an implicit success criterion.

!!! note "Stratification of Selves"
    Three identity-adjacent notions layer rather than compete. A **Posture** is a per-run mechanical configuration—output schema, tool grant, `ModelSettings`, and prompt frame. A **Lens** (**[Simulation (ADR 31)](./31-simulation.md)**) is a Posture template employed for expansion isolation in the Shadow. A **Persona** (**[Mirror (ADR 32)](./32-identity.md)**) is a durable identity that *wears* Postures across runs. Persona chooses; Posture constrains; Lens diversifies.

!!! note "The identity triad: who / voice / what-it-can-do"
    Three orthogonal axes name an acting agent and must not be conflated. The **Sigil** is *who* (identity and permission scope, **[Security (09)](./09-security.md)**). The **Persona** is *voice* (durable style, **[Mirror (ADR 32)](./32-identity.md)**). The **Kit** is *what-it-can-do* — the packed Arsenal (instructions + tools + model choice) an agent **equips** to become a **Specialist**. `Kit` and its registry the `Shed` (formerly *Craft* / *Grimoire*) are the locked terms for the capability-packing model; it is roadmap (Wave 5) and not yet built. The running instance is always the Specialist; the Kit is the packed form.

### 1. Late-Binding Intelligence

To prevent "Brain-Locking," the Agent's definition is decoupled from its implementation. The `Model` and `FunctionToolset` are resources that must be requested from the system's sovereign controller at runtime.

- **Dynamic Arsenal:** An Agent’s available tools are not static; they are hydrated from the resolved `tool_provider` for that run.
- **Model Agnosticism:** The same Pydantic AI Agent logic can run on local quantized models, frontier cloud models, or specialized cognitive capabilities wrapped by Animators, as selected by the dispatcher at the moment of invocation.
- **Framework Boundary:** This model/provider agnosticism does not imply arbitrary in-process agent-framework compatibility. Foreign frameworks must cross a protocol boundary or be assimilated into the native runtime.
- **Provider Pair Contract:** Every run binds an explicit `model_provider` plus `tool_provider`; no agent hardcodes either side.
- **Concrete Binding:** For OpenAI-compatible runtimes, binding is explicit through the resolved connector endpoint (`base_url`) plus the selected model id (for example `OpenAIProvider(base_url=...)` + `OpenAIChatModel(..., provider=...)`).
- **Archive as Tool:** Memory recall is granted as a late-bound tool (`query_archive`/`recall_past_karma`) only when the required embedding path is available; agent specifications never hardcode memory wiring.

!!! note "Cognitive Primitive Selection"
    The Agent map should route labor through the smallest sufficient primitive. A deterministic, compact action is a Tool. A demand-loaded procedure or policy bundle is a Skill-like instruction surface. An isolated reasoning context with its own typed result is a child Agent. Unsafe or bulk deterministic execution is a Tomb/Worker payload. All four remain subordinate to Dispatcher grants, Graph topology, HitL policy, and typed output contracts.

    The selection question is also a context-pressure question. Large data dumps belong behind code execution or Worker payloads, not repeated tool returns. "Always do X" guidance belongs in a demand-loaded instruction surface, not every system prompt. A child Agent is justified by isolated context, independent exploration, or a typed handoff; a subagent that only returns one scalar is usually a Tool in disguise.

```python
# Example of a stateless Specification Class
# Model and Tools are NOT defined here.
coder_agent = Agent[LychDDeps, CodeDiff | Explanation](
    system_prompt="Role: Senior Python Engineer..."
)
```

### 2. Dependency Injection (`RunContext`)

To allow the probabilistic mind to interact with the deterministic body, the system utilizes Pydantic AI’s **`RunContext`**.

- **The Bridge:** Tools and prompts receive a strictly typed `RunContext[LychDDeps]`, providing safe access to the **[Phylactery (06)](06-persistence.md)** and system settings without exposing global mutable state.
- **State Preservation:** This allows the Agent to query the database, consult internal archives, or trigger background labor while remaining isolated within a validated execution context.

#### The LychDDeps Covenant

`LychDDeps` is the keystone dependency contract carried by every `RunContext[LychDDeps]`. It holds, as typed fields (not code):

- the active **Sigil** and its permission scopes;
- the **`CapabilityGrant`** in force for the step (**[Dispatcher (ADR 22)](./22-dispatcher.md)**);
- a **Dispatcher handle** for Modality-Zip and deferred sensory tools;
- a scoped **Phylactery session**, Archive-gated per **[IAM (ADR 38)](./38-iam.md)**;
- the **Context Orchestrator** handle (**[Context (ADR 21)](./21-context.md)**);
- the run and step **correlation IDs** (**[Observability (ADR 29)](./29-observability.md)** Trace Correlation Contract).

`LychDDeps` carries **no raw secrets**. Provider and API credentials remain in the control plane and are resolved outside the cognitive context (**[Security (ADR 09)](./09-security.md)**); a Sigil grants authority, it does not ferry the secret itself.

### 3. Intelligence Tuning (`ModelSettings`)

Every resolution provides a dynamic **`ModelSettings`** object. This allows the system to enforce strict constraints (e.g., `temperature`, `max_tokens`, `top_p`) at the moment of invocation, ensuring the Agent adheres to the "Physics" defined in the **[Codex (12)](12-configuration.md)**.

### 4. Advanced Tool Artifacts (`ToolReturn`)

Tools in LychD provide rich feedback beyond simple strings.

- **Metadata (Artifacts):** Tools can return **`ToolReturn`** objects, separating the `return_value` (sent to the LLM) from the `metadata` (persisted as a permanent artifact for the user).
- **Action Rejection Evidence:** When a tool rejects a call, the validator owns the local truth of why. Rejections should carry a compact failure class such as `precondition_miss`, `invalid_arguments`, `policy_block`, or `dependency_unavailable`, plus relevant `required_state`, `observed_state`, and retryability metadata. The Agent may receive a concise repair hint, but the persistent artifact records the boundary fact so later diagnosis does not confuse model blindness with an ambiguous or incomplete state surface.
- **Multi-Modal Content:** Using **`BinaryContent`** (images/PDFs), tools can provide visual context to models supporting vision, allowing for "Observation" rituals where the model describes what the tool "saw."

### 5. Deferred Execution (The Long Sleep)

The architecture adopts Pydantic AI's native **Deferred Tools** mechanism to handle high-latency or high-risk operations:

- **`ApprovalRequired`:** Tools marked with `requires_approval=True` (or raising the exception) trigger a "Stasis" event. The Agent run ends with a **`DeferredToolRequests`** object containing a **`ToolCallPart`** for human review.
- **`CallDeferred`:** Used by tools that delegate heavy labor to background workers. The mind hibernates by committing a deferred request/result boundary into the **[Phylactery (06)](06-persistence.md)**.
- **Rehydration:** Once approvals or results are received as **`DeferredToolResults`**, the mind is re-entered from the persisted boundary. Volatile frames may be gone; committed message history, typed state, and deferred tool markers provide the replay surface.

### 6. Autonomous Error Correction (`ModelRetry`)

The system leverages built-in **`ModelRetry`** mechanisms. If a tool execution fails due to a logical error or Pydantic validation failure, the exception is fed back into the context as a system message. This forces the Agent to correct its own thought process internally, presenting the Magus only with a "Verified Truth."

`ModelRetry` is bounded correction, not punitive recursion. When repeated retries expose a missing premise, contradictory instruction, or impossible schema, the run should converge to a typed bottleneck state and hand that state to Graph, Shadow, or HitL. A loop that keeps demanding a completed artifact after the task has become structurally false is treated as Viparyaya pressure, not perseverance.

Tool-boundary rejection classes guide this convergence. A repeated `precondition_miss` indicates that the visible state, hidden validator state, or action affordance contract is misaligned; the repair target may be the state schema rather than the model prompt. A repeated `invalid_arguments` may justify `ModelRetry`; a repeated `policy_block` should usually become a typed bottleneck instead of another attempt.

### 7. Multi-Agent Delegation & Usage Limits

Complex behaviors are achieved by composing Agents in a hierarchy:

- **Agent Delegation:** A parent Agent calls a child Agent as a tool. The parent passes `ctx.usage` to the child, ensuring token limits and **`UsageLimits`** are enforced globally across the entire chain.
- **Programmatic Hand-off:** One agent completes a task and returns a structured object, which the application logic then passes to a different specialized agent for the next step of the ritual.
- **Deep Agents:** For self-directed system evolution, agents are granted specialized toolsets for file operations and sandboxed code execution, managed via isolated speculative environments.

### 8. Semantic Senses (Embedders as Infrastructure)

The Agentic Arsenal includes the Pydantic AI **`Embedder`** class. Unlike text generation, embedding is treated as a specialized hardware-intensive provider route.

- **Container Dependency:** An embedder typically requires its own container body defined as a Quadlet within a specific operational state and surfaced as a provider.
- **Orchestrated Swapping:** When an Agent invokes a tool requiring `embed_query()` or `embed_documents()`, the dispatcher must ensure the required hardware is active. If a resource conflict occurs, the intent is queued until the GPU is liberated.

## Consequences

!!! success "Positive"
    - **Hardware Resonance:** The Agent's provider routes intelligently adapt to the current form of the machine, maximizing the utility of limited local VRAM.
    - **Mathematical Precision:** Application logic never interacts with "hallucinated strings"; it receives only validated, typed objects.
    - **Contextual Continuity:** By integrating with persistence protocols, committed agentic progress can span days and survive system reboots.

!!! failure "Negative"
    - **Cognitive Latency:** Swapping toolsets based on hardware availability can introduce delays (30-60s) during state transitions.
    - **Prompt Pressure:** As dynamic arsenals grow, the system prompt consumes a larger portion of the context window, requiring aggressive optimization of the working memory.
