---
title: 15. Agent Framework
icon: material/brain
---

# :material-brain: 15. Pydantic AI and Graph for Agentic Orchestration

!!! abstract "Context and Problem Statement"
    The core of LychD is an autonomous agent capable of reasoning, coding, and self-evolution. To build this, we require a framework to orchestrate LLM interactions, manage state, and define complex workflows. The current landscape is dominated by corporate walled gardens (OpenAI SDKs) or bloated "magic" frameworks (LangChain) that obscure logic.

    We need a framework that respects our intelligence. We need a tool that is type-safe, transparent, model-agnostic, and built by champions of the open-source community, not by corporations that view developers as resources to be mined.

## Decision Drivers

- **Type Safety as Law:** The framework must leverage Python's type system to move errors from runtime to write-time. "If it compiles, it works."
- **Transparency over Magic:** We reject "black box" agents. We require granular control over the control flow, state, and prompt construction.
- **Independence:** The framework must not act as a vendor lock-in mechanism. It must treat all models—local or remote—as interchangeable commodities.
- **Simplicity:** The framework should not attempt to solve problems outside its scope (like memory or vector storage).

## Considered Options

!!! failure "Option 1: LangChain / CrewAI"
    The popular choices.

    - **Pros:** Massive ecosystem.
    - **Cons:** They are "abstraction towers" that obscure what is actually happening. They are sledgehammers where we need precision instruments.

!!! failure "Option 2: Corporate SDKs (OpenAI/Microsoft/Google)"
    SDKs from major cloud providers.

    - **Pros:** Slick integration with their respective clouds.
    - **Cons:** We do not trust these entities to maintain these tools for the public good. Their primary incentive is to funnel users into their ecosystems. We will not build our castle on rented land.

!!! success "Option 3: PydanticAI + Pydantic Graph"
    A new, lean framework from the creators of Pydantic.

    - **Pros:**
        - **Native Type Safety:** Built by the team that defined modern Python validation. It brings the ergonomic "FastAPI feeling" to agent development.
        - **Graph-Based Orchestration:** `pydantic-graph` provides a rigorous, Finite State Machine approach to complex workflows.
        - **Observability Freedom:** Built on standard OpenTelemetry. This allows us to easily redirect all tracing data to our self-hosted **Arize Phoenix** instance, maintaining our independence.
        - **Model Agnostic:** It supports every provider equally.

## Decision Outcome

We will use **PydanticAI** as the foundation for our agentic logic. It represents the "Hammer"—a reliable, transparent tool for building robust agents.

For complex, multi-step workflows (such as the Autopoiesis logic), we will use **Pydantic Graph**. This allows us to model the agent's thought process as a typed, stateful graph, providing the precision of a "Nail Gun" where standard control flow would degrade into chaos.

By choosing PydanticAI, we align ourselves with the true champions of Python open source—builders who care about developer experience and correctness.

### Consequences

!!! success "Positive"
    - **Robustness:** The codebase will be rigorously type-checked, reducing runtime hallucinations and logic errors.
    - **Sovereignty:** We retain full ownership of our observability data by piping PydanticAI's OpenTelemetry output to Arize Phoenix.
    - **Independence:** We are insulated from the whims of AI mega-corporations and their volatile product strategies.

!!! failure "Negative"
    - **Maturity:** PydanticAI is newer than established players like LangChain. We will likely encounter edge cases that require us to be pioneers in the ecosystem. This is an accepted cost of leadership.
