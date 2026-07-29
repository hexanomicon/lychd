---
title: 36. Vision
icon: material/eye-settings-outline
---

# :material-eye-settings-outline: 36. The Vision Prism

!!! abstract "Context and Problem Statement"
    Interpreting terminal output, structural diagrams, and graphical user interfaces depends on the ingestion and analysis of pixel data. Vision Language Models (VLMs) impose significant VRAM demands, creating a physical resource conflict with high-tier reasoning models on consumer-grade hardware. A static infrastructure model results in either systemic OOM failures or permanent "blindness." Additionally, visual services operate in a dual capacity: providing model-backed Animator capabilities and specialized tool capabilities. This duality necessitates an orchestration strategy that manages sight as a stateful, dynamically dispatched capability without destabilizing the machine’s primary cognitive loop.

## Requirements

- **Independent Manifestation:** OCR, a dedicated VLM, multimodal chat, deterministic transforms,
  generation, and editing remain independently selectable capabilities. A named Coven may group
  compatible local services for operator convenience but is not the unit of semantic dispatch.
- **Provider-Tool Segmentation:** Provision of a mechanism to distinguish between model-backed **Animator** capabilities and tool-style **Animator** capabilities during the discovery phase.
- **The Stasis Trigger:** Mandatory integration with the **[Dispatcher (22)](22-dispatcher.md)**. When a vision tool is invoked while the hardware is "Cold," it must raise the `HardwareTransitionRequired` signal to freeze the cognitive thread via the **[Stasis Protocol (22)](22-dispatcher.md)**.
- **Multimodal Context Integration:** Authorized artifact materialization followed by
  provider-native conversion. Pydantic AI **`BinaryContent`** is one adapter representation, not
  the storage or universal interchange format.
- **Dynamic VRAM Budgeting:** Support for model tiering and declared coexistence so a small visual
  provider may remain beside a reasoning provider when the measured resource envelope permits it.
- **Declared Transformation:** Decode, orientation, resize, crop, and normalization steps must be
  explicit, reproducible where possible, and record provenance plus information loss.
- **Sovereign Optic Wall:** Classification and Ward policy determine provider eligibility.
  Summarization never launders restricted pixels into automatically safe egress.

## Considered Options

!!! failure "Option 1: Specialized Vision Sidecars"
    Running a separate, permanent vision container alongside the primary reasoning model.

    -   **Cons:** **Catastrophic VRAM Contention.** Running two massive models (e.g., a 70B Reasoner and a 13B VLM) simultaneously is impossible on consumer-grade hardware. It violates the **[Law of Exclusivity (08)](08-containers.md)**.

!!! failure "Option 2: Pure Cloud Vision (GPT-4o / Claude 3.5)"
    Offloading all visual processing to external Portals.

    -   **Cons:** **The Breach of Privacy.** Sending screenshots of private code or internal infrastructure to the cloud is a violation of the **[Iron Pact (00)](00-license.md)**.

!!! success "Option 3: Independent Optic Capabilities"
    Treating visual work as a family/modality contract whose selected provider and declared
    dependencies are dynamically readied by the existing control plane.

    -   **Pros:**
        -   **Hardware Safety:** The Orchestrator ensures the selected heavy Eye is only resident when needed.
        -   **Logical Parallelism:** Utilizes the **Stasis Protocol** to allow the mind to "pause" while the eyes open, preserving thought continuity across hardware swaps.
        -   **Composability:** OCR, chat-with-image, generation, and a dedicated Eye can evolve and
            be admitted independently.

## Decision Outcome

**The Prism** is adopted as the visual-lifecycle Extension Domain. It governs artifact admission,
declared transformation, provider binding, grounded observation, and visual provenance. It does
not require a future atomic `vision.coven`.

!!! warning "Current multimodal floor is schema and admission, not execution"
    The implemented core has immutable `ArtifactRef`/`ArtifactContent` intent parts, MIME-to-modality
    projection, declared `modalities_in`/`modalities_out`, and Dispatcher subset filtering. It does
    not yet have an artifact blob store/materializer, Bridge upload surface, graph-state artifact
    propagation, `BinaryContent` conversion, image normalization/resize pipeline, Prism
    manifestation, OCR tool, or managed visual provider. The current Bridge workflow persists the
    intent shape but
    passes only its text `prompt` into the agent and requests no image modality. Sections below are
    target design; artifact references must not be mistaken for available bytes.

