---
title: Animator
icon: fontawesome/solid/heart-pulse
---

# :fontawesome-solid-heart-pulse: Animator

> _"The Construct is perfect. The Runes are inscribed. Yet, the machine lies silent in the Crypt. The Animator is the arcane current that strikes the cold iron and commands it to THINK."_

The Animator is the subsystem responsible for **Inference Abstraction**. It is the unified definition of an "Intelligence" within the LychD ecosystem.

In the code, the Animator is the **Base Class** from which all cognition descends. Whether the mind is a massive 70B parameter model running on your local GPU, or a distant API endpoint in a datacenter, they are all **Animators**. They all obey the same laws.

## 📜 The Holy Contract

The Vessel does not care _where_ the intelligence comes from—only that it answers the summons. To enforce this, the Animator defines a strict **Contract of Existence**. Any entity that wishes to speak through the Lich must possess:

1. **Identity (Name):** A unique designation in the system (e.g., `hermes`, `logic-alpha`).
2. **Manifestation (URI):** A valid endpoint where the electrical signals are received (e.g., `http://localhost:8080/v1` or `https://api.openai.com/v1`).
3. **The Secret (API Key):** An optional key to unlock the gate.

!!! abstract "The Universal Tongue"
    The Lich speaks only one language: **Strict, Typed JSON**.

    The Animator standardizes all sources of power into a single interface compliant with the **OpenAI API Standard**. This creates a powerful abstraction:

    - **Hot-Swappable Souls:** You can banish a local Llama-3 model and summon a GPT-4 Portal without changing a single line of the application code.
    - **Unified Personality:** Every Animator inherits standard [Generation Parameters](#the-intelligence-profile), ensuring that even cloud models respect your preferred "Temperature" and "Creativity."

## ⚡ The Sources of Power

The Animator draws its energy from two distinct types of sources, inscribed in your **[Codex](../codex.md)**.

### :material-hexagon-slice-6: [Soulstones](./soulstone.md)

#### "The Trapped Spirit."

- **Location:** `~/.config/lychd/soulstones/*.toml`
- **Nature:** Local, Containerized, Owned.

These are the engines running within the Sepulcher itself, bound to your physical hardware (GPUs). They are defined as Quadlet containers. The Animator supports any OpenAI-compatible runner, but favors:

- **vLLM:** For high-throughput serving.
- **SGLang:** For structured decoding speed.
- **ExLlamaV2:** For maximum tokens-per-second on consumer cards.
- **Llama.cpp:** For CPU offloading and widespread compatibility.

### :material-weather-hurricane: [Portals](./portal.md)

#### "The Rift to the Void."

- **Location:** `~/.config/lychd/portals/*.toml`
- **Nature:** Remote, Ephemeral, Rented.

These are connections to alien intelligences dwelling in the cloud (OpenAI, Anthropic, Groq). They do not run on your hardware; the Animator merely opens a gateway to send the prompt and receive the completion.

## 🧠 The Intelligence Profile

Every Animator possesses a default "Personality" defined in its schema. If a user does not specify parameters during a request, the Animator enforces its own nature.

| Parameter | Default | Description |
| :--- | :--- | :--- |
| `temperature` | `0.7` | The chaos factor. Higher values breed creativity; lower values breed logic. |
| `top_p` | `0.9` | The nucleus sampling threshold. |
| `max_tokens` | `4096` | The limit of the entity's breath before it must stop speaking. |

## 🫀 The Galvanic Arc

The Animator is not a biological organ; it is a **circuit**. It governs the cycle of Request and Response.

1. **The Impulse:** The Vessel sends a structured Pydantic object (the Prompt) to the Animator.
2. **The Routing:** The Animator resolves the target URI. If it is a **Soulstone**, it verifies the local port is active. If it is a **Portal**, it injects the API Key.
3. **The Stream:** The tokens flow back in real-time via Server-Sent Events (SSE).

!!! tip "The Rite of the Swap"
    Because the Animator relies on standard protocols, your "Logic Model" can be swapped instantaneously. If `soulstone-flash` crashes, the system can be configured to failover to `portal-gpt4` automatically (Feature in Roadmap).
