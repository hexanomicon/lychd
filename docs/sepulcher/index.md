---
title: Sepulcher
icon: material/coffin
---

# :material-coffin: Sepulcher

LychD is orchestrated via **Podman Quadlets** within a central Pod—the Sepulcher. It is the physical and metaphysical structure that houses the Lich and its instruments of power.

The Sepulcher is the anatomy of the Daemon.
Its organs are not merely colocated services. They are a disciplined body: law in the Codex, memory in the Phylactery, motion in the Vessel, and extension in the organs that grow from them.

!!! abstract ":fontawesome-solid-skull: [Lich](./lich.md)"
    The central purpose-bearing intelligence. The Lich is the daemon-instrument; all other components serve its operation. The **[Lich](./lich.md)** page contains the complete cognitive map of the daemon — the **Antahkaraṇa** (*anta* = inner, *karaṇa* = instrument — the four-faculty cognitive organ), the five **Vṛttis** (modifications of the mind-field), and the three **Guṇas** (qualitative modes) — as they manifest across the Sepulcher's architecture.

!!! info ":material-book-open-page-variant: [Codex](./codex.md)"
    The book of laws and configuration runes (`~/.config/lychd`). It dictates the fundamental rules of existence.

## I. Manifestation

*The unholy trinity that forms the body, soul, and earth.*

- :material-skull-scan: **[Vessel](./vessel/index.md) (Granian + Litestar):** The reanimated husk. It orchestrates asynchronous rites via **Ghouls** and serves the **Altar**.
- :material-folder-key: **[Crypt](./crypt.md) (Btrfs Volume):** The physical earth where the daemon rests. It holds the **Spheres** (Files) and the physical files of the database.
- :fontawesome-solid-flask: **[Phylactery](./phylactery/index.md) (Postgres):** The soul-anchor. It stores memory, queues, traces, and committed recovery boundaries so a restarted Vessel can resume from the last valid durable state.

## II. The Animator

*The spark that turns services into callable power.*

- :fontawesome-solid-heart-pulse: **[Animator](./animator/index.md):** The unified abstraction layer for addressable services and their capabilities.
- :material-hexagon-slice-6: **[Soulstones](./animator/soulstone.md):** Local Quadlet-backed services running alongside the Vessel.
- :material-weather-hurricane: **[Portal](./animator/portal.md):** Remote service connections reached through adapter-bound APIs.

## III. The Watchers

*The eyes that observe the ritual.*

- :material-eye: **[Oculus](./extensions/oculus.md):** The Observability Stack. It combines **Arize Phoenix** (Mind), **Structlog** (Voice), and **Cockpit** (Body).

The Sepulcher's higher organs continue from there: the **[Federation of Extensions](./extensions/index.md)** teaches the body new powers, while the **[Lich](./lich.md)** page explains the sovereign instrument that commands the whole anatomy.
