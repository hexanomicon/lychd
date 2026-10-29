---
title: Soulstone Engines
icon: material/engine
---

# :material-engine: Soulstone Engines

Choose an **engine** for the execution it can supply, then give it a local body through a
Soulstone adapter, Rune, Quadlet, and declared resources. The upstream engine alone is neither
the Soulstone instance nor a model or semantic extension.

```text
engine + adapter + Rune + Quadlet + resources = one local Soulstone instance
```

The engine pages own runtime-specific launch shape, connector dialect, readiness and activation,
resource placement, containment, and evidence. Choose an engine below for that adapter's
requirements, then use the common [Soulstone contract](../index.md) to bind its local instance,
admit work through Dispatcher, and request Orchestrator transitions. Each engine page states its
delivery boundary; an entry in this map does not establish a delivered adapter.

| Engine | Primary shape | Use |
| --- | --- | --- |
| [vLLM](vllm.md) | resident OpenAI-compatible model server | Kinetic model serving |
| [SGLang](sglang.md) | resident OpenAI-compatible model server | Radix model serving |
| [llama.cpp](llamacpp.md) | single-model server or in-process router | Titan model serving and dynamic activation |
| [ExLlamaV3 through TabbyAPI](exllamav3.md) | dynamically activated model service | strict TabbyAPI-backed model serving |
| [ComfyUI](comfyui.md) | queued graph/workflow engine | image, video, spatial, and exact audio-capable profiles |
| [audio.cpp](audiocpp.md) | audio inference with an independently managed service or worker lifecycle | bounded music, separation, and speech profiles |

The same engine may manifest several Soulstones with different model sets, graphs, GPUs, conflict
domains, and capability profiles. `comfy-qwen`, `comfy-ltx`, and `comfy-music3`, for example, may
use one ComfyUI image while remaining separate managed service instances.

Qualify the particular work you intend to run on that engine. Model, graph, node set,
quantization, license, and hardware placement belong to an exact capability profile. The
selected adapter and owning extension or Composition must admit them; an engine's name cannot
establish these facts for every model or workflow it can load.

## Engine versus technical contract and semantic owner

The engine performs a bounded execution. Choose the technical contract and consuming owner for
each returned facet:

| Returned facet | Continue to |
| --- | --- |
| image, video, visual observation, spatial form, or structured motion | [Prism](../../../extensions/prism/index.md) for the exact technical interface and [Atelier](../../../../compositions/atelier/index.md) or another named consuming Composition for adoption |
| speech transcription, synthesis, cloning, or delivery | [Echo](../../../extensions/echo.md) and the requesting owner |
| music, musical vocal, production effect, or musical cue map | [Riffmaw](../../../../compositions/riffmaw/index.md) |
| timed-language dialogue, narration, or caption edition | [Language Edition](../../../../compositions/language-edition/index.md), using its exact Echo and Translation operations |
| picture-bound effect, foley, room tone, or ambience | [Broadcast](../../../../compositions/broadcast/index.md) |
| game-event, state, space, listener, or runtime sound | [Foundry](../../../../compositions/foundry/sound.md) |
| final audiovisual assembly | [Broadcast's pinned renderer and timeline](../../../../compositions/broadcast/render.md) |

Prism settles technical results, Core owns any `ServiceJobAttempt@1`, and each consuming owner
independently admits its facet. For model-native video with sound, follow
[compound-facet admission](../../../extensions/prism/video.md#admit-every-compound-facet) before
selecting the profile.

An engine that can emit more than one modality does not absorb those domains. The exact Rune and
capability profile determine which operations may execute; each application facet still needs its
own semantic admission receipt.
