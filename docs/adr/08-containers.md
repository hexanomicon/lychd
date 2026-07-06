---
title: 8. Containers
icon: material/cube-outline
---

# :material-cube-outline: 8. Containers: Systemd Quadlets

!!! abstract "Context and Problem Statement"
    The LychD architecture functions as a unified **pod** of interconnected **services** including the primary **Vessel**, the **Phylactery**, and a dynamic federation of **extensions**.

    It operates on a single sovereign Linux host where hardware resources—particularly GPU VRAM—are finite and contention-prone. Inference services may be multi-faceted (e.g., Vision + OCR), and multiple containers may compete for exclusive hardware domains. Without deterministic grouping, lifecycle authority, and transactional updates, resource contention can result in Out-of-Memory (OOM) failures or unstable boot states.

## Requirements

- **Host-Native Orchestration:** Integration with the operating system’s init system (Systemd) to manage lifecycle, recovery, and boot-time determinism.

- **Declarative Infrastructure Model:** Infrastructure must be expressed declaratively and manifested reproducibly from defined intent.

- **Finite Hardware Governance:** Scarce hardware domains (e.g., GPU VRAM) must be explicitly managed to prevent contention and undefined behavior.

- **Atomic Operational States:** Containers must be grouped into mutually exclusive **Covens** that activate and deactivate as indivisible states.

- **Kernel-Enforced Exclusivity:** Hardware conflicts must be enforced at the init/kernel level rather than through cooperative runtime behavior.

- **Semantic Capability Expression:** Infrastructure definitions must support overlapping and composable capability tags (e.g., `vision`, `reasoning`, `stt`) without introducing deployment ambiguity.

- **Identity Symmetry:** The host/container UID boundary must be resolved without privilege escalation, enabling native interaction with persistent volumes.

- **Transactional Inscription:** Infrastructure updates must be atomic; a failed configuration ritual must never leave the system in a partial or non-bootable state.


## Considered Options

!!! failure "Rejected: K3s (Kubernetes)"
    A lightweight Kubernetes distribution was considered for its robust, declarative orchestration.

    -   **Cons:** **Excessive Complexity.** Introduces a massive architectural overhead for a single-host system. Runs parallel to the host's init system, creating two separate sources of truth for service management.

!!! failure "Rejected: Docker Compose"
    The most common tool for defining multi-container applications.

    -   **Cons:** **No Native Exclusivity.** Lacks any mechanism to enforce the **Law of Exclusivity** at the kernel level. Operates outside the host's init system, complicating recovery and boot-time management.

!!! failure "Rejected: Cross-Platform Service Routers (e.g., LlamaSwap)"
    Using a Go-based router to manage container lifecycle, ports, and multi-service conflicts across different operating systems.

    -   **Cons:** **The Cross-Platform Complexity Trap.** Abstraction breaks native integration. Attempting to simulate hardware governance in user-space forces the system to abandon kernel-level `Conflicts=` directives and the double-rootless security model. Pure, OS-native integration (Systemd) is preferred over application-level reinvention. Other platforms can build independent implementations and commune through the A2A Intercom.

!!! success "Chosen: Podman Quadlets (Systemd)"
    Leveraging Podman's ability to generate Systemd unit files from a simple definition.

    -   **Pros:** **Deep OS Integration.** Treats containers as first-class Systemd services. **Kernel-Enforced Exclusivity** via `Conflicts=`. Supports `UserNS=keep-id` for **Identity Symmetry**.

## Decision Outcome

Podman Quadlets are adopted as the exclusive orchestration mechanism. These unit definitions serve as the physical blueprint of the Daemon. They are organized into **Covens** for state management and paired with logical Animator capabilities for semantic discovery.

Terminology boundary: configuration **runes** are TOML declarations in the Codex (see **[Configuration (12)](12-configuration.md)**). This ADR governs the generated **Quadlet manifests** and their Systemd lifecycle.

!!! note "Manifestation Boundary"
    Quadlets are physical manifestations, not cognitive binding objects. The binding path for Agents and Graphs lives through logical Animator records, runtime/connectors, the capability registry, and the Dispatcher grant surface. The Orchestrator may use Quadlet service or target identity to change hardware state, but a generated Quadlet should not become the object that proves a capability exists to an Agent.

