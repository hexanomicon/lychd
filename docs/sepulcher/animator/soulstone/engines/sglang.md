---
title: SGLang
icon: material/graph
---

# :material-graph: SGLang

**SGLang** is a model-serving engine with an OpenAI-compatible service surface and its own
runtime-native graph/DSL features. LychD binds the declared service through the Soulstone adapter;
it does not require the caller to depend on `sgl.gen` or any other SGLang-specific language.

Adapter-specific flags remain part of the exact engine profile. They must be declared, pinned, and
included in the runtime receipt rather than inferred from a generic OpenAI-compatible endpoint.

The exact image, model, quantization, GPU and driver, launch arguments, readiness, inference, and
shutdown still require an operator receipt. The current delivery boundary is recorded under
[SGLang integration](../../../../state-of-the-work.md#sglang-integration).

See [Soulstone Disciplines](../disciplines.md#ii-the-radix-sglang),
[SGLang](https://github.com/sgl-project/sglang), and the
[OpenAI-compatible connector boundary](../../connectors.md#openai-compatibility-is-per-dialect).
