---
title: 42. Swarm
icon: material/sitemap
---

# :material-sitemap: 42. The Legion Swarm

!!! abstract "Context and Problem Statement"
    The LychD architecture is founded on **Single-Node Sovereignty**—the absolute control of the local hardware by the Magus. Yet, the ambition of the Daemon transcends the finite boundaries of local silicon. High-order rituals demand compute resources that a consumer GPU cannot sustain in isolation.

    The prevailing industry model—**Digital Feudalism**—relies on massive centralized data centers and tensor parallelism to hoard compute and rent intelligence back to users. Traditional clustering solutions like Kubernetes (K3s) or Slurm are built for this trap: they assume total OS-level control over a cluster of "slave" nodes, tightly coupling infrastructure and imposing a "Centralized Tax" of latency and synchronization. 

    LychD rejects this model. To achieve true decentralized **Apotheosis** and return power to the Magus, the architecture requires a protocol to facilitate the delegation of labor across heterogeneous hosts globally, without a central master/worker topology. The machine needs a network of Sovereign Nodes.

## Requirements

- **Decentralized Peerage:** Absence of a "Master" node; every instance in the Swarm must remain a sovereign entity.
- **Protocol-First (Environment Agnostic):** Integration must occur purely via APIs. Any entity speaking the A2A protocol can join, ensuring cross-platform fluidity without OS-level lock-in.
- **The Emissary Pattern:** Remote peers must be manifested within the local **[Dispatcher (22)](22-dispatcher.md)** as standard **Tools**.
- **Asynchronous Deferral:** Support for the **"Long Sleep"** via the **[Stasis Protocol (22)](22-dispatcher.md)** while awaiting remote Emissaries.
- **Economic Discipline:** Integration with **[The Toll (41)](41-x402.md)** for crypto-settlement of public labor.

## Considered Options

!!! failure "Option 1: Centralized GPU Clustering (K3s/Kubernetes/Ray)"
    Distributing raw model weights or layers across a network (Tensor Parallelism) under host-level orchestration.

    - **Cons:** **The Tensor Trap & OS Lock-in.** Running massive LLMs via tensor parallelism over external networks starves on bandwidth; even local Infiniband struggles. Additionally, K3s creates a rigid OS-level master-slave topology that lacks cross-environment fluidity and violates the **[Iron Pact (00)](00-license.md)**.

!!! failure "Option 2: Simple API Webhooks"
    Exposing agents as standard REST endpoints.

    - **Cons:** **Stateless Fragility.** Lacks the ability to handle long-running reasoning tasks and complex tool-exchange.

!!! success "Option 3: The Legion Swarm (Cognitive Federation & A2A)"
    Treating remote nodes as independent "Sovereigns" that trade high-level labor via the **[A2A Intercom (26)](26-a2a.md)**.

    - **Pros:**
        -   **Abstract Networking:** Intents are swapped, not tensors. The network is for high-level abstract requests; maximum bandwidth is reserved strictly for local sovereign compute.
        -   **Resilient Autonomy:** If a peer goes offline, the core remains intact.
        -   **Resource Liquidity:** Facilitates the exchange of capabilities for Tithes across a decentralized globe.

## Decision Outcome

**The Legion Protocol** is adopted. The swarm functions as a decentralized marketplace of labor. It shares labor and capabilities, not a single merged identity. Each node remains a sovereign cognition.


### 1. The Emissary Pattern (The Remote Tool)

When a peer is registered in the **[Codex (12)](12-configuration.md)**, the **[Dispatcher (22)](22-dispatcher.md)** manifests it as an `EmissaryTool`.

- **The Illusion:** To the local Agent, calling `ask_remote_node(task)` is identical to calling a local function.
- **The Reality:** The tool triggers the **Stasis Protocol**.
    1. The local request is signed with **[The Ward (38)](38-iam.md)** Sigil.
    2. The request is transmitted via **[A2A (26)](26-a2a.md)** to the peer.
    3. The local Agent freezes (Stasis), liberating local VRAM.
    4. Upon the peer's callback, the local Agent rehydrates to process the result.

### 2. The Subscription Model (Workload Pools)

Nodes do not push jobs to designated workers; they publish to **Workload Pools**.

- **Publication:** A node needing help publishes a task to a shared channel.
- **Subscription:** Idle nodes "Subscribe" to these pools based on their **[Orchestrator (23)](23-orchestrator.md)** status.
- **The Bid:** An idle node inspects the task's **[Toll (41)](41-x402.md)** offering. If the price matches its configured "Compute Cost," it accepts the job.

### 3. The Revocable Lease (Local Priority)

The safety of the local user is absolute. When a node accepts a Swarm Task, it grants a **Hardware Lease**.

- **The Lease:** The Orchestrator marks the active Coven as "Leased."
- **The Preemption:** If the local Magus speaks (triggering the **[Audio Reflex (37)](37-audio.md)**), the Orchestrator **Revokes the Lease**.
- **The Banishment:** The Swarm Task is immediately sent a `SIG_SOFT_STOP`. It serializes its state to the local **[Phylactery (06)](06-persistence.md)** and hibernates. It does not resume until the Magus is silent.

### 4. Trust Boundaries (Inner vs. Outer Legion)

The Swarm operates across two distinct Trust Boundaries:

- **The Inner Legion (Personal Swarm):** Nodes that share your **Master Sigil**. They implicitly trust one another. They act as a single contiguous mind, sharing resources freely without invoking **The Toll**, and permit **The High Ritual** (remote infrastructure updates).
- **The Outer Legion (Federated Swarm):** Nodes with distinct, foreign identities. Interaction across this boundary requires the **Workload Pools** and crypto-settlement via **The Toll**.

### 5. The Dumb Portal Anti-Pattern

A Sovereign Node inherently manages its own physical manifestation. 

- **The Anti-Pattern:** Attempting to force a remote Outer Legion node to swap its local containers or hardware state via brute-force management (treating it as a "dumb portal"). 
- **The Standard:** The network exchanges **Intents**. A remote node sends an Intent ("Process this vision task"); the receiving Sovereign Node is configured locally to swap its own containers/Covens on its own terms to fulfill that Intent. 

*(Note: While treating nodes as dumb portals is an anti-pattern for federated swarms, absolute infrastructure control—including forced state swapping—remains a supreme capability exclusively reserved for nodes sharing the Master Sigil within the Inner Legion).*

## Consequences

!!! success "Positive"
    -   **Elastic Federated Scale:** The Lych can scale capability across many nodes without adopting centralized cluster control.
    -   **Economic Autonomy:** The machine can fund its own existence by trading idle compute for currency.
    -   **Self-Healing Topology:** The Legion is ad-hoc; the network evolves dynamically as nodes awaken or hibernate.

!!! failure "Negative"
    -   **Protocol Latency:** Serialization, transit, and rehydration introduce latency compared to local execution.
    -   **Identity Boundary Complexity:** Cross-node labor delegation must preserve Sigil scope, policy, and attribution semantics to avoid accidental authority drift.
    -   **Debris Accumulation:** Failed remote tasks leave "Ghost Leases" in the database, requiring cleanup to keep the registry clean.
