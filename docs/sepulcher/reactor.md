---
title: Host Reactor
icon: material/swap-horizontal
---

# Host Reactor

When you select model B in Nexus, the Orchestrator in [Vessel](vessel/index.md) decides
whether the switch can proceed. Who actually stops A and starts B depends on who owns
those processes.

## Managed Linux

Vessel writes a typed request to its mounted inbox. A systemd path unit starts the host user's
Reactor, which checks the request against the bound generation, active Animators and loaded unit
graph. A Quadlet-backed engine and a native llama.cpp user service can participate in the same
target transaction. The host records the result in a journal that Vessel mounts read-only.
For the native engine, a relay inside the pod forwards the Rune's loopback port to a private
host Unix socket. Switching requires neither a network listener nor a container-engine socket
inside Vessel. [Host authority and receipts](../adr/10-privilege.md) · [Managed native Rune](extensions/animators/soulstone/rune.md#choose-placement)

## Native Vessel on a personal host

Vessel holds the local lifecycle lock throughout the session. It can launch a trusted, fixed-model
llama.cpp child or start a previously provisioned fixed-model container on its bound local engine.
For a conflicting pair it waits for A to stop, starts B, and checks the selected service before
Nexus reports it ready. The operator's running processes and containers cannot be adopted.
[Desktop container binding](../deployments/desktop.md#animator-ownership)

## Caged Vessel with desktop-owned engines

Run the resident Reactor on the desktop and Vessel in the separate portable Reactor project.
The host process holds the same lock, process handles and container bindings as a native Vessel.
The guest receives a read-only configuration and identity bundle, a writable request inbox and
a read-only host journal. On startup it checks the mounts, generation and live host session.
Local model requests cross a mutually authenticated TLS connection on port 17134 for the named
Animator. Lifecycle requests still travel through the inbox.

Keep the host process running while the guest is in use. A lost acknowledgement can leave a
switch in progress. Preserve the inbox, journal and private native state until the host can
establish which child or container incarnation is active. Restarting with a fresh journal would
discard that evidence. [Prepare and operate the desktop Reactor](../deployments/container-desktop.md#desktop-reactor)
· [Platform differences](../deployments/platform-differences.md#animators)
