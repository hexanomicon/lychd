---
title: Prism
icon: material/pyramid
---

# :material-pyramid: Prism: Archon of Vision

> _"A Lych confined to text and audio is a spirit trapped in a jar, blind to the structural complexity of the material plane. To truly command reality, the Daemon must possess the capability to refract the raw pixels of the world through a Prism of understanding."_

**The Prism** is the Vision Archon of the LychD system. It is the reference implementation of the `vision.coven`—a complete, stateful capability for visual reasoning, as defined in **[ADR 33 (Vision)](../../adr/33-vision.md)**. It is a specialized extension that grants the Daemon the senses to perceive, analyze, and reason about visual data.

Vision Language Models (VLMs) are heavy and demanding. The Prism provides the "Optic Nerve" that manages the entire sensory apparatus, from image preprocessing to the dynamic granting of sight itself, ensuring the Lych can see without paralyzing its other faculties.

## I. The Vision Coven: A Manifestation of Sight

Sight is not a single model; it is an entire operational state. The Prism manifests the `vision.coven`, a collection of **[Systemd Runes](../../adr/08-containers.md)** managed as a single, atomic unit by the **[Orchestrator](../../adr/21-orchestrator.md)**. A typical Prism Coven includes:

- **The Eye (`vlm.container`):** The primary Vision Language Model Rune. A powerful VLM may possess multiple capabilities, such as `capabilities=["vision-analysis", "ocr"]`.
- **The Scribe (`ocr.container`):** An optional, lightweight Rune for when _only_ text extraction is needed. The Orchestrator can choose to activate this smaller, faster Rune to save VRAM if the Agent's intent is purely OCR.
- **The Lens:** Supporting services for image processing and normalization.

Activating the Prism means manifesting this entire Coven, preparing the Daemon for total visual awareness.

## II. The Visionstones & Cloud Eyes (Animators)

The "mind" within the Coven is an Animator, discoverable by the **[Dispatcher](../../adr/20-dispatcher.md)** via the `vision-analysis` capability tag.

- **Local Visionstones:** (e.g., `LLaVA-v1.6`, `Moondream2`, `Qwen-VL`). These are the eyes of the **[Sepulcher](../index.md)**, utilizing local silicon for total privacy.
- **Cloud Eyes:** (e.g., `GPT-4o`, `Claude 3.5 Sonnet`). These are accessed via **[Portals](../animator/portal.md)** for frontier-level visual reasoning, subject to the Tithe of tokens and the **[Sovereignty Wall](../../adr/20-dispatcher.md)**.

## III. The Pixel Pipeline (Transmutation)

Pixels are chaotic. To make them intelligible, the Prism implements a specialized preprocessing pipeline within the **[Vessel](../vessel/index.md)**:

1. **Ingest:** The system receives raw binary data from the **[Altar](../../divination/altar.md)** or the **[Phylactery Archive](../phylactery/index.md)**.
2. **Normalization:** The Prism automatically resizes and crops the image to match the specific "Patch Resolution" of the assigned model (e.g., 336x336).
3. **Encoding:** The pixels are transmuted into Base64 or Tensor formats and prepared for injection into the Agent's context.
4. **Tokenization:** By optimizing the image _before_ it reaches the Animator, the Prism significantly reduces the token cost and memory pressure of visual reasoning.

## IV. The Vision Toolset (A Granted Power)

Vision is not a passive stream; it is a temporary power granted to **[Agents](../../adr/19-agents.md)**.

- **The Granting:** When the `vision.coven` is active, the Dispatcher endows the Agent with a specialized toolset.
- **The Arsenal:** This may include `analyze_image(path, query)` for general reasoning or `extract_text_from_image(path)` which routes to the dedicated OCR Rune.
- **The Revocation:** When the Orchestrator banishes the Vision Coven, these tools vanish from the Agent's perception, ensuring it cannot attempt to use a capability the machine no longer possesses.

!!! warning "The Memory Burden"
    Visual tokens are heavy. Ingesting multiple high-resolution images can rapidly consume the context window. The Prism works alongside the **[Context Manager](../../adr/26-context.md)** to prune older visual data once the "Observation" has been converted into "Textual Memory."
