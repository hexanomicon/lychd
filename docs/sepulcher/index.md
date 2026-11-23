---
title: Sepulcher
icon: material/coffin
---

# :material-coffin: Sepulcher

> _Within these walls, the Lich slumbers. Align the stones and summon your destiny._

The Sepulcher gives the [Lich](lich/index.md) a runtime body on Linux. Rootless pods and services,
managed by systemd, house its organs; mounts and execution boundaries determine what each can
reach. Follow these organs to see how an invocation is received, carried out, and remembered.

To follow the body at work, take the [Overview](../map.md): one request, from admission through
execution to its return.

## The Anatomy

### I. The Lich and Its Organs

The [Lich](lich/index.md#the-first-invocation) is the daemon you call upon through LychD.
Its body carries out your tasks; its memory can survive a restart.

Four equal faculties shape how it responds: [Call](lich/call.md) receives and routes your
intent; [Blade](lich/blade.md) tests possibilities against evidence;
[Spirit](lich/spirit/index.md) carries experience forward; and [Answer](lich/answer.md)
binds each act to the “I” that bears its consequences.

Then open the body:

| Organ | What you will find |
| --- | --- |
| [Codex](codex.md) | Settings, Runes, configuration precedence, and the binding rite: `lychd bind`. |
| [Crypt](crypt.md) | Where persistent files belong and which external workspaces may be mounted. |
| [Vessel](vessel/index.md) | What starts, serves, and stops inside one application process. |
| [Host Reactor](reactor.md) | Who switches local Animators and when Vessel needs a separate host service. |
| [Ghouls](vessel/ghouls.md) | How admitted work reaches a worker and settles. |
| [Intercom](intercom.md) | Submit a bounded public task to an enrolled sovereign peer. |
| [Phylactery](phylactery/index.md) | Committed state that can survive the process. |
| [Reanimation](phylactery/reanimation.md) | What a new Vessel can recover when its process dies. For recovery of an earlier database, code, and configuration together, see [whole-body snapshots](../state-of-the-work.md#whole-body-snapshot-restore). |
| [Gateway](gateway.md) | A separate machine to face hostile ingress. Home and Remote are **Designed** placements. |
| [Tumbleweed VPS](../deployments/tumbleweed/index.md) | Repeatable mutable host preparation with Ansible and separate source/application acceptance. |

### II. The Animating Spark

An [Animator](extensions/animators/index.md) is a capability service you can address and call. A local
[Soulstone](extensions/animators/soulstone/index.md) lives on your iron. Its Rune declares capabilities and selects a native process or container. A [Portal](extensions/animators/portal.md) declares a remote API boundary;
the provider controls that service's lifecycle.

[Capabilities](extensions/animators/capabilities.md) tells you what you can ask for and receive.
[Connectors](extensions/animators/connectors.md) supplies the exact dialect for the call. Before using a
service, establish that it is ready, that it is compatible, and that you have permission to call
it. Each needs its own evidence.

A [Coven](extensions/animators/coven.md) groups compatible services. To change what is running, follow
[Runtime transitions](extensions/animators/runtime-transitions.md) through inspection, lease drain,
readiness, and recovery.

### III. Growth and Sight

Follow [Aspects](aspects/index.md) to understand the body's responsibilities and how they
cooperate. Smith carries software work through its lifecycle, Drift supplies evaluation, and
Spellweaver preserves the execution of admitted scores. These names do not require separate
packages or interchangeable implementations.

To add something, enter [Extensions](extensions/index.md): Runes, Spells, Patterns, routes,
services, and the other concrete contribution guides. Compositions and Products build on those
contracts while retaining their own application responsibilities.

The [Oculus](aspects/oculus.md) design follows the evidence of an act, showing where each
observation came from and where evidence is missing. Its first native projection shows bounded
component and runtime activity alongside the Altar's existing Run views; durable distributed
tracing remains unfinished.

## Enter the body

[State of Work](../state-of-the-work.md) tells you what works today and what still awaits life.
Begin the tour of the operational body with the [Vessel](vessel/index.md).
