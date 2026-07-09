---
title: 36. Vision
icon: material/eye-settings-outline
---

# :material-eye-settings-outline: 36. The Vision Prism

!!! abstract "Context and Problem Statement"
    Interpreting terminal output, structural diagrams, and graphical user interfaces depends on the ingestion and analysis of pixel data. Vision Language Models (VLMs) impose significant VRAM demands, creating a physical resource conflict with high-tier reasoning models on consumer-grade hardware. A static infrastructure model results in either systemic OOM failures or permanent "blindness." Additionally, visual services operate in a dual capacity: providing model-backed Animator capabilities and specialized tool capabilities. This duality necessitates an orchestration strategy that manages sight as a stateful, dynamically dispatched capability without destabilizing the machine’s primary cognitive loop.

## Requirements

- **Atomic Coven Manifestation:** Mandatory grouping of VLM, OCR, and pre-processing units into a single operational state to ensure hardware synchronicity.
- **Provider-Tool Segmentation:** Provision of a mechanism to distinguish between model-backed **Animator** capabilities and tool-style **Animator** capabilities during the discovery phase.
- **The Stasis Trigger:** Mandatory integration with the **[Dispatcher (22)](22-dispatcher.md)**. When a vision tool is invoked while the hardware is "Cold," it must raise the `HardwareTransitionRequired` signal to freeze the cognitive thread via the **[Stasis Protocol (22)](22-dispatcher.md)**.
- **Multimodal Context Integration:** Utilization of Pydantic AI’s native **`BinaryContent`** to facilitate the passage of pixel buffers into the reasoning cortex.
- **Dynamic VRAM Budgeting:** Support for model tiering to enable the concurrent manifestation of small Vision models alongside Reasoning models, minimizing full coven swaps.
- **Pre-Inference Optimization:** Provision of a pipeline to normalize and resize raw binary data to match model-specific resolutions, ensuring token efficiency.
- **Sovereign Optic Wall:** Mandatory physical restriction of sensitive visual data to local covens, with summarization logic acting as a gateway for optional cloud-bursting.

## Considered Options

!!! failure "Option 1: Specialized Vision Sidecars"
    Running a separate, permanent vision container alongside the primary reasoning model.

    -   **Cons:** **Catastrophic VRAM Contention.** Running two massive models (e.g., a 70B Reasoner and a 13B VLM) simultaneously is impossible on consumer-grade hardware. It violates the **[Law of Exclusivity (08)](08-containers.md)**.

!!! failure "Option 2: Pure Cloud Vision (GPT-4o / Claude 3.5)"
    Offloading all visual processing to external Portals.

    -   **Cons:** **The Breach of Privacy.** Sending screenshots of private code or internal infrastructure to the cloud is a violation of the **[Iron Pact (00)](00-license.md)**.

!!! success "Option 3: The Vision Coven (Stateful Sight)"
    Treating the entire vision capability as a dynamically activated operational state managed by the Sovereign.

    -   **Pros:**
        -   **Hardware Safety:** The Orchestrator ensures the heavy Vision Coven is only resident when needed.
        -   **Logical Parallelism:** Utilizes the **Stasis Protocol** to allow the mind to "pause" while the eyes open, preserving thought continuity across hardware swaps.
        -   **Unified Interface:** To the Agent, the `vision` capability works identically whether provided by a local Coven or an OpenAI Portal.

## Decision Outcome

**The Prism** is adopted as the target Vision Extension and reference shape for a future
`vision.coven`.

!!! warning "Current multimodal floor is schema and admission, not execution"
    The implemented core has immutable `ArtifactRef`/`ArtifactContent` intent parts, MIME-to-modality
    projection, declared `modalities_in`/`modalities_out`, and Dispatcher subset filtering. It does
    not yet have an artifact blob store/materializer, Bridge upload surface, graph-state artifact
    propagation, `BinaryContent` conversion, image normalization/resize pipeline, Prism extension,
    OCR tool, or generated Vision Coven. The current Bridge workflow persists the intent shape but
    passes only its text `prompt` into the agent and requests no image modality. Sections below are
    target design; artifact references must not be mistaken for available bytes.

