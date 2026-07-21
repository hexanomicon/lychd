---
title: Portal
icon: material/weather-hurricane
---

# :material-weather-hurricane: Portal: The Rift to the Remote Sky

> _"Not all spirits can be contained within the Crypt. Some are distant, rented, and sharp enough to matter. To commune with them, the sky is opened under seal."_

A **Portal** is a configured connection to an external service: cloud intelligence, hosted tooling, remote observability, paid APIs, or another sovereign node. Unlike a **[Soulstone](./soulstone.md)**, which lives and breathes on local iron through Quadlet/systemd, a Portal delegates the capability to a network boundary.

Technically, a **Portal Rune** is the Codex TOML declaration for a Portal. The runtime **Portal** is the remote Animator hydrated from that Rune. It generates no Quadlet manifests and consumes no local VRAM. It teaches the **[Dispatcher](../../adr/22-dispatcher.md)** and binder how to hydrate a remote endpoint into live capability surfaces such as Pydantic AI models, deferred tools, query clients, or peer calls.

## 🌀 The Nature of the Rift

Portals serve specific strategic purposes in the Necromancer's arsenal:

- **The Frontier Reasoning:** When the logic required is too complex for a local model, summon the crushing intellect of a frontier model (e.g., `gpt-4o`, `claude-3-5-sonnet`).
- **The Prototyping:** Before the Magus commits to downloading terabytes of weights, a Portal can test prompts against a reference intelligence.
- **The Burst Overflow:** If local VRAM is fully occupied by a high-priority **[Simulation](../../adr/31-simulation.md)**, the system can route simpler tasks through a Portal.
- **The External Instrument:** If a capability lives outside the Sepulcher, such as hosted search, remote metrics, payment-gated APIs, or peer-node labor, a Portal lets LychD call it without pretending it is local.

## 📜 The Pydantic Bridge

LychD leverages adapter-backed binding so Portals are first-class citizens of the runtime.

- **Endpoint + Connector Identity:** Runtime binding is driven by `provider_name`, optional `base_url`, and connector-owned capability semantics.
- **Standardized Runtime Contract:** Regardless of the vendor, the Portal enters the system through the same **[Animator](./index.md)** runtime/binder path.
- **Capability Surface:** Portal capabilities are exposed by the resolved connector, not by Portal-specific tool fields.
- **The Fallback Ritual:** The system often wraps a local Soulstone and a remote Portal into a `FallbackModel`. If local hardware returns a 4xx or 5xx error, the Lich automatically tears the sky and replays the request through the Portal to ensure the thought is completed.

Current implementation scope:

- Model-backed Portals are hydrated through the OpenAI-compatible path (`OpenAIProvider` + `OpenAIChatModel`).
- Additional provider-native binders (Anthropic, Google, etc.) and non-model service binders are extension points, not hardcoded in the core registry.

## 🖋️ Inscribing a Portal

To open a rift, define its properties under a provider-specific Portal anchor in the Codex. `PortalConfig` is the abstract branch at `runes/animator/portals/`; concrete provider Runes such as `OpenAIPortalConfig` and `GoogleGeminiPortalConfig` own the TOML files below their own leaf directories.

```toml
# ~/.config/lychd/runes/animator/portals/openai/main.toml

name = "gpt4"
description = "The Frontier Intelligence."

# The Offering (Security)
# Reference a Podman secret name, not a raw API key value.
api_key_secret_name = "portal_openai_main"

```

```bash
printf '%s' "$OPENAI_API_KEY" | podman secret create --replace portal_openai_main -
```

## :material-key-link: Secret Lifecycle

Portal auth is reference-driven:

1. Portal Rune stores only `api_key_secret_name = "<name>"`.
2. `lychd bind` verifies the named Podman secret exists.
3. If missing, bind fails closed before writing units.
4. Vessel receives `Secret=<name>` and connector reads `/run/secrets/<name>`.

Core app secrets (`APP` signing key and DB password) are auto-generated as startup fallbacks only when no secret source is configured. Portal secrets are never auto-generated and must be explicitly created.

A Portal API secret name may never alias either core secret name. Multiple Portals may
deliberately reference the same provider credential because their connectors all execute inside
the trusted Vessel; doing so also deliberately shares that credential's rotation and blast radius.

For policy and boundary details, see [Security (ADR 09)](../../adr/09-security.md) and [Configuration (ADR 12)](../../adr/12-configuration.md).

