---
title: 8. Containers
icon: material/cube-outline
---

# :material-cube-outline: 8. Containers: Systemd Quadlets

!!! abstract "Context and Problem Statement"
    The LychD architecture functions as a unified **pod** of interconnected **services** including the primary **Vessel**, the **Phylactery**, and a dynamic federation of **extensions**.

    It operates on a single sovereign Linux host where hardware resources—particularly GPU VRAM—are finite and contention-prone. Inference services may be multi-faceted (e.g., Vision + OCR), and multiple containers may compete for exclusive hardware domains. Without deterministic grouping, one lifecycle authority, and transactional updates, resource contention can result in Out-of-Memory (OOM) failures or unstable boot states.

## Requirements

- **Host-Native Orchestration:** Integration with the operating system’s init system (Systemd) to manage lifecycle, recovery, and boot-time determinism.

- **Declarative Infrastructure Model:** Infrastructure must be expressed declaratively and manifested reproducibly from defined intent.

- **Finite Hardware Governance:** Scarce hardware domains (e.g., GPU VRAM) must be explicitly managed to prevent contention and undefined behavior.

- **Explicit Operational Grouping:** Containers may be grouped into **Coven targets** for operator/systemd aggregation without turning group metadata into a hidden stop policy.

- **Single Runtime Effect Owner:** Every application- or agent-initiated stop/start set must come
  from the serialized Orchestrator plan so lease admission and drain cover every physical effect.
  Generated units must not hide additional `Conflicts=` stops. A host operator retains an explicit
  break-glass Systemd path and assumes responsibility when bypassing that protocol.

- **Semantic Capability Expression:** Infrastructure definitions must support overlapping and composable capability tags (e.g., `vision`, `reasoning`, `stt`) without introducing deployment ambiguity.

- **Identity Symmetry:** The host/container UID boundary must be resolved without privilege escalation, enabling native interaction with persistent volumes.

- **Transactional Inscription:** Infrastructure updates must be atomic; a failed configuration ritual must never leave the system in a partial or non-bootable state.


## Considered Options

!!! failure "Rejected: K3s (Kubernetes)"
    A lightweight Kubernetes distribution was considered for its robust, declarative orchestration.

    -   **Cons:** **Excessive Complexity.** Introduces a massive architectural overhead for a single-host system. Runs parallel to the host's init system, creating two separate sources of truth for service management.

!!! failure "Rejected: Docker Compose"
    The most common tool for defining multi-container applications.

    -   **Cons:** **No Native User-Service Contract.** Operates outside the host's init system, complicating ordered recovery, path-triggered host mediation, target grouping, and single-owner lifecycle observation.

!!! failure "Rejected: Cross-Platform Service Routers (e.g., LlamaSwap)"
    Using a Go-based router to manage container lifecycle, ports, and multi-service conflicts across different operating systems.

    -   **Cons:** **The Cross-Platform Complexity Trap.** Abstraction breaks native integration with rootless user services, Podman identity mapping, path-triggered host mediation, and the Linux sandbox. Other platforms can build independent implementations and commune through the A2A Intercom.

!!! success "Chosen: Podman Quadlets (Systemd)"
    Leveraging Podman's ability to generate Systemd unit files from a simple definition.

    -   **Pros:** **Deep OS Integration.** Treats containers as first-class Systemd services, exposes observable start/stop state, supports target grouping and ordered dependencies, and provides `UserNS=keep-id` for **Identity Symmetry**.

## Decision Outcome

Podman Quadlets are adopted as the exclusive container manifestation mechanism. These unit
definitions serve as the physical blueprint of the Daemon. They may join **Coven targets** for
operator grouping and are paired with logical Animator capabilities for semantic discovery; the
Orchestrator remains the only lifecycle policy owner.

### Platform Support Boundary

LychD supports one host embodiment: a free and open-source Linux stack with Systemd, cgroup v2,
and rootless Podman/Quadlet. Every software layer entrusted with LychD's host authority,
isolation, lifecycle, or recovery must be inspectable, modifiable, rebuildable, and replaceable by
the operator. Proprietary host operating systems are outside project scope.

Private operator-owned extensions and external Portals remain valid at their declared boundaries.
They may contribute local organs or negotiated labor, but neither changes the supported host
substrate or may become a required owner of LychD's continuity.

