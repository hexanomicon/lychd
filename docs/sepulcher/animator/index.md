---
title: Animator
icon: fontawesome/solid/heart-pulse
---

# :fontawesome-solid-heart-pulse: Animator

> _"The Construct is perfect. The Runes are inscribed. The Phylactery waits. Yet, the machine lies silent in the Crypt. The Animator is the arcane current that strikes the cold iron and commands it to CALCULATE."_

The Animator is the subsystem responsible for **Inference Abstraction**. It is the bridge between the [Vessel](../vessel/index.md)'s logic and the raw, chaotic intelligence that powers it. It manages the flow of tokens, the context windows, and the generation parameters.

In the architecture of LychD, the Vessel does not care _where_ the intelligence comes from—only that it answers the summons.

!!! abstract "The Universal Tongue (OpenAI Compatibility)"
    The Lich speaks only one language: **Strict, Typed JSON**.

    The Animator standardizes all sources of power—whether a local GPU cluster or a distant cloud server—into a single, unified interface compliant with the **OpenAI API Standard**. This creates a powerful abstraction:

    *   **Hot-Swappable Souls:** You can banish a 7B parameter model and summon a 70B parameter model without changing a single line of the Vessel's code.
    *   **Fallback Rituals:** If a local Soulstone fails (OOM), the Animator can seamlessly redirect the stream to a Portal (Cloud API) to ensure the thought is completed.

## ⚡ The Sources of Power

The Animator draws its energy from two distinct types of sources, defined in your **[Codex](../codex.md)**.

### :material-hexagon-slice-6: [Soulstones](./soulstone.md) (Local Inference)

**"The Trapped Spirit."**

These are the engines running within the Sepulcher itself, bound to your physical hardware (GPUs). They are defined as Quadlet containers (like `vLLM` or `SGLang`) that sit on the local network.

- **Pros:** Absolute privacy, zero latency cost, no "rate limits," full control over the weights.
- **Cons:** Bound by the VRAM of your physical machine. The spirit is only as strong as the cage you build for it.

### :material-weather-hurricane: [Portals](./portal.md) (Cloud APIs)

**"The Rift to the Void."**

These are connections to the vast, alien intelligences dwelling in the cloud (OpenAI, Anthropic, Groq). They do not run on your hardware; the Animator merely opens a gateway to send the prompt and receive the completion.

- **Pros:** Infinite intelligence, massive context windows, no hardware requirements.
- **Cons:** You pay a tithe in gold (credits) and privacy. The thought leaves your sanctum.

## 🫀 The Galvanic Arc

The Animator is not a biological organ; it is a **circuit**. It governs the cycle of Request and Response.

1.  **The Impulse:** The Vessel sends a structured Pydantic object (the Prompt) to the Animator.
2.  **The Routing:** The Animator directs this voltage to the active Soulstone or Portal.
3.  **The Stream:** The tokens flow back in real-time via Server-Sent Events (SSE). The Animator normalizes these sparks, ensuring the [Altar](../../divination/altar.md) displays a smooth, continuous stream of consciousness.

!!! tip "The Rite of the Swap"
    Because the Animator relies on standard protocols, your "Model Backend" is effectively a modular component.

    Do you wish to switch from Llama-3 to Mistral? Do you wish to switch from vLLM to Llama.cpp? Simply change the **Rune** in the `conf.d/` directory.

    Once the configuration is changed, you must invoke the **[Rite of Reanimation](../phylactery/reanimation.md)**. The Lich will willingly terminate its current process and instantly respawn with the new personality loaded, retaining all memories in the Phylactery.
