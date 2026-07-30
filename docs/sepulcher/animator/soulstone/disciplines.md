---
title: Soulstone Disciplines
icon: material/atom
---

# :material-atom: Soulstone Disciplines

A discipline is the adapter knowledge that turns one Soulstone Rune into a callable local
Animator: launch arguments, capability synthesis, probes, and any supported runtime-native model
activation. Core registers `vllm`, `sglang`, `llamacpp`, and `exllamav3` runtime profiles.

## I. The Kinetic (vLLM) {#i-the-kinetic-vllm}

The vLLM adapter serves a pinned model through an OpenAI-compatible surface. Its synthesized
defaults include `--gpu-memory-utilization 0.9`, `--max-num-seqs 1`, and
`--quantization awq`. Put intentional changes in the runtime's `extra_args`, or use `exec` when
the whole command must become operator-owned.

A server pinned to one model produces `is_dynamic=False` capabilities. Its endpoint binds after
the model loads, so reachability and warmth coincide. Current planning and connector behavior are
covered by focused tests; a named image, model, driver, readiness, inference, and shutdown receipt
remains [operator validation](../../../state-of-the-work.md#vllm-integration).

## II. The Radix (SGLang) {#ii-the-radix-sglang}

SGLang also presents an OpenAI-compatible service; LychD does not require its `sgl.gen` DSL.
Adapter-specific options such as `--enable-marlin` belong in `extra_args`. Its live runtime
receipt remains [operator validation](../../../state-of-the-work.md#sglang-integration).

## III. The Titan (llama.cpp) {#iii-the-titan-llamacpp}

llama.cpp admits GPU/CPU offload flags such as `--n-gpu-layers` and `--n-cpu-moe`. It supports two
startup shapes:

- `single` starts with `-m <model_path>` and serves one alias;
- `router` starts without `-m` and uses `--models-dir` or `--models-preset` for in-process loading.

Argument and mode precedence is deterministic:

1. explicit `exec` disables synthesis;
2. explicit `startup_mode = "single"` or `"router"` chooses the shape;
3. `startup_mode = "auto"` selects single when `model_path` exists, otherwise router;
4. `extra_args` append last.

The router's declared models are `is_dynamic=True`. Once the container is reachable, an unloaded
model is `ACTIVATABLE`; activation moves it through `WARMING` to `WARM`. A swap may return the old
model toward `ACTIVATABLE` or `COLD`.

## Dynamic Activation Is Not Restart

The [Orchestrator](../../../adr/23-orchestrator.md) owns supported activation. A running router can
load a model without a systemd transaction; reclaiming a conflicting physical runtime still uses
the serialized target switch. Callers never invoke a runtime control API as a side route around
the Dispatcher.

Repository tests cover llama.cpp planning, discovery, capability derivation, and load/unload
control. A real engine/GPU/model result remains
[operator validation](../../../state-of-the-work.md#llamacpp-integration). ExLlamaV3 uses a
separate dynamic contract described in [ExLlamaV3 through TabbyAPI](./exllamav3.md).
