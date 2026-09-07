---
title: SGLang
icon: material/graph
---

# :material-graph: SGLang

**SGLang** is a model-serving engine with an OpenAI-compatible service surface and its own
runtime-native graph/DSL features. LychD binds the declared service through the Soulstone adapter;
it does not require the caller to depend on `sgl.gen` or any other SGLang-specific language.

The current adapter uses **operator-owned `exec` passthrough**: the Rune supplies the complete
SGLang launch command, while typed fields retain container and endpoint intent. Its registered
`OpenAICompatibleRuntimeAdapter` binds that declared service; it does not synthesize an SGLang
program from a generic endpoint. Keep the command's listening port and served model aligned with
the declared endpoint and model identity.

Pin framework flags with that command and include them in the exact engine profile and runtime
receipt. Neither a healthy URL nor a generic compatibility label establishes every declared model
or API operation.

The exact image, model, quantization, GPU and driver, launch arguments, readiness, inference, and
shutdown still require an operator receipt. The current delivery boundary is recorded under
[SGLang integration](../../../../state-of-the-work.md#sglang-integration).

See [Soulstone Disciplines](../disciplines.md#ii-the-radix-sglang),
[SGLang](https://github.com/sgl-project/sglang), and the
[OpenAI-compatible connector boundary](../../connectors.md#openai-compatibility-is-per-dialect).
