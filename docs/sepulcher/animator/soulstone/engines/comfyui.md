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

The first candidate profiles are Qwen image generation/editing, LTX or Wan video workflows, and
later exact sound/form graphs. Each profile must separately prove input and output modalities,
limits, cancellation, VRAM/offload behavior, model licenses, and artifact validation.

See [ComfyUI](https://github.com/Comfy-Org/ComfyUI), the
[ComfyUI server routes](https://docs.comfy.org/development/comfyui-server/comms_routes), and the
owning [Prism Image](../../../extensions/prism/image.md),
[Prism Video](../../../extensions/prism/video.md),
[Prism Form](../../../extensions/prism/form.md), and
[Riffmaw](../../../../compositions/riffmaw/index.md) contracts.
