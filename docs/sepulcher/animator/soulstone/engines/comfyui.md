---
title: ComfyUI
icon: material/graph-outline
---

# :material-graph-outline: ComfyUI

Choose a bounded workflow before admitting [ComfyUI](https://github.com/Comfy-Org/ComfyUI). Its
graph and dependency closure must describe exactly what may execute, which parameters may vary, and
how results return to their owners. ComfyUI is a graph execution engine; a local service can become
a Soulstone when LychD owns its container, queue, readiness, GPU placement, model mounts, and
lifecycle. Several semantic owners may use that engine.

This native adapter is a **Designed** candidate. No native ServiceJob adapter or admitted visual
byte path is delivered;
[State of Work](../../../../state-of-the-work.md#vision-admission) owns delivery status.
The separate [Workbench engineering probe](../../../../compositions/riffmaw/workbench.md)
exercises classic-server submission/reconciliation and bounded retrieval outside native admission.
Its mock-transport evidence does not prove a running server, model closure, generation or semantic
acceptance. [State](../../../../state-of-the-work.md#music-comfy-engineering-probes) owns that subset.

## Keep model, engine, and road apart

Begin with the operation and the owner that will judge its result. That domain's immutable
semantic profile pins request and result schemas, model or voice identity, languages, formats,
license, limits, and bake evidence. Each engine or provider implementation then pins this exact
semantic revision together with its dialect, runtime, placement, and evidence.

This comparison must reach beyond a familiar model name. Local open-weight MiniMax Music and the
hosted MiniMax API remain different routes unless exact model, protocol, and evidence establish
equivalence. The [engine and semantic-owner map](index.md#engine-versus-technical-contract-and-semantic-owner)
explains the shared division of responsibility.

The preset is the complete program you are admitting: immutable editor/API graph, node and
custom-node closure, model files, permitted parameter openings, output mapping and paths,
network behavior, container revision, and licenses. [Assimilation](../../../../adr/35-assimilation.md)
must admit that program before execution. A caller can then choose the preset and its permitted
parameters. Arbitrary caller graphs, partner/cloud nodes, runtime downloads, and ambient
custom-node installation remain closed.

The Soulstone Rune pins the local container, endpoint, devices, mounts, lifecycle, resources, and
admitted profile/preset references. A Portal requires separate admission of provider, endpoint,
dialect, credentials, custody, cost, and reconciliation. A local pack name proves no remote
equivalence.

[Scroll placement](../../../extensions/weaver/pattern-lifecycle.md) pins the semantic Spell request,
result, authority, recovery, and finish. Its
Resolution Lock pins the chosen exact local Soulstone or Portal implementation. Comfy editor state
is not a Scroll.

## Pin the dialect and execution lifecycle

The official external [Comfy API v2](https://docs.comfy.org/api-reference/v2/overview) is exposed
by cloud and serverless services. Self-hosting that v2 API currently requires a
separately pinned `comfy-api-proxy` alongside ordinary ComfyUI; its default loopback arrangement
connects proxy port 8189 to ComfyUI port 8188. A deployment choosing that dialect therefore pins
both services. The [classic server](https://docs.comfy.org/development/comfyui-server/comms_routes),
including `/prompt`, `/history`, `/queue`, `/interrupt`, and WebSocket communication, remains a
distinct dialect.

Before relying on job recovery, pin the chosen route's authentication, retention, and restart
behavior. The [v2 submission](https://docs.comfy.org/api-reference/v2/jobs/submit-a-workflow-for-execution)
contract uses a single-use `Idempotency-Key`: a duplicate is rejected, rather than returning the
previous response. The self-hosted proxy needs persistent
[`--state-dir` storage](https://github.com/Comfy-Org/comfy-api-proxy/blob/main/docs/batch-workloads.md#persistence---state-dir)
for its own records, which does not preserve ComfyUI queue/history or output bytes after restart.
If submission is ambiguous, look it up before deciding recovery. Blind retry is inadmissible:
it cannot resolve the missing account.

An admitted adapter must supply upload, submit, queue, progress, history, output, interruption,
cancellation-request, and reconciliation facts. Core alone owns `ServiceJobAttempt@1`; the domain
job links that attempt. LychD retains authority, custody, retry law, and canonical provenance.
Filenames and PNG metadata may support evidence, but cannot serve as durable identity.

## Measure each admitted profile

GPU placement belongs to an exact profile and instance. Separate `comfy-qwen` and `comfy-ltx`
instances may use separate GPUs. An experimental multi-GPU instance requires explicit device nodes
and a measured profile. Neither arrangement implies parallelism, pooled VRAM, residency, or
batching.

Candidate profiles begin with Qwen [image/edit](../../../extensions/prism/image.md), LTX-2.5 or Wan
[video](../../../extensions/prism/video.md), and MiniMax Music 3. Exact speech, role-qualified
sound, and [Form](../../../extensions/prism/form.md) profiles follow. Each must independently prove
inputs and outputs, languages, limits, cancellation, VRAM and offload behavior, licenses, and
artifact validation. Evidence for one profile does not admit another.

## Preserve compound results through handoff

For native synchronized video and sound, the exact Prism `VideoJob@2` receives provider identity,
the compound container digest, child streams, shared timebase, and engine facts. Sound is enabled
only after `MediaFacetAuthoritySet@1` declares every requested role, the consuming Composition
identity and revision, and the owner-request digest. Follow Prism's
[compound-facet admission](../../../extensions/prism/video.md#admit-every-compound-facet) for
detailed sound preflight and inseparable-facet behavior.

Prism links the Core attempt; Reliquary owns custody and provenance. Each requested facet needs
its consuming owner's independent `SemanticFacetAdmissionReceipt@1` under the linked Video
contract. Unexpected sound is quarantined or deleted rather than assigned a guessed owner.

Broadcast alone judges the final editorial audiovisual relation. Engine completion supplies
execution facts; passage to an application still requires the exact profile's artifact validation,
preserved custody and provenance, and each requested facet's independent semantic admission.
