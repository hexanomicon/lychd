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

Choose the return needed by the consuming owner:

| Return | Passage |
| --- | --- |
| Text, regions, reading order, tables, or document derivatives | [Scanner](scanner.md). |
| Boxes, masks, depth, pose, flow, tracks, or registered change estimates | [Sight](sight.md), with a separate [Live Sight](live-sight.md) session for armed streams. |
| New or edited still-image candidates | [Image](image.md). |
| Generated or transformed moving-image candidates | [Video](video.md), including exact authorization and independent admission for native sound facets. |
| Geometry, appearance, parts, rigs, assemblies, or field representations | [Form](form.md); [Voxel and block export](voxel-and-block-export.md) follows bounded grids through schematic read-back. |
| Reusable motion curves, retargeted clips, or technical motion findings | [Kinesis](kinesis.md), with [Live Kinesis](live-kinesis.md) for bounded epoch-to-rig sessions. |

A deployment may combine these faculties, precise workers, deterministic
[Prism Lens transforms](../../../adr/36-vision.md#decision), and an image-capable multimodal Mind.
Each profile remains an exact implementation closure; the Mind remains chat, and activating one
service does not activate every faculty. Generation and editing
are separate effects from grounded observation.

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

## Designed interface register

These are semantic interfaces, not delivered source or claims that every provider implements every
operation:

| Interface and operation guide | Domain request/result | Execution binding |
| --- | --- | --- |
| [`prism.image@2`](image.md#one-job-explicit-operation) | `ImageJob@2` and image artifacts/receipts | Animator `durable_job` → `JobGrant` |
| [`prism.video@2`](video.md#one-temporal-job-several-proved-operations) | `VideoJob@2` and video artifacts/receipts | Animator `durable_job` → `JobGrant` |
| [`prism.sight@2`](sight.md#one-finite-job-exact-operation) | `SightJob@2` / `VisualObservationSet@1` | Animator `call`/`durable_job` → matching grant; finite tool → Resolution Lock + `ToolProfile` |
| [`prism.form@2`](form.md#one-form-job-explicit-operation) | `FormJob@2` / `FormAssetSet@1` | Animator job → `JobGrant`; finite tool → Resolution Lock + `ToolProfile` |
| [`prism.kinesis@2`](kinesis.md#one-finite-job-exact-operation) | `KinesisJob@2` / motion or findings set | Animator job → `JobGrant`; finite tool → Resolution Lock + `ToolProfile` |
| [`prism.scanner@1`](scanner.md#what-the-scanner-route-actually-owes): inspect, extract, OCR, structure | Scanner request / `DocumentObservation@1` | Animator call/job → matching grant; direct tool → Resolution Lock + `ToolProfile` |

Each leaf gives its operations and candidate dialect/driver studies.

The Designed-only `prism.image@1`, `prism.video@1`, `prism.sight@1`, `prism.form@1`, and
`prism.kinesis@1` interfaces and their corresponding `*Job@1` request meanings remain historical.
Revision `2` separates Prism technical result settlement from a consuming Composition's semantic
adoption; Kinesis additionally replaces the former generic sonic-cue input with exact musical cue
and clock contracts. No capability registry, domain job, or service attempt used the `@1` designs,
so there is no executable migration. `prism.scanner@1` is unchanged.

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
