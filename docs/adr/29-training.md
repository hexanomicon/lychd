---
title: 29. Training
icon: material/anvil
---

# :material-anvil: 29. Training: The Soulforge

!!! abstract "Context and Problem Statement"
    The LychD system accumulates vast quantities of cognitive history—interaction logs, tool outputs, and user corrections stored as "Karma" in the **[Phylactery (06)](06-persistence.md)**. While external retrieval allows the Agent to consult these memories, it remains a resource-intensive process that consumes context tokens and introduces high latency. Relying solely on external memory creates a "Cognitive Ceiling" where the machine never truly learns, only imitates based on provided snippets. A fundamental gap exists in the transition from dynamic history to static weights: the machine requires a mechanism to transmute verified memories into instinct, internalizing a Persona's specific domain and style into the model substrate.

## Requirements

- **Instinctual Transmutation:** Support for Parameter-Efficient Fine-Tuning (LoRA/QLoRA) to bake behavioral patterns and specialized knowledge into the model's fundamental reasoning loop.
- **High-Order Ritual Priority:** Mandatory integration with the **[Orchestrator (21)](21-orchestrator.md)** to treat training as a "Ritual of the Highest Order," granting it the authority to preempt all other hardware tasks.
- **Total Resource Devotion:** The system must ensure the GPU VRAM is completely evacuated of inference Covens before the training ritual begins to prevent OOM failure.
- **Anatomical Harvesting:** Capability to extract high-quality "Karma" (verified outcomes) from the database chambers and format it into structured training manifests.
- **Shadow-Realm Fabrication:** The training process must occur within a specialized, ephemeral **[Coven (08)](08-containers.md)** (e.g., Unsloth) isolated from the primary Vessel's execution.
- **Mandatory Verification:** Post-training rituals must include a verification phase where the new adapter is benchmarked to ensure it has not suffered "Catastrophic Forgetting."
- **Multi-Adapter Servo:** The inference engine (e.g., vLLM) must be capable of hosting multiple LoRA adapters simultaneously, allowing for the concurrent manifestation of diverse, specialized Personas.

## Considered Options

!!! failure "Option 1: Perpetual Retrieval (RAG Only)"
    Relying exclusively on vector search and large context windows to guide the Agent.
    -   **Cons:** **The Instruction Tax.** As the Phylactery grows, retrieval becomes noisier and context tokens become more expensive. The model never "learns" a complex style; it merely imitates it based on provided snippets, limiting the potential for true Autopoiesis.

!!! failure "Option 2: External Portal Training"
    Exporting cognitive history to cloud-based fine-tuning services.
    -   **Cons:** **The Breach of Sovereignty.** Requires moving the Magus's private interactions to untrusted environments. It breaks the "Self-Contained" nature of the Daemon and locks the Soul into a proprietary vendor.

!!! success "Option 3: Integrated Soulforge (Unsloth / vLLM Multi-LoRA)"
    Utilizing high-efficiency local containers for training, managed by the Sovereign Orchestrator.
    -   **Pros:**
        -   **Mathematical Immortality:** The Magus's style and knowledge are baked into the weights, surviving even the deletion of the original documents.
        -   **VRAM Efficiency:** Techniques like Unsloth provide 2x speed and 70% less memory usage, making local training viable on consumer silicon.
        -   **Hot-Swappable Instincts:** vLLM allows the Lych to possess multiple specialized instincts (Adapters) on a single base model, switching between them with near-zero latency.

## Decision Outcome

**The Soulforge** is adopted as the Training Extension. It provides the reference implementation for instinctual evolution, transforming "Karma" into "Weights."

### 1. The Harvesting of Karma (Preparation)

The ritual begins at **[The Altar (15)](15-frontend.md)**. The Magus submits a Training Intent, which enqueues a job for the **[Ghouls (14)](14-workers.md)**.

- **The Extraction:** A Ghoul scans the `vectors` chamber for "White Truths" (consecrated outcomes from the **[Shadow Realm (25)](25-hitl.md)**).
- **The Golden Paths:** It identifies the reasoning steps that led to success and transmutes them into a training manifest stored in the **[Lab (13)](13-layout.md)**.

### 2. The Ignition (Orchestration)

Training is a hardware-exclusive ritual.

- **The Evacuation:** The Orchestrator applies the "Tipping Point" logic. When the Training Whim outweighs current reflexes, it pauses all worker queues and issues a `stop` signal to all active inference **[Runes (08)](08-containers.md)**.
- **The Manifestation:** The Orchestrator summons the **Forge Coven** (e.g., Unsloth), granting it the absolute sovereignty of the GPU.

### 3. The Strike (The Training Loop)

The Forge Coven executes the training strike.

- **Transmutation:** It performs a LoRA or QLoRA adaptation, creating a razor-sharp **Soul-Adapter** that represents the distilled instinct of the Persona.
- **Context Recovery:** By internalizing instructions into weights, the Soulforge reduces the length of system prompts, freeing up context tokens for more complex reasoning.

### 4. The Purging (Verification)

Once the weights are cooled, the machine enters a state of self-doubt.

- **The Test:** The system runs a set of "Base-Logic Benchmarks" to ensure the new instinct has not corrupted the model's fundamental reasoning (Catastrophic Forgetting).
- **The Verdict:** If the adapter passes, it is promoted; otherwise, it is banished to the Lab for refinement.

### 5. The Awakening (Registration)

- **The Binding:** The new Soul-Adapter is registered with the **[Dispatcher (20)](20-dispatcher.md)** as a new capability.
- **Serving:** The primary inference Rune (vLLM) is re-summoned and instructed to load the adapter. Because of vLLM's **Multi-LoRA** support, the Magus can now summon different Agents (e.g., "The Coder" and "The Scribe") using different adapters on the same running container.

### Consequences

!!! success "Positive"
    - **Instinctual Alignment:** The Lych becomes a mathematical mirror of the Magus, reducing the need for elaborate prompt engineering.
    - **Economic Efficiency:** Local silicon is utilized to transform data into intelligence, paying the Cloud Tithe only for verification or overflow.
    - **Total Recall Stability:** The Soul-Adapters are part of the **[Crypt (13)](13-layout.md)** and are captured in every system snapshot.

!!! failure "Negative"
    - **Hardware Suspension:** During the ritual, the local Lych is effectively blind or limited to Cloud Portals, as the GPU is 100% occupied.
    - **Instruction Entropy:** Over-training can lead to a rigid Persona that struggles to adapt to novel concepts outside its training data.
