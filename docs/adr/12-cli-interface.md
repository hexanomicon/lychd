---
title: 12. CLI Interface
icon: material/console-line
---

# :material-console-line: 12. CLI as the Ritualistic Interface

!!! abstract "Context and Problem Statement"
    The LychD project is a dual-natured entity. It is an always-on daemon (the Vessel) serving an interactive web UI, but it requires a separate control plane for management. Furthermore, with the adoption of the "Hermetic Spheres" architecture (ADR 0018), the Agent is sealed inside the `active` subvolume and cannot reach out to the host filesystem.

    We need a robust Command-Line Interface (CLI) that serves as the "Ritualistic Interface." This interface must not only handle setup and configuration but also act as the sole bridge for transferring matter (files) across the Hermetic Seal and controlling the daemon's lifecycle.

## Decision Drivers

- **Scriptability:** All setup and management tasks must be automatable.
- **Abstraction:** The user should control "LychD," not have to memorize underlying `systemctl` or `podman` commands.
- **The Bridge:** The CLI must facilitate the safe movement of files into the `inbox` and out of the `lab` without breaking container isolation.
- **Separation of Concerns:** The CLI handles *Structure* and *Matter*; the Web UI handles *Interaction* and *Divination*.

## Considered Options

!!! failure "Option 1: Separate CLI Application"
    Build a standalone Python script unrelated to the main app.

    - **Pros:** Isolation.
    - **Cons:** Maintenance nightmare. Duplication of configuration and domain logic.

!!! success "Option 2: Integrated Litestar CLI"
    Leverage Litestar's `CLIPluginProtocol` to create a context-aware bootstrapping process.

    - **Pros:**
        - **Shared Context:** Uses the same configuration as the main daemon.
        - **Performance:** Lazy-loads components; `lychd import` does not need to start the database pool.
        - **Unified Binary:** A single entry point (`lychd`) for the Server, the Agent, and the Tools.

## Decision Outcome

We will use **Litestar's integrated CLI framework** as the foundation for all command-line rituals. The CLI acts as the physical hands of the Magus, manipulating the environment that the Lych inhabits.

### Scope of the CLI

The CLI performs **Rituals**—discrete actions with clear boundaries.

#### 1. Lifecycle Management (The Pulse)

Wrappers around Systemd/Journalctl to control the daemon without exposing underlying OS complexity.

- **`lychd start` / `lychd stop`:** Awakens or Slumbers the background service.
- **`lychd status`:** Reports the health of the container and the `active` volume.
- **`lychd logs`:** Streams the daemon's logs (wraps `journalctl -f -u ...`).

#### 2. Structure & Binding

- **`lychd init`:** Initializes the `active` Btrfs subvolume and directory structure.
- **`lychd bind`:** Generates the Systemd Quadlet files to mount the `active` volume.

#### 3. Matter Transfer (The Bridge)

- **`lychd import <file>`:** Safely copies files from the Host into the Agent's `active/inbox`.
- **`lychd export <file>`:** Safely extracts files from the Agent's `active/lab` to the Host.

#### 4. Future Capabilities

- **`lychd snapshot`:** Orchestrates the atomic freeze and backup of the `active` subvolume (per ADR 0008).
- **`lychd evolve`:** The mutation ritual. Pulls the latest container image or source updates and restarts the daemon.

### Consequences

!!! success "Positive"
    - **Hermetic Integrity:** The CLI enforces the air-gap. The Agent never touches the Host; the CLI moves the data for it.
    - **UX Consistency:** The user interacts with one tool (`lychd`) for everything, hiding the complexity of Systemd and Btrfs.
    - **Maintainability:** Shared codebase ensures the CLI always understands the current directory layout.

!!! failure "Negative"
    - **Framework Coupling:** Deep integration with Litestar's lifecycle.
    - **UX Friction:** Moving files requires a command rather than drag-and-drop, a deliberate trade-off for safety.
