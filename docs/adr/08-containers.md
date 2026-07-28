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

- **Explicit Operational Grouping:** Containers may be grouped into **Coven targets** for
  operator/systemd aggregation without confusing membership with physical incompatibility.

- **Declared Conflict Topology:** Soulstone Runes must be able to name the finite hardware domains
  they cannot share. Binding must compile that declaration into inspectable systemd relationships
  rather than infer incompatibility from Coven names.

- **Divided Lifecycle Authority:** The Orchestrator decides *when* a transition is admissible and
  closes and drains the exact affected set. Systemd decides *how* the physical stop/switch/start
  transaction is executed from generated Animator targets and `Conflicts=` edges. The Orchestrator
  and actuator must derive the same graph, and the actuator must bind the loaded runtime units to
  the exact Scribe-owned unit set and source paths before any effect.

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
Orchestrator remains the only lifecycle policy owner while systemd remains the physical
transaction engine.

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
2. **The Animator Target (`lychd-animator-*.target`):** One generated transaction boundary per
   local Soulstone. It requires and gates the concrete service and carries the compiled conflict
   topology addressed by the Orchestrator.
3. **The Coven Target (`lychd-coven-*.target`):** A compatible aggregate of Animator targets,
   generated for real multi-member Covens and reserved as an explicit operator break-glass surface.
4. **The Core Units:** Persistent services essential for the system (`vessel`, `phylactery`).
5. **The Extension Units:** Dynamic services defined by installed organs.
6. **The Portals:** Logical bridges to remote APIs (no physical containers).

### 2. Capabilities: The Soul of the Animator

Metadata for routing lives with logical animator rune schemas/runtime animators, not in the generated Quadlet manifests. The **[Dispatcher (22)](22-dispatcher.md)** consumes that logical layer while this ADR governs the physical container topology.

Capabilities define what an Animator can do (for example `chat`, `vision`, `tts`, or adapter-defined families). Each carries an **`is_dynamic` flag** and projects a live **phase**, defined canonically in the **[Dispatcher (22)](22-dispatcher.md)**:

