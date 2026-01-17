---
title: Portal
icon: material/weather-hurricane
---

# :material-weather-hurricane: Portal

> _"Not all spirits can be contained within the Crypt. Some are too vast, too alien, and too terrible to dwell on mortal iron. To commune with them, we do not build a cage; we tear open the sky."_

A **Portal** is a configured connection to an external, cloud-based intelligence (OpenAI, Anthropic, Groq, OpenRouter). Unlike a [Soulstone](./soulstone.md), which lives and breathes on your local GPU, a Portal delegates the act of cognition to distant, hyperscale entities dwelling in the Void.

Technically, a Portal is a pure configuration entry within the **[Codex](../codex.md)**. It generates no containers and consumes no local resources. It simply teaches the **[Animator](./index.md)** how to route a prompt to a remote endpoint.

## 🌀 The Nature of the Rift

Portals serve specific strategic purposes in the Necromancer's arsenal:

- **The Heavy Lift:** When the logic required is too complex for a local 7B model, summon the crushing intellect of a frontier model (e.g., GPT-4o, Claude 3.5 Sonnet).
- **The Prototyping:** Before you commit to downloading terabytes of weights, use a Portal to test your prompts against a reference intelligence.
- **The Fallback:** A Portal can serve as a safety net. If your local Soulstone is overwhelmed, the Animator can divert the stream to the Portal.

## 📜 Inscribing a Portal

To open a rift, you must define it in the `portals/` directory of your Codex.

```toml
# ~/.config/lychd/portals/openai.toml

[gpt4]
description = "The Frontier Intelligence."
provider = "openai"

# 1. The Address (Manifestation)
uri = "https://api.openai.com/v1"

# 2. The Identity (Contract)
model_name = "gpt-4o"

# 3. The Offering (Security)
# We map an Environment Variable to the API Key.
# This keeps your key safe, even if you share this TOML file.
api_key_env = "OPENAI_API_KEY"

# 4. The Personality (Optional Defaults)
temperature = 1.0
max_tokens = 8192
```

!!! danger "The Tithe (Token Creep)"
    Beware, Magus. While a [Soulstone](./soulstone.md) serves you for the cost of electricity, a Portal demands a **Tithe**.
    Every token generated, every thought processed, draws credits directly from your provider account. The Lich does not care about your bank balance; it will loop, iterate, and generate until the work is done or your card is declined.

!!! warning "The Leak of Secrets"
    When you use a Portal, you are sending your data through the Rift. The [Phylactery's](../phylactery/index.md) privacy guarantee is voided the moment the packet leaves your network. Do not whisper secrets to the Void that you cannot bear the alien gods to hear.