### 1. The Quadlet Hierarchy

The Sepulcher is organized into a strict hierarchy managed by the host's init system:

1. **The Pod (`lychd.pod`):** A shared network and resource namespace forming the physical boundary of the Sepulcher.
2. **The Coven Target (`lychd-coven-*.target`):** A meta-unit generated for multi-member Covens, providing a "master switch" for the Orchestrator.
3. **The Core Units:** Persistent services essential for the system (`vessel`, `phylactery`).
4. **The Extension Units:** Dynamic services defined by installed organs.
5. **The Portals:** Logical bridges to remote APIs (no physical containers).

### 2. Capabilities: The Soul of the Animator

Metadata for routing lives with logical animator rune schemas/runtime animators, not in the generated Quadlet manifests. The **[Dispatcher (22)](22-dispatcher.md)** consumes that logical layer while this ADR governs the physical container topology.

Capabilities define what an Animator can do (for example `chat`, `vision`, `tts`, or adapter-defined families). Each carries a **lifecycle** and projects a live **phase**, defined canonically in the **[Dispatcher (22)](22-dispatcher.md)**:

- **`CapabilityLifecycle`**: `STATIC` (ready as soon as the container's endpoint is reachable) or `DYNAMIC` (the container is up but the model needs an in-runtime activation step). For dynamic containers (like a `llama.cpp` router) that swap models internally without restarting, the Orchestrator invokes a model load before that capability reaches `WARM`.
- **`CapabilityPhase`**: the live readiness ladder — `COLD`, `ACTIVATABLE`, `WARMING`, `WARM`, `ERROR`, `UNKNOWN`.

### 3. Covens: The Law of Exclusivity

To manage finite hardware, containers are organized into **Covens** (groups). The system operates under **"Implicit Exclusivity, Explicit Alliances"**: every Coven conflicts with every other Coven by default.

- **The Coven (`groups`):** A container belongs to one or more Covens.
- **The Alliance (`alliances`):** Only Covens listed together are permitted to run concurrently.
- **Automated Conflict Resolution:** The transmutation + inscription pipeline calculates enemies and forges explicit `Conflicts=` directives in each `.container` file, listing enemy `.target` or `.service` units to prevent GPU over-allocation.

### 4. Intra-Coven Dependencies (The Chain of Command)

The Magus can specify standard Systemd ordering and dependency directives directly within a Soulstone's definition.

- **Direct Translation:** The transmutation pipeline carries keys like `after`, `wants`, and `requires` into the generated Quadlet manifest.
- **Target Interaction:** When starting a Coven Target, Systemd resolves the internal dependency graph, ensuring services start in the correct order (e.g., pre-processors before models).

### 5. Federated Quadlet Registration

Extensions will provide generated container blueprints through a shaped
orchestration/transmutation store, not a flat `ExtensionContext` method. Rune
config ownership/discovery remains governed by **[Configuration (12)](12-configuration.md)**.
The CLI treats all Quadlet manifests as a single inscription set so the **Law of
Exclusivity** and port arbitration are enforced across the entire organism.

**Initial Phase vs Future Refinements:**
For the Initial Phase (V1), all extensions (including Webcrawlers) are configured to join the single `lychd.pod` by default. This simplifies networking and allows Layer 7 authentication to manage internal boundaries. However, the Quadlet generation architecture inherently supports standalone execution, meaning future versions can deploy extensions to isolated network namespaces outside the Pod.

### 6. Networking and Port Arbitration

Arbitrated by the Pod unit. All containers share the `localhost` interface. Host visibility is expressed through Pod `PublishPort` mappings generated from validated port declarations in the runtime manifest pipeline.

### 7. Identity Symmetry (The Double Non-Root Bridge)

To resolve the UID permission gap without granting privileged access, the Quadlet generation pipeline binds the container process to the host user's numerical identity.

- **Mechanism:** Every generated Quadlet must include the following directives:
    1. **`User=%U`**: A Systemd specifier that forces the process to start with the UID of the Magus who invoked the service, overriding the Image's internal default.
    2. **`UserNS=keep-id`**: Instructs Podman to map that host UID directly into the container without translation.
- **Effect:** The process runs as a "nameless" UID matching the host identity (e.g., UID 1000). Because it is not UID 0 (Root), it has no administrative power inside the container, yet it gains native access to the **[Crypt (13)](13-layout.md)** volumes.
- **Cross-Reference:** The "Fail-Secure" logic and the detailed security theory behind this "Double Non-Root" posture are addressed in **[Security (09)](09-security.md)**.

### 8. The Rite of Atomic Inscription

The inscription pipeline (via the Scribe service) implements a transactional update ritual to prevent systemic corruption:

- **Staging Phase:** Quadlets are inscribed into a temporary directory.
- **Atomic Swap:** Upon successful generation, the Writer performs a rapid cleanup and moves the new files to the active **Binding Site** (`~/.config/containers/systemd/`).

This atomicity covers generated unit manifests only. Durable state snapshots and Btrfs/COW recovery semantics are handled by **[Snapshots (07)](07-snapshots.md)** over the **[Layout (13)](13-layout.md)** persistence regions.

### 9. Quadlets as Manifestations of Local Animators

Physical Quadlets are transmuted from logical **Soulstone Runes** and paired by stable service identity. Metadata is decoupled: the physical unit file contains infrastructure logic, while the Animator layer handles adapter/capability discovery for the Dispatcher, Orchestrator, Graph, and extension surfaces. Model and tool discovery are common capability families, not the limit of the pattern.

### 10. llama.cpp Router Presets (`--models-preset`)

The `llama-server` router mode supports a models preset `.ini` file (`--models-preset`) that defines per-model launch arguments and global defaults. This capability is adopted as a first-class container behavior for `llama.cpp` covens.

- **Dual-Layer Control Plane:**
    - **Static Layer (Codex Rune):** Coven identity, topology, and hardware governance (`groups`, `alliances`, `dedicated`, `persistent_resident`).
    - **Dynamic Layer (Router Preset):** In-server model loading profiles, per-model runtime knobs, and router defaults.
- **Soft-Swap Priority:** If a `llama.cpp` coven is already warm, model transitions should prefer router-native `/models/load` behavior over physical container restarts.
- **Hard-Swap Boundary:** Kernel-level `Conflicts=` and coven target transitions remain authoritative for cross-coven VRAM reclamation.
- **Precedence Law:** Router runtime behavior follows upstream precedence semantics:
    1. CLI args passed to `llama-server`
    2. Model-specific preset section
    3. Global preset section (`[*]`)
- **Router Sovereignty:** Router-controlled flags (e.g., host/port/auth/model alias and related bootstrap controls) remain under LychD runtime authority and are not delegated to preset ownership.

### 11. Security and Trust Boundaries

The container topology acts as the foundational layer for the system's defense-in-depth model. While Quadlets govern the physical resource boundaries (VRAM, CPUs, and mount propagation), the logical authority boundaries—such as the split between the trusted **Vessel** and the semi-trusted **Tomb** execution plane—are governed by strict security policy.

The Tomb container is a **brainless executor**. It runs no agent logic, graph runners, or LLM provider calls. It receives serialized script payloads via SAQ, executes them in the `nono` sandbox, and returns `stdout`. All cognitive labor remains in the Vessel. See **[Workers (14)](14-workers.md)** for the full doctrine.

For the full definition of the Dual-Plane Trust Delta, secret distribution, and the internal `nono` subprocess sandboxing, refer to **[Security (09)](09-security.md)**.

### Consequences

!!! success "Positive"
    - **Hardware Determinism:** GPU VRAM is strictly managed via kernel-level conflicts.
    - **Operational Reliability:** Atomic updates guarantee a bootable state at all times.
    - **Identity Fluidity:** Technical UID mapping enables native, non-root filesystem interaction.

!!! failure "Negative"
    - **Linux Ecology Lock-in:** Binds LychD irrevocably to Systemd and Podman.
    - **Orchestration Overhead:** State transitions require deterministic startup/shutdown latency.
