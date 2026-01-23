---
title: 8. Containers
icon: material/cube-outline
---

# :material-cube-outline: 8. Containers: Systemd Runes

!!! abstract "Context and Problem Statement"
    The LychD architecture functions as a "Sepulcher"—a unified pod of interconnected services including the primary Vessel, the persistent Phylactery, and a dynamic federation of extensions. Orchestrating this complex environment on a single Linux host requires a system that is declarative, resilient, and natively integrated with the operating system's lifecycle. A primary challenge involves the management of finite hardware resources, specifically GPU VRAM; the system must group inference containers into atomic, mutually exclusive **Operational States** to prevent hardware contention and Out-of-Memory (OOM) failures. Furthermore, as AI services are often multi-faceted (e.g., providing both Vision and OCR), the infrastructure definition must be capable of expressing nuanced, overlapping capabilities while maintaining deterministic deployment and transactional safety.

## Requirements

- **Host-Native Orchestration:** Mandatory integration with the operating system's init system (Systemd) to manage service lifecycles and recovery.
- **Atomic Resource States:** Capability to group container definitions into **Covens**—mutually exclusive operational states managed as single units.
- **Semantic Capability Tagging:** Support for assigning multiple functional tags (e.g., `vision`, `reasoning`, `stt`) to a single container for intelligent discovery.
- **The Law of Exclusivity:** Physical enforcement of container conflicts at the kernel/init level to ensure deterministic resource allocation.
- **Declarative Blueprinting:** Automated generation of immutable infrastructure definitions (**Runes**) from the user's central configuration.
- **Identity Symmetry:** Native resolution of the host/container UID permission mismatch to allow seamless interaction with persistent volumes.
- **Transactional Inscription:** Infrastructure updates must be atomic; a failed configuration ritual must not leave the host in a non-bootable or inconsistent state.

## Decision Outcome

**Podman Quadlets** are adopted as the exclusive orchestration mechanism. These definitions, referred to as **Runes**, serve as the physical blueprint of the Daemon. They are organized into **Covens** for state management and tagged with **Capabilities** for semantic discovery by the internal dispatcher.

### 1. The Runic Hierarchy

The Sepulcher is organized into a strict hierarchy managed by the host's init system:

1. **The Pod (`lychd.pod`):** A shared network and resource namespace that forms the physical boundary of the Sepulcher. It encapsulates all core and extension services.
2. **The Core Runes:** Persistent services essential for the system's existence:
    - `vessel.container`: The primary application kernel.
    - `phylactery.container`: The persistent PostgreSQL/PgVector engine.
    - `oculus.container`: The observability and tracing stack (Arize Phoenix).
3. **The Extension Runes:** Dynamic services defined by installed organs. Each Rune declares a set of functional `Capabilities` and belongs to one or more `Covens`.

### 2. Capabilities: The Soul of the Rune

A Rune is defined not merely by its image, but by the abstract services it provides to the agentic cortex. The `ContainerRune` schema includes a `Capabilities` list (e.g., `["vision-analysis", "ocr", "text-generation"]`).

- **Discovery:** This metadata is the primary data source used by the **[Dispatcher (20)](20-dispatcher.md)** to map an Agent's abstract intent to a physical provider.
- **Nuanced Provisioning:** This allows the cortex to identify when a single, powerful Rune (like a multimodal VLM) can satisfy multiple requirements simultaneously, minimizing unnecessary container startup overhead.

### 3. Covens: The Law of Exclusivity

To manage finite hardware, Runes are organized into **Covens**, representing mutually exclusive operational states.

- **The Mapping ("The Law"):** Operational States are referred to as **Covens** in Lore and are defined via the `groups` key in the **[Codex (12)](12-configuration.md)**.
- **The Coven Tag:** A Rune belongs to a Coven if it shares a group name (e.g., `groups=["reasoning"]`). A Rune may belong to multiple non-conflicting Covens.
- **Automated Conflict Resolution:** The **Rune Scribe** (`lychd bind`) generates Systemd `Conflicts=` directives between Runes that do not share at least one group. This ensures that only one resource-heavy Coven occupies the GPU VRAM at a time.
- **State Transition:** When a service from the `vision` coven is summoned, `systemd` automatically and gracefully terminates all running services from the `reasoning` coven before the new state is manifested.

### 4. Federated Rune Registration

The Runic Hierarchy is not limited to the Core kernel. The system supports **Inversion of Control** for infrastructure:

- **Registration Hook:** Extensions provide their own infrastructure blueprints by invoking `context.add_rune(RuneDefinition)` during the assimilation phase.
- **Unified Scribing:** The **[Rune Scribe (18)](18-cli.md)** treats core runes and extension runes as a single, flattened manifest, ensuring that the **Law of Exclusivity** and **Port Arbitration** are enforced across the entire organism.

### 5. Networking and Port Arbitration

Network management is arbitrated by the Pod unit to ensure collision-free internal and external communication.

- **Shared Namespace:** All containers within `lychd.pod` share the `localhost` interface, enabling high-performance internal communication via standard ports.
- **Dynamic Exposure:** The `ContainerRune` schema includes an `ExposePort` flag. When enabled, the Scribe adds the Rune's port mapping to the `PublishPort` directive of the main `lychd.pod`, granting it visibility to the host or the **[Proxy (30)](30-proxy.md)**.

### 6. Identity Symmetry

To solve the "Permission Paradox," all generated Runes utilize the `UserNS=keep-id` mapping.

- **Mechanism:** This instructs Podman to map the host user's UID/GID directly to the same ID inside the container.
- **Result:** The process inside the container runs with the exact identity of the Magus. This ensures that mounted volumes in the **[Crypt (13)](13-layout.md)**—including source code and database files—are accessible without permission errors or insecure host-side permission overrides.

### 7. The Rite of Atomic Inscription

To prevent systemic corruption—where a crash during configuration leaves the host in an unbootable state—the **Scribe** implements a transactional update ritual.

- **The Shadow Phase:** All new Runes are first inscribed into a temporary "Shadow" directory.
- **The Atomic Swap:** Only upon the successful generation of the entire manifest does the Scribe perform a rapid cleanup and move the new files to the active **Binding Site** (`~/.config/containers/systemd/`). This ensures the system always transitions between two valid, bootable states.

### 8. Runes as Capability Providers

Runes are the physical manifestation of the abstract capabilities defined in **[Extensions (05)](05-extensions.md)**.

- **Semantic Tagging:** Every Rune is tagged with one or more functional capabilities.
- **Late Discovery:** The system remains blind to the specific contents of a container; it only identifies the capability tag (e.g., `vision`, `stt`), allowing for model-agnostic infrastructure.

### Consequences

!!! success "Positive"
    - **Intelligent Resource Scaling:** Multi-capability tagging allows the system to satisfy complex intents with the minimum number of active containers.
    - **Hardware Determinism:** GPU VRAM is strictly managed by the host init system, preventing resource contention and unrecoverable OOM crashes.
    - **Sovereign Security:** The `keep-id` mapping provides a seamless security bridge, maintaining the rootless posture while enabling effortless filesystem interaction.
    - **Operational Reliability:** The Atomic Inscription ritual guarantees system integrity, even if the binding process is interrupted by power loss or failure.

!!! failure "Negative"
    - **Linux Ecology Lock-in:** This architecture binds LychD irrevocably to Linux distributions utilizing Systemd and Podman.
    - **Orchestration Overhead:** The interplay between semantic Capabilities and physical Covens requires a sophisticated Orchestrator to mitigate state-swap latency.
