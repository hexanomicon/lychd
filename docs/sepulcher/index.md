---
title: Sepulcher
icon: material/coffin
---

# :material-coffin: Sepulcher

> _Within these walls, the Lich slumbers. Align the stones and summon your destiny._

The Sepulcher is LychD's runtime body: rootless pods and services, managed by systemd on Linux,
with their mounts and execution boundaries. These pages lay open the organs that sustain the
[Lich](lich/index.md) from one invocation to the next.

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

The [Federation of Extensions](extensions/index.md) maps fifteen stable jurisdictions for new
organs. It explains how a Domain relates to a selected package, a contribution, or a provider,
and how Compositions and Products use them.

The [Oculus](extensions/oculus.md) design follows the evidence of an act, showing where each
observation came from and where evidence is missing. Native Oculus remains **Designed**;
today's Altar offers a narrower view of the work.

## Enter the body

[State of Work](../state-of-the-work.md) tells you what works today and what still awaits life.
Begin the tour of the operational body with the [Vessel](vessel/index.md).