- **`is_dynamic`**: `False` (ready as soon as the container's endpoint is reachable) or `True` (the container is up but the model needs an in-runtime activation step). For dynamic containers (like a `llama.cpp` router) that swap models internally without restarting, the Orchestrator invokes a model load before that capability reaches `WARM`.
- **`CapabilityPhase`**: the live readiness ladder — `COLD`, `ACTIVATABLE`, `WARMING`, `WARM`, `ERROR`, `UNKNOWN`.

### 3. Covens and Conflict Domains

Covens and conflict domains answer different questions:

- **The Coven (`groups`):** which compatible Soulstones should an operator be able to address as
  one named aggregate?
- **The Conflict Domain (`[concurrency].conflict_domains`):** which dedicated, non-resident
  Soulstones cannot inhabit the same finite hardware domain?
- **The Alliance (`alliances`):** reserved configuration shape for later policy. It is not a
  conflict declaration or a safety boundary.

Conflict domains form an undirected graph. Two lifecycle-managed Soulstones conflict when their
declared domain sets overlap. An explicit empty list means the operator declares that Soulstone
compatible with every other managed Soulstone in this graph. Omitting the field on a dedicated,
non-resident Soulstone assigns the compiler-owned `default-exclusive` unknown domain. It is a
conservative wildcard: it conflicts with every dedicated non-resident whose effective domain set
is non-empty, including explicitly labelled Runes. Only explicit `[]` declares coexistence and
removes that Soulstone from the graph, so partially migrating legacy Runes cannot silently widen
coexistence. A persistent resident or shared Soulstone may not participate in a conflict domain:
binding rejects a non-empty set rather than generating a unit capable of mutating a runtime outside
that law.

Binding compiles one Animator target per Soulstone and places each conflict edge on those targets.
The target `Requires=` and is `Before=` its concrete service; the service `BindsTo=` and is
`After=` its target, so one lifetime boundary represents the Animator. For each sorted conflict
pair `A < B`, the compiler emits the edge once on `B` as `Conflicts=A.target` plus
`After=A.target`. `Conflicts=` is reciprocal while the single lexical ordering edge avoids a cycle
and provides stop-before-start behavior in either direction. Coven targets `Wants=` and are
`After=` only mutually compatible Animator targets; each member is `PartOf=` its Coven. Binding
rejects a Coven whose own members conflict.

These generated effects are **declared, not hidden**. The Orchestrator recomputes the same graph
from validated Rune intent, closes admission and drains the exact active conflict neighborhood,
and validates the observed world immediately before mutation. In mediated mode the Host Reactor
separately rejects an intent whose configuration digest no longer matches current registry truth.
In both actuator modes, loaded-graph attestation then requires a validated Scribe ownership
receipt; enumerates the installed and loaded LychD target namespace; and proves the exact
Animator-target, service, and Coven relationships, receipt-owned sources, unit-file states, and
reload/drop-in condition. Only then does the actuator ask systemd to start the selected target in
one compound transaction. Systemd, not application code, performs the resulting
stop/switch/start.

Directly starting an Animator or Coven target remains a host-operator break-glass action. It
bypasses priority admission, lease drain, stale-world validation, WARM convergence, and
compensation, so application code, agents, and extension policy must never use either target class
as a shortcut.

Every joined container declares `StartWithPod=false`. Starting `lychd.pod` therefore establishes the
shared namespace without implicitly starting every Soulstone. Core dependency edges start the
Phylactery, migration gate, and Vessel in order; only `persistent_resident` Animator targets are
wanted at boot, while dedicated non-residents are started on demand by the Orchestrator or by an
explicit operator target action. This keeps
Pod creation from bypassing exclusivity and boot policy.

### 4. Intra-Coven Dependencies (The Chain of Command)

The Magus can specify standard Systemd ordering and dependency directives directly within a Soulstone's definition.

- **Direct Translation:** The transmutation pipeline carries keys like `after`, `wants`, and `requires` into the generated Quadlet manifest.
- **Target Interaction:** When an operator explicitly starts a Coven Target, Systemd resolves the
  compatible Animator-target dependency graph, ensuring services start in the correct order (e.g.,
  pre-processors before models). This is a break-glass/administrative path, not an Orchestrator
  transition.

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
- **Complete-State Transaction:** The binding command supplies the complete desired set of
  generated Quadlets, Animator targets, Coven targets, and LychD plain user units to one
  reconciliation. A previously owned plain unit absent from that desired set is stale and is
  removed in the same commit; it is never left behind by a partial second write.
- **Cross-Site Rollback:** Quadlet and plain systemd binding sites form one Scribe transaction. Before mutation, the Scribe prepares same-filesystem backups; a failure at either site restores both sites and the prior same-UID, `0600` authority manifest.
- **Shared Directory Law:** The Scribe never initializes a Git repository or stages files in either shared user binding directory. Source history belongs to the Codex and project repositories; generated projections are recovered from validated intent and the ownership ledger.

This atomicity covers generated unit manifests only. Durable state snapshots and Btrfs/COW recovery semantics are handled by **[Snapshots (07)](07-snapshots.md)** over the **[Layout (13)](13-layout.md)** persistence regions.

### 9. Quadlets as Manifestations of Local Animators

Physical Quadlets are transmuted from logical **Soulstone Runes** and paired by stable service identity. Metadata is decoupled: the physical unit file contains infrastructure logic, while the Animator layer handles adapter/capability discovery for the Dispatcher, Orchestrator, Graph, and extension surfaces. Model and tool discovery are common capability families, not the limit of the pattern.

### 10. llama.cpp Router Presets (`--models-preset`)

The `llama-server` router mode supports a models preset `.ini` file (`--models-preset`) that defines per-model launch arguments and global defaults. This capability is adopted as a first-class container behavior for `llama.cpp` covens.

- **Dual-Layer Control Plane:**
    - **Static Layer (Codex Rune):** target grouping and lifecycle intent (`groups`, `dedicated`,
      `persistent_resident`, `conflict_domains`); `alliances` is reserved for later policy.
    - **Dynamic Layer (Router Preset):** In-server model loading profiles, per-model runtime knobs, and router defaults.
- **Soft-Swap Priority:** If a `llama.cpp` Animator is already warm, model transitions should
  prefer router-native `/models/load` behavior over physical container restarts.
- **Hard-Swap Boundary:** The Orchestrator's serialized choose/close/drain/validate path is
  authoritative for application VRAM reclamation. It submits one Animator-target start after graph
  attestation; systemd executes the compiled conflict transaction. A manual operator target action
  remains an explicit bypass.
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
    - **Hardware Determinism:** The Orchestrator admits and drains the exact declared conflict set;
      systemd executes one inspectable physical transaction from the same graph.
    - **Operational Reliability:** Atomic updates guarantee a bootable state at all times.
    - **Identity Fluidity:** Technical UID mapping enables native, non-root filesystem interaction.

!!! failure "Negative"
    - **Linux Ecology Lock-in:** Binds LychD irrevocably to Systemd and Podman.
    - **Orchestration Overhead:** State transitions require deterministic startup/shutdown latency.
    - **Declaration Responsibility:** An explicit empty conflict set is an operator assertion of
      coexistence; systemd cannot compensate for an incorrect hardware declaration.
    - **Break-Glass Responsibility:** Direct operator actions on Animator or Coven targets bypass
      runtime admission, drain, and readiness guarantees.
