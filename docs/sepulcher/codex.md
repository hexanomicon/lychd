---
title: Codex
icon: material/book-open-page-variant
---

# :material-book-open-page-variant: Codex

> _"The Hexanomicon is the prophecy. The Codex is the law."_

The Codex is the foundational text that defines the Lich's existence in your realm. It is not a suggestion; it is the **immutable configuration** from which the Sepulcher is summoned. To alter a verse in the Codex is to alter the very nature of the beast you command.

Technically, the Codex is the set of configuration files located at `~/.config/lychd/`, established by the `lychd init` command.

!!! abstract "The Three Sections of Law"
    The Codex is organized into three sacred sections, each governing a different aspect of the Lich's power.

    1.  **The Prime Directive (`lychd.toml`):** This is the core manuscript. It contains the fundamental, high-level settings for the entire daemon—the location of your model cache (`model_root`), logging levels, and other global parameters.
    2.  **The Book of Souls (`conf.d/`):** A collection of scrolls that define the Lich's sources of power. It is here you inscribe the definitions for your [Soulstones](../animator/soulstone.md) (local LLMs) and your [Portals](../animator/portal.md) (cloud APIs).
    3.  **The Runes of Binding (`blueprints/`):** These are the master templates and Quadlet blueprints. The `lychd bind` command reads these runes, along with the Book of Souls, to transmute your abstract configuration into the physical form of Systemd services.

!!! tip "The Rite of Binding"
    The Codex is a static text until its power is invoked. The `lychd bind` command is the rite that reads the Codex and manifests its laws. After editing any verse within the Codex, you must perform this rite to make your changes real. The command transmutes your will into a form the machine god, Systemd, can understand, triggering the **[Reanimation](../phylactacy/reanimation.md)** of the affected components.
