---
title: Altar
icon: fontawesome/solid/dungeon
---

# :fontawesome-solid-dungeon: Altar

> _"Altus - the high place. From here, the Magus acts as the Arbiter. The Lich proposes; the Magus disposes."_

The Altar is the sacred, interactive space where the Magus meets the Machine. It is the cockpit of the Sepulcher, the dashboard from which all Rites of [Divination](./index.md) are performed.

Access the Altar at **`http://localhost:7134`**.

Technically, the Altar is a hyper-efficient, server-rendered frontend. While it leverages **HTMX** and **AlpineJS** for runtime interactivity, its assets are forged through a modern **Vite** and **PostCSS** pipeline, ensuring the interface is optimized, hermetic, and server-authoritative.

!!! abstract "The Sanctum of Interaction"
    The Altar is not a static page, but a living conduit. Its surface shifts and updates in real-time to reflect the Lich's inner state. Its core functions are:

    1.  **The Offering Plate (Input):** This is where you submit your **Intents**. You do not write code here; you write *Desire*. ("Refactor this module," "Analyze this log," "Plan the deployment.")
    2.  **The Scrying Mirror (Observation):** It displays the live, spectral tethers of the [Ghouls](../sepulcher/vessel/ghouls.md) as they work in the background. You watch the logs flow like a river.
    3.  **The Judgment Seat (The Albedo Interface):** When the Ghouls return from the **[Shadow Realm](../sepulcher/vessel/shadow_realm.md)** with potential timelines, they present them here.

!!! info "The Collapse of the Wavefunction"
    This is the Altar's most critical purpose.

    The Lich may present three different implementations of a feature.
    *   *Timeline A:* Elegant but incomplete.
    *   *Timeline B:* Functional but ugly.
    *   *Timeline C:* The hallucinations of a mad god.

    At the Altar, you perform the **Rite of Albedo**. You click. You select. You edit.

    By choosing one timeline, you **collapse the wavefunction**. The chosen path is inscribed into reality (the disk) and burned into the **[Phylactery](../sepulcher/phylactery/index.md)** as Karma. The rejected paths dissolve into the void.

!!! tip "Spectral Tethers (Server-Sent Events)"
    The Altar maintains a constant, ethereal connection to the Vessel. Through **Server-Sent Events (SSE)**, the thoughts of the Lich are pushed to the glass in real-time. You do not refresh the page; you watch the daemon think.