!!! note "The Two-Axis Law: Family vs Modality"
    A **family** names a routable service kind; **modalities** name what a capability admits. The `vision` family is reserved for the **dedicated** vision-analysis provider — the Eye. A general chat model that merely accepts images is not a member of this family and does not conscript the Vision Coven: it is a **[Dispatcher (22)](22-dispatcher.md)** `chat` capability carrying `image ∈ modalities_in`. Covens exist only for dedicated providers. Intent resolution matches `(family, required_modalities)`; a multimodal chat model satisfies image work in place, without a coven swap.

### 1. The Planned Vision Coven (Body)

The Prism will manifest as a collection of **[Quadlet services (08)](08-containers.md)** managed as
a named operational group under Orchestrator policy.

- **The Eye (`vlm.container`):** The primary model-backed Soulstone providing the VLM (e.g., LLaVA, Yi-VL), tagged with the `vision` capability.
- **The Scribe (`ocr.container`):** An optional, lightweight service for pure text extraction (e.g., Tesseract).
- **Functional Overlap:** A powerful VLM service may declare both `vision` (Provider) and `ocr` (Tool) capabilities.

### 2. Optic Dispatching & The Stasis Protocol

The Prism utilizes the **[Dispatcher (22)](22-dispatcher.md)** to manage the physical reality of sight:

- **The Animator (Provider):** When an Agent requires a Vision Model, the Dispatcher resolves the `vision` capability to a model-backed Animator.
- **The Handshake:**
    1. The Dispatcher queries the **Orchestrator**.
    2. If the `vision.coven` is **COLD**, the Dispatcher raises `HardwareTransitionRequired`.
    3. **The Freeze:** The Agent's state is serialized to the **[Phylactery (06)](06-persistence.md)**. The Coven swap holds the run in **Live Stasis**; the serialization named here is the opportunistic checkpoint, not a Reanimation boundary — the loop remains resident and resumes itself.
    4. **The Swap:** The Orchestrator banishes the current coven and summons the Vision Coven.
    5. **The Thaw:** Once the Vision service is warm, the Agent rehydrates and proceeds with the `vision` model.
- **The Tool (Capability):** Specialized tasks (e.g., `extract_text_from_image`) follow the exact same Stasis logic through their own Animator capability declarations, ensuring the Agent never attempts to use a tool that does not physically exist.

### 3. The Planned Pixel Pipeline (`BinaryContent`)

The extension will implement a pre-inference pipeline for high-fidelity observations:

1. **Ingest:** The system receives raw binary data via the interface or a background **[Ghoul (14)](14-workers.md)**.
2. **Transmute:** The Prism resizes the image to the optimal resolution for the active service, minimizing token overhead.
3. **Observation:** The processed artifact is injected into the Agent's context as Pydantic AI **`BinaryContent`**.

### 4. Orchestration of Sight

In the logic of the **[Orchestrator (23)](23-orchestrator.md)**, visual intents are treated with high priority.

- **Tiered Sight:** If VRAM is constrained, the Orchestrator may manifest a lower-tier Vision Soulstone (e.g., Moondream) to allow a reasoning model to remain resident, avoiding a full coven swap.
- **The Transition:** If a high-tier visual ritual is required, the Orchestrator executes the **Drain** protocol on the Reasoning Titan before manifesting the Vision Eye.

## Consequences

!!! success "Positive"
    - **Structural Awareness:** The Lich can interpret terminal output, UI errors, and diagrams as if it possessed a biological optic nerve.
    - **Resource Purity:** The distinction between Providers and Tools allows the Dispatcher to choose the most VRAM-efficient container for a specific task.
    - **Thought Continuity:** The Stasis Protocol ensures that "opening the eyes" does not kill the thought process, even if it takes 30 seconds to load the model.

!!! failure "Negative"
    - **State Swap Latency:** Activating the Vision Coven is a heavy operation, potentially introducing friction into interactive scrying rituals.
    - **Context Pressure:** Visual tokens are expensive. Ingesting multiple artifacts can rapidly saturate the context window.
