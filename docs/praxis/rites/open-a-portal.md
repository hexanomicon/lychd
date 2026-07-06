---
title: Open a Portal
icon: material/door-open
---

# :material-door-open: Rite — Open a Portal

**Goal:** connect a remote provider (a cloud model) and see its capability on the
[Nexus](../../divination/altar/nexus.md).

**Prerequisites:** a running daemon ([First Breath](../../summoning/first-breath.md)), and an
API key for the provider.

A [Portal](../../sepulcher/animator/portal.md) is a remote Animator. It consumes no local
VRAM and its capabilities are always `STATIC` — reachable means warm.

## Steps

### 1. Store the API key as a named Podman secret

A Portal Rune references a secret by *name*, never by value. LychD resolves credentials from
Podman secrets, which the Vessel mounts at `/run/secrets/`. Create the secret under the name
you will reference from the rune:

```bash
printf '%s' "$OPENAI_API_KEY" | podman secret create portal_openai_main -
```

!!! note "Secret resolution"
    The rune only ever names the secret. At bind, LychD renders a `Secret=` line into the
    Vessel's Quadlet so the running connector reads the value from
    `/run/secrets/portal_openai_main`. The rune files themselves carry no secret material.

### 2. Write the Portal Rune

Create the rune under the Codex portals tree:

```toml title="~/.config/lychd/runes/animator/portals/openai/main.toml"
name = "openai-main"
description = "OpenAI frontier chat."
api_key_secret_name = "portal_openai_main"

[[models]]
id = "gpt-5.2"
description = "Frontier chat model."

[models.capabilities]
supports_tools = true
modalities_in = ["text", "image"]
```

The `provider_name` and default endpoint come from the OpenAI portal schema. Declare at
least one `[[models]]` block — a Portal with zero models yields zero capabilities. For every
field, see the [Portal Rune reference](../runes/portals.md).

!!! warning "Egress is opt-in"
    Binding this Portal makes **no** network call: `probe` defaults to `false`. Set
    `probe = true` only if you want a live reachability check at bind time.

### 3. Bind

```bash
lychd bind
```

Portals generate no systemd units, but `bind` validates the rune and registers the Portal's
capabilities.

## Verify

Confirm the Portal's capability is known and warm:

```bash
lychd animators
```

You should see `openai-main` in the table with a `chat` capability for `gpt-5.2`. On the
[Nexus](../../divination/altar/nexus.md) it shows as **active** — a `STATIC` Portal is warm
as soon as it is reachable. You can now select it from the
[Bridge](../../divination/altar/index.md) and route Intents to it.

If the capability does not appear, confirm the rune parsed — `lychd bind` reports a named
error on an invalid rune, and a rune that fails validation is never registered. See
[Exorcism](../exorcism.md).
