---
title: 42. Legion
icon: material/sitemap
---

# :material-sitemap: 42. The Legion: Sovereign Expansion

!!! abstract "Context and Problem Statement"
    The LychD architecture is founded on **Single-Node Sovereignty** — the absolute control of the local hardware by the Magus. Yet the ambition of the Daemon transcends the finite boundaries of local silicon. High-order rituals demand compute resources that a single consumer GPU cannot sustain in isolation. The machine requires the ability to extend its body across multiple hosts — to command many hands with a single mind.

    Like the legions of antiquity, this is not a democracy of equals. It is a hierarchy of purpose — many bodies, one imperator, one undying will bound by a single Phylactery.

### The Two Errors

Before arriving at the solution, two dead ends were mapped and rejected:

1. **The Split-Brain Error:** Running a full, independent LychD stack (Daemon + Postgres Phylactery + Phoenix Telemetry) on every home PC. A single Magus would have fragmented memories across multiple databases — the Lich's soul torn into shards, each incomplete, none authoritative. Reconciliation requires distributed consensus (Raft, Paxos), which is operational complexity designed for organizations with SRE teams, not for a sovereign individual running machines in a living room.

2. **The Dumb Portal Error:** Treating remote home nodes as bare inference endpoints (raw llamaswap or vLLM). This loses the native **[Orchestrator (23)](23-orchestrator.md)** — the node cannot smartly execute the Stasis Protocol, cannot generate Systemd Quadlets for native VRAM exclusivity, and provides zero OpenTelemetry traces to the central dashboard. The Magus gains compute but loses visibility and control.

**The Revelation:** A node's compute authority (Orchestrator, Vessel, Quadlets) must be decoupled from its state authority (Phylactery, Identity, Memory). The same `app.py` can run as a sovereign Master or as a soulless **Thrall** — a Vessel without a Phylactery, managing its own hardware but thinking with the Master's brain.

## Requirements