Terminology boundary: configuration **runes** are TOML declarations in the Codex (see **[Configuration (12)](12-configuration.md)**). This ADR governs the generated **Quadlet manifests** and their Systemd lifecycle.

!!! note "Manifestation Boundary"
    Quadlets are physical manifestations, not cognitive binding objects. The binding path for Agents and Graphs lives through logical Animator records, runtime/connectors, the capability registry, and the Dispatcher grant surface. The Orchestrator may use Quadlet service or target identity to change hardware state, but a generated Quadlet should not become the object that proves a capability exists to an Agent.

### 1. The Quadlet Hierarchy

The Sepulcher is organized into a strict hierarchy managed by the host's init system:

1. **The Pod (`lychd.pod`):** A shared network and resource namespace forming the physical boundary of the Sepulcher.
2. **The Coven Target (`lychd-coven-*.target`):** A meta-unit generated for multi-member Covens,
   providing an explicit operator aggregation and break-glass switch. The application Orchestrator
   addresses planned member units, not this bypass surface.
3. **The Core Units:** Persistent services essential for the system (`vessel`, `phylactery`).
4. **The Extension Units:** Dynamic services defined by installed organs.
5. **The Portals:** Logical bridges to remote APIs (no physical containers).

### 2. Capabilities: The Soul of the Animator

Metadata for routing lives with logical animator rune schemas/runtime animators, not in the generated Quadlet manifests. The **[Dispatcher (22)](22-dispatcher.md)** consumes that logical layer while this ADR governs the physical container topology.

Capabilities define what an Animator can do (for example `chat`, `vision`, `tts`, or adapter-defined families). Each carries an **`is_dynamic` flag** and projects a live **phase**, defined canonically in the **[Dispatcher (22)](22-dispatcher.md)**:

