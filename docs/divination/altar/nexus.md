---
title: Nexus
icon: material/transit-connection-variant
---

# :material-transit-connection-variant: Nexus

The Nexus is the capability board — the machine's power state as seen from the
[Altar](index.md). It is the operator surface for the
**[Dispatcher](../../adr/22-dispatcher.md)** (which capability a request resolves to) and
the **[Orchestrator](../../adr/23-orchestrator.md)** (which hardware is warm and what is
swapping).

## Reading a capability's state

Every capability the daemon knows about appears on the Nexus in one of six states. This is
the projection the Orchestrator and Dispatcher agree on — the state you read here is the
state a run will actually see.

| State | Meaning | What you can do |
| :--- | :--- | :--- |
| **active** | Warm and accepting requests right now. | Route to it immediately; no swap needed. |
| **warming** | Activation in flight — the model is loading. | Wait; it will become **active** shortly. |
| **awaited** | A `DYNAMIC` capability that is reachable but not yet loaded (the container is up; the model needs an in-runtime activation step). | Request it and the Dispatcher drives the soft activation for you. |
| **cold** | The unit is down or the endpoint is unreachable. | Requesting it triggers a hardware transition (a coven swap) if LychD owns its lifecycle. |
| **fault** | The capability is in error. | Diagnose via [Exorcism](../../praxis/exorcism.md) — check the unit's logs. |

These map directly to a capability's underlying **lifecycle** and **phase**, explained for
users in [Capabilities](../../sepulcher/animator/capabilities.md) and canonically in the
[Dispatcher (22)](../../adr/22-dispatcher.md). The Nexus never shows raw enum values — it
shows this operator vocabulary.

## What else the Nexus shows

- Which **[Coven](../../adr/23-orchestrator.md)** is active, and which are warming, cold, or
  in a swap.
- Which **[Soulstones](../../sepulcher/animator/soulstone.md)** and
  **[Portals](../../sepulcher/animator/portal.md)** are available.
- Queue depth and active work per queue, and the **leases** currently held — the live
  grants a run holds against a capability. A capability with an active lease is protected:
  the Orchestrator's drain waits for it to release before a swap. See
  [Manage Covens](../../praxis/rites/manage-covens.md).
- The hardware pressure and swap tickets behind any pending transition.

## Driving a transition

If you want a model or coven that is currently occupied by background work, the Nexus is
where the tradeoff becomes legible — and, where policy allows, where you request the swap.
A hard swap is gated by priority: a low-priority request against a busy coven is declined
rather than allowed to thrash the hardware. The full rite is
[Manage Covens](../../praxis/rites/manage-covens.md).

The Altar surface may expose a small coven status or request control elsewhere, but the
Nexus is where the full routing and power state becomes inspectable. Orchestration is never
hidden behind a casual dropdown.
