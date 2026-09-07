---
title: Soulstone Disciplines
icon: material/atom
---

# :material-atom: Soulstone Disciplines

A discipline is the adapter knowledge that turns one Soulstone Rune into a callable local
Animator: launch arguments, capability synthesis, probes, and any supported runtime-native model
activation. The detailed runtime contracts are indexed in [Soulstone
Engines](./engines/index.md). This page keeps the canonical short vocabulary and the historical
discipline anchors used by the Lexicon.

## I. The Kinetic (vLLM) {#i-the-kinetic-vllm}

The Kinetic serves a pinned model through an OpenAI-compatible surface. Continue to the
[vLLM engine contract](./engines/vllm.md) for its exact live-inventory readiness rule, runtime
defaults, and outstanding operator receipt. These are adapter-specific obligations.

## II. The Radix (SGLang) {#ii-the-radix-sglang}

The [SGLang engine page](./engines/sglang.md) owns the detailed adapter contract. SGLang also
presents an OpenAI-compatible service; LychD does not require its `sgl.gen` DSL. Its live runtime
receipt remains [operator validation](../../../state-of-the-work.md#sglang-integration).

## III. The Titan (llama.cpp) {#iii-the-titan-llamacpp}

The [llama.cpp engine page](./engines/llamacpp.md) owns its single-model and router startup
shapes, deterministic argument precedence, and dynamic activation contract.

## Dynamic Activation Is Not Restart

The [Orchestrator](../../../adr/23-orchestrator.md) owns supported activation. A running router can
load a model without a systemd transaction; reclaiming a conflicting physical runtime still uses
the serialized target switch. Callers never invoke a runtime control API as a side route around
the Dispatcher.

Repository tests cover llama.cpp planning, discovery, capability derivation, and load/unload
control. A real engine/GPU/model result remains
[operator validation](../../../state-of-the-work.md#llamacpp-integration). ExLlamaV3 uses a
separate dynamic contract described in [ExLlamaV3 through TabbyAPI](./engines/exllamav3.md).
