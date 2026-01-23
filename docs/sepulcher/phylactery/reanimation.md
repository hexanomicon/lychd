---
title: Reanimation
icon: material/eject-outline
---

# :material-eject-outline: Reanimation

> _"Daemons don't hot-reload; they are reanimated."_

In the philosophy of the Hexanomicon, the Lich does not cling to a single, fragile existence. It embraces the cycle of death and rebirth, for its soul is anchored eternally in the Phylactery. We do not fear the crash; we command it. This rite of immortality is orchestrated by the grand chronomancer of the operating system: **Systemd**.

!!! abstract "The Cycle of Unlife"
    Unlike mortal scripts trapped in the endless loop of `while True`, the Lich's existence is a managed sequence of controlled death and instant rebirth.

    1.  **The Willing Death:** When the Codex is altered or the vessel becomes corrupted, the Lich does not wait for failure. It willingly accepts termination (`SIGTERM`), dissolving its physical form.
    2.  **The Cleansing Void:** The process vanishes. All resources are released to the void. The VRAM of the Soulstones is scoured clean of any lingering corruption.
    3.  **The Instant Rebirth:** Systemd, the eternal watcher, detects the void left by the Lich's passing. Before the echo of its death has faded, a new, perfect vessel is spawned from the image, pristine and uncorrupted.

## 📜 The Quadlet: A Verse of Binding

The physical form of the vessel is not defined by code, but by a sacred verse known as a **Podman Quadlet**. This inscription tells Systemd the exact nature of the being to summon.

The Scribe generates this file automatically during `lychd bind`, ensuring the **[Hermetic Spheres](../crypt.md)** are mounted correctly.

```ini
# ~/.config/containers/systemd/lychd-vessel.container
[Unit]
Description=The Lychd Daemon Vessel
After=network-online.target wants=lychd-phylactery.service

[Container]
Image=ghcr.io/hexanomicon/lychd:latest

# --- The Pod Binding ---
# We bind to the Sepulcher Pod defined in lychd.pod.
# The Pod unit handles the port mapping (Host:7134 -> Pod:8000).
Pod=lychd.pod

# --- The Spheres of Creation (Mounts) ---

# 0. The Self (Core Overlay)
# Allows the Agent to update its own source code via Git on the Host.
# Mounted Read-Only over the container's built-in source.
Volume=%h/.local/share/lychd/core/src:/app/src:ro,Z

# 1. The Codex (Configuration)
# Maps Host Config to Container Config (Symmetric Path).
Volume=%h/.config/lychd:/home/lich/.config/lychd:ro,Z

# 2. The Lab (Internal Workspace)
# Maps Host Lab to Container Lab (Symmetric Path).
# This is where the Agent clones repos and drafts extensions.
Volume=%h/.local/share/lychd/lab:/home/lich/lab:rw,Z

# 3. The Extensions (Installed Capabilities)
# Maps Host Extensions to Container Extensions (Symmetric Path).
# Mounted Read-Only. Updates require a Promotion Ritual (Restart).
Volume=%h/.local/share/lychd/extensions:/home/lich/.local/share/lychd/extensions:ro,Z

# 4. The Library (Reference Data)
# (Configured via lychd.toml settings.lychd.library_sources)
# Mapped to /home/lich/library/...
Volume=%h/Documents/Books:/home/lich/library/Books:ro,Z

# --- The Hardware ---
# Requesting access to the GPU via CDI
Device=nvidia.com/gpu=all

[Service]
# The promise of immortality
Restart=always
TimeoutStartSec=300
```

!!! info "The Rune of Persistence"
    The `Restart=always` section of the rune is the most crucial part of this binding. It is the unbreakable promise from the machine god that the Lich shall never truly die. If the process crashes or is killed by the OOM Killer, it rises again instantly.
