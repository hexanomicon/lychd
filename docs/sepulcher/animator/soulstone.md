---
title: Soulstone
icon: material/hexagon-slice-6
---

# :material-hexagon-slice-6: Soulstone

> _"A Portal is a whisper from the void, but a Soulstone is a god trapped in a bottle. It lives on your iron. It burns your electricity. It obeys only you."_

A **Soulstone** is a containerized Local LLM inference server. It is the engine of the [Animator](./index.md) that runs within the physical walls of the [Sepulcher](../index.md).

Technically, a Soulstone is a **Podman Quadlet** running an OpenAI-compatible server (such as **vLLM**, **SGLang**, or **Llama.cpp**). The framework reads your definitions and generates the necessary Systemd service files to manage their lifecycle.

## 💎 The Three Forms of Binding

You may summon Soulstones in three distinct configurations, depending on your hardware and your hunger.

### I. The Solitary (Single Model)

This is the standard binding. One container holds one model. It is stable, isolated, and precise.

```toml
# ~/.config/lychd/conf.d/soulstones.toml

[soulstones.llamacpp_glm4]
port = 8080
description = "High-intelligence model with CPU offload via Llama.cpp."
image = "ghcr.io/ggerganov/llama.cpp:server-cuda"
# The framework injects this filename into the exec command template
model_filename = "GLM-4.5-Air-Q4_K_M-00001-of-00002.gguf"
# Overrides the default volume to be read-only
volumes = ["{{model_root}}/glm_4.5_air:/models:ro,z"]
exec = [
    "-m", "/models/{{model_filename}}",
    "-c", "32768",
    "--host", "0.0.0.0",
    "--port", "8080",
    "--flash-attn",
    "-ngl", "99",
    "--jinja"
]
```

### II. The Coven (Grouped Containers)

For the Magus who wishes to run distinct engines side-by-side (e.g., a vLLM server for logic and a Llama.cpp server for embeddings).

**The Two-Dot Rule:**
To bind Soulstones into a cooperative group, name them with a hierarchy: `soulstones.<group_name>.<model_name>`.

- **Inclusive:** Soulstones in the same group do _not_ conflict. Systemd allows them to run together.
- **Exclusive:** The Group conflicts with any soulstone outside of it.

### III. The Hydra (Llama.cpp Router)

_Experimental Support._

The `llama.cpp` server has evolved to support a **Router** mode. This allows a single container to serve multiple models from a directory, swapping them into memory as requested.

This is not a Coven (multiple processes); it is a **Hydra** (one process, many heads).

To summon a Hydra, you point the execution command to a directory rather than a specific file, allowing the internal router of the server to manage the "slots."

```toml
[soulstones.hydra_router]
image = "ghcr.io/ggerganov/llama.cpp:server-cuda"
volumes = ["{{model_root}}/mixed_quantized:/models:ro,z"]
exec = [
    "--model-url", "/models/", # The directory where the heads reside
    "--port", "8080",
    "--parallel", "4" # Serve 4 requests at once
]
```

## ⚔️ The Law of Exclusivity

LychD enforces strict resource discipline via Systemd `Conflicts=`:

- **Solitary vs Solitary:** `soulstone-glm` will kill `soulstone-mistral`.
- **Group vs Group:** `soulstone-alpha-*` will kill `soulstone-beta-*`.
- **Hydra:** A Hydra is treated as a Solitary entity. It demands the GPU. It will kill other Soulstones to claim the hardware.

!!! danger "The Burden of the Hydra"
    While the Hydra allows for great flexibility, it shares a single memory pool. If you ask the Hydra to manifest too many heads (models) simultaneously, or if the models are too large for the shared context, the beast will starve (OOM) and the container will collapse. Manage your VRAM wisely.
