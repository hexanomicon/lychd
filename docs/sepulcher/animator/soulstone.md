---
title: Soulstone
icon: material/hexagon-slice-6
---

# :material-hexagon-slice-6: Soulstone

> _"A Portal is a whisper from the void, but a Soulstone is a god trapped in a bottle. It lives on your iron. It burns your electricity. It obeys only you."_

A **Soulstone** is a containerized Local LLM inference server. It is the engine of the [Animator](./index.md) that runs within the physical walls of the [Sepulcher](../index.md).

Technically, a Soulstone is a **Podman Quadlet** running an **OpenAI-compatible** server. While the Lich prefers the speed of **SGLang**, **vLLM**, **Llama.cpp** or **ExLLamaV2/V3**, it is engine-agnostic. Any container that accepts standard OpenAI chat completion requests can be bound to the system.

## 💎 The Forms of Binding

You may summon Soulstones in two distinct configurations, depending on your hardware and your hunger.

### I. The Solitary (Single Model)

This is the standard binding. One container holds one model. It assumes it owns the GPU. Starting a Solitary soulstone will automatically terminate any other running soulstones to free up VRAM.

**Example: High-Performance SGLang Binding**

```toml
# ~/.config/lychd/soulstones/flash.toml

[flash]
description = "High-throughput SGLang server."
image = "lmsysorg/sglang:latest"
port = 30000

# The Weights (Host Path)
model_path = "/mnt/models/Meta-Llama-3-70B-Instruct"

# Execution Arguments (Passed to the container entrypoint)
# Note: You must map the internal container path (/models) manually in the arguments.
exec = [
    "python3", "-m", "sglang.launch_server",
    "--model-path", "/models/Meta-Llama-3-70B-Instruct",
    "--host", "0.0.0.0",
    "--port", "30000"
]

# Volume Mapping: Host Path -> Container Path
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
# Note: vLLM expects the internal path
exec = ["--model", "/models/Llama-3-70B-Instruct", "--port", "8000"]
volumes = ["/mnt/models:/models:ro,z"]

# Beta: The Fast Hand (Llama.cpp)
[logic.beta]
image = "ghcr.io/ggerganov/llama.cpp:server-cuda"
port = 8001
model_path = "/models/Hermes-Function-Call.gguf"
# Note: Llama.cpp GGUF binding
exec = ["-m", "/models/hermes.gguf", "-c", "8192", "--port", "8001", "-ngl", "99"]
volumes = ["/mnt/models:/models:ro,z"]
```

## ⚔️ The Law of Exclusivity

LychD enforces strict resource discipline via Systemd `Conflicts=`. This prevents Out-Of-Memory (OOM) crashes by ensuring two massive models never fight for the same VRAM unless you explicitly grouped them.

* **Solitary vs Solitary:** `soulstone-flash` will kill `soulstone-mistral`.
* **Group vs Group:** `soulstone-logic-*` will kill `soulstone-creative-*`.
* **Solitary vs Group:** A Solitary model (Highlander rule) will kill the entire Coven to claim the hardware.

!!! warning "The Port Singularity"
    **Every Soulstone must listen on a unique port.**

    Even if two groups (e.g., `logic.*` and `creative.*`) are mutually exclusive and never run simultaneously, they **cannot** share Port 8000.

    **Why?** Physics. When Systemd stops the Logic container, the Linux Kernel holds the TCP port in a `TIME_WAIT` state for ~60 seconds to drain packets. If the Creative container tries to bind that same port immediately, it will crash with `Address already in use`.
