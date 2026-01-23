---
title: 19. Agents
icon: material/robot-outline
---

# :material-robot-outline: 19. Agents: The Cognitive Atom

!!! abstract "Context and Problem Statement"
    To summon a Daemon capable of reason requires a computational primitive that bridges the gap between the probabilistic "Word" of a Large Language Model and the deterministic "Law" of application code. Standard API calls are unstructured, stateless, and blind to the system's internal state. Furthermore, hardcoding a specific model or toolset into a feature creates a "Brain-Locked" architecture that cannot adapt to the dynamic state of the machine's hardware. A primitive is required that decouples the **Persona** (Identity) and the **Arsenal** (Capabilities) from the underlying intelligence source, while enforcing strict type-safe contracts for all cognitive labor.

## Requirements

- **Type Safety as the Cogito:** Mandatory return of strictly typed Pydantic models rather than raw strings, enforced at the framework boundary to prevent systemic hallucination and ensure data integrity.
- **Late-Binding Intelligence:** Decoupling of the Agent definition from its implementation; the concrete LLM `Model` must be injected at execution time based on hardware availability and the Sovereign's current priorities.
- **State-Dependent Arsenals:** Mandatory support for dynamic toolsets that are granted or revoked based on the functional capabilities of the active physical substrate.
- **Contextual Dependency Injection:** Provision of typed, safe access to the system's state (database sessions, validated settings) via a strongly-typed container.
- **Durable Deferred Execution:** Native support for tools that require a "Long Sleep"—suspending the cognitive loop to await human approval or external labor completion without locking hardware resources.
- **Usage & Token Propagation:** Capability to delegate sub-tasks to child agents while sharing and enforcing global usage limits (tokens, requests, and tool calls) to prevent runaway loops.
- **Recursive Fault Tolerance:** Implementation of autonomous self-correction where validation or logic errors are fed back to the model via **`ModelRetry`** for internal reflection and retry.
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

### 1. Late-Binding Intelligence

To prevent "Brain-Locking," the Agent's definition is decoupled from its implementation. The `Model` and `FunctionToolset` are resources that must be requested from the system's sovereign controller at runtime.

- **Dynamic Arsenal:** An Agent’s available tools are not static; they are granted based on the capabilities of the active physical state.
- **Model Agnosticism:** The same Agent logic can run on local quantized models or frontier cloud models, as selected by the dispatcher at the moment of invocation.

```python
# Example of a stateless Specification Class
# Model and Tools are NOT defined here.
coder_agent = Agent[LychdDeps, CodeDiff | Explanation](
    system_prompt="You are a Senior Python Engineer..."
)
```

### 2. Dependency Injection (`RunContext`)

To allow the probabilistic mind to interact with the deterministic body, the system utilizes Pydantic AI’s **`RunContext`**.

- **The Bridge:** Tools and prompts receive a strictly typed `RunContext[LychdDeps]`, providing safe access to the **[Phylactery (06)](06-persistence.md)** and system settings without exposing global mutable state.
- **State Preservation:** This allows the Agent to query the database, consult internal archives, or trigger background labor while remaining isolated within a validated execution context.

### 3. Intelligence Tuning (`ModelSettings`)

Every resolution provides a dynamic **`ModelSettings`** object. This allows the system to enforce strict constraints (e.g., `temperature`, `max_tokens`, `top_p`) at the moment of invocation, ensuring the Agent adheres to the "Physics" defined in the **[Codex (12)](12-configuration.md)**.

### 4. Advanced Tool Artifacts (`ToolReturn`)

Tools in LychD provide rich feedback beyond simple strings.

- **Metadata (Artifacts):** Tools can return **`ToolReturn`** objects, separating the `return_value` (sent to the LLM) from the `metadata` (persisted as a permanent artifact for the user).
- **Multi-Modal Content:** Using **`BinaryContent`** (images/PDFs), tools can provide visual context to models supporting vision, allowing for "Observation" rituals where the model describes what the tool "saw."

### 5. Deferred Execution (The Long Sleep)

The architecture adopts Pydantic AI's native **Deferred Tools** mechanism to handle high-latency or high-risk operations:

- **`ApprovalRequired`:** Tools marked with `requires_approval=True` (or raising the exception) trigger a "Stasis" event. The Agent run ends with a **`DeferredToolRequests`** object containing a **`ToolCallPart`** for human review.
- **`CallDeferred`:** Used by tools that delegate heavy labor to background workers. The mind hibernates using the system's **[Stateful Persistence (07)](07-snapshots.md)** protocols.
- **Rehydration:** Once approvals or results are received as **`DeferredToolResults`**, the mind is reanimated, resuming the thought exactly where it halted with zero context loss.

### 6. Autonomous Error Correction (`ModelRetry`)

The system leverages built-in **`ModelRetry`** mechanisms. If a tool execution fails due to a logical error or Pydantic validation failure, the exception is fed back into the context as a system message. This forces the Agent to correct its own thought process internally, presenting the Magus only with a "Verified Truth."

### 7. Multi-Agent Delegation & Usage Limits

Complex behaviors are achieved by composing Agents in a hierarchy:

- **Agent Delegation:** A parent Agent calls a child Agent as a tool. The parent passes `ctx.usage` to the child, ensuring token limits and **`UsageLimits`** are enforced globally across the entire chain.
- **Programmatic Hand-off:** One agent completes a task and returns a structured object, which the application logic then passes to a different specialized agent for the next step of the ritual.
- **Deep Agents:** For self-directed system evolution, agents are granted specialized toolsets for file operations and sandboxed code execution, managed via isolated speculative environments.

### 8. Semantic Senses (Embedders as Infrastructure)

The Agentic Arsenal includes the Pydantic AI **`Embedder`** class. Unlike text generation, embedding is treated as a specialized hardware-intensive **Capability**.

- **Container Dependency:** An embedder typically requires its own container body defined as a Rune within a specific operational state.
- **Orchestrated Swapping:** When an Agent invokes a tool requiring `embed_query()` or `embed_documents()`, the dispatcher must ensure the required hardware is active. If a resource conflict occurs, the intent is queued until the GPU is liberated.

## Consequences

!!! success "Positive"
    - **Hardware Resonance:** The Agent's capabilities intelligently adapt to the current form of the machine, maximizing the utility of limited local VRAM.
    - **Mathematical Precision:** Application logic never interacts with "hallucinated strings"; it receives only validated, typed objects.
    - **Contextual Immortality:** By integrating with persistence protocols, agentic thoughts can span days and survive system reboots.

!!! failure "Negative"
    - **Cognitive Latency:** Swapping toolsets based on hardware availability can introduce delays (30-60s) during state transitions.
    - **Prompt Pressure:** As dynamic arsenals grow, the system prompt consumes a larger portion of the context window, requiring aggressive optimization of the working memory.