!!! danger "The Tithe (Token Creep)"
    Beware, Magus. While a [Soulstone](./soulstone.md) serves for the cost of electricity, a Portal demands a **Tithe**.
    Every thought processed draws credits from an external account. The Lich does not care about the balance; it can loop and generate until the work is done or the card is declined.

!!! warning "The Leak of Secrets"
    Portal use sends data through the Rift. The **[Sovereignty Wall](../../adr/09-security.md)** and Dispatcher privatization policy are the shield.
    - In sovereignty-restricted modes, Portals may be disabled entirely.
    - Sensitive intents or high-privatization context may forbid Portal egress, forcing the work to local iron or sanitization workflows.

## Opening a Portal

Connect a remote provider end to end and confirm it on the [Nexus](../../divination/altar/nexus.md). Prerequisites: a running daemon ([the Awakening](../../summoning.md#the-awakening)) and a provider API key.

1. **Store the API key as a named Podman secret** (the rune references it by name, never by value — see *Secret Lifecycle* above):
   ```bash
   printf '%s' "$OPENAI_API_KEY" | podman secret create portal_openai_main -
   ```
2. **Write the Portal Rune** under `runes/animator/portals/<group>/<name>.toml` (see *Inscribing a Portal* above and the reference below). Declare at least one `[[models]]` block — a Portal with zero models yields zero capabilities.
3. **Bind:** `lychd bind`. Portals generate no systemd units, but bind validates the rune and registers the Portal's capabilities.
4. **Verify:** `lychd animators` shows the Portal with its capability; on the [Nexus](../../divination/altar/nexus.md) it reads **active** — a Portal (`is_dynamic=False`) is warm as soon as it is reachable. Route Intents to it from the [Bridge](../../divination/altar/index.md).

!!! warning "Egress is opt-in"
    Binding a Portal makes **no** network call: `probe` defaults to `false`. Set `probe = true` only for a live reachability check at bind. If the capability never appears, confirm the rune parsed — `lychd bind` reports a named error on an invalid rune, and a rune that fails validation is never registered.

## Portal Rune reference

A **Portal Rune** lives under `~/.config/lychd/runes/animator/portals/<group>/<name>.toml`. It generates no Quadlet manifest and consumes no local VRAM; its capabilities always carry `is_dynamic=False`.

### Top-level fields

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `name` | string (required) | — | Animator name; first segment of every capability key (`<name>:<family>:<model_id>`). |
| `description` | string | `""` | Human note. |
| `provider_name` | string (required) | — | Provider identity (e.g. `openai`, `google-gemini`). Set by the provider-specific schema. |
| `base_url` | URL | provider default | Endpoint override. |
| `api_key_secret_name` | string | `null` | **Name** of the API-key secret (never the value). |
| `models` | list of `[[models]]` | `[]` | Declared models (below). |
| `generation` | `[generation]` table | `null` | Default generation profile for this portal. |
| `probe` | bool | `false` | Opt-in live reachability probe. Off by default — **no surprise egress**. |

!!! note "Zero models means zero capabilities"
    A Portal with no `[[models]]` blocks yields no routable capabilities. LychD does not guess a remote provider's catalog; declare at least one model to make the Portal usable.

### The `[[models]]` blocks

One entry per model you want to route to. Each yields a capability spec. A Portal `[[models]]` block has no `path` (the model lives remotely); everything else — the `[models.capabilities]` hints and `[models.generation]` table — matches the [Soulstone Rune reference](./soulstone.md#soulstone-rune-reference).

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `id` | string (required) | — | Remote model id; last segment of the capability key. |
| `description` | string | `null` | Human note. |
| `[models.capabilities]` | table | `null` | Capability hints (see the Soulstone reference). |
| `[models.generation]` | table | `null` | Per-model generation overrides. |

### Example

```toml
name = "openai-main"
description = "Reference OpenAI portal (is_dynamic=False; image admission + tool support)."
api_key_secret_name = "portal_openai_main"

[generation]
temperature = 0.5

[[models]]
id = "gpt-5.2"
description = "Frontier chat model with vision admission and tool support."

[models.capabilities]
supports_tools = true
modalities_in = ["text", "image"]

[models.generation]
max_tokens = 4096
```

This yields `openai-main:chat:gpt-5.2` (`is_dynamic=False`). The `provider_name` and default `base_url` come from the OpenAI portal schema; you override only what you need.

> _A Portal is not a shortcut. It is a sealed opening in the sky, used only when local iron cannot finish the thought._
