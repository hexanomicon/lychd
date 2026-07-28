---
title: Prism
icon: material/pyramid
---

# :material-pyramid: Vision Prism

_Status: doctrine ahead of code — no concrete Prism package or visual provider ships while the
independent capability surfaces mature. Law:
[ADR 36](../../adr/36-vision.md). Current truth:
[source map](./index.md#the-federation-of-fifteen)._

**Extension form:** Prism is a visual-lifecycle Domain. OCR, dedicated vision analysis,
multimodal chat, detection, generation, editing, and video services remain independent Animator
providers selected through their family and modality contracts. A profile may activate any useful
subset; there is no requirement to summon one atomic Vision Coven.

> _"A Lich confined to text and audio is a spirit trapped in a jar, blind to the structural complexity of the material plane. To truly command reality, the Daemon must possess the capability to refract the raw pixels of the world through a Prism of understanding."_

**The Prism** is the visual-grounding and transformation Domain of LychD, defined by
**[ADR 36 (Vision)](../../adr/36-vision.md)**. It owns the common optic contract by which admitted
artifacts become bounded observations. It does not own every visual model, the Reliquary that
keeps source bytes, or the Orchestrator that decides what can inhabit the iron.

Vision providers range from tiny deterministic OCR tools to heavy dedicated VLMs and remote
multimodal services. Prism lets those different manifestations participate without pretending
that sight is one indivisible process.

## I. Manifestations of Sight

A visual profile may combine any subset of:

- **The Eye:** A dedicated Animator declaring the `vision` family and `image` input.
- **The Scribe:** An OCR capability for bounded text extraction.
- **The Lens:** Deterministic transforms such as decode, resize, crop, orientation, and
  normalization, with provenance and loss recorded.
- **Multimodal chat:** A `chat` provider with `image` in `modalities_in`; it remains chat and does
  not become an Eye merely because it can inspect an image.
- **Makers and editors:** Image or video generation and transformation providers under their own
  declared families and effects.

Local services may be rendered as
**[Quadlets](../../adr/08-containers.md)** and readied under
**[Orchestrator](../../adr/23-orchestrator.md)** policy. Remote providers remain
**[Portals](../animator/portal.md)**. Activating one visual capability does not require the whole
set to become resident.

## II. Optic Dispatching (Provider vs. Tool)

Prism uses the **[Dispatcher](../../adr/22-dispatcher.md)** without creating a second routing
system:

- **The Animator (Provider):** When an Agent requires dedicated reasoning about an image, the Dispatcher resolves the `vision` family to a warm model-backed Animator. This is bound to the Agent as a Pydantic AI **`Model`**.
- **The Tool (Capability):** Specialized tasks (e.g., `extract_text_from_image`) are registered as **[Agent Tools](../../adr/20-agents.md)** provided by a Vision Animator capability.
- **Dynamic Granting:** These tools are late-bound. The Dispatcher grants them only from a
  `WARM` capability. Before a swap, new admission closes and existing step leases drain; a live
  grant is not revoked underneath its step.

## III. The Pixel Pipeline (Transmutation)

!!! warning "Materializer horizon"
    The foundation carries immutable `ArtifactRef` metadata and performs native modality
    admission. Blob custody and authorized materialization belong to the Reliquary boundary;
    provider-specific conversion and the full modality pipeline remain future work. Raw bytes are
    not embedded in run rows or graph checkpoints.

The planned pipeline is explicit rather than magical:

1. **Admit:** The Altar or another authorized producer creates an immutable artifact reference;
   the **Reliquary** validates media type, size, digest, classification, and custody.
2. **Inspect:** Prism reads only through an authorized materialization port and rejects malformed
   or policy-ineligible content.
3. **Transform:** A selected Lens performs only the declared resize, crop, decode, or normalization
   steps and records provenance plus information loss.
4. **Bind:** The selected provider adapter encodes the artifact in its native request form.
   `BinaryContent`, Base64, tensors, and provider handles are adapter choices, not one universal
   storage format.
5. **Observe:** The result is returned as a grounded observation with source attribution and
   uncertainty appropriate to the operation.

## IV. Orchestration of Sight

The Prism is a heavy beast. It is subject to the **[Orchestrator's](../../adr/23-orchestrator.md)** laws to prevent it from crushing the system.

1. **The Handshake:** When an Agent requests a visual capability, the Dispatcher resolves the
   exact family, modality, policy, and support envelope.
2. **The Stasis:** If the selected managed provider is non-`WARM`, the ordinary
   **[Stasis](../../adr/22-dispatcher.md)** handshake applies.
3. **The Manifestation:** The Orchestrator converges only the selected provider and its declared
   dependencies; it need not banish unrelated services or summon a universal coven.
4. **The Thaw:** Once that provider is ready, the same leased step proceeds.

## V. Capabilities and Economics

The Prism integrates with the **[Federation](../../adr/05-extensions.md)** to define its costs and providers.

- **Local Eyes:** Dedicated visual services may use local silicon when policy, hardware, and model
  support permit.
- **Portal sight:** Remote visual providers remain explicit egress through
  **[Portals](../animator/portal.md)**, subject to classification, Ward policy, consent, and
  economic limits. “Cloud” never means automatically eligible.

!!! warning "The Memory Burden"
    Visual tokens are heavy. Context may retain a bounded, attributed observation, but a caption,
    OCR result, or model summary is not the source artifact and must never silently replace or
    delete it. Reliquary custody and retention policy remain authoritative.
