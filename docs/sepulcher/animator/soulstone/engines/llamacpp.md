---
title: llama.cpp
icon: material/chip
---

# :material-chip: llama.cpp

**llama.cpp** is a local model-serving engine with two materially different Soulstone shapes:

- `single` starts with one declared model and serves one stable alias;
- `router` starts without a model and activates declared models in process.

## Launch and identity

The adapter translates the Rune into a deterministic launch plan. Explicit `exec` owns the whole
command; otherwise explicit `startup_mode` wins, `auto` chooses `single` when `model_path` exists
and `router` otherwise, and typed `extra_args` append last. GPU/CPU offload remains an exact
profile fact, not a universal VRAM promise.

With passthrough `exec`, the operator must keep its listening port and served alias aligned with
the declared endpoint and model identity. Declaration compilation rejects a known `--port` or
`LLAMA_ARG_PORT` value that conflicts with the resolved endpoint, including a final `extra_args`
override of a managed command. LychD does not rewrite passthrough commands or infer unknown wrapper
syntax; declare the endpoint and command consistently for a runnable profile.

For managed single-model operation, `served_model_id` supplies the generated `--alias` and the
capability identity when no explicit `[[models]]` catalogue is present. Otherwise the model path
basename supplies that alias. Declared model ids must match the engine's live inventory; a healthy
process alone cannot grant an absent model. The single-model probe validates `/v1/models` after
`/health`, following the upstream [Model Info API](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md#get-v1models-openai-compatible-model-info-api).

## Context allocation

Managed context metadata comes from the generated command, including final `extra_args`.
The catalogue derives a conservative per-request bound from positive total `-c` context divided
by positive `-np` parallel slots, reduced by any explicit `--kv-unified-per-slot` cap. Thus
`-c 8192 -np 4` admits a 2048-token bound even when a unified KV layout might permit more for one
request. Generated flags override environment and preset values. Explicit `exec` without known
positive context and slot counts leaves that derived bound unknown; automatic or malformed
command/environment context inputs do not silently fall back to a lower-priority value. These flags follow the upstream
[server parameters](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md#server-specific-params).
The bound describes configured allocation, not the loaded model's training context or a live
hardware measurement. Explicit generation overlays remain request policy; they do not change
the engine's allocation.

## Readiness and control

Router models are dynamic capabilities. An unloaded model may be `ACTIVATABLE`, activation passes
through `WARMING`, and only verified live inventory makes it `WARM`. Dynamic activation is not a
restart; reclaiming a conflicting physical runtime remains an Orchestrator transition.

The current repository proves planning, discovery, capability derivation, and load/unload control.
A real engine/GPU/model result remains [operator validation](../../../../state-of-the-work.md#llamacpp-integration).

Control receipts are intentionally literal: load/unload succeeds only on JSON boolean `true`, not
`1` or `"true"`, and a slot count rejects Python/JSON booleans even though they are integer-like.
Known numeric preset keys use their canonical integer or floating type; boolean words are ignored
rather than silently becoming `0` or `1`. Treat those refusals as malformed provider/configuration
evidence, not as successful control.

See [Soulstone Disciplines](../disciplines.md#iii-the-titan-llamacpp),
[llama.cpp](https://github.com/ggml-org/llama.cpp), and the
[repository support files](https://github.com/hexanomicon/lychd/tree/main/examples/llamacpp).
