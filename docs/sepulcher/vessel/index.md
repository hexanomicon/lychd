---
title: Vessel
icon: material/skull-scan
---

# :material-skull-scan: Vessel

> _“The Vessel is where the daemon takes breath: one trusted process, never the whole Lich.”_

The Vessel is LychD's trusted application process and composition root. It serves the
[Altar](../../divination/altar/index.md), admits supported Invocations, binds domain services, and
hands queued execution to [Ghouls](./ghouls.md). Through it the [Lich](../lich/index.md) can answer.

!!! abstract "Anatomy of the Husk"
    Four technologies give the current Vessel its shape:

    - **The Breath (`Granian`):** production ASGI.
    - **The Skeleton (`Litestar`):** routing, injection, lifecycle, and API authority.
    - **The Wards (`Pydantic`):** typed configuration and validation.
    - **The Synapses (`Pydantic AI`):** Agent and Graph mechanics over
      [Animator](../animator/index.md) capabilities.

!!! info "The Will of the Vessel"
    The current Vessel has three concrete duties:

    1. **Serve the Altar:** Litestar serves the compiled static SvelteKit client and remains the
       sole API and server authority.
    2. **Admit work:** supported Intent enters a pinned Pattern, Run, authority, and continuity
       boundary.
    3. **Coordinate execution:** Ghouls perform admitted background work while the Dispatcher,
       Orchestrator, Graph, and Phylactery retain their separate jurisdictions.

Exactly one ASGI process is a correctness boundary. Its two SAQ workers, live run events,
cancellation, and service graph share one event loop; a second process or reload supervisor would
create a second private world.

Queue connection, service construction, registry warm-up, and substrate publication must succeed
before the Altar serves. Reconciliation then runs best-effort: failure is logged and leaves the
Altar available. Shutdown stops workers before collaborators and queues.

!!! warning "A Conduit, Not the Source"
    Process death ends volatile work and live subscribers. State committed through the
    [Phylactery](../phylactery/index.md) may cross that boundary through a supported
    [Reanimation](../phylactery/reanimation.md) path.

Follow [Ghouls](./ghouls.md) for execution or the [Phylactery](../phylactery/index.md) for what
survives. [ADR 11](../../adr/11-backend.md) owns this architecture; [Topology-A local run
execution](../../state-of-the-work.md#topology-a-local-runs) is **Available**.
