---
title: Portal Runes
icon: material/weather-hurricane
---

# :material-weather-hurricane: Portal Rune reference

A **Portal Rune** declares a connection to a remote provider — a cloud model, hosted tool,
or peer service. It lives under `~/.config/lychd/runes/animator/portals/<group>/<name>.toml`.
A Portal generates no Quadlet manifest and consumes no local VRAM; its capabilities are
always `STATIC`. For the concept, see [Portal](../../sepulcher/animator/portal.md).

## Top-level fields

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
    A Portal with no `[[models]]` blocks yields no routable capabilities — reachable but
    unadvertised. Declare at least one model to make the Portal usable. This is honest by
    design: LychD does not guess a remote provider's catalog.

!!! warning "The probe is opt-in"
    With `probe = false` (the default), binding a Portal performs **no** network calls. Set
    `probe = true` only when you want a live reachability check at bind — it makes one
    request to the provider's endpoint.

## The `[[models]]` blocks

One entry per model you want to route to. Each yields a capability spec.

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `id` | string (required) | — | Remote model id; last segment of the capability key. |
| `description` | string | `null` | Human note. |
| `[models.capabilities]` | table | `null` | Capability hints (same shape as a Soulstone's — see the [Soulstone reference](soulstones.md#modelscapabilities-capability-hints)). |
| `[models.generation]` | table | `null` | Per-model generation overrides. |

A Portal `[[models]]` block has no `path` (the model lives remotely). Everything else — the
capability hints and `[generation]` table — matches the
[Soulstone Rune reference](soulstones.md).

## Example

An OpenAI Portal exposing one frontier chat model with tool support and image admission:

```toml
name = "openai-main"
description = "Reference OpenAI portal (STATIC; image admission + tool support)."
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

This yields `openai-main:chat:gpt-5.2` (`STATIC`). The `provider_name` and default
`base_url` come from the OpenAI portal schema; you only override what you need.

To connect a Portal end to end and confirm it on the [Nexus](../../divination/altar/nexus.md),
follow the [Open a Portal](../rites/open-a-portal.md) rite.