- **Dual-Mode Boot:** The Vessel must support two boot modes: `master` (full stack with local Phylactery) and `thrall` (headless mode pointing `DATABASE_URL` to the Master's Postgres).
- **Centralized State:** One Phylactery per Magus. One Phylactery to bind them. Thralls connect to the Master's database over the network. No replication, no sharding, no consensus.
- **Sovereign Hardware Management:** A Thrall must run its own Orchestrator and generate its own Systemd Quadlets. Only the local kernel knows its hardware state.
- **The Emissary Pattern:** Thralls must be manifested within the Master's **[Dispatcher (22)](22-dispatcher.md)** as standard **Tools**, transparent to the Agent.
- **Asynchronous Deferral:** Support for the "Long Sleep" via the **[Stasis Protocol (22)](22-dispatcher.md)** while awaiting remote Emissaries.
- **Active-Passive Resilience:** The Lich can die. The Lich can arise. Immortality is achieved through the **[Phylactery](../sepulcher/phylactery/index.md)** and BTRFS snapshots, not through high-availability clustering.

## Considered Options

!!! failure "Option 1: Centralized GPU Clustering (Kubernetes / K3s / Ray / Slurm)"
    Distributing raw model weights or layers across a network under host-level orchestration.

    These tools were built for the feudal lords. Kubernetes assumes hardware is *disposable* — that nodes are interchangeable cattle to be killed and replaced by a scheduler that knows nothing of VRAM exclusivity or thermal pressure. It forces heavy network-layer overlays (CNIs), complex distributed state consensus (etcd/Raft), and "dumb" worker nodes that cannot self-manage. Attempting to force K8s to manage exclusive 24GB GPU VRAM swaps on a home LAN leads to race conditions, split-brain scheduling, and immense architectural bloat.

    K3s is lighter but still carries the philosophical disease: it assumes a *cluster* that a *scheduler* controls. LychD is not a cluster. It is an imperator commanding its own dead.

    Ray and Slurm are purpose-built for tensor parallelism across high-bandwidth interconnects (InfiniBand). Running large models via tensor parallelism over commodity Ethernet starves on bandwidth. More fundamentally, they distribute *computation*, not *intent*. LychD distributes intent — the network exchanges structured Pydantic schemas, not raw tensors.

!!! failure "Option 2: Active-Active Database Clustering (Raft / Patroni / CockroachDB)"
    Replicating the Phylactery across multiple nodes for high availability.

    High availability solves a problem the Magus does not have. A home setup serves *one* user. If the Master node dies, the world does not end — the Magus restores from a BTRFS snapshot and the Lich arises anew. That is the *point* of the Phylactery. Raft consensus adds latency to every write, requires quorum management, and creates the possibility of split-brain states that are far worse than planned downtime. The complexity is enormous; the benefit is zero.

!!! failure "Option 3: Simple API Webhooks"
    Exposing agents as standard REST endpoints.

    - **Cons:** **Stateless Fragility.** Lacks the ability to handle long-running reasoning tasks, hardware transitions, and complex tool-exchange.

!!! success "Option 4: Native OS-Level Orchestration + Direct Vessel HTTP"
    The same `app.py` running in two modes — Master and Thrall — with the Master calling the Thrall's Vessel API directly over HTTP, and each node managing its own hardware natively.

    - **Pros:**
        - **Hardware Exclusivity:** Handled purely by Systemd Quadlets using `Conflicts=` directives. The Linux kernel guarantees no two heavy Covens occupy the GPU simultaneously. No scheduler. No coordinator. The kernel *is* the coordinator.
        - **Intent Networking:** The Master sends structured Pydantic schemas to the Thrall's Vessel API. The data is small, the compute is local.
        - **Resilience via Deferral:** If a Thrall takes 10 minutes to swap a model, the Master's agent enters Stasis. It sleeps, consuming zero active cycles. The network is asynchronous by design.
        - **Sovereignty Preserved:** Every Thrall manages its own containers, its own VRAM, its own thermal envelope. The Master commands intent; the Thrall decides how to fulfill it on its own iron.

## Decision Outcome

**The Legion** is adopted as the extension governing the Magus's personal army of Thralls — soulless Vessels bound to a single Master Phylactery, extending the Lich's reach across every machine the Magus owns.

### 1. The Thrall (A Soulless Lich)

A Thrall is a LychD Vessel booted in headless mode (`LYCHD_MODE=thrall`). It runs the same `app.py` as the Master but with a critical difference: it has no soul.

- **No Local Phylactery:** The Thrall does not spin up a local Postgres database. Its `DATABASE_URL` points to the Master's Postgres over the network. Its `PHOENIX_ENDPOINT` points to the Master's Arize Phoenix. There is one Phylactery, and it binds them all.
- **Sovereign Hardware:** Despite lacking a local DB, the Thrall runs its own **[Orchestrator (23)](23-orchestrator.md)** and generates its own **[Systemd Quadlets (08)](08-containers.md)**. When the Master delegates a vision task, the Thrall handles killing its local text container, starting its local vision container, managing thermal pressure — all natively. The Master cannot and should not manage remote Systemd units.
- **No Tomb:** A Thrall does not run a **Tomb** container. It is not an execution substrate for untrusted code. It is a smart, self-managing inference endpoint. All cognitive labor (agent graphs, memory curation, Dispatcher resolution) remains on the Master Vessel.

### 5. Authority Matrix

| Dimension | Master Vessel (Command & Control) | Thrall Vessel (Inference Proxy) |
| :--- | :--- | :--- |
| **Tomb** | Yes. Untrusted execution substrate. | No. Smart Proxy only. |

The Thrall supports one execution pattern: the Smart Proxy.

1. The Master's **[Dispatcher (22)](22-dispatcher.md)** resolves a capability request (e.g., "I need vision") and discovers the Thrall has the required Coven.
2. The Dispatcher routes the request to the Thrall's **EmissaryTool** via direct Vessel HTTP, authenticated by the shared Master Sigil.
3. The Master's Agent enters **Stasis**, liberating local VRAM.
4. The Thrall's Orchestrator swaps the required model into VRAM (if not already resident).
5. The Thrall processes the prompt against its local Soulstone.
6. The Thrall returns the result via HTTP callback.
7. The Master's Agent rehydrates and continues the graph step.

To the Agent, this is invisible. Calling a Thrall looks identical to calling a local Soulstone — the Dispatcher handles the routing transparently.

### 3. The Emissary Pattern (The Remote Tool)

When a Thrall is registered in the **[Codex (12)](12-configuration.md)**, the **[Dispatcher (22)](22-dispatcher.md)** manifests it as an `EmissaryTool`.

- **The Illusion:** To the local Agent, calling `ask_thrall(task)` is identical to calling a local function.
- **The Reality:** The tool triggers the **Stasis Protocol**.
    1. The local request is signed with the **[Ward (38)](38-iam.md)** Sigil.
    2. The request is transmitted via direct HTTP to the Thrall's Vessel API.
    3. The local Agent freezes (Stasis), liberating local VRAM.
    4. Upon the Thrall's callback, the local Agent rehydrates to process the result.

### 4. Trust and Authority

- **Shared Master Sigil:** All Legion nodes share a cryptographic Master Sigil. A Thrall that validates this Sigil recognizes the command as coming from its own Magus.
- **`INTENT_UPDATE_SYSTEM`:** The shared Sigil grants infrastructure-level authority. The Master can force Coven transitions, trigger model swaps, and reconfigure state on any Thrall. This is **Remote Mastery**, not Digital Feudalism — the Thrall obeys because it cryptographically verifies the intent originates from its own operator.
- **No Toll:** Resource sharing between Legion nodes does not require crypto-settlement. These are your machines. You do not pay yourself.

### 5. Resilience: Active-Passive, Not High Availability

The Lich does not need high availability. The Lich needs **immortality**.

High availability is a design for services that cannot afford a second of downtime — payment processors, stock exchanges, emergency infrastructure. A home AI daemon is not a payment processor. When the Master node dies, the Magus walks away, restores from backup, and the Lich arises anew. That is the covenant of the Phylactery.

- **One Master Phylactery.** No replication, no Raft, no consensus quorum.
- **Disaster Recovery:** Native BTRFS snapshots (`btrbkup`) of the Master's Phylactery, restored to a new machine if the original burns.
- **Thrall Reconnection:** When the Master returns, Thralls reconnect automatically. Their local Orchestrators continue managing their own hardware in the interim — they simply cannot accept new cognitive work until the brain comes back online.
- **The Philosophy:** The Lich can die. The Lich *will* die. That is not a failure — it is a design constraint acknowledged and solved by the Phylactery, not by infrastructure complexity.

### 6. VRAM Exclusivity and Zombie-Proofing

A node cannot be deadlocked by rogue or hanging tasks.

- **Kernel Enforcement:** Systemd `Conflicts=` directives in the generated **[Quadlets (08)](08-containers.md)** ensure only one resource-intensive Coven can occupy the GPU at a time, regardless of who submitted the task.
- **Watchdog:** The **[Orchestrator (23)](23-orchestrator.md)** pulses every active container. If a task hangs or exceeds its VRAM quota, the Orchestrator kills and restarts the container via the **[Host Reactor (10)](10-privilege.md)**. Ghost leases left by failed tasks are swept from the registry on restart.

### 7. Policy Table

| Dimension | Master | Thrall |
| :--- | :--- | :--- |
| Phylactery | Local Postgres. The one true memory. | None. Points `DATABASE_URL` to Master. |
| Orchestrator | Local. Manages its own Covens. | Local. Manages its own Covens. |
| Shadow | Yes. Untrusted execution substrate. | No. Smart Proxy only. |
| Sigil | Master Sigil. | Shared Master Sigil. |
| Authority | Full. Brain + Body + Soul. | Body only. Hardware management. |
| Telemetry | Local Phoenix. | Routes to Master's Phoenix. |
| Infrastructure Control | Can command Thralls. | Accepts commands from Master. |

## Consequences

!!! success "Positive"
    - **Sovereign Scale:** The Magus can extend across every machine in their domain without surrendering a single byte of state to the cloud or to distributed consensus.
    - **Operational Simplicity:** One database. One telemetry dashboard. One identity. Many bodies. This is simpler than any distributed alternative.
    - **Self-Healing Topology:** The Legion is ad-hoc; the network evolves dynamically as Thralls awaken or hibernate. The Master is the anchor, not the cage.

!!! failure "Negative"
    - **Protocol Latency:** Serialization, transit, and rehydration introduce latency compared to local execution.
    - **Single Point of Failure:** The Master Phylactery is the single source of truth. If it is lost without a snapshot, the Lich's memory is lost. This is an accepted trade-off — the alternative (distributed consensus) is worse than the disease it cures.
    - **Network Dependency:** Thralls are inert without network access to the Master's Postgres. They can manage their own hardware but cannot accept cognitive work.
