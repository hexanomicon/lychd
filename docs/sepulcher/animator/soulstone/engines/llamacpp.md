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

Engine idle sleep is unsupported because readiness probes and `autoload=false` cannot fence its
automatic wake. Managed argument vectors begin with `--sleep-idle-seconds -1`; omit
`sleep_idle_seconds` or set it to `-1`. `extra_args` cannot contain any sleep control.
Passthrough `exec` must begin with that exact disabling pair: either
`["--sleep-idle-seconds", "-1", ...]` for an image entrypoint, or
`["llama-server", "--sleep-idle-seconds", "-1", ...]` for a complete command.
The executable token must be nonempty and cannot begin with `-`. Admitted bytes are not rewritten.
Later sleep controls, duplicate disabling flags, underscore aliases, equals spellings, and
misplaced or malformed disabling arguments fail validation. This deliberately bounds the command
shape instead of inferring arbitrary option arity; a flag consumed as another option's value
cannot supply admission. Custom wrappers that cannot honor this contract are outside the
supported llama.cpp profile.

This contract was checked against upstream revision
[`434ddbbc0e30522e897670681e503b797c12b7c1`](https://github.com/ggml-org/llama.cpp/commit/434ddbbc0e30522e897670681e503b797c12b7c1):
the router [overlays CLI arguments on every model preset](https://github.com/ggml-org/llama.cpp/blob/434ddbbc0e30522e897670681e503b797c12b7c1/tools/server/server-models.cpp#L531),
while [sleeping children still count as running](https://github.com/ggml-org/llama.cpp/blob/434ddbbc0e30522e897670681e503b797c12b7c1/tools/server/server-models.h#L93)
for router autoload admission. The default is disabled, but the explicit command value also
overrides sleep enabled in global, model, directory, or cached presets. Command validation does
not attest an already-running service or external changes; operator validation must check the
actual image revision and arguments.
The pinned [argument parser](https://github.com/ggml-org/llama.cpp/blob/434ddbbc0e30522e897670681e503b797c12b7c1/common/arg.cpp#L816)
normalizes underscore option names and consumes values positionally; equals-form sleep flags are
not accepted by that engine revision.

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

Router models are dynamic capabilities. Each model's inventory status determines its readiness:
clean `unloaded` admits activation, `loading` means `WARMING`, and `loaded` plus ready health supplies warmth.
Missing declared models and malformed inventories fail closed; failed, sleeping, downloading, or
unknown statuses cannot authorize activation. One model's health cannot establish a sibling's state.
Activation rechecks inventory and does not repeat a load already in progress. Inference and targeted
health requests carry `autoload=false`; with engine idle sleep disabled, a missing loaded model
cannot silently trigger router loading or eviction.
Dynamic activation is not a restart; reclaiming a conflicting physical runtime remains an
Orchestrator transition.

The current repository proves planning, discovery, capability derivation, and model-load control.
Model unloading is not a separate adapter operation; whole-runtime shutdown belongs to Orchestrator.
A real engine/GPU/model result remains [operator validation](../../../../state-of-the-work.md#llamacpp-integration).

Control receipts are intentionally literal: model-load succeeds only on JSON boolean `true`, not
`1` or `"true"`, and a slot count rejects Python/JSON booleans even though they are integer-like.
Known numeric preset keys use their canonical integer or floating type; boolean words are ignored
rather than silently becoming `0` or `1`. Treat those refusals as malformed provider/configuration
evidence, not as successful control.

See [Soulstone Disciplines](../disciplines.md#iii-the-titan-llamacpp),
[llama.cpp](https://github.com/ggml-org/llama.cpp), and the
[repository support files](https://github.com/hexanomicon/lychd/tree/main/examples/llamacpp).
