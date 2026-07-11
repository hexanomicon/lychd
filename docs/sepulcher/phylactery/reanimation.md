---
title: Reanimation
icon: material/eject-outline
---

# :material-eject-outline: Reanimation

> _"Daemons don't hot-reload; they are reanimated."_

In the philosophy of the Hexanomicon, the Lich does not cling to a single, fragile process. It embraces the cycle of death and rebirth because its durable state is anchored in the Phylactery. The crash is not feared; it is bounded. The physical rite of process return is orchestrated by the grand chronomancer of the operating system: **Systemd**.

!!! abstract "The Cycle of Unlife"
    Unlike mortal scripts trapped in the endless loop of `while True`, the Lich's existence is a managed sequence of controlled death and disciplined rebirth.

    1. **The Willing Death:** When the Codex is altered or the vessel becomes corrupted, the Lich does not wait for failure. It willingly accepts termination (`SIGTERM`), dissolving its physical form.
    2. **The Cleansing Silence:** The process vanishes. All resources are released. The VRAM of the Soulstones is scoured clean of any lingering corruption.
    3. **The Managed Rebirth:** Systemd, the eternal watcher, detects the absence left by the Lich's passing and spawns a fresh Vessel from the image. The new process then recovers committed state from the Phylactery rather than pretending every volatile frame survived.

## 📜 The Quadlet: A Verse of Binding

The physical form of the vessel is not defined by code, but by a sacred verse known as a **Podman Quadlet**. This inscription tells Systemd the exact nature of the being to summon.

The Scribe generates this file automatically during `lychd bind`, ensuring the **[Hermetic Spheres](../crypt.md)** are mounted correctly.

```ini
# ~/.config/containers/systemd/lychd-vessel.container
[Unit]
Description=The LychD Daemon Vessel
Wants=network-online.target lychd-phylactery.service lychd-migrate.service
Requires=lychd-migrate.service
After=network-online.target lychd-migrate.service

[Container]
Image=ghcr.io/hexanomicon/lychd:latest

# --- The Pod Binding ---
# Binding to the Sepulcher Pod defined in lychd.pod.
# The Pod unit handles the port mapping (Host:7134 -> Pod:8000).
Pod=lychd.pod

# --- The Spheres of Creation (Mounts) ---

# 0. The Codex (Configuration)
# Maps Host Config to Container Config (Symmetric Path).
Volume=%h/.config/lychd:%h/.config/lychd:ro,Z

# 1. The Crypt (Persistent Reality)
# Maps the full Crypt symmetrically; stricter read-only overlays below
# prevent Core and Extension mutation during normal runtime.
Volume=%h/.local/share/lychd:%h/.local/share/lychd:rw,Z

# 2. The Self (Core Overlay)
# Allows promoted changes to bind host-side source through the VCS layer.
# Mounted Read-Only over the container's built-in source.
Volume=%h/.local/share/lychd/core:%h/.local/share/lychd/core:ro,Z

# 3. The Extensions (Installed Capabilities)
# Maps Host Extensions to Container Extensions (Symmetric Path).
# Mounted Read-Only. Updates require a Promotion Ritual (Restart).
Volume=%h/.local/share/lychd/extensions:%h/.local/share/lychd/extensions:ro,Z

# 4. The Library (Reference Data)
# (Configured via lychd.toml settings.lychd.library_sources)
# Mapped as a read-only Outland beneath ~/work/library/...
Volume=%h/Documents/Books:%h/work/library/Books:ro,Z

# --- The Hardware ---
# Requesting access to the GPU via CDI
Device=nvidia.com/gpu=all

[Service]
# The promise of immortality
Restart=always
TimeoutStartSec=300
```

!!! info "The Rune of Persistence"
    The `Restart=always` section of the rune is the operating system's oath that the Vessel shall rise again. If the process crashes or is killed by the OOM Killer, Systemd starts a new process as policy allows. This is process resurrection, not proof that every cognitive frame survived; durable continuity comes from Phylactery queues, committed outputs, and declared graph checkpoints. The foundation stores each durable graph history as a Postgres JSONB document owned by its run. A transactional graph/queue outbox is later work. Snapshots remain the heavier boundary when whole body/soul rollback is required.
