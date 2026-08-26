---
title: ComfyUI
icon: material/graph-outline
---

# :material-graph-outline: ComfyUI

**ComfyUI** is a graph execution engine, not a Prism, Echo, or Riffmaw domain. A local ComfyUI
service can be a Soulstone when LychD owns its container, queue, readiness, GPU placement, model
mounts, and lifecycle. The same engine may produce capabilities for several semantic owners.

| Engine output | Owning LychD office |
| --- | --- |
| image, image edit, video, vision, or spatial graph | Prism |
| speech or other bounded audio operation | Echo when it satisfies the speech contract |
| music, voice, sound, or sonic synchronization artifact | Riffmaw |
| final audiovisual assembly | Broadcast |

## Keep model, engine, and road apart

The same semantic job may have several independently admitted realizations:

| Layer | Owns |
| --- | --- |
| Prism, Echo, or Riffmaw profile | Exact operation, request/result schema, model or voice identity, languages, formats, licence, limits, and bake evidence. |
| ComfyUI preset | One immutable graph, node closure, model-file bindings, open parameters, and output mapping for that profile. |
| Soulstone Rune | Local container, endpoint, devices, mounts, lifecycle, resources, and the exact admitted profile/preset references exposed by this instance. |
| Portal profile | A separately admitted remote provider, endpoint, dialect, credential, custody, cost, and reconciliation path. It is never inferred from the existence of a local pack with a similar name. |
| Scroll placement | The semantic Spell contract and its inputs, outputs, authority, recovery, and finish boundary. It does not name ComfyUI editor state. |
| Resolution Lock | The exact local Soulstone or Portal implementation selected for this casting. |

This is not duplicate model truth. The owning domain publishes one immutable semantic profile;
each engine or provider implementation states exactly which revision it implements and adds only
its dialect, runtime, placement, and evidence facts. A local open-weight MiniMax Music profile and
a hosted MiniMax music API, for example, are different implementations unless exact model,
protocol, and evidence identity prove otherwise.

The first adapter should expose an immutable LychD workflow profile rather than accept arbitrary
graphs from callers. A profile pins the editor/API graph, node and custom-node closure, model
files, parameter openings, output paths, network behavior, container revision, and license set.
Partner/cloud nodes, runtime downloads, ambient custom-node installation, and arbitrary imported
workflows fail closed.

The adapter owns the engine dialect: upload, submit, queue state, progress events, history,
outputs, interruption/cancellation request, and reconciliation. LychD still owns
`ServiceJobAttempt@1`, authority, artifact custody, retry law, and canonical provenance. A Comfy
filename or PNG metadata is evidence, not durable identity.

GPU placement is a Soulstone/profile fact. One managed host may run separate `comfy-qwen` and
`comfy-ltx` instances on different GPUs, or one experimental multi-GPU service with explicit
workflow device nodes. LychD must not infer parallelism, shared VRAM, model residency, or safe
batching from ComfyUI visibility alone.

The first candidate profiles are Qwen image generation/editing, LTX-2.5 or Wan video workflows,
MiniMax Music 3 generation, and later exact speech, sound, and Form graphs. Each profile must
separately prove input and output modalities, languages, limits, cancellation, VRAM/offload
behavior, model licences, and artifact validation. If an LTX preset returns synchronized sound and
video, the adapter emits separately attributable streams: Prism/Voidlight may judge the visual
candidate, Riffmaw the sonic candidate, and Broadcast their final relation.

See [ComfyUI](https://github.com/Comfy-Org/ComfyUI), the
[ComfyUI server routes](https://docs.comfy.org/development/comfyui-server/comms_routes), and the
owning [Prism Image](../../../extensions/prism/image.md),
[Prism Video](../../../extensions/prism/video.md),
[Prism Form](../../../extensions/prism/form.md), and
[Riffmaw](../../../../compositions/riffmaw/index.md) contracts.