!!! note "The Two-Axis Law: Family vs Modality"
    A **family** names a routable service kind; **modalities** name what a capability admits. The
    `vision` family is reserved for the **dedicated** vision-analysis provider—the Eye. A general
    chat model that merely accepts images is not a member of this family: it is a
    **[Dispatcher (22)](22-dispatcher.md)** `chat` capability carrying
    `image ∈ modalities_in`. Intent resolution matches `(family, required_modalities)`; a
    multimodal chat model satisfies image work in place without being renamed or conscripting
    unrelated visual providers.

### 1. Planned Visual Manifestations

Prism may manifest through independently registered capabilities. Local providers may be rendered
as **[Quadlet services (08)](08-containers.md)** and may share an operator-facing Coven only when
their declared coexistence and resource profile permit it.

- **The Eye (`vlm.container`):** The primary model-backed Soulstone providing the VLM (e.g., LLaVA, Yi-VL), tagged with the `vision` capability.
- **The Scribe (`ocr.container`):** An optional, lightweight service for pure text extraction (e.g., Tesseract).
- **The Lens:** Deterministic decode, orientation, resize, crop, and normalization transforms.
- **Functional Overlap:** One service may declare both `vision` and `ocr` capabilities, but each
  declaration retains its own contract and support evidence.

### 2. Optic Dispatching & The Stasis Protocol

The Prism utilizes the **[Dispatcher (22)](22-dispatcher.md)** to manage the physical reality of sight:

- **The Animator (Provider):** When an Agent requires a Vision Model, the Dispatcher resolves the `vision` capability to a model-backed Animator.
- **The Handshake:**
    1. The Dispatcher queries the **Orchestrator**.
    2. If the selected managed capability is non-`WARM`, the Dispatcher raises
       `HardwareTransitionRequired`.
    3. **The Freeze:** The run enters **Live Stasis** and may take an opportunistic
       **[Phylactery (06)](06-persistence.md)** checkpoint. Serialization is not mandatory for this
       resident pause and does not create a Reanimation boundary.
    4. **The Swap:** The Orchestrator converges the selected provider and only its declared
       dependencies, draining actual conflicts.
    5. **The Thaw:** Once the selected service is warm, the same leased step proceeds.
- **The Tool (Capability):** Specialized tasks (e.g., `extract_text_from_image`) follow the exact same Stasis logic through their own Animator capability declarations, ensuring the Agent never attempts to use a tool that does not physically exist.

### 3. The Planned Pixel Pipeline

The extension will implement a pre-inference pipeline for high-fidelity observations:

1. **Admit:** The system creates an immutable artifact reference; the Reliquary validates media
   type, size, digest, classification, custody, and retention.
2. **Materialize:** Prism reads bytes only through an authorized port and rejects malformed or
   ineligible content.
3. **Transmute:** A selected Lens performs declared transforms, preserving the source and recording
   provenance plus loss.
4. **Bind:** The provider adapter encodes the admitted artifact as `BinaryContent`, Base64,
   tensor input, or a provider handle according to its native contract.
5. **Observe:** Output carries source attribution and uncertainty appropriate to OCR, detection,
   captioning, or generative transformation.

### 4. Orchestration of Sight

Visual intent has no automatic priority class. The admitting Pattern and operator policy declare
urgency; the **[Orchestrator (23)](23-orchestrator.md)** applies physical readiness law.

- **Tiered Sight:** If policy and measured capability claims permit it, Dispatcher may select a
  lower-tier Eye whose resource envelope can coexist with the active reasoning provider.
- **The Transition:** If a high-tier visual ritual is required, the Orchestrator executes the **Drain** protocol on the Reasoning Titan before manifesting the Vision Eye.

## Consequences

!!! success "Positive"
    - **Structural Awareness:** The Lich can interpret terminal output, UI errors, and diagrams as if it possessed a biological optic nerve.
    - **Resource Purity:** Independent capability declarations let the Dispatcher choose the
      smallest eligible provider for a specific task.
    - **Thought Continuity:** The Stasis Protocol ensures that "opening the eyes" does not kill the thought process, even if it takes 30 seconds to load the model.

!!! failure "Negative"
    - **State Swap Latency:** Activating a heavy dedicated Eye may introduce friction into
      interactive visual-inspection rituals.
    - **Context Pressure:** Visual tokens are expensive. Ingesting multiple artifacts can rapidly saturate the context window.
