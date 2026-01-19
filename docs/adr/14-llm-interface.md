---
title: 14. LLM Interface
icon: material/robot-outline
---

# :material-robot-outline: 14. Unified LLM Provider Interface ("The Animator")

!!! abstract "Context and Problem Statement"
    The LychD agents must leverage a variety of Large Language Models to perform its tasks. These models exist in two fundamentally different forms: self-hosted, containerized inference servers running on local hardware ("[Soulstones](../sepulcher/animator/soulstone.md)"), and third-party, cloud-based APIs ("[Portals](../sepulcher/animator/portal.md)").

## Decision Drivers

- **Unified Abstraction:** The core application must interact with a single interface ("[The Animator](../sepulcher/animator/index.md)") to prevent brittle coupling between reasoning logic and specific provider implementations.
- **Interchangeability:** The system must allow a user to switch between local and remote models (e.g., Llama 3 vs. GPT-4o) purely through configuration, facilitating rapid testing and extension.
- **Standardization:** All communication with any LLM provider must utilize a single, well-defined API schema (OpenAI Standard).
- **Resource Exclusivity:** The system must strictly manage the lifecycle of local inference servers to prevent GPU VRAM contention (OOM crashes).

## Considered Options

!!! failure "Option 1: Ad-Hoc Provider Logic"
    Implement provider-specific connection libraries (e.g., `openai-python`, `anthropic-python`) directly within the application's service layer.

    - **Pros:** Fast to implement for a single provider.
    - **Cons:** **Unmaintainable.** Leads to a tightly-coupled system where switching providers requires code changes. It violates the DRY principle and makes adding new providers (e.g., `vLLM`) a complex refactoring task.

!!! success "Option 2: Unified Interface with a Standardized Protocol"
    Define an abstract interface, **The Animator**, that represents generic "Intelligence." Mandate that all providers conform to a single API protocol.

    - **Pros:**
        - **Decoupling:** Application logic deals only with abstract "Prompts" and "Responses," not with "OpenAI" or "Anthropic" SDKs.
        - **Hot-Swapping:** Providers become configuration artifacts.
        - **Lifecycle Management:** Allows the system to treat local models as managed system services while treating cloud models as simple endpoints.
    - **Cons:** Requires enforcing the OpenAI API standard across all local and remote providers.

## Decision Outcome

We will implement the **[Animator](../sepulcher/animator/index.md)** subsystem as the unified abstraction for all intelligence. The core technical decision is to **standardize all LLM communication on the OpenAI-compatible API schema.**

The Animator interface supports two distinct implementations:

### 1. Soulstones (Local Containers)

**"The Trapped Spirit."** ([Documentation](../sepulcher/animator/soulstone.md))

- **Definition:** Self-hosted inference servers (e.g., `vLLM`, `Llama.cpp`) running as Podman Quadlets.
- **Lifecycle:** Managed via Systemd. The system generates `.container` files that enforce strict **Resource Exclusivity**.
    - **The Law of Exclusivity:** Utilizing Systemd's `Conflicts=` directive, the system ensures that starting one large model automatically terminates conflicting models to free GPU VRAM.
- **Communication:** Configured with a local URI (e.g., `http://localhost:8080/v1`).

### 2. Portals (Remote APIs)

**"The Rift to the Void."** ([Documentation](../sepulcher/animator/portal.md))

- **Definition:** Connections to third-party cloud APIs (e.g., OpenAI, Anthropic, Groq).
- **Lifecycle:** Pure configuration; no local resources are managed.
- **Communication:** Configured with a remote URI and an API key.

By mandating that all local servers expose an OpenAI-compatible endpoint, the application treats a local 8B model and a remote frontier model as identical, interchangeable components.

### Consequences

!!! success "Positive"
    - **Total Decoupling:** The Agent's reasoning logic is completely isolated from the inference source. Switching from GPT-4 to Llama-3 requires changing one line in a TOML file.
    - **Hardware Safety:** The "Law of Exclusivity" prevents the most common failure mode in local AI (OOM crashes) by leveraging Systemd to manage VRAM contention automatically.
    - **Ecosystem Compatibility:** By standardizing on the OpenAI schema, LychD is instantly compatible with the vast majority of modern inference tools (vLLM, Ollama, Llama.cpp) which all support this standard.

!!! failure "Negative"
    - **The Port Singularity:** Because Systemd holds TCP ports in `TIME_WAIT` after a service stops, switching between local models on the same port (e.g., 8080) can cause temporary binding errors. Unique ports must be assigned to each Soulstone definition.
