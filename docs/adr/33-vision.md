---
title: 33. Vision
icon: material/camera
---

# :material-camera: 33. Vision: The Prism

### Abstract

!!! abstract "Context and Problem Statement"
    Interpreting terminal output, structural diagrams, and graphical user interfaces depends on the ingestion and analysis of pixel data. Vision Language Models (VLMs) impose significant VRAM demands, creating a physical resource conflict with high-tier reasoning models on consumer-grade hardware. A static infrastructure model results in either systemic OOM failures or permanent "blindness." Additionally, visual containers operate in a dual capacity: providing both raw inference (Animators) and specialized logic (Tools). This duality necessitates an orchestration strategy that manages sight as a stateful, dynamically dispatched capability without destabilizing the machine’s primary cognitive loop.

## Requirements

- **Atomic Coven Manifestation:** Mandatory grouping of VLM, OCR, and pre-processing units into a single operational state to ensure hardware synchronicity.
- **Provider-Tool Segmentation:** Provision of a mechanism to distinguish between **Animators** (Inference Providers) and **Tools** (Capability Functions) during the discovery phase.
- **Late-Binding Visual Arsenal:** Mandatory integration with the **[Dispatcher (20)](20-dispatcher.md)** to ensure visual tools are only perceiveable by the Agent when the physical hardware state matches the intent.
- **Multimodal Context Integration:** Utilization of Pydantic AI’s native **`BinaryContent`** to facilitate the passage of pixel buffers into the reasoning cortex.
- **Dynamic VRAM Budgeting:** Support for model tiering to enable the concurrent manifestation of small Vision models alongside Reasoning models, minimizing full coven swaps.
- **Pre-Inference Optimization:** Provision of a pipeline to normalize and resize raw binary data to match model-specific resolutions, ensuring token efficiency.
- **Sovereign Optic Wall:** Mandatory physical restriction of sensitive visual data to local covens, with summarization logic acting as a gateway for optional cloud-bursting.

## Considered Options

!!! failure "Option 1: Specialized Vision Sidecars"
    Running a separate, permanent vision container alongside the primary reasoning model.
    -   **Cons:** **Catastrophic VRAM Contention.** Running two massive models (e.g., a 70B Reasoner and a 13B VLM) simultaneously is impossible on consumer-grade hardware. It violates the **[Law of Exclusivity (08)](08-containers.md)** and leads to immediate system failure.

!!! failure "Option 2: Pure Cloud Vision (GPT-4o / Claude 3.5)"
    Offloading all visual processing to external Portals.
    -   **Cons:** **The Breach of Privacy.** Sending screenshots of private code or internal infrastructure to the cloud is a violation of the **[Iron Pact (00)](00-license.md)**. It introduces significant token costs and destroys the "Self-Contained" nature of the Daemon.

!!! success "Option 3: The Vision Coven"
    Treating the entire vision capability as a dynamically activated operational state managed by the Sovereign.
    -   **Pros:**
        -   **Hardware Safety:** The Orchestrator ensures the heavy Vision Coven is only resident when needed, terminating conflicting models to liberate VRAM.
        -   **Capability Cohesion:** A single intent can manifest the VLM, an OCR tool, and image preprocessors in a coordinated ritual.
        -   **Unified Interface:** To the Agent, the `vision-analysis` capability works identically whether provided by a local Coven or an OpenAI Portal.

## Decision Outcome

**The Prism** is adopted as the Vision Extension. It is implemented as the reference implementation of the `vision.coven`—a stateful capability for structural visual reasoning.

### 1. The Vision Coven (Body)

The Prism manifests as a collection of **[Runes (08)](08-containers.md)** managed as a mutually exclusive state. A single container body often serves multiple roles:

- **The Eye (`vlm.container`):** The primary Soulstone providing the VLM (e.g., LLaVA, Yi-VL), tagged with the `vision-analysis` capability.
- **The Scribe (`ocr.container`):** An optional, lightweight Rune for pure text extraction (e.g., Tesseract), allowing the Orchestrator to save VRAM if the Agent only requires OCR.
- **Functional Overlap:** A powerful VLM Rune may declare both `vision-analysis` (Provider) and `ocr` (Tool) capabilities, allowing the Dispatcher to maximize resource utility.

### 2. Optic Dispatching (Provider vs. Tool)

The Prism utilizes the **[Dispatcher (20)](20-dispatcher.md)** to manage the duality of visual capabilities within the **[ContainerRune (08)](08-containers.md)**:

- **The Animator (Provider):** When an Agent requires reasoning about an image, the Dispatcher resolves the `vision-analysis` tag to the active VLM. This is bound to the Agent as a Pydantic AI **`Model`**.
- **The Tool (Capability):** Specialized tasks (e.g., `extract_text_from_image`) are registered as **[Agent Tools (19)](19-agents.md)** provided by the Vision Rune.
- **Dynamic Granting:** These tools are "Late-Bound." They only appear in the Agent's arsenal when the Orchestrator confirms the physical Vision Coven is manifested and "Warm." When the machine swaps to a different state, the tools are revoked to prevent the mind from attempting to "see" while blind.

### 3. The Pixel Pipeline (`BinaryContent`)

The extension implements a pre-inference pipeline to ensure high-fidelity "Observations":

1. **Ingest:** The system receives raw binary data via the interface or a background **[Ghoul (14)](14-workers.md)**.
2. **Transmute:** The Prism resizes the image to the optimal resolution for the active Rune, minimizing token overhead.
3. **Observation:** The processed artifact is injected into the Agent's context as Pydantic AI **`BinaryContent`**. The Agent decodes this artifact, transforming raw pixels into structured textual memory or "Karma."

### 4. Orchestration of Sight

In the logic of the **[Orchestrator (21)](21-orchestrator.md)**, visual intents are treated with high priority.

- **Tiered Sight:** If VRAM is constrained, the Orchestrator may manifest a lower-tier Vision Soulstone (e.g., Moondream) to allow a reasoning model to remain resident, avoiding a full coven swap.
- **The Transition:** If a high-tier visual ritual is required, the Orchestrator executes the five-step transition, banishing the Reasoning Titan to make room for the Vision Eye.

## Consequences

!!! success "Positive"
    - **Structural Awareness:** The Lych can interpret terminal output, UI errors, and diagrams as if it possessed a biological optic nerve.
    - **Resource Purity:** The distinction between Providers and Tools allows the Dispatcher to choose the most VRAM-efficient container for a specific task.
    - **Privacy Sovereignty:** Sensitive visual data is processed locally, with only summarized meanings ever reaching a Cloud Portal if necessary.

!!! failure "Negative"
    - **State Swap Latency:** Activating the Vision Coven is a heavy operation (30-60s), potentially introducing friction into interactive scrying rituals.
    - **Context Pressure:** Visual tokens are expensive. Ingesting multiple artifacts can rapidly saturate the context window, requiring aggressive management by the **[Context Orchestrator (26)](26-context.md)**.
