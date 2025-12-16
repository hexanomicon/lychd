---
title: Portal
icon: material/weather-hurricane
---

# :material-weather-hurricane: Portal

> _"Not all spirits can be contained within the Crypt. Some are too vast, too alien, and too terrible to dwell on mortal iron. To commune with them, we do not build a cage; we tear open the sky."_

A **Portal** is a configured connection to an external, cloud-based intelligence (OpenAI, Anthropic, Groq, OpenRouter). Unlike a [Soulstone](./soulstone.md), which lives and breathes on your local GPU, a Portal delegates the act of cognition to distant, hyperscale entities dwelling in the Void.

Technically, a Portal is an API Client definition within the **[Codex](../codex.md)** that adheres to the universal schema, but routes traffic outside the [Sepulcher](../index.md).

## 🌀 The Nature of the Rift

Portals serve specific strategic purposes in the Necromancer's arsenal:

- **The Heavy Lift:** When the logic required is too complex for a local 7B or 70B parameter model, the Portal allows you to summon the crushing intellect of a frontier model (e.g., GPT-4o, Claude 3.5 Sonnet).
- **The Prototyping:** Before you commit to downloading terabytes of weights and reserving GPU clusters, use a Portal to test your [Aspects](../lich.md) and Prompts.
- **The Safety Net:** A Portal can serve as a fallback. If your local Soulstone is overwhelmed or crashes, the [Animator](./index.md) can divert the stream to the Portal to ensure the [Ritual](../../ritual.md) completes.

## 📜 Inscribing a Portal

To open a rift, you must define it in your `conf.d/` directory. You do not need Quadlets for this, only the **API Key** (The Offering) and the endpoint.

```toml
# ~/.config/lychd/conf.d/portal-void.toml

[animator.portal]
name = "void-gpt"
provider = "openai"  # or "anthropic", "openrouter"
model = "gpt-4o"

[animator.portal.credentials]
# The Key must be passed via environment variables for security
api_key_env = "OPENAI_API_KEY"
```

!!! danger "The Tithe (Token Creep)"
    Beware, Magus. While a [Soulstone](./soulstone.md) serves you for the cost of electricity, a Portal demands a **Tithe**.

    Every token generated, every thought processed, draws gold directly from your coffers. The Lich does not care about your bank account; it will loop, iterate, and generate until the work is done or your credit card is declined.

    *   **Monitor the Usage:** Keep a close eye on the [Harvester's](../watchers/harvester.md) metrics.
    *   **Set Limits:** Use the budget controls in the Codex to prevent a runaway Ghoul from bankrupting your tower.

!!! warning "The Leak of Secrets"
    When you use a Portal, you are sending your data through the Rift. The [Phylactery's](../phylactery/index.md) privacy guarantee is voided the moment the packet leaves your network. Do not whisper secrets to the Void that you cannot bear the alien gods to hear.
