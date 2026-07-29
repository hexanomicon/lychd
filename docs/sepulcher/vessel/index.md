---
title: Vessel
icon: material/skull-scan
---

# :material-skull-scan: Vessel

> _“The Vessel is where the daemon takes breath: one trusted process, never the whole Lich.”_

The Vessel is LychD's application process and composition root. It serves the
[Altar](../../divination/altar/index.md), admits supported Invocations, binds domain services, and
hands background execution to [Ghouls](./ghouls.md). It is the running body through which the
[Lich](../lich/index.md) can answer, not the whole Lich by itself.

!!! abstract "Anatomy of the Husk"
    Four technologies give the current Vessel its shape:

    - **The Breath (`Granian`):** the production ASGI server that carries HTTP into the process.
    - **The Skeleton (`Litestar`):** routing, dependency injection, lifecycle, and API authority.
    - **The Wards (`Pydantic`):** typed configuration and boundary validation.
    - **The Synapses (`Pydantic AI`):** typed Agent and Graph mechanics over capabilities supplied
      by [Animators](../animator/index.md).

!!! info "The Will of the Vessel"
    The current Vessel has three concrete duties:

    1. **Serve the Altar:** Litestar serves the compiled static SvelteKit client and remains the
       sole API and production-server authority.
    2. **Admit work:** supported Intent enters a pinned Pattern, run, authority, and continuity
       boundary before execution.
    3. **Coordinate execution:** Ghouls perform admitted background work while the Dispatcher,
       Orchestrator, Graph, and Phylactery retain their separate jurisdictions.

    [Shadow](../extensions/shadow/index.md) remains a designed simulation office; it is not a fourth
    delivered Vessel duty.

!!! warning "A Conduit, Not the Source"
    Process death is not durable continuity. Only state committed through the
    [Phylactery](../phylactery/index.md) can cross that boundary, and only the supported
    [Reanimation](../phylactery/reanimation.md) paths may bring it back. A database record is not a
    soul, and an uncommitted frame is not promised a return.
