---
title: vLLM
icon: material/rocket-launch
---

# :material-rocket-launch: vLLM

**vLLM** is a resident model-serving engine behind an OpenAI-compatible connector. The Soulstone
adapter binds one declared model service to a Rune, derives its model capability, probes the live
inventory, and exposes it only when the exact declared model is ready.

The adapter owns runtime defaults and translation of typed Rune fields into launch arguments.
Intentional engine-specific changes belong in the runtime's typed overrides or an explicit
operator-owned `exec`; they do not become Core-wide generation law.

The exact model, quantization, GPU topology, image digest, arguments, readiness, inference, and
shutdown still require an operator receipt. The current delivery boundary is recorded under
[vLLM integration](../../../../state-of-the-work.md#vllm-integration).

See [Soulstone Disciplines](../disciplines.md#i-the-kinetic-vllm), [vLLM](https://docs.vllm.ai/),
and the [OpenAI-compatible connector boundary](../../connectors.md#openai-compatibility-is-per-dialect).
