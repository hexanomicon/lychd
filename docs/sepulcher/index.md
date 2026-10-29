---
title: Sepulcher
icon: material/coffin
---

# :material-coffin: Sepulcher

> _Within these walls, the Lich slumbers. Align the stones and summon your destiny._

The Sepulcher gives the [Lich](lich/index.md) a runtime body on Linux. Rootless pods and services,
managed by systemd, house its organs; mounts and execution boundaries determine what each can
reach. Follow these organs to see how an invocation is received, carried out, and remembered.

To follow the body at work, take the [Map](../map.md): one request, from admission through
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
| [Ghouls](vessel/ghouls.md) | How admitted work reaches a worker and settles. |
| [Intercom](intercom.md) | Submit a bounded public task to an enrolled sovereign peer. |
| [Phylactery](phylactery/index.md) | Committed state that can survive the process. |
| [Reanimation](phylactery/reanimation.md) | What can return after death. |
| [Gateway](gateway.md) | A separate machine to face hostile ingress. Home and Remote are **Designed** placements. |

### II. The Animating Spark

An [Animator](animator/index.md) is a capability service you can address and call. A local
[Soulstone](animator/soulstone/index.md) lives on your iron, with its Rune, container, devices,
mounts, secrets, and lifecycle. A [Portal](animator/portal.md) declares a remote API boundary;
the provider controls that service's lifecycle.

[Capabilities](animator/capabilities.md) tells you what you can ask for and receive.
[Connectors](animator/connectors.md) supplies the exact dialect for the call. Before using a
service, establish that it is ready, that it is compatible, and that you have permission to call
it. Each needs its own evidence.

A [Coven](animator/coven.md) groups compatible services. To change what is running, follow
[Runtime transitions](animator/runtime-transitions.md) through inspection, lease drain,
readiness, and recovery.

### III. Growth and Sight

To understand how the body can grow, enter the [Federation of Extensions](extensions/index.md).
It maps fifteen stable jurisdictions and distinguishes a Domain from the package that registers
a contribution or the provider that implements it. Compositions and Products build on these
roles without absorbing their authority.

The [Oculus](extensions/oculus.md) design follows the evidence of an act, showing where each
observation came from and where evidence is missing. Native Oculus remains **Designed**;
today's Altar offers a narrower view of the work.

## Enter the body

[State of Work](../state-of-the-work.md) tells you what works today and what still awaits life.
Begin the tour of the operational body with the [Vessel](vessel/index.md).
