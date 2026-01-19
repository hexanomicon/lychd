---
title: 15. Agent Framework
icon: material/brain
---

# :material-brain: 15. Pydantic AI and Graph for Agentic Orchestration

!!! abstract "Context and Problem Statement"
    The implementation of "[Autopoiesis](../divination/transcendence/immortality.md)" demands an agent capable of reliable, multi-step self-modification. A structural foundation is required to bridge the gap between stochastic LLM outputs and rigid software logic, transforming probabilistic generation into deterministic application state.


## Decision Drivers

- **Vendor-Agnostic Orchestration:** The framework must orchestrate LLM interactions without acting as a lock-in mechanism for specific cloud providers. It must treat all models—local or remote—as interchangeable commodities.
- **Transparency over Magic:** Excessive abstraction layers that obscure underlying logic are rejected. The solution must provide granular control over control flow, state management, and prompt construction.
- **Type Safety as Law:** The framework must leverage Python's type system to shift errors from runtime to write-time. The architecture demands a "FastAPI-like" experience where schema validation is intrinsic to the agent's operation.
- **Graph-Based State Management:** Complex, multi-step workflows require a rigorous, Finite State Machine approach to prevent logic from degrading into unstructured chaos.
- **Observability Freedom:** The tool must utilize standard OpenTelemetry for tracing, allowing integration with self-hosted tools (Arize Phoenix) rather than forcing data into proprietary cloud dashboards.

## Considered Options

!!! failure "Option 1: LangChain / CrewAI"
    The prevalent industry standards for agent orchestration.

    -   **Pros:** Massive ecosystem and documentation coverage.
    -   **Cons:** **Abstraction Overload.** These frameworks often function as "abstraction towers" that obscure the underlying prompt engineering. They are heavyweight tools ("sledgehammers") that lack the precision required for this project.

!!! failure "Option 2: Corporate SDKs (OpenAI/Microsoft/Google)"
    Official SDKs provided by major model vendors.

    -   **Pros:** Seamless integration with their respective cloud ecosystems.
    -   **Cons:** **Incentive Misalignment.** These tools are designed to funnel users into specific proprietary ecosystems. Building the core architecture on them creates a dependency on external product strategies that may not align with open-source values.

!!! success "Option 3: PydanticAI + Pydantic Graph"
    A lean, type-centric framework developed by the creators of Pydantic.

    -   **Pros:**
        -   **Native Type Safety:** Built by the team that defined modern Python validation, ensuring robust compile-time checks.
        -   **Graph-Based Orchestration:** `pydantic-graph` provides a rigorous state machine approach for complex logic.
        -   **Model Agnostic:** Supports all providers equally via a unified interface.
        -   **Standardized Tracing:** Built on OpenTelemetry, allowing seamless integration with local observability tools.

## Decision Outcome

**PydanticAI** is adopted as the foundational framework for agentic logic, representing the standard tool for robust interactions.

Additionally, **Pydantic Graph** is mandated for complex, multi-step workflows (specifically the [Autopoiesis](../divination/transcendence/immortality.md) self-evolution logic). This allows the agent's thought process to be modeled as a typed, stateful graph, providing the structural rigour necessary to prevent recursive logic errors during self-modification.

### Consequences

!!! success "Positive"
    - **Codebase Robustness:** The rigorous application of type-checking to LLM outputs significantly reduces runtime hallucinations and structural logic errors.
    - **Data Sovereignty:** By piping PydanticAI's standard OpenTelemetry output to a self-hosted **Arize Phoenix** instance, the project retains full ownership of its observability data.
    - **Ecosystem Independence:** The architecture remains insulated from the volatile product strategies of AI mega-corporations, preserving the "Hermetic" nature of the daemon.

!!! failure "Negative"
    - **Ecosystem Maturity:** PydanticAI is a newer entrant compared to established frameworks like LangChain. The project may encounter edge cases or documentation gaps that require upstream contributions or workarounds.
