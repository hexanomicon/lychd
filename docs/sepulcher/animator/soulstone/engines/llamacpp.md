---
title: llama.cpp
icon: material/chip
---

# :material-chip: llama.cpp

**llama.cpp** is a local model-serving engine with two materially different Soulstone shapes:

- `single` starts with one declared model and serves one stable alias;
- `router` starts without a model and activates declared models in process.

The adapter translates the Rune into a deterministic launch plan. Explicit `exec` owns the whole
command; otherwise explicit `startup_mode` wins, `auto` chooses `single` when `model_path` exists
and `router` otherwise, and typed `extra_args` append last. GPU/CPU offload remains an exact
profile fact, not a universal VRAM promise.

Router models are dynamic capabilities. An unloaded model may be `ACTIVATABLE`, activation passes
through `WARMING`, and only verified live inventory makes it `WARM`. Dynamic activation is not a
restart; reclaiming a conflicting physical runtime remains an Orchestrator transition.

The current repository proves planning, discovery, capability derivation, and load/unload control.
A real engine/GPU/model result remains [operator validation](../../../../state-of-the-work.md#llamacpp-integration).

See [Soulstone Disciplines](../disciplines.md#iii-the-titan-llamacpp),
[llama.cpp](https://github.com/ggml-org/llama.cpp), and the
[repository support files](https://github.com/hexanomicon/lychd/tree/main/examples/llamacpp).
