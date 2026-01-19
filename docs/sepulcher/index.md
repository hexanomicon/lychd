---
icon: material/coffin
---

# :material-coffin: Sepulcher

LychD is orchestrated via **Podman Quadlets** within a central Pod—the Sepulcher. It is the physical and metaphysical structure that houses the Lich and its instruments of power.

The Sepulcher is the anatomy of the Daemon.

!!! abstract ":fontawesome-solid-skull: [Lich](./lich.md)"
    The central intelligence and sovereign will. The Lich is the master; all other components are its servants or extensions of its being.

!!! info ":material-book-open-page-variant: [Codex](./codex.md)"
    The book of laws and configuration runes (`~/.config/lychd`). It dictates the fundamental rules of existence.

## I. Manifestation

*The unholy trinity that forms the body, soul, and earth.*

* :material-skull-scan: **[Vessel](./vessel/index.md) (Granian + Litestar):** The reanimated husk. It orchestrates asynchronous rites via **Ghouls** and serves the **Altar**.
* :material-folder-key: **[Crypt](./crypt.md) (Btrfs Volume):** The physical earth where the daemon rests. It holds the **Spheres** (Files) and the physical files of the database.
* :fontawesome-solid-flask: **[Phylactery](./phylactery/index.md) (Postgres):** The soul-anchor. If the Vessel is destroyed, the Lich reforms instantly from this point.

## II. The Animator

*The spark of cognition that moves the Vessel.*

* :fontawesome-solid-heart-pulse: **[Animator](./animator/index.md):** The unified abstraction layer for intelligence.
* :material-hexagon-slice-6: **[Soulstones](./animator/soulstone.md):** Trapped spirits (Local LLMs) running alongside the Vessel.
* :material-weather-hurricane: **[Portal](./animator/portal.md):** A rift drawing power from distant cloud APIs.

## III. The Watchers

*The eyes that observe the ritual.*

* :material-eye: **[Oculus](./oculus.md):** The Observability Stack. It combines **Arize Phoenix** (Mind), **Structlog** (Voice), and **Cockpit** (Body).
