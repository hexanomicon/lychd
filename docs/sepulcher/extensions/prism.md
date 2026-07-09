---
title: Prism
icon: material/pyramid
---

# :material-pyramid: Vision Prism

_Status: doctrine ahead of code — the media substrate ships as the built-in `video` package while the full `vision.coven` surface matures. Law: [ADR 36](../../adr/36-vision.md). Current truth: [source map](./index.md#the-federation-of-fifteen)._

> _"A Lich confined to text and audio is a spirit trapped in a jar, blind to the structural complexity of the material plane. To truly command reality, the Daemon must possess the capability to refract the raw pixels of the world through a Prism of understanding."_

**The Prism** is the planned Vision Extension of the LychD system. It is the reference design for a
future `vision.coven`—a stateful capability for visual reasoning defined in
**[ADR 36 (Vision)](../../adr/36-vision.md)**.

Vision Language Models (VLMs) are heavy and demanding. The Prism provides the "Optic Nerve" that manages the entire sensory apparatus, from image preprocessing to the dynamic granting of sight itself, ensuring the Lich can see without paralyzing its other faculties.

## I. The Vision Coven: A Manifestation of Sight

Sight is not a single model; it is an entire operational state. The planned Prism groups local
**[Soulstones](../animator/soulstone.md)** rendered as **[Quadlet services](../../adr/08-containers.md)**
and readied under **[Orchestrator](../../adr/23-orchestrator.md)** policy. A typical Prism Coven includes:

- **The Eye (`vlm.container`):** The primary Vision Language Model Soulstone. A dedicated Eye declares the canonical `vision` family with `image` input; OCR may be a separately declared tool or capability rather than an invented `vision-analysis` family.
- **The Scribe (`ocr.container`):** An optional, lightweight Soulstone for when _only_ text extraction is needed. The Orchestrator can choose to activate this smaller, faster service to save VRAM if the Agent's intent is purely OCR.
- **The Lens:** Supporting services for image processing and normalization.

Activating the Prism means manifesting this entire Coven, preparing the Daemon for total visual awareness.

## II. Optic Dispatching (Provider vs. Tool)

The Prism utilizes the **[Dispatcher](../../adr/22-dispatcher.md)** to manage the duality of visual capabilities within the generated **[Quadlet manifests](../../adr/08-containers.md)**:

- **The Animator (Provider):** When an Agent requires dedicated reasoning about an image, the Dispatcher resolves the `vision` family to a warm model-backed Animator. This is bound to the Agent as a Pydantic AI **`Model`**.
- **The Tool (Capability):** Specialized tasks (e.g., `extract_text_from_image`) are registered as **[Agent Tools](../../adr/20-agents.md)** provided by a Vision Animator capability.
- **Dynamic Granting:** These tools are "Late-Bound." The Dispatcher grants them only from a `WARM` capability. Before a swap, new admission closes and existing step leases drain; a live grant is not revoked underneath its step.

## III. The Pixel Pipeline (Transmutation)

!!! warning "Materializer horizon"
    The foundation carries immutable `ArtifactRef` metadata and performs native modality
    admission. Blob storage, authorized materialization, normalization, provider-specific binary
    conversion, and the full Modality Zip pipeline below remain Prism work; raw bytes are not
    embedded in run rows or graph checkpoints.

Pixels are chaotic. To make them intelligible, the planned Prism materializer follows this preprocessing pipeline within the **[Vessel](../vessel/index.md)**:

1. **Ingest:** The system receives raw binary data from the **[Altar](../../divination/altar/)** or the **[Phylactery Archive](../phylactery/index.md)**.
2. **Normalization:** The Prism automatically resizes and crops the image to match the specific "Patch Resolution" of the assigned model (e.g., 336x336).
3. **Encoding:** The pixels are transmuted into Base64 or Tensor formats and prepared for injection into the Agent's context via Pydantic AI's **`BinaryContent`**.
4. **Tokenization:** By optimizing the image _before_ it reaches the Animator, the Prism significantly reduces the token cost and memory pressure of visual reasoning.

## IV. Orchestration of Sight

The Prism is a heavy beast. It is subject to the **[Orchestrator's](../../adr/23-orchestrator.md)** laws to prevent it from crushing the system.

1. **The Handshake:** When the Agent requests a Vision Tool, the Dispatcher selects semantically; a managed non-WARM phase emits HTR for the Graph to hand to the Orchestrator.
2. **The Stasis:** If the `vision.coven` is cold, the Agent enters **[Stasis](../../adr/22-dispatcher.md)**.
3. **The Manifestation:** The Orchestrator banishes the current coven and summons the Vision Coven.
4. **The Thaw:** Once the Vision Animator is warm, the Agent rehydrates and proceeds with the visual task.

## V. Capabilities and Economics

The Prism integrates with the **[Federation](../../adr/05-extensions.md)** to define its costs and providers.

- **Local Visionstones:** (e.g., `LLaVA-v1.6`, `Moondream2`, `Qwen-VL`). These are the eyes of the **[Sepulcher](../index.md)**, utilizing local silicon for total privacy.
- **Cloud Eyes:** (e.g., `GPT-4o`, `Claude 3.5 Sonnet`). These are accessed via **[Portals](../animator/portal.md)** for frontier-level visual reasoning, subject to the Tithe of tokens and the **[Sovereignty Wall](../../adr/09-security.md)**.

!!! warning "The Memory Burden"
    Visual tokens are heavy. Ingesting multiple high-resolution images can rapidly consume the context window. The Prism works alongside the **[Context Manager](../../adr/21-context.md)** to prune older visual data once the "Observation" has been converted into "Textual Memory."
