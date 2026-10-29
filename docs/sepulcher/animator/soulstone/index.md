---
title: Soulstone
icon: material/hexagon-slice-6
---

# :material-hexagon-slice-6: Soulstone: The Forged Local Engine

> _A daemon in a bottle, with its fire in your keeping._

A **Soulstone** keeps a service on your own iron: it is a local [Animator](../index.md) running
in a rootless Podman container, projected through Quadlet and supervised by the user's systemd
manager. You describe the service in an immutable **Soulstone Rune** in the Codex. Binding
compiles that intent into its physical service. The Animator adapter then declares what it can
do, probes whether it is ready, and translates any supported runtime-native operations.

For a model-backed capability, the Soulstone is the local furnace in which an
[Animus](../index.md#animus-the-power-answering) may become active. The loaded model lends bounded
power through its Connector and CapabilityGrant; it is not the Lich's Spirit or identity.

The local contract also preserves a practical dimension of sovereignty: useful capability can be
possessed, inspected, stopped, and resumed by the operator rather than existing only as revocable
remote tenancy.

<span id="soulstone-rune-reference"></span>

## The Local Contract

To give a Soulstone its body, name the `quadlet.image`, runtime, models, endpoint, devices,
mounts, secrets, and lifecycle intent. It receives only that declared substrate. The generated
Quadlet governs the service; callers receive a scoped capability rather than the container
itself. The live Soulstone Animator holds the Rune and Connector, separately from the generated
Quadlet document.

The [Rune's schema boundary](./rune.md#schema-and-process-generation) keeps embedded deployment
structure separate from Rune ancestry and Domain ownership. `Soulstone` remains one domain concept,
never `Soul + Stone`, and the only service term ending in “Stone”.

Read [Soulstone Rune](./rune.md) to declare the service and its models. Read
[Resources and Secrets](./resources.md) before granting a device, mount, port, or credential.

## Choose a Discipline

[Disciplines](./disciplines.md) is the short map of the built-in runtime families. The detailed
engine contracts live under [Soulstone Engines](./engines/index.md), including the difference
between a server pinned to one model and a router that activates models in process. The engine
pages own runtime-specific launch, connector, readiness, resource, and evidence boundaries;
Soulstone owns their local lifecycle and Rune binding.

<span id="coven-management-the-group-rule"></span>

## Lifecycle and Readiness

The [Dispatcher](../../../adr/22-dispatcher.md) grants only `WARM`; the
[Orchestrator](../../../adr/23-orchestrator.md) alone owns managed starts, dynamic activation,
conflict drain, and compensation. [Coven](../coven.md) groups compatible services; declared
conflict domains govern physical incompatibility.

## Proof and Recovery

Repository tests prove compilation, adapter contracts, and the declared-conflict topology. A real
systemd/Podman/GPU/model run still needs the named receipt recorded by
[State of Work](../../../state-of-the-work.md#systemd-podman-embodiment). Refusal before mutation
leaves the prior world intact; uncertain mutation remains contained for operator recovery.
