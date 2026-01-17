---
title: Soulstone
icon: material/hexagon-slice-6
---

# :material-hexagon-slice-6: Soulstone

> _"A Portal is a whisper from the void, but a Soulstone is a god trapped in a bottle. It lives on your iron. It burns your electricity. It obeys only you."_

A **Soulstone** is a containerized Local LLM inference server. It is the engine of the [Animator](./index.md) that runs within the physical walls of the [Sepulcher](../index.md).

Technically, a Soulstone is a **Podman Quadlet** running an OpenAI-compatible server (such as **vLLM** or **Llama.cpp**). The Scribe reads your definitions and generates the necessary Systemd service files to manage their lifecycle.

## 💎 The Forms of Binding

You may summon Soulstones in two distinct configurations, depending on your hardware and your hunger.

### I. The Solitary (Single Model)

This is the standard binding. One container holds one model. It assumes it owns the GPU. Starting a Solitary soulstone will automatically terminate any other running soulstones to free up VRAM.

```toml
# ~/.config/lychd/soulstones/hermes.toml

[hermes]
description = "Reasoning model via Llama.cpp."
image = "ghcr.io/ggerganov/llama.cpp:server-cuda"
port = 8080

# The Weights
model_path = "/mnt/models/Hermes-2-Pro-Llama-3-8B-Q8_0.gguf"
model_format = "GGUF"

# Execution Arguments (Passed to the container entrypoint)
exec = [
    "-m", "/models/hermes.gguf", # Note: Map internal path manually if using custom volumes
    "-c", "8192",
    "--host", "0.0.0.0",
    "--port", "8080",
    "-ngl", "99"
]

# Optional: Extra Volumes
volumes = ["/mnt/models:/models:ro,z"]
```

### II. The Coven (Grouped Containers)

For the Magus who wishes to run distinct engines side-by-side (e.g., a vLLM server for logic and a smaller Llama.cpp server for function calling).

**The Two-Dot Rule:**
To bind Soulstones into a cooperative group, use the nested TOML syntax: `[group_name.model_name]`.

* **Inclusive:** Soulstones within the same group (`logic.alpha` and `logic.beta`) do _not_ conflict. Systemd allows them to run together.
* **Exclusive:** The Group conflicts with any soulstone outside of it (`logic.*` will kill `creative.*`).

```toml
# ~/.config/lychd/soulstones/logic_cluster.toml

# Alpha: The Big Brain (vLLM)
[logic.alpha]
image = "vllm/vllm-openai"
port = 8000
model_path = "/models/Llama-3-70B-Instruct"
model_name = "llama-3-70b"

# Beta: The Fast Hand (Llama.cpp)
[logic.beta]
image = "ghcr.io/ggerganov/llama.cpp:server-cuda"
port = 8001
model_path = "/models/Hermes-Function-Call.gguf"
model_name = "hermes-func"
```

## ⚔️ The Law of Exclusivity

LychD enforces strict resource discipline via Systemd `Conflicts=`. This prevents Out-Of-Memory (OOM) crashes by ensuring two massive models never fight for the same VRAM unless you explicitly grouped them.

* **Solitary vs Solitary:** `soulstone-hermes` will kill `soulstone-mistral`.
* **Group vs Group:** `soulstone-logic-*` will kill `soulstone-creative-*`.
* **Solitary vs Group:** A Solitary model (Highlander rule) will kill the entire Coven to claim the hardware.
