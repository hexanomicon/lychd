---
title: Animator
icon: fontawesome/solid/heart-pulse
---

# :fontawesome-solid-heart-pulse: Animator

> _"The Construct is perfect. The Runes are inscribed. Yet, the machine lies silent in the Crypt. The Animator is the arcane current that strikes the cold iron and commands it to THINK."_

The Animator is the subsystem responsible for **Inference Abstraction**. It is the unified definition of an "Intelligence" within the LychD ecosystem.

In the code, the Animator is the **Base Specification** from which all cognition descends. Whether the mind is a massive local model occupying your GPU's VRAM, or a distant API endpoint in a datacenter, they are all **Animators**. They all obey the same laws of identity and behavior.

## 📜 The Holy Contract

The Vessel does not care _where_ the intelligence comes from—only that it answers the summons. To enforce this, the Animator defines a strict **Contract of Existence**. Any entity that wishes to speak through the Lich must possess a set of **Capabilities**.

!!! abstract "The Universal Tongue"
    The Lich speaks only one language: **Strict, Typed JSON**.

    The Animator standardizes all sources of power into a single interface compliant with the **OpenAI API Standard**. This creates a powerful abstraction:

    - **Capability-Based Routing:** You no longer request a "Model." You request a **[Capability Set](../../adr/08-containers.md)** (e.g., `{"text-generation", "vision"}`). The system identifies the best Animator to fulfill the intent.
    - **Hot-Swappable Souls:** You can banish a local model and summon a Cloud Portal without changing a single line of Agentic logic.
    - **Unified Personality:** Every Animator inherits standard [Generation Parameters](#the-intelligence-profile), ensuring even alien cloud models respect your preferred "Temperature."

## ⚡ The Sources of Power

The Animator draws its energy from two distinct types of sources, inscribed in your **[Codex](../codex.md)**.

### :material-hexagon-slice-6: [Soulstones](./soulstone.md)

#### "The Trapped Spirit."

- **Nature:** Local, Containerized, Stateful.
These are the engines running within the Sepulcher itself. A Soulstone definition is the "Scroll" used by the system to forge a physical **[Systemd Rune](../../adr/08-containers.md)**. They belong to **Covens** and are subject to the **[Orchestrator's](../../adr/21-orchestrator.md)** law of exclusivity.

### :material-weather-hurricane: [Portals](./portal.md)

#### "The Rift to the Void."

- **Nature:** Remote, Ephemeral, Rented.
These are connections to alien intelligences dwelling in the cloud. They generate no Runes and consume no VRAM. They represent "Burst" capacity or frontier reasoning, gated by the **[Sovereignty Wall](../../adr/21-orchestrator.md)**.

## 🧠 The Intelligence Profile

Every Animator possesses a default "Personality" defined in its schema. These parameters govern the stochastic nature of the "Word."

| Parameter | Default | Description |
| :--- | :--- | :--- |
| `max_context` | `4096` | The total window of the entity's working memory. |
| `temperature` | `0.7` | The chaos factor. Higher values breed creativity; lower values breed logic. |
| `top_p` | `0.9` | The nucleus sampling threshold. |
| `max_tokens` | `4096` | The limit of the entity's breath before it must stop speaking. |

## 🫀 The Galvanic Arc

The Animator is the circuit that governs the cycle of Request and Response.

1. **The Impulse:** An Agent requires a capability. It submits an **Intent** to the **[Orchestrator](../../adr/21-orchestrator.md)**.
2. **The Manifestation:** If the Animator is a **Soulstone**, the system ensures its **Coven** is active. If it is a **Portal**, it prepares the Rift.
3. **The Dispatch:** The **[Dispatcher](../../adr/20-dispatcher.md)** transmutes the Animator into a live `pydantic_ai.Model`.
4. **The Stream:** Tokens flow back in real-time to the **[Altar](../../divination/altar.md)**.
