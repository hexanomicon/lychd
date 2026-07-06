---
title: The First Soulstone
icon: material/hexagon-slice-6
---

# :material-hexagon-slice-6: Stage 4 — The First Soulstone

A [Soulstone](../sepulcher/animator/soulstone.md) is a local model service running on your
own iron. You declare it as a **Soulstone Rune** — a TOML file in the Codex — and `bind`
transmutes that declaration into a systemd service. This stage writes your first Soulstone
Rune and binds it.

## Write the rune

Soulstone Runes live under `~/.config/lychd/runes/animator/soulstones/`. Create one for a
`llama.cpp` server. This example runs the server in **router** mode, which loads models on
demand (a `DYNAMIC` capability):

```toml title="~/.config/lychd/runes/animator/soulstones/llamacpp/atelier.toml"
name = "atelier"
description = "My first local model service."
groups = ["atelier"]
startup_mode = "router"
models_dir = "/models"

[concurrency]
dedicated = true
persistent_resident = false

[[models]]
id = "qwen3-8b"
path = "/models/qwen3-8b"
description = "A local chat model."

[models.capabilities]
supports_tools = true
```

What each part declares:

- `name` — the Animator's name. It becomes the first segment of every capability key this
  Soulstone yields: `atelier:chat:qwen3-8b`.
- `startup_mode = "router"` — the `llama.cpp` router loads models on demand, so its
  capabilities are `DYNAMIC` (see [Capabilities](../sepulcher/animator/capabilities.md)).
  A single-model server (for example vLLM) is `STATIC` instead — reachable means warm.
- `[concurrency]` — `dedicated = true` means LychD owns this runtime's lifecycle and may
  swap it; `persistent_resident = false` means it is not pinned to survive every swap.
- `[[models]]` — one block per model. The `id` and `path` are required; `path` resolves
  against your `model_root`. The `[models.capabilities]` hints declare what the model can
  do — here, tool calling.

The full schema, including every field and how to declare vision, embeddings, and
generation defaults, is the [Soulstone Rune reference](../praxis/runes/soulstones.md).

!!! tip "A simpler STATIC alternative"
    If you run a single-model server such as vLLM, the capability is `STATIC` — it is warm
    the moment its endpoint is reachable, with no activation step. See the
    [reference](../praxis/runes/soulstones.md) for a vLLM example.

## Bind it

Transmute the Codex into systemd units:

```bash
lychd bind
```

This reads your runes and installed extensions, generates the podman/systemd
[Quadlet](../sepulcher/codex.md) manifests, and reloads the user daemon. The circle is
bound.

## Verify the soulstone

Confirm LychD sees the Soulstone and can read its declared capabilities:

```bash
lychd animators
```

You should see `atelier` listed with a `chat` capability for your model. Its **Active** and
**Warm** columns stay empty until the daemon runs and the model warms — that is expected
before the First Breath. If `bind` failed or the animator is missing, see
[Exorcism](../praxis/exorcism.md).

With a bound Soulstone, proceed to [The First Breath](first-breath.md).
