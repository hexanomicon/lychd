---
title: Legion
icon: material/hexagon-multiple-outline
---

# :material-hexagon-multiple-outline: Legion

> _"Data centers were built to hoard the sky, renting out the rain. The Legion is built to fracture the sky, and bring the storm to earth."_

**The Legion** is the Swarm Extension of the LychD system. It is the implementation of **[ADR 42 (Swarm)](../../adr/42-swarm.md)**—the protocol that binds independent Liches into a collaborative **Necropolis** and breaks the cycle of **Digital Feudalism**.

The mega-corporations bet trillions to centralize AGI, forcing reliance on remote tenancy and rigid cluster topology. The Legion is the rebellion. It is a new-age architecture that decentralizes AGI across the globe, returning the economy of compute to the people. 

While the **[Intercom (A2A)](../../adr/26-a2a.md)** provides the language, The Legion provides the **Society**. Intents are networked, not tensors. The Legion transforms isolated daemons into a federated labor fabric, exchanging abstract capabilities instead of surrendering sovereignty. Each node remains a sovereign cognition with its own Mirror, memory scope, and consent boundary.

## I. The Emissary Pattern (The Remote Instrument)

The Legion rejects the concept of "Master" and "Slave." Instead, it utilizes the **Emissary Pattern**.

- **The Manifestation:** When a peer node is registered in the **[Codex](../codex.md)**, The Legion manifests it within the local **[Dispatcher](../../adr/22-dispatcher.md)** as a standard **Tool**.
- **The Illusion:** To the local Agent, calling `ask_remote_node(task)` is identical to calling a local function.
- **The Reality:**
    1. The request is serialized and signed with the **[Ward Sigil](./ward.md)**.
    2. It traverses the **[Veil](./veil.md)** to the remote peer.
    3. The local Agent enters **[Stasis](../../adr/22-dispatcher.md)**, freeing local resources.
    4. Upon the peer's callback, the local Agent rehydrates to process the result.

## II. The Subscription (Workload Pools)

Nodes do not push jobs to specific workers; they publish intents to **Workload Pools**.

- **The Pool:** A shared, encrypted channel (via DHT or Relay) representing a specific need (e.g., `pool:vision:high-res`).
- **The Subscription:** Idle nodes "Subscribe" to these pools based on their **[Orchestrator](../../adr/23-orchestrator.md)** status. A node with a warm Vision Coven subscribes to the vision pool.
- **The Lease:** When a node accepts a task, it grants a **Revocable Lease** on its hardware. If its local Magus returns, the lease is revoked, and the task is returned to the pool.

## III. The Outer Legion (Federated Swarm)

The Outer Legion is the decentralized, public labor fabric. It enables federated scale across the globe without a central coordinator or shared identity.

- **Specialization:** One node acts as the "Eye" (Vision Heavy), another the "Mind" (Logic Heavy).
- **The Protocol over the Portal:** A node in the Outer Legion cannot be treated as a "dumb portal." You do not remote-control its hardware; you send it an Intent, and the sovereign node decides how to swap its own containers to get the job done.
- **The Shadow:** A fleet of sovereign nodes can be coordinated by **[The Shadow](./shadow.md)** to explore thousands of simulation branches in parallel.
- **The Economic Balance:** The Outer Legion is governed by **[The Toll](./toll.md)**. Remote labor is traded via crypto-settlement, ensuring no node can parasitize the network without contributing value.

## IV. The Inner Legion (The High Ritual)

Within circles of absolute trust (sharing the **Master Sigil**), the Swarm operates as your personal enclave—a private, unified architecture exempt from **The Toll**. 

In the Inner Legion, you possess the supreme power: **Remote Mastery**. 
- **The Command:** A controlling node can issue `INTENT_UPDATE_SYSTEM` via the A2A channel.
- **The Execution:** The receiving node validates the Sigil and writes the intent to the **[Host Reactor](../../adr/10-privilege.md)**.
- **The Result:** Unlike the Outer Legion, you *can* force container swaps, execute infrastructure updates, and reanimate trusted physical bodies across the globe. You are the architect of your own decentralized realm.
