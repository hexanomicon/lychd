---
title: Animator
icon: fontawesome/solid/heart-pulse
---

# :fontawesome-solid-heart-pulse: Animator

> _Follow the spark to where the iron answers._

A workflow may need a model to answer, a search service to find material, or a renderer to draw.
The **Animator** gives LychD an addressable handle for discovering, probing, and invoking that
service's typed capabilities. A model is one possible source of power; independently managed
search, rendering, or speech services can supply others. The handle says where a capability can
answer. The service's deployment manifest and the application's purpose belong elsewhere.

## Two Sources of Power

| Source | What the operator declares | What LychD can control |
| --- | --- | --- |
| [Soulstone](soulstone/index.md), **The Furnace of Animus** | Local Rune, rootless Podman/Quadlet service, models or profiles, devices, mounts, secrets, and lifecycle. | Admitted local service and supported runtime-native transitions. |
| [Portal](portal.md), **The Rift to the Remote Sky** | Remote endpoint, provider contract, explicit models or profiles, and credential reference. | Its own admitted connection; no provider start, stop, repair, or local VRAM. |

[Portal Roads](portal-roads.md) selects a remote custody and economic road. [Audio hardware and
host routes](audio-routes.md) handles device attachments; a raw device or finite host helper does
not become an Animator merely because its work uses audio.

## The Holy Contract

Check what the service declares, what its bound surface has proved, and what is ready now.
[Capabilities](capabilities.md#declaration-evidence-observation-and-grant) keeps those records
distinct: a probe may invalidate a declaration, but cannot invent a capability.

Adapters keep native protocols behind the stable surface requested by Graph or an extension.
An Animator-backed web effect still needs Scout's separate grant, destination, budget, and receipt.

## The Galvanic Arc

```text
typed demand → declared eligible profile → current observation
  ├─ WARM and admitted → exact grant and lease → invocation → owned return
  └─ managed but cold → handle-free transition → readiness → dispatch again
```

If the service is ready and the request is admitted, Dispatcher supplies the grant and lease.
If a managed service must change first, Orchestrator performs the admissible physical or
runtime-native transition. The waiting Graph keeps neither Connector nor lease while readiness
converges, then returns to dispatch. Current implementation performs this handshake for the
narrower v1 family/model demand and chat-model/toolset compatibility grant.

## Animus: the power answering

**Animus** names the power answering through an admitted, active capability. A loaded model—Gemma
behind llama.cpp—is its clearest instance. The term creates no new runtime object. Orchestrator
owns activation; the Animator is the address, the Connector its conduit, and the CapabilityGrant
the exact permission and lease.

A Spell shapes that draw into a typed request. The return becomes candidate material for the
Circle: Blade discriminates, Spirit carries it in [Flux](../lich/spirit/flux.md), and Answer
binds the act locally. Inference alone supplies neither Persona, identity, memory, authority, nor
operational Cognizance.

## Capability and Readiness

Use [Capabilities](capabilities.md) to name the required operation and interpret its grant or
refusal. Use [Connectors](connectors.md) to bind its exact dialect. For compatible local groups,
enter [Coven](coven.md); to inspect or request a change, follow
[Runtime transitions](runtime-transitions.md).
[State of Work](../../state-of-the-work.md#animation-and-orchestration) owns what each route proves.
