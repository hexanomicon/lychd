---
title: Prism
icon: material/pyramid
---

# :material-pyramid: Prism

> _Sight begins when a source survives the seeing._

**Prism** is LychD's visual-grounding and transformation Extension Domain. It turns admitted
visual sources into bounded transformations and observations without letting captions, OCR,
crops, or model judgments replace them.

Vision admission is **Partial**: current code preserves immutable `ArtifactRef` metadata, projects
image modality, distinguishes `vision` from image-capable `chat`, and filters declarations, but no
Prism package, byte-custody or materialization path, OCR tool, or visual provider ships today.
[State of Work](../../state-of-the-work.md#vision-admission) owns that boundary;
[ADR 36](../../adr/36-vision.md) owns the designed contract.

## Several faculties, one source

One profile may compose a dedicated vision provider, an OCR extractor, a deterministic decode or
transform service, and an image-capable multimodal chat provider—which remains `chat`. Image or
video generation and editing stay under a separate effect contract. Activating one neither loads
the others nor creates another routing system.

## The optic path

```text
admit source into custody
→ authorize materialization
→ inspect and decode
→ apply a declared transform
→ dispatch an eligible provider
→ retain a grounded observation or derived artifact
```

The Reliquary must own source bytes before Prism acts. An `ArtifactRef` is immutable metadata, not
byte custody or bearer authority; the designed materializer rechecks authority on every read.
The source remains under its retention policy; see the
[artifact-reference boundary](../../state-of-the-work.md#artifact-reference-contract).

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

Prism uses ordinary [Capabilities](../animator/capabilities.md) and
[Dispatcher](../../adr/22-dispatcher.md) routing. A local provider may be a managed Soulstone; a
remote service remains an explicit [Portal](../animator/portal.md). If a selected managed
capability is not `WARM`, ordinary Graph Stasis and
[Orchestrator](../../adr/23-orchestrator.md) readiness apply. The waiting transition carries no
lease; Prism cannot revoke an issued lease or infer remote fallback from scarce local iron.

Designed Portal egress additionally requires eligible classification, explicit policy, consent
where required, and a cost bound. Policy is evaluated on both the source and every derived
artifact: a crop, caption, or normalized frame cannot launder restricted pixels.
