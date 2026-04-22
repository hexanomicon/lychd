---
title:  Prism
icon: material/pyramid
---

# :material-pyramid: Vision Prism

> _"A Lych confined to text and audio is a spirit trapped in a jar, blind to the structural complexity of the material plane. To truly command reality, the Daemon must possess the capability to refract the raw pixels of the world through a Prism of understanding."_

**The Prism** is the Vision Extension of the LychD system. It is the reference implementation of the `vision.coven`—a complete, stateful capability for visual reasoning, as defined in **[ADR 36 (Vision)](../../adr/36-vision.md)**.

Vision Language Models (VLMs) are heavy and demanding. The Prism provides the "Optic Nerve" that manages the entire sensory apparatus, from image preprocessing to the dynamic granting of sight itself, ensuring the Lych can see without paralyzing its other faculties.

## I. The Vision Coven: A Manifestation of Sight

Sight is not a single model; it is an entire operational state. The Prism manifests the `vision.coven`, a collection of **[Systemd Runes](../../adr/08-containers.md)** managed as a single, atomic unit by the **[Orchestrator](../../adr/23-orchestrator.md)**. A typical Prism Coven includes:

- **The Eye (`vlm.container`):** The primary Vision Language Model Rune. A powerful VLM may possess multiple capabilities, such as `capabilities=["vision-analysis", "ocr"]`.
- **The Scribe (`ocr.container`):** An optional, lightweight Rune for when _only_ text extraction is needed. The Orchestrator can choose to activate this smaller, faster Rune to save VRAM if the Agent's intent is purely OCR.
- **The Lens:** Supporting services for image processing and normalization.

Activating the Prism means manifesting this entire Coven, preparing the Daemon for total visual awareness.

## II. Optic Dispatching (Provider vs. Tool)

The Prism utilizes the **[Dispatcher](../../adr/22-dispatcher.md)** to manage the duality of visual capabilities within the **[ContainerRune](../../adr/08-containers.md)**:

- **The Animator (Provider):** When an Agent requires reasoning about an image, the Dispatcher resolves the `vision-analysis` tag to the active VLM. This is bound to the Agent as a Pydantic AI **`Model`**.
- **The Tool (Capability):** Specialized tasks (e.g., `extract_text_from_image`) are registered as **[Agent Tools](../../adr/20-agents.md)** provided by the Vision Rune.
- **Dynamic Granting:** These tools are "Late-Bound." They only appear in the Agent's arsenal when the Orchestrator confirms the physical Vision Coven is manifested and "Warm." When the machine swaps to a different state, the tools are revoked to prevent the mind from attempting to "see" while blind.

## III. The Pixel Pipeline (Transmutation)

Pixels are chaotic. To make them intelligible, the Prism implements a specialized preprocessing pipeline within the **[Vessel](../vessel/index.md)**:

1. **Ingest:** The system receives raw binary data from the **[Altar](../../divination/altar.md)** or the **[Phylactery Archive](../phylactery/index.md)**.
2. **Normalization:** The Prism automatically resizes and crops the image to match the specific "Patch Resolution" of the assigned model (e.g., 336x336).
3. **Encoding:** The pixels are transmuted into Base64 or Tensor formats and prepared for injection into the Agent's context via Pydantic AI's **`BinaryContent`**.
4. **Tokenization:** By optimizing the image _before_ it reaches the Animator, the Prism significantly reduces the token cost and memory pressure of visual reasoning.

## IV. Orchestration of Sight

The Prism is a heavy beast. It is subject to the **[Orchestrator's](../../adr/23-orchestrator.md)** laws to prevent it from crushing the system.

1. **The Handshake:** When the Agent requests a Vision Tool, the Dispatcher queries the Orchestrator.
2. **The Stasis:** If the `vision.coven` is cold, the Agent enters **[Stasis](../../adr/22-dispatcher.md)**.
3. **The Manifestation:** The Orchestrator banishes the current coven and summons the Vision Coven.
4. **The Thaw:** Once the Vision Rune is warm, the Agent rehydrates and proceeds with the visual task.

## V. Capabilities and Economics

The Prism integrates with the **[Federation](../../adr/05-extensions.md)** to define its costs and providers.

- **Local Visionstones:** (e.g., `LLaVA-v1.6`, `Moondream2`, `Qwen-VL`). These are the eyes of the **[Sepulcher](../index.md)**, utilizing local silicon for total privacy.
- **Cloud Eyes:** (e.g., `GPT-4o`, `Claude 3.5 Sonnet`). These are accessed via **[Portals](../animator/portal.md)** for frontier-level visual reasoning, subject to the Tithe of tokens and the **[Sovereignty Wall](../../adr/22-dispatcher.md)**.

!!! warning "The Memory Burden"
    Visual tokens are heavy. Ingesting multiple high-resolution images can rapidly consume the context window. The Prism works alongside the **[Context Manager](../../adr/21-context.md)** to prune older visual data once the "Observation" has been converted into "Textual Memory."
