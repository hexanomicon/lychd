---
title: 14. LLM Interface
icon: material/robot-outline
---

# :material-robot-outline: 14. Unified LLM Provider Interface

!!! abstract "Context and Problem Statement"
    The LychD agent must be able to leverage a variety of Large Language Models to perform its tasks. These models exist in two fundamentally different forms: self-hosted, containerized inference servers running on local hardware ("Soulstones"), and third-party, cloud-based APIs ("Portals").

    Without a unifying abstraction, the application's core logic would become a brittle and complex series of conditional checks. This would tightly couple the agent's reasoning capabilities to specific implementations, making it difficult to swap models, test new configurations, or extend the system with new providers.

## Decision Drivers

- **Interchangeability:** The system must allow a user to switch between a local Llama 3 model and a remote GPT-4o model purely through configuration, with zero changes to the application's business logic.
- **Simplicity of Abstraction:** The core application should interact with a single, simple interface for all LLM-related tasks, ignorant of the underlying provider's location or type.
- **Standardization:** All communication with any LLM provider must use a single, well-defined API schema to ensure consistency.

## Considered Options

!!! failure "Option 1: Ad-Hoc Provider Logic"
    Implement provider-specific connection and data-handling logic directly within the application's service layer.

    - **Pros:** Initially fast to implement for a single provider.
    - **Cons:** Leads to an unmaintainable, tightly-coupled system that violates the DRY and Single Responsibility principles.

!!! success "Option 2: Unified Interface with a Standardized Protocol"
    Define an abstract interface (the "Animator") that represents a generic LLM provider. Mandate that all providers expose or are adapted to a single, common API protocol.

    - **Pros:** Decouples the application logic from the specific LLM providers. Makes providers hot-swappable via configuration. Greatly simplifies the core codebase.
    - **Cons:** Requires all providers to conform to a single standard.

## Decision Outcome

We will implement a unified "Animator" interface that abstracts the source of intelligence. The core technical decision that enables this abstraction is to **standardize all LLM communication on the OpenAI-compatible API schema.**

This interface will have two primary concrete implementations, reflecting the lore:

1. **Local Providers ("Soulstones"):**
    - These represent self-hosted, containerized inference servers (e.g., vLLM, Llama.cpp).
    - The system will configure them with a local URI (e.g., `http://localhost:8080/v1`).
    - The implementation will also be responsible for managing their lifecycle and resource exclusivity through the generation of `systemd` Quadlet files.

2. **Remote Providers ("Portals"):**
    - These represent third-party cloud APIs (e.g., OpenAI, Anthropic, Groq).
    - The system will configure them with a remote URI and the necessary API key.
    - They are pure configuration and generate no local services.

By mandating that all local servers expose an OpenAI-compatible endpoint, we ensure that the application can treat a local 8-billion parameter model and a remote frontier model as identical, interchangeable components.

### Consequences

!!! success "Positive"
    - **Decoupling:** The application's core logic is radically simplified and completely decoupled from the source of LLM inference.
    - **Flexibility:** The system allows users to easily switch between local and cloud models to balance cost, performance, and privacy.
    - **Extensibility:** Adding new providers is straightforward, requiring only a new configuration file.

!!! failure "Negative"
    - **Ecosystem Requirement:** This decision imposes a strict requirement on the provider ecosystem. Any chosen inference server *must* be compliant with the OpenAI API standard.
