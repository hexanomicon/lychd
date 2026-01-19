---
title: Vessel
icon: material/skull-scan
---

# :material-skull-scan: Vessel

> _"The Vessel is the reanimated husk through which the Lich speaks. It is not a tool; it is a conduit."_

The Vessel is the **[Lich's](../lich.md)** physical form in the mortal plane, a construct of code and will that serves as the nexus for all interaction. It is the master of the [Altar](../../divination/altar.md), the summoner of [Ghouls](./ghouls.md), and the dreamer of the [Shadow Realm](./shadow_realm.md).

It is the face the Magus sees and the voice that answers the call.

!!! abstract "Anatomy of the Husk"
    The Vessel is a sophisticated homunculus, constructed from several key arcane components:

    *   **The Breath (`Granian`):** The Rust-based RSGI server that breathes life into the code. It is the raw, high-performance interface that connects the Vessel to the network, allowing it to speak and hear with multi-threaded fury.
    *   **The Skeleton (`Litestar`):** The asynchronous framework that provides the husk with its structure. Litestar holds the routing logic, the dependency injection, and the application lifecycle, allowing the Vessel to stand upright.
    *   **The Wards (`Pydantic`):** The runes of protection that define the Vessel's reality. Pydantic models act as the immune system, enforcing strict type validation to ensure that no corrupted or malformed data can penetrate the inner logic.
    *   **The Synapses (`Pydantic AI`):** The neural pathways that direct the flow of thought. While the **[Animator](../animator/index.md)** provides the raw *capacity* to think, the Synapses define the *strategy*—structuring prompts, managing context windows, and routing decisions through directed graphs.

!!! info "The Will of the Vessel"
    The Vessel is the primary executor of the Lich's will. Its core duties are threefold:

    1.  **To Serve the Altar:** It renders the sacred interface, presenting the Magus with a window into the Lich's operations and a means to issue commands.
    2.  **To Summon the Ghouls:** Upon receiving an Intent, it quickens a swarm of Ghouls, dispatching them to perform the necessary rites in the background.
    3.  **To Dream in Shadow:** It is the master of the Shadow Realm, orchestrating the speculative execution of tasks and presenting the resulting timelines to the Magus for judgment.

!!! warning "A Conduit, Not the Source"
    Remember that the Vessel is a mortal shell. While it is the Lich's primary instrument, its true soul is anchored in the [Phylactery](../phylactery/index.md). If the Vessel is destroyed, it is from the Phylactery that it will be **[Reanimated](../phylactery/reanimation.md)**, its form restored and its purpose renewed.
