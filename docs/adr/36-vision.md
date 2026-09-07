---
title: 36. Vision
icon: material/eye-settings-outline
---

# :material-eye-settings-outline: 36. Vision

!!! abstract "Context"
    A visual source is material with a history, not an oversized prompt. Seeing or transforming
    an image, video, document, or spatial form needs custody, authorization, hostile-media
    handling, declared transformation, and a result that can still name what it used.

## Status

Vision admission is **Partial**. The current v1 compatibility spine defines immutable `ArtifactRef`
metadata, projects image media types to the `image` modality, distinguishes the closed `vision`
family from image-capable `chat`, and filters capability declarations by required input modality.
Delegated-job contracts can carry artifact references; the current `Intent` and Bridge admission
remain text-only and carry neither artifacts nor required modalities through the Run ledger.
These shapes prove metadata and routing contracts, not an executable visual interface.

It does **not** upload, store, authorize, materialize, decode, normalize, or transport image
bytes. Bridge does not forward artifact modalities into dispatch. No Prism package, Reliquary
backend, OCR tool, or managed visual provider ships. [State of
Work](../state-of-the-work.md#vision-admission) owns that boundary.

## Decision

**Prism** is the visual-grounding and transformation Domain. It turns an admitted source artifact
into bounded derivatives and observations while retaining source identity, classification,
provenance, and declared information loss.

| Faculty | Contract |
| --- | --- |
| **Eye (Prism)** | Dedicated general visual analysis; current v1 projects this as the `vision` family. |
| **Multimodal Mind** | A `model.chat@1` profile with image input; current v1 projects `chat` plus `image` in `modalities_in`, and it remains chat. |
| **Sight** | Finite typed estimates such as regions, masks, tracks, depth, pose, flow, and registered change under a dedicated perception contract; later live sources require a separate bounded session. |
| **Scanner** | Source-grounded document extraction through native parsing, OCR, layout, reading order, and structured reconstruction. |
| **Lens (Prism)** | Deterministic decode, orientation, crop, resize, or normalization. |
| **Maker/editor** | Text- or source-conditioned image and time-based video generation or mutation producing new artifacts through separate effect contracts. |
| **Form** | Bounded generation, reconstruction, texturing, structural decomposition, rigging, rendering, and representation conversion of spatial material through separate tool or effect contracts. |
| **Kinesis** | Bounded recovery, generation, retargeting, cleanup, synchronization, validation, and conversion of structured motion through a dedicated finite-job contract. |

Here Eye and Lens name Prism faculties. An external [observability Eye](29-observability.md)
consumes bounded evidence exports; a [Shadow Lens](20-agents.md#mechanical-cognitive-postures)
seeds a speculative branch with a Posture. Their owners and contracts remain distinct.

### Language and faculty admission

Visual language is typed per job, not inherited from the host or Altar locale. Original prompt,
requested model-facing language, permitted detection, translation or enhancement revision, and
declared loss remain separate facts. A translated prompt is a derivative instruction, not a
replacement for the operator's visual direction; a model that happens to understand a language
has not passed the image, video, typography, or control bake for that language.

A Coven may group compatible local services for operation. It is not a dispatch unit: manifesting
one visual faculty does not manifest the rest.

Form does not establish a universal `spatial` Dispatcher family. Each future implementation must
declare its exact operation, accepted modalities, produced artifact facets, tool or effect
semantics, and recovery contract; a repository that can emit a mesh is not thereby a general 3D
runtime.

### Finite and live perception

Sight likewise does not establish another capability family or turn image-capable chat into
precise perception. A finite Sight result binds every estimate to original source pixels and, for
video, exact frame identity, PTS, and rational timebase through the full transform chain. Masks,
depth and flow remain typed derivative artifacts; confidence is model evidence rather than a
universal probability; a local track id is not identity; and an uncovered region or skipped frame
cannot prove absence.

A camera or feed is not a finite `SightJob` extended indefinitely. Its future session binds capture
purpose and authority, source and stream epoch, privacy masks, active window, viewers, retention,
bounded queues, sampling and drop policy, gaps, and downstream consumers. A proved contiguous
transport reconnect may continue the same epoch; otherwise reconnect closes it, and every new
epoch receives a new track namespace. Observation grants no PTZ, recording, robot, game, or other
effect authority.

### Spatial form, motion, and engine use

Form owns the exact skeleton, hierarchy, rest and bind pose, skinning, morph controls, and rig
revision. Kinesis owns structured curves and their technical motion derivatives. A pose
observation is not a motion clip; a rig is not proof of compatible animation; moving pixels are
not reusable curves; and a clip is not an engine controller or an authorized world effect.
`KinesisJob@2` acts on finite admitted material and returns a typed `MotionAssetSet@1` or, for
validation, `MotionFindingSet@1`; later live motion requires a separate `LiveKinesisSession@2`
with bounded queues, clock and calibration epochs, drop policy, consent, retention, and consumers.
Neither contract inherits source capture, creative acceptance, engine, avatar, robot, or
publication authority.

A portable Form assembly remains spatial material rather than a playable engine world. Foundry
owns engine-native scene hierarchy, placements, collision and physics meaning, navigation,
streaming, animation-controller use, gameplay bindings, scenario evidence, and build derivatives.
Import or a beauty render proves none of those facts.

## Custody before sight

The Reliquary owns source bytes before Prism acts. Its durable reference binds artifact identity
and SHA-256 digest, media type and byte size, classification and owning Principal, plus custody
and retention policy. The future materializer rechecks authority on every read. `ArtifactRef` is
neither byte custody nor a bearer token; a provider URL is neither durable custody nor permission.

Decoders receive hostile input. Admission bounds supported formats, dimensions, frames, pages,
geometry, vertices, faces, nodes, materials, textures, scene depth, animation channels, bone
influences, points, splats, voxels, archive expansion, decompression, metadata, and parser or
compute resources. Media-type labels are claims to verify. Embedded links, external URIs,
profiles, scripts, drivers, plug-ins, scene procedures, and metadata receive no network or
execution authority.

## One optic path

```text
admit source → authorize materialization → inspect and decode → admit declared transform or effect
→ resolve an exact finite tool or dispatch an eligible provider → retain grounded observation or derivative
```

Each Prism Lens transformation records its exact parent, operation and implementation revision,
parameters, result artifact and digest, and loss from crop, resize, compression, frame selection,
or color conversion. The source remains available according to retention policy; a thumbnail,
OCR result, or caption cannot silently replace it.

Provider adapters may use Pydantic AI `BinaryContent`, Base64, a tensor, or a provider handle.
Those are request representations, never the universal artifact format.

## Dispatch, egress, and result

A Pattern asks for an exact semantic interface, operation, typed material, and feature facts.
Current v1 can only project general analysis as `vision` plus `image` and general reasoning as
`chat` plus `image`; precise Sight, Scanner, Lens, Image, Video, Form, and Kinesis work requires its
own declared service or tool contract. Generated visual output never arises merely because a chat
capability accepts visual input. The
[Dispatcher](22-dispatcher.md) admits only an eligible capability.
For an otherwise eligible managed binding that is not `WARM`, Dispatcher returns
`HardwareTransitionRequired`; the requesting Run enters Graph Stasis while
[Orchestrator](23-orchestrator.md) converges readiness, then re-dispatches. In current source,
however, even a `WARM` v1 `vision` declaration fails closed at grant issue because no typed visual
surface exists; readiness convergence cannot manufacture one. A live pause need not become a
Reanimation boundary. Prism cannot evict a provider, revoke a lease, raise priority, or infer
remote fallback.
Declared coexistence and measured operator evidence, not a universal VRAM formula, decide whether
visual and reasoning providers can remain resident together.

A Portal additionally needs source-and-derivative classification eligibility, explicit egress
policy, consent where required, and a cost bound. A caption cannot launder restricted pixels;
[Security](09-security.md#portal-privatization-and-egress) evaluates every source and derivative.

A grounded observation names the source and derivative chain; relevant page, frame, time, or
region; task; producing provider or deterministic revision; output; and suitable uncertainty. It
also says whether it is extraction, deterministic geometrical measurement, learned estimate, or
interpretation. OCR is attributed extraction, a caption interpretation, and generated or edited
image, video, audio-video, mesh, scene, voxel, or structured-motion material a new artifact set
with effect provenance. Fluent output never becomes source truth, and conversion between spatial
or motion representations creates a new derivative with declared loss.

### Compound media and application acceptance

Synchronized audio and video from a provider belong to one technical attempt and one compound
provenance parent. Before execution, `MediaFacetAuthoritySet@1` names every requested semantic
role, its owning Composition identity and revision, and the exact owner-request digest. Prism
records the container, stream digests, shared timebase and technical settlement.

Each declared owner then issues its own `SemanticFacetAdmissionReceipt@1` before that facet may
enter application truth:

- Voidlight judges visual and VFX material;
- Riffmaw judges music;
- Language Edition judges timed-language material;
- Foundry judges interactive world sound; and
- Broadcast judges picture-bound sound and the final editorial audiovisual relation.

An undeclared facet fails closed. Inseparable streams must be accepted or refused for their
declared compound use. Neither the provider's output shape nor a `generate_sound` flag supplies
an owner's judgment.

## Consequences and acceptance

Prism keeps vision, multimodal chat, OCR, transforms, and generation composable while preserving
the path from result to source. It also makes custody, safe decoding, derivative storage,
retention, and provider loss first-class costs.

It cannot move beyond the current schema seam until focused evidence proves upload and custody,
principal-bound materialization, hostile-media limits, transform lineage, modality forwarding,
local and Portal policy, provider conversion, grounded results, retention/deletion, and failure
recovery.
