---
title: 20. Dispatcher
icon: material/directions-fork
---

# :material-directions-fork: 20. Dispatcher: The Semantic Cortex

!!! abstract "Context and Problem Statement"
    Cognitive labor in LychD requires abstract capabilities—such as text generation, visual analysis, or vocal perception—but the physical infrastructure is distributed across discrete, state-dependent containers. A single container body often provides multiple overlapping services, creating a complex many-to-many mapping between logical intent and the physical substrate. Without an intelligent cortex to arbitrate these connections, the machine remains blind to its own potential, leading to resource contention, inefficient model loading, and a failure to maintain the sovereign privacy of the Magus's data.

## Requirements

- **Capability Set Resolution:** Mandatory ability to accept a multi-faceted set of functional requirements and identify the most efficient hardware configuration to satisfy them.
- **Late-Binding Provisioning:** Implementation of the system’s late-binding primitives; reasoning entities must remain stateless specifications until the Dispatcher transmutes a physical body into a live mind.
- **Provider-Tool Segmentation:** Mandatory differentiation between **Animators** (Inference Providers) and **Function Toolsets** (Capability Tools) during the assembly of a task's runtime environment.
- **Hardware-Aware Model Tiering:** Capability to propose fallback models of varying scales to satisfy the VRAM budgeting constraints defined by the system's sovereign controller.
- **The Sovereignty Wall:** Physical enforcement of the "Local-Only" toggle, ensuring the total removal of remote providers from the resolution path when required.
- **Self-Healing Verification:** Mandatory implementation of endpoint health checks to trigger autonomous retry cycles upon service failure.

## Considered Options

!!! failure "Option 1: Static Model Registry"
    Utilizing a hardcoded mapping that binds reasoning tasks to specific model identifiers.
    - **Cons:** **Logical Rigidity.** It fails to account for containers with multiple capabilities. If a task requires both Vision and OCR, a static registry cannot identify that a single multimodal container satisfies both, leading to redundant resource allocation and VRAM waste.

!!! failure "Option 2: Network-Layer Load Balancers"
    Deploying standard proxies to route traffic based on service name strings.
    - **Cons:** **Semantic Blindness.** These tools operate outside the cognitive framework and are unaware of VRAM pressure, model tiers, or the functional capabilities of a container. They cannot perform the "Matching" required for specialized tool-inference pairings.

!!! success "Option 3: Semantic Capability Resolution & Late-Binding"
    A two-stage engine that treats hardware states as functional providers, utilizing a generic binding protocol.
    - **Pros:**
        - **Dynamic Pathfinding:** Resolves an abstract intent against available physical configurations in real-time.
        - **Substrate Efficiency:** Maximizes the utility of limited local silicon by preferring multimodal containers.
        - **Alignment:** Leverages industry-standard `Model` and `FunctionToolset` abstractions for zero-boilerplate hydration of the machine's mind.

## Decision Outcome

The Dispatcher is implemented as the **Semantic Cortex**—the switchboard of the Daemon. It functions as the intelligent link between the system's physical authority and its logical perception.

### 1. The World Model (Capability Indexing)

At boot, the Dispatcher constructs an in-memory index of the Sepulcher’s potential:

- **The Scan:** It introspects every container definition found in the system's law books.
- **The Inversion:** It creates an inverted index mapping functional tags (e.g., `text-generation`, `vision-analysis`, `stt`) to the specific containers and remote providers that provide them.
- **The State Map:** It identifies which containers share operational groups, allowing it to calculate which state transitions are "free" and which require the banishment of current models.

### 2. The Resolution Algorithm (Pathfinding)

When a reasoning step submits a set of required capabilities, the Dispatcher executes a multi-stage resolution:

1. **Candidate Selection:** It identifies all physical entities providing the requested capabilities.
2. **Satisfaction Check:** It filters for operational states that satisfy the *entire* requested set. It prioritizes single multi-capability containers (e.g., a VLM) over multiple specialized ones to conserve hardware resources.
3. **Tiering & Budgeting:** Under resource pressure, the Dispatcher applies **Model Tiering**. It may satisfy an intent using a smaller model tier (e.g., 8B) to ensure critical sensory containers (like Vision) can remain resident in VRAM.
4. **Sovereignty Filtering:** If the system is in "Sovereign Mode," all remote cloud providers are physically purged from the candidate list before ranking begins.

### 3. Capability Segmentation (Mind vs. Hand)

To manage the hardware duality of the **[ContainerRune (08)](08-containers.md)**, the Dispatcher classifies functional tags into two tiers during grant assembly:

- **Animators (The Mind):** High-level capabilities (e.g., `text-generation`, `vision-analysis`) are bound to the Agent as Pydantic AI **`Models`**.
- **Function Toolsets (The Hand):** Auxiliary capabilities (e.g., `ocr`, `search_archive`) are bound as **`FunctionTools`**.
- **Late-Bound Granting:** The Dispatcher ensures that an Agent only perceives a Tool (Hand) if the corresponding Animator (Mind) is active in VRAM. This prevents "Ghost Tools" where an Agent attempts to use a capability that has no physical inference engine resident.

### 4. The Runtime Grant Factory (Transmutation)

Once the physical state is manifested, the Dispatcher performs the **Grafting Ritual**. It transmutes abstract container definitions into live objects:

- **Late-Binding:** It instantiates the mind and configures it with settings (max tokens, temperature) derived from the system's primary configuration files.
- **Context Injection:** The complete grant—the Model and its associated Toolset—is injected into the reasoning context, endowing the Daemon with its mind and senses for the duration of the current task.

### 5. The Native Lexicon (Efficiency Sidecar)

To minimize the "Instruction Tax" on primary reasoning models, the Dispatcher manages a **Permanent Sidecar**—a sub-2B parameter model resident in VRAM.

- **Lore Parsing:** The Sidecar handles the initial translation of abstract intents into technical parameters using the system's **[Lexicon](../lexicon.md)**.
- **Format Verification:** It offloads the procedural labor of formatting tool arguments and verifying data schemas, reserving the compute of the primary mind for actual logic.

### 6. Health and Verification

Before returning a grant, the Dispatcher performs a **Stateless Pulse**:

- It pings the assigned endpoint to ensure the model is "Warm" and the inference cache is ready.
- If the pulse fails, it triggers an autonomous retry signal, notifying the sovereign controller to investigate the health of the container or restart the service.

## Consequences

!!! success "Positive"
    - **Resource Purity:** The system utilizes the most efficient hardware configuration for any given task, preventing VRAM waste.
    - **Late-Binding Security:** Logic never possesses permanent access to tools; it is granted a temporary "Arsenal" that is revoked the moment the task concludes.
    - **Sovereign Enforcement:** Privacy is guaranteed at the cortex level; sensitive data is physically blocked from entering cloud-resolution paths.
    - **Logical Transparency:** The machine's internal world is simplified to a single Model and Toolset, hiding the immense complexity of hardware management behind a clean interface.

!!! failure "Negative"
    - **Cold-Start Latency:** Resolving a novel set of capabilities and verifying health adds a measurable delay to the initiation of complex tasks.
    - **Tiering Subjectivity:** Downgrading models may result in reduced quality; the Magus must tune the system's "Inertia" to balance speed and intelligence.
    - **Registry Complexity:** Maintaining a synchronized map of containers, capabilities, and states requires robust handling of extension-registration edge cases.
