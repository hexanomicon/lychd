---
title: Soulstone Engines
icon: material/engine
---

# :material-engine: Soulstone Engines

An **engine** is an upstream execution substrate that a Soulstone adapter can bind into a local
Animator. It is not itself a Soulstone, a model, or a semantic extension.

```text
engine + adapter + Rune + Quadlet + resources = one local Soulstone instance
```

The engine pages own runtime-specific launch shape, connector dialect, readiness and activation,
resource placement, containment, and evidence. The common [Soulstone
contract](../index.md) owns lifecycle, Rune binding, Dispatcher admission, and Orchestrator
transitions.

| Engine | Primary shape | Current office |
| --- | --- | --- |
| [vLLM](vllm.md) | resident OpenAI-compatible model server | Kinetic model serving |
| [SGLang](sglang.md) | resident OpenAI-compatible model server | Radix model serving |
| [llama.cpp](llamacpp.md) | single-model server or in-process router | Titan model serving and dynamic activation |
| [ExLlamaV3 through TabbyAPI](exllamav3.md) | dynamically activated model service | strict TabbyAPI-backed model serving |
| [ComfyUI](comfyui.md) | queued graph/workflow engine | image, video, spatial, and exact audio-capable profiles |
| [audio.cpp](audiocpp.md) | local audio inference service or worker | bounded music, separation, and speech profiles |

The same engine may manifest several Soulstones with different model sets, graphs, GPUs, conflict
domains, and capability profiles. `comfy-qwen`, `comfy-ltx`, and `comfy-music3`, for example, may
use one ComfyUI image while remaining separate managed service instances.

Models and workflow graphs are not universal engine facts. An exact model, graph, node set,
quantization, license, and hardware placement become a capability profile only after the selected
engine adapter and the owning extension or Composition have admitted them.

## Engine versus contract and admission owner

The engine performs a bounded execution; another owner defines what the result means:

| Returned capability | Contract and admission owner |
| --- | --- |
| image, visual observation, video, or spatial form | Prism technical contract; the consuming Composition owns application admission and judgment |
| speech transcription or synthesis | Echo |
| music, musical vocal or musical production effect, or musical cue map | Riffmaw |
| timed-language dialogue, narration, or caption edition | Language Edition over exact Echo and Translation operations |
| picture-bound effect, foley, ambience, or final audiovisual relation | Broadcast |

An engine that can emit more than one modality does not absorb those domains. The exact Rune and
capability profile determine which operations are admitted.
