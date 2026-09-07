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

This adapter is a **Designed** candidate. No LychD Comfy adapter or visual byte path is delivered;
[State of Work](../../../../state-of-the-work.md#vision-admission) owns delivery status.

## Keep model, engine, and road apart

An immutable semantic profile belongs to its domain and pins the operation, request and result
schemas, model or voice identity, languages, formats, license, limits, and bake evidence. Each
engine/provider implementation pins that exact semantic revision together with its dialect, runtime,
placement, and evidence. Local open-weight MiniMax Music and the hosted MiniMax API remain distinct
unless exact model, protocol, and evidence establish equivalence. The
[engine and semantic-owner map](index.md#engine-versus-technical-contract-and-semantic-owner)
supplies the shared division of responsibility.

A Comfy preset pins the immutable editor/API graph, complete node and custom-node closure, model
files, allowed parameter openings, output mapping and paths, network behavior, container revision, and license
set. The complete engine program must pass [Assimilation](../../../../adr/35-assimilation.md)
before execution. Callers select an admitted preset and its permitted parameters. Arbitrary caller
graphs, partner/cloud nodes, runtime downloads, and ambient custom-node installation fail closed.

The Soulstone Rune pins the local container, endpoint, devices, mounts, lifecycle, resources, and
admitted profile/preset references. A Portal requires separate admission of provider, endpoint,
dialect, credentials, custody, cost, and reconciliation. A local pack name proves no remote
equivalence.

[Scroll placement](../../../extensions/weaver/pattern-lifecycle.md) pins the semantic Spell request,
result, authority, recovery, and finish. Its
Resolution Lock pins the chosen exact local Soulstone or Portal implementation. Comfy editor state
is not a Scroll.

## Pin the dialect and execution lifecycle

The official external [Comfy API v2](https://docs.comfy.org/api-reference/v2/overview) is currently
beta 0.1.x, exposed by cloud and serverless services. Self-hosting that v2 API currently requires a
separately pinned `comfy-api-proxy` alongside ordinary ComfyUI; its default loopback arrangement
connects proxy port 8189 to ComfyUI port 8188. A deployment choosing that dialect therefore pins
both services. The [classic server](https://docs.comfy.org/development/comfyui-server/comms_routes),
including `/prompt`, `/history`, `/queue`, `/interrupt`, and WebSocket communication, remains a
distinct dialect.

Pin authentication and the exact behavior of the chosen route. For
[v2 submission](https://docs.comfy.org/api-reference/v2/jobs/submit-a-workflow-for-execution),
creation is durable until expiry, and a single-use `Idempotency-Key` rejects duplicate submission
rather than replaying a response. An ambiguous submit therefore requires lookup before deciding
recovery; blind retry is inadmissible.

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
