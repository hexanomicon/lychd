---
title: Soulstone
icon: material/hexagon-slice-6
---

# :material-hexagon-slice-6: Soulstone: The Forged Local Engine

> _"A Portal is a whisper from the remote sky, but a Soulstone is a daemon in a bottle. It lives
> on local iron. It burns local electricity. It answers only the Magus."_

A **Soulstone** is a local [Animator](../index.md): a rootless Podman container projected through
Quadlet and supervised by the user's systemd manager. Its **Soulstone Rune** is immutable Codex
intent. Binding compiles that intent into a physical service; the Animator adapter separately
declares capabilities, probes readiness, and translates supported runtime-native operations.

The local contract also preserves a practical dimension of sovereignty: useful capability can be
possessed, inspected, stopped, and resumed by the operator rather than existing only as revocable
remote tenancy.

<span id="soulstone-rune-reference"></span>

## The Local Contract

Local placement carries local obligations. A Soulstone names its image, runtime, models, endpoint,
devices, mounts, secrets, and lifecycle intent. It receives only that explicit substrate. A
generated Quadlet is its body, not the capability object granted to a caller.

Read [Soulstone Rune](./rune.md) to declare the service and its models. Read
[Resources and Secrets](./resources.md) before granting a device, mount, port, or credential.

## Choose a Discipline

[Disciplines](./disciplines.md) explains the built-in vLLM, SGLang, and llama.cpp runtime shapes,
including the difference between a server pinned to one model and a router that activates models
in process. [ExLlamaV3 through TabbyAPI](./exllamav3.md) owns that runtime's stricter two-key,
whole-stream, and containment contract.

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
