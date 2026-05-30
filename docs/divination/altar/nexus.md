---
title: Nexus
icon: material/transit-connection-variant
---

# :material-transit-connection-variant: Nexus

The Nexus is the heart of the machine as seen from the Altar.

It is the operator surface for the **[Dispatcher](../../adr/22-dispatcher.md)**, **[Orchestrator](../../adr/23-orchestrator.md)**, **[Animator](../../sepulcher/animator/index.md)**, and active **Covens**.

The Nexus shows:

- which Invocations and worker jobs are pressuring the system
- which queues are active, blocked, or draining
- which Coven is active
- which Covens are busy, warming, sleeping, or available
- which Soulstones and Portals are available
- which capabilities the Dispatcher can grant
- what hardware pressure exists
- what is warming, sleeping, swapping, or unhealthy

The Altar surface may expose a small Coven status or request control, but the Nexus is where the full routing and power state becomes inspectable.

If the Magus wants a model or Coven that is currently occupied by background work, the Nexus is the place to understand the tradeoff and, where policy allows, stop, reprioritize, warm, or swap work. The Altar should not hide this orchestration behind a casual dropdown.
