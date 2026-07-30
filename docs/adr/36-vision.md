---
title: 36. Vision
icon: material/eye-settings-outline
---

# :material-eye-settings-outline: 36. Vision

!!! abstract "Context"
    An image is a source with a history, not an oversized prompt. Seeing it needs custody,
    authorization, hostile-media handling, declared transformation, and an observation that can
    still name what was seen.

## Status

Vision admission is **Partial**. The current core carries immutable `ArtifactRef` metadata in an
`Intent`, projects image media types to the `image` modality, distinguishes the dedicated
`vision` family from image-capable `chat`, and filters declarations by required input modality.

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
| **Eye** | Dedicated analysis through the `vision` family. |
| **Multimodal Mind** | A `chat` capability with `image` in `modalities_in`; it remains chat. |
| **Scribe** | OCR with text regions and source coordinates. |
| **Lens** | Deterministic decode, orientation, crop, resize, or normalization. |
| **Maker/editor** | Image generation or mutation through a separate effect contract. |

A Coven may group compatible local services for operation. It is not a dispatch unit: manifesting
one visual faculty does not manifest the rest.

## Custody before sight

The Reliquary owns source bytes before Prism acts. Its durable reference binds artifact identity
and SHA-256 digest, media type and byte size, classification and owning Principal, plus custody
and retention policy. The future materializer rechecks authority on every read. `ArtifactRef` is
neither byte custody nor a bearer token; a provider URL is neither durable custody nor permission.

Decoders receive hostile input. Admission bounds supported formats, dimensions, frames, pages,
decompression, metadata, and parser resources. Media-type labels are claims to verify. Embedded
links, profiles, scripts, and metadata receive no network or execution authority.

## One optic path

```text
admit source → authorize materialization → inspect and decode → apply declared Lens transforms
→ dispatch eligible provider → retain grounded observation or derivative
```

Each Lens transformation records its exact parent, operation and implementation revision,
parameters, result artifact and digest, and loss from crop, resize, compression, frame selection,
or color conversion. The source remains available according to retention policy; a thumbnail,
OCR result, or caption cannot silently replace it.

Provider adapters may use Pydantic AI `BinaryContent`, Base64, a tensor, or a provider handle.
Those are request representations, never the universal artifact format.

## Dispatch, egress, and result

A Pattern asks for exact capability and material: analysis is `vision` plus `image`; general
reasoning can be `chat` plus `image`; OCR and deterministic transforms require their own declared
service or tool contracts. The [Dispatcher](22-dispatcher.md) admits only an eligible capability.
An unwarm managed provider follows ordinary Graph Stasis and [Orchestrator](23-orchestrator.md)
readiness through `HardwareTransitionRequired`; a live pause need not become a Reanimation
boundary. Prism cannot evict a provider, revoke a lease, raise priority, or infer remote fallback.
Declared coexistence and measured operator evidence, not a universal VRAM formula, decide whether
visual and reasoning providers can remain resident together.

A Portal additionally needs source-and-derivative classification eligibility, explicit egress
policy, consent where required, and a cost bound. A caption cannot launder restricted pixels;
[Security](09-security.md#portal-privatization-and-egress) evaluates every source and derivative.

A grounded observation names the source and derivative chain; relevant page, frame, time, or
region; task; producing provider or deterministic revision; output; and suitable uncertainty. It
also says whether it is extraction, geometrical measurement, or inference. OCR is attributed
extraction, a caption interpretation, and generated or edited imagery a new artifact with effect
provenance. Fluent output never becomes source truth.

## Consequences and acceptance

Prism keeps vision, multimodal chat, OCR, transforms, and generation composable while preserving
the path from result to source. It also makes custody, safe decoding, derivative storage,
retention, and provider loss first-class costs.

It cannot move beyond the current schema seam until focused evidence proves upload and custody,
principal-bound materialization, hostile-media limits, transform lineage, modality forwarding,
local and Portal policy, provider conversion, grounded results, retention/deletion, and failure
recovery.
