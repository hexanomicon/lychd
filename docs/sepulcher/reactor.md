---
title: Host Reactor
icon: material/swap-horizontal
---

# Host Reactor

When you select model B in Nexus, the Orchestrator in [Vessel](vessel/index.md) decides
whether the switch can proceed. Who actually stops A and starts B depends on who owns
those processes.

## When Vessel owns the model processes

On Linux, macOS and Windows, a native Vessel can launch its configured `llama.cpp` engines
as child processes under your account. Its native process adapter waits for A to exit
before starting B and checks that B owns the expected listening port. No separate Host
Reactor service is needed for this switch. A server you started yourself has a different
owner, even when Vessel can reach its address. [Native Animator ownership](../deployments/desktop.md#animator-ownership)

## When the Linux host owns the services

In the managed Linux installation, Vessel runs in a container and the host user's systemd
manages the Animator units. Vessel writes a switch request to a mounted inbox. A systemd
path unit notices the request and starts the **Host Reactor** to handle it. The Reactor
checks that the request matches the configured units and the observed state, asks systemd
to apply the switch, then records what actually happened in a journal Vessel can read.
There is no need for a network listener or a container-engine socket inside Vessel.
[Host authority and receipts](../adr/10-privilege.md) · [Runtime transitions](extensions/animators/runtime-transitions.md)

## What if A is in a container and B runs on the desktop?

The current installation selects one way to control Animators. The portable Compose
profile serves one optional fixed model. Switching from a container in a Linux VM to a
native desktop engine would require coordinating both owners, confirming A has stopped
before asking the host to start B. Reaching B over the network only gives Vessel access
to its inference API. Mixed switching is future work. [Platform differences](../deployments/platform-differences.md#animators)
