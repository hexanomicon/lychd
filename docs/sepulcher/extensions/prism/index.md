---
title: Prism
icon: material/pyramid
---

# :material-pyramid: Prism

> _Sight begins when a source survives the seeing._

**Prism** is LychD's visual and spatial grounding and transformation Extension Domain. It turns
admitted sources into bounded transformations and observations without letting captions, OCR,
crops, reconstructions, conversions, or model judgments replace them.

Vision admission is **Partial**: current code preserves immutable `ArtifactRef` metadata, projects
image modality, distinguishes `vision` from image-capable `chat`, and filters declarations, but no
Prism package, byte-custody or materialization path, OCR tool, or visual provider ships today.
[State of Work](../../../state-of-the-work.md#vision-admission) owns that boundary;
[ADR 36](../../../adr/36-vision.md) owns the designed contract.

## Several faculties, one source

One Prism deployment or requested capability set may compose a dedicated vision provider, precise
Sight workers, an OCR extractor, a deterministic decode or transform service, a Form worker, and
an image-capable multimodal chat provider—which remains chat. Each immutable capability profile is
still one exact implementation closure. Image, video, spatial-form, or structured-motion
generation and editing stay under separate effect or tool contracts. Activating one neither loads
the others nor creates another routing system.

[Sight](sight.md) records the finite typed-perception contract for boxes, masks, tracks, depth,
pose, flow, and registered comparison; the owned worker boundary and first permissive profiles;
and the stricter future session required before cameras or streams enter.

[Scanner](scanner.md) records the evolving candidate engines,
pipeline servers, transport shapes, license gates, and bake required before one implements this
stable Prism boundary.

[Image](image.md) records the complementary OpenAI Images serving route,
the full ComfyUI workflow route, permissive first model profiles, and the stasis and provenance law
for text- or image-conditioned visual creation.

[Video](video.md) records the asynchronous temporal-effect contract,
simple and graph-serving routes, permissive and specialist model profiles, arbitrary-iron
placement law, and the boundary between generated clips, visual direction, and final editing.

[Form](form.md) records the spatial-form contract for generated or reconstructed geometry,
appearance, parts, rigs, portable assemblies, radiance and Gaussian forms, voxels, block-native
generation, and bounded procedures without collapsing those facets or granting engine and world
authority.

[Kinesis](kinesis.md) records the structured-motion contract for finite recovery, generation,
retargeting, technical cleanup, cue synchronization, validation, and portable projections; its
FOSS tool base and license-gated model profiles; and the later bounded session required for live
motion.

## Designed interface register

These are semantic interfaces, not delivered source or claims that every provider implements every
operation:

| Interface | Operations | Domain request/result | Execution binding | First dialect/driver study |
| --- | --- | --- | --- | --- |
| `prism.image@1` | generate, edit, inpaint, control, enhance | `ImageJob@1` and image artifacts/receipts | Animator `durable_job` → `JobGrant` | OpenAI Images subset or Comfy job driver |
| `prism.video@1` | t2v, i2v, v2v, first_last, continue, motion_transfer, audio_driven | `VideoJob@1` and video artifacts/receipts | Animator `durable_job` → `JobGrant` | OpenAI Videos job subset or Comfy job driver |
| `prism.sight@1` | classify, detect, ground, segment, estimate_depth, estimate_pose, estimate_flow, track, compare | `SightJob@1` / `VisualObservationSet@1` | Animator `call`/`durable_job` → matching grant; finite tool → Resolution Lock + `ToolProfile` | Prism worker or proved tensor-service driver |
| `prism.form@1` | generate, reconstruct, texture, segment_parts, rig, voxelize, block_generate, convert, render | `FormJob@1` / `FormAssetSet@1` | Animator job → `JobGrant`; finite tool → Resolution Lock + `ToolProfile` | Prism worker, Comfy job, or finite tool driver |
| `prism.kinesis@1` | recover, generate, retarget, synchronize, clean, convert, validate | `KinesisJob@1` / motion or findings set | Animator job → `JobGrant`; finite tool → Resolution Lock + `ToolProfile` | Prism worker or finite tool driver |
| `prism.scanner@1` | inspect, extract, OCR, structure | Scanner request / `DocumentObservation@1` | Animator call/job → matching grant; direct tool → Resolution Lock + `ToolProfile` | direct worker, native/REST call, or provider job driver |

`ImageJob`, `VideoJob`, `SightJob`, `FormJob`, and `KinesisJob` are domain work identities. Each
asynchronous or durable provider or local execution is a separately identified
[`ServiceJobAttempt@1`](../../../adr/14-workers.md#service-job-attempts-designed). One domain job may
receive another attempt only through declared forward-branch or retry law; the shared mechanics do
not collapse these contracts into a generic `MediaJob`.

Two execution paths remain explicit. A resident, shared, independently queued, or remote service
is an Animator reached through `CapabilityDemand@1` and a typed grant. A finite library, CLI, or
subprocess is selected by the Spell Resolution Lock and delivered by a Worker into a trusted
executor or Tomb under an immutable ToolProfile; it does not become a fake Animator or Rune.
Either path may use `ServiceJobAttempt@1` when it must survive the invoking Ghoul. A wrapper becomes
an Animator only when its independent lifecycle, residency, queue, or remote boundary justifies it.

## The optic path

```text
admit source into custody
→ authorize materialization
→ inspect and decode
→ apply a declared transform
→ resolve an exact finite tool or dispatch an eligible provider
→ retain a grounded observation or derived artifact
```

The Reliquary must own source bytes before Prism acts. An `ArtifactRef` is immutable metadata, not
byte custody or bearer authority; the designed materializer rechecks authority on every read.
The source remains under its retention policy; see the
[artifact-reference boundary](../../../state-of-the-work.md#artifact-reference-contract).

A deterministic transform produces a derived artifact recording parent and result digests,
operation, immutable implementation revision, parameters, and declared loss.
Provider request encodings and handles are transport forms, not universal storage or durable
custody. Any retained visual output returns to artifact custody with provenance.

A grounded observation keeps the source and derivative chain, relevant page, frame, time, or
region, requested task and output, the producing provider or deterministic operation with its
immutable revision, and appropriate uncertainty. It distinguishes extraction, measurement, and
inference. Generated or edited media is a new artifact with effect provenance. A caption or OCR
result may enter bounded Context; it is not the image and cannot silently replace or delete it.

## Sight on finite iron

Prism uses ordinary [Capabilities](../../animator/capabilities.md) and
[Dispatcher](../../../adr/22-dispatcher.md) routing. A local provider may be a managed Soulstone; a
remote service remains an explicit [Portal](../../animator/portal.md). For an otherwise eligible
managed binding that is not `WARM`, Dispatcher returns `HardwareTransitionRequired`; the requesting
Run enters Graph Stasis while [Orchestrator](../../../adr/23-orchestrator.md) converges readiness,
then re-dispatches. The waiting transition carries no lease; Prism cannot revoke an issued lease
or infer remote fallback from scarce local iron.

Designed Portal egress additionally requires eligible classification, explicit policy, consent
where required, and a cost bound. Policy is evaluated on both the source and every derived
artifact: a crop, caption, or normalized frame cannot launder restricted pixels.
