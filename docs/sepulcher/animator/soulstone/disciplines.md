---
title: Soulstone Disciplines
icon: material/atom
---

# :material-atom: Soulstone Disciplines

Each runtime needs its own knowledge of how to start, declare capabilities, report readiness,
and—where supported—activate a model inside the running service. A **discipline** is that adapter
knowledge applied to a Soulstone Rune. [Soulstone Engines](./engines/index.md) indexes the detailed
contracts. The short names and historical anchors below remain the vocabulary used by the Lexicon.

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

Repository tests cover llama.cpp planning, discovery, capability derivation, and model loading.
Model unloading is not a separate adapter operation; Orchestrator shuts down whole runtimes. A real engine/GPU/model result remains
[operator validation](../../../state-of-the-work.md#llamacpp-integration). ExLlamaV3 uses a
separate dynamic contract described in [ExLlamaV3 through TabbyAPI](./engines/exllamav3.md).
