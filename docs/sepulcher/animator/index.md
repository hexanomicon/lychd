---
title: Animator
icon: fontawesome/solid/heart-pulse
---

# :fontawesome-solid-heart-pulse: Animator

> _"The Construct is perfect. The Scrolls are inscribed. Yet, the machine lies silent in the Crypt. The Animator is the arcane current that strikes the cold iron and commands it to THINK."_

The Animator is the subsystem responsible for **Inference Abstraction**. It is the unified runtime definition of an "Intelligence" within the LychD ecosystem.

An Animator is a **live, addressable service** — not an abstract concept. Every Animator is one of two things:

- **[Soulstone](./soulstone.md)**: A local containerized inference engine running on the Magus's own iron (llama.cpp, vLLM, SGLang, Whisper, Bark…).
- **[Portal](./portal.md)**: A live connection to a remote API in the cloud (OpenAI, Anthropic, Google…).

Both satisfy the same **Animator Binding Contract**, exposing callable model and tool surfaces to the **[Dispatcher](../../adr/22-dispatcher.md)**. Whether the mind lives on your GPU or in a distant datacenter, it obeys the same laws of identity and behavior.

## 📜 The Holy Contract

The Vessel does not care _where_ the intelligence comes from—only that it answers the summons. To enforce this, the Animator defines a strict **Contract of Existence**. Any entity that wishes to speak through the Lich must possess a set of **Capabilities**.

!!! abstract "The Universal Tongue"
    The Lich speaks only one language: **Strict, Typed JSON**.

    The Animator standardizes all sources of power into a single typed runtime contract. In the current core, many connectors expose an **OpenAI-compatible surface** through Pydantic AI, while preserving room for provider-specific connectors later. This creates a powerful abstraction:

    - **Capability-Based Routing:** You request an intent (reasoning, vision, tools) and the system resolves a suitable Animator from the active substrate.
    - **Hot-Swappable Souls:** You can banish a local model and summon a Cloud Portal without changing a single line of Agentic logic.
    - **Unified Personality:** Every Animator inherits standard [Generation Parameters](#the-intelligence-profile), ensuring even alien cloud models respect your preferred "Temperature."

## ⚡ The Sources of Power

The Animator draws its energy from two distinct types of sources, inscribed in your **[Codex](../codex.md)**.

### :material-hexagon-slice-6: [Soulstones](./soulstone.md)

#### "The Trapped Spirit."

- **Nature:** Local, Containerized, Stateful.
These are the engines running within the Sepulcher itself. A Soulstone is a **rune config** in the Codex that the system transmutes into physical Quadlet manifests and services (see **[Containers (08)](../../adr/08-containers.md)**). They belong to **Covens** and are subject to the **[Orchestrator's](../../adr/23-orchestrator.md)** law of exclusivity.
- **Exclusive vs Shared:** A Soulstone may be declared `exclusive: true` (the default) or `exclusive: false` in the Codex. An **exclusive** Soulstone is fully owned by the Orchestrator — it may kill, swap, restart, and reconfigure it freely. A **shared** Soulstone is one the Magus also exposes to other services outside LychD (e.g., a vLLM instance serving both the Lich and a separate application). The Orchestrator treats shared Soulstones as **read-only**: it can route requests to them but cannot manage their lifecycle. This prevents the Orchestrator from killing a container that something else depends on.

### :material-weather-hurricane: [Portals](./portal.md)

#### "The Rift to the Void."

- **Nature:** Remote, Ephemeral, Rented.
These are connections to alien intelligences dwelling in the cloud. They generate no Quadlet manifests and consume no local VRAM. They represent "Burst" capacity or frontier reasoning, gated by the **[Sovereignty Wall](../../adr/23-orchestrator.md)**.

## 🧠 The Intelligence Profile

Every Animator possesses a default "Personality" defined in its schema. These parameters govern the stochastic nature of the "Word."

| Parameter | Default | Description |
| :--- | :--- | :--- |
| `max_context` | `4096` | The total window of the entity's working memory. |
| `temperature` | `0.7` | The chaos factor. Higher values breed creativity; lower values breed logic. |
| `top_p` | `0.9` | The nucleus sampling threshold. |
| `max_tokens` | `4096` | The limit of the entity's breath before it must stop speaking. |

## ⚡ Capabilities

Every Animator declares which **Capabilities** it can provide. A `Capability` is a typed class registered via `ExtensionContext`. The **[Dispatcher](../../adr/22-dispatcher.md)** queries active capabilities to resolve which Animator satisfies an Agent's request.

Capabilities carry two state flags (defined in **[Containers (08)](../../adr/08-containers.md)**):

- **`is_static`**: Available immediately once the container is running (baked into the image).
- **`is_active`**: Currently ready for requests (model loaded and warm).

The canonical capability types recognized by the Dispatcher:

| Capability | Description | Example Providers |
| :--- | :--- | :--- |
| `ChatCompletion` | Text reasoning / generation (OpenAI-compatible `/v1/chat/completions`) | llama.cpp, vLLM, SGLang, OpenAI, Anthropic |
| `VisionCompletion` | Multimodal — image + text input | llava (llama.cpp), vLLM vision, OpenAI GPT-4o |
| `Embedding` | Dense vector embeddings (`/v1/embeddings`) | llama.cpp, vLLM, OpenAI ada-002 |
| `STT` | Speech-to-Text — audio → transcript | Whisper (local), OpenAI Whisper API |
| `TTS` | Text-to-Speech — text → audio | Bark, Coqui, OpenAI TTS API |
| `VoiceCompletion` | Real-time voice pipeline (Realtime API pattern) | OpenAI Realtime, future local equivalents |
| `ToolExecution` | Sandboxed code / tool execution (Shadow Realm) | nono-wrapped containers |

Not all Animators offer all capabilities. A single llama.cpp Soulstone in router mode can expose different capabilities depending on which model is currently loaded — capabilities flip `is_active` as models hot-swap, without restarting the container. The Orchestrator manages these transitions.

## 🫀 The Galvanic Arc

The Animator is the circuit that governs the cycle of Request and Response.

1. **The Impulse:** An Agent requires a capability. It submits an **Intent** to the **[Orchestrator](../../adr/23-orchestrator.md)**.
2. **The Manifestation:** If the Animator is a **Soulstone**, the system ensures its **Coven** is active. If it is a **Portal**, it prepares the Rift.
3. **The Resolution:** The **[Dispatcher](../../adr/22-dispatcher.md)** resolves a runtime animator/connector (with policy still allowed to reason in provider-route terms).
4. **The Binding:** The runtime binder hydrates a Pydantic AI model and toolsets from the selected animator connector (for many current runtimes, via an OpenAI-compatible `base_url` and a selected/default model id).
5. **The Stream:** Tokens flow back in real-time to the **[Altar](../../divination/altar.md)**.

## 🧭 Runtime Blueprint

For credential flow and runtime-specific configuration, see **[Portal](./portal.md)** and **[Soulstone](./soulstone.md)**.