- **`is_dynamic`**: `False` (ready as soon as the container's endpoint is reachable) or `True` (the container is up but the model needs an in-runtime activation step). For dynamic containers (like a `llama.cpp` router) that swap models internally without restarting, the Orchestrator invokes a model load before that capability reaches `WARM`.
- **`CapabilityPhase`**: the live readiness ladder — `COLD`, `ACTIVATABLE`, `WARMING`, `WARM`, `ERROR`, `UNKNOWN`.

### 3. Covens: Grouping Without Hidden Mutation

Containers may be organized into **Covens** through their `groups` labels. A real multi-member group
produces a systemd target so operators can address the members as a named aggregate. Group metadata
does not synthesize `Conflicts=` and does not decide which runtime may coexist.

- **The Coven (`groups`):** A container belongs to one or more Covens.
- **The Alliance (`alliances`):** Reserved configuration shape for a future group-aware policy. It
  is non-enforcing in the v1 `evict-idle` runtime and must not be treated as a safety boundary.
- **The Effect Law:** Generated Soulstone units contain no hidden conflict side effects. The v1
  switch policy conservatively plans every active, dedicated, non-`persistent_resident` Animator as
  an evictee, regardless of group, then closes admission and drains that exact set before the
  actuator stops anything.

Starting a Coven target explicitly starts its installed members; stopping the target propagates to
members through their `PartOf=` relationship. Those are host-operator actions outside the runtime
protocol. They bypass priority admission, lease drain, and WARM convergence, so application code,
agents, and extension policy must never invoke Coven targets as an actuation shortcut. This
break-glass authority is operationally useful, but it is not a safe workload orchestration API.

Every joined container declares `StartWithPod=false`. Starting `lychd.pod` therefore establishes the
shared namespace without implicitly starting every Soulstone. Core dependency edges start the
Phylactery, migration gate, and Vessel in order; only `persistent_resident` Soulstones are wanted at
boot, while dedicated non-residents are started on demand by the Orchestrator or by an explicit
operator Coven-target action. This keeps
Pod creation from bypassing exclusivity and boot policy.

### 4. Intra-Coven Dependencies (The Chain of Command)

The Magus can specify standard Systemd ordering and dependency directives directly within a Soulstone's definition.

- **Direct Translation:** The transmutation pipeline carries keys like `after`, `wants`, and `requires` into the generated Quadlet manifest.
- **Target Interaction:** When an operator explicitly starts a Coven Target, Systemd resolves the
  internal dependency graph, ensuring services start in the correct order (e.g., pre-processors
  before models). This is a break-glass/administrative path, not an Orchestrator transition.

### 5. Federated Quadlet Registration

Extensions will provide generated container blueprints through a shaped
orchestration/transmutation store, not a flat `ExtensionContext` method. Rune
config ownership/discovery remains governed by **[Configuration (12)](12-configuration.md)**.
The CLI treats all Quadlet manifests as a single inscription set so the **Law of
Exclusivity** and port arbitration are enforced across the entire organism.

**Initial Phase vs Future Refinements:**
For the Initial Phase (V1), all extensions (including Webcrawlers) are configured to join the
single `lychd.pod` by default. This simplifies networking, but the shared Pod is not an
authentication boundary: exact mounts, unit-scoped secrets, and service credentials must still
enforce internal authority. The Quadlet generation architecture inherently supports standalone
execution, so future versions can deploy extensions to isolated network namespaces outside the Pod.

### 6. Networking and Port Arbitration

Arbitrated by the Pod unit. All joined containers share the Pod's `localhost` interface. Host
visibility is expressed through Pod `PublishPort` mappings generated from validated port
declarations in the runtime manifest pipeline. Every core and extension-contributed host mapping is
prefixed with `127.0.0.1:`; the generated foundation does not publish a service on all host
interfaces. Loopback publication is a local-access boundary, not remote authentication—an external
front door requires a separately designed authenticated/TLS proxy.

### 7. Identity Symmetry (The Double Non-Root Bridge)

To resolve the UID permission gap without granting privileged access, the Quadlet generation
pipeline establishes identity at the correct topology level:

- **Pod namespace:** `lychd.pod` declares `UserNS=keep-id` once. Containers joined to that Pod
  inherit its user namespace; Podman ignores a separate per-container user-namespace request in
  this topology, so generated joined `.container` files do not repeat `UserNS=`.
- **User-owned application units:** the Vessel, migration gate, and Soulstones declare `User=%U`,
  binding those processes to the invoking Magus's numerical identity rather than a hardcoded UID.
- **Image-owned data unit:** the Phylactery preserves the Postgres image user. Its data bind uses
  `:U,Z` so rootless Podman maps ownership for that image identity while retaining the private
  SELinux label.

The application processes can therefore interact with explicitly assigned user-owned volumes
without widening their modes. Identity symmetry does not grant every container the whole
**[Crypt (13)](13-layout.md)**; mount assignment remains the data-authority boundary.

- **Cross-Reference:** The "Fail-Secure" logic and the detailed security theory behind this "Double Non-Root" posture are addressed in **[Security (09)](09-security.md)**.

### 8. The Rite of Atomic Inscription

The inscription pipeline (via the Scribe service) implements a transactional update ritual to prevent systemic corruption:

- **Staging Phase:** The complete desired Quadlet and plain-unit set is rendered before live mutation.
- **Exact Ownership:** A validated owner-only `.lychd-owned.json` manifest in the Quadlet binding
  site records the exact LychD-owned filenames in the Quadlet and systemd user-unit sites as
  separate sets. This authority file must be a regular non-symlink owned by the invoking UID with
  mode `0600`. A filename suffix alone never grants ownership. Unsafe or duplicate entries,
  malformed manifests, invalid authority metadata, and a requested target name already occupied
  by an unowned file fail the bind closed.
- **Per-File Atomic Replacement:** Every staged unit is copied to its destination filesystem, flushed, and installed with an atomic rename. Files from the prior generation are removed only when the ownership manifest names that exact path. Unrelated operator Quadlets and systemd units remain untouched, including files with suffixes LychD also generates.
- **Complete-State Transaction:** The binding command supplies the complete desired set of generated Quadlets, Coven targets, and LychD plain user units to one reconciliation. A previously owned plain unit absent from that desired set is stale and is removed in the same commit; it is never left behind by a partial second write.
- **Cross-Site Rollback:** Quadlet and plain systemd binding sites form one Scribe transaction. Before mutation, the Scribe prepares same-filesystem backups; a failure at either site restores both sites and the prior same-UID, `0600` authority manifest.
- **Shared Directory Law:** The Scribe never initializes a Git repository or stages files in either shared user binding directory. Source history belongs to the Codex and project repositories; generated projections are recovered from validated intent and the ownership ledger.

This atomicity covers generated unit manifests only. Durable state snapshots and Btrfs/COW recovery semantics are handled by **[Snapshots (07)](07-snapshots.md)** over the **[Layout (13)](13-layout.md)** persistence regions.

### 9. Quadlets as Manifestations of Local Animators

Physical Quadlets are transmuted from logical **Soulstone Runes** and paired by stable service identity. Metadata is decoupled: the physical unit file contains infrastructure logic, while the Animator layer handles adapter/capability discovery for the Dispatcher, Orchestrator, Graph, and extension surfaces. Model and tool discovery are common capability families, not the limit of the pattern.

### 10. llama.cpp Router Presets (`--models-preset`)

The `llama-server` router mode supports a models preset `.ini` file (`--models-preset`) that defines per-model launch arguments and global defaults. This capability is adopted as a first-class container behavior for `llama.cpp` covens.

- **Dual-Layer Control Plane:**
    - **Static Layer (Codex Rune):** target grouping and lifecycle intent (`groups`, `dedicated`, `persistent_resident`); `alliances` is reserved for a future group-aware policy.
    - **Dynamic Layer (Router Preset):** In-server model loading profiles, per-model runtime knobs, and router defaults.
- **Soft-Swap Priority:** If a `llama.cpp` coven is already warm, model transitions should prefer router-native `/models/load` behavior over physical container restarts.
- **Hard-Swap Boundary:** The Orchestrator's serialized plan/drain/actuate path is authoritative for
  application VRAM reclamation. Coven targets group units and add no conflict-driven stop; a manual
  operator target action remains an explicit bypass.
- **Precedence Law:** Router runtime behavior follows upstream precedence semantics:
    1. CLI args passed to `llama-server`
    2. Model-specific preset section
    3. Global preset section (`[*]`)
- **Router Sovereignty:** Router-controlled flags (e.g., host/port/auth/model alias and related bootstrap controls) remain under LychD runtime authority and are not delegated to preset ownership.

### 11. Security and Trust Boundaries

The container topology acts as the foundational layer for the system's defense-in-depth model. While Quadlets govern the physical resource boundaries (VRAM, CPUs, and mount propagation), the logical authority boundaries—such as the split between the trusted **Vessel** and the semi-trusted **Tomb** execution plane—are governed by strict security policy.

The implemented core mount floor is intentionally narrow. The Vessel receives the Codex read-only,
Lab read-write, Core and Extensions read-only, and—only in the
default `host-reactor` mode—the Reactor inbox read-write and sibling terminal journal read-only. It
receives no whole-Crypt mount. The migration gate receives only the read-only configuration/code mounts
needed to run migrations. Soulstones receive only explicitly configured model/runtime volumes and
secrets. Every global, rune, and adapter-contributed volume passes one protected-root gate before
rendering, so neither its host nor container endpoint may overlap the Codex, Crypt,
trigger/Reactor, or user-systemd binding sites.

The planned Tomb container is a **brainless executor**. When implemented, it will run no agent
logic, graph runners, or LLM provider calls; serialized unsafe hand-work will execute inside its
`nono` subprocess sandbox. The v1 foundation does not generate a Tomb unit or worker profile, so
untrusted code execution is not yet an available safe surface. See **[Workers (14)](14-workers.md)**
for the full doctrine.

For the full definition of the Dual-Plane Trust Delta, secret distribution, and the internal `nono` subprocess sandboxing, refer to **[Security (09)](09-security.md)**.

### Consequences

!!! success "Positive"
    - **Hardware Determinism:** One serialized runtime effect owner plans every application/agent
      stop/start and drains the exact evictee set before mutation.
    - **Operational Reliability:** Atomic updates guarantee a bootable state at all times.
    - **Identity Fluidity:** Technical UID mapping enables native, non-root filesystem interaction.

!!! failure "Negative"
    - **Linux Ecology Lock-in:** Binds LychD irrevocably to Systemd and Podman.
    - **Orchestration Overhead:** State transitions require deterministic startup/shutdown latency.
    - **Break-Glass Responsibility:** Direct operator actions on Coven targets bypass runtime
      admission, drain, and readiness guarantees.
