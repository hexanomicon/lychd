---
title: 12. CLI Interface
icon: material/console-line
---

# :material-console-line: 12. CLI as the Ritualistic Interface

!!! abstract "Context and Problem Statement"
    The LychD system operates as an always-on daemon ("The Vessel") serving an interactive web UI. However, a separate control plane is required for management tasks such as initialization, configuration, and lifecycle control.

    Furthermore, the adoption of the "Hermetic Spheres" architecture (ADR 0018) isolates the Agent within a restricted `active` subvolume, preventing it from accessing the host filesystem directly. A mechanism is required to bridge this isolation—acting as a secure conduit for transferring matter (files) and controlling the daemon without exposing the user to the underlying complexity of `systemctl` or `podman`.

## Decision Drivers

- **Bridging the Hermetic Seal:** The interface must facilitate the safe movement of files into and out of the **Lab** without breaking container isolation or requiring manual root operations.
- **Orchestration Abstraction:** The user interacts with "LychD" as a unified concept; the underlying system commands (`systemctl`, `journalctl`, `podman`) should be abstracted away.
- **Shared Configuration Context:** The management tool must share the exact same configuration logic and domain models as the main application to prevent drift.
- **Scriptability:** All setup and management tasks must be automatable via standard shell scripting.

## Considered Options

!!! failure "Option 1: Standalone CLI Script"
    Develop a distinct Python script or Bash wrapper independent of the main application codebase.

    - **Pros:** Total isolation from the application runtime dependencies.
    - **Cons:** **Maintenance Burden.** Leads to duplication of configuration parsing, path constants, and domain logic. As the application evolves, the standalone script inevitably drifts, leading to bugs.

!!! success "Option 2: Integrated Litestar CLI"
    Leverage Litestar's `CLIPluginProtocol` to create a context-aware bootstrapping process within the main application codebase.

    - **Pros:**
        - **Shared Context:** Utilizes the exact same `Settings` and `Constants` modules as the daemon.
        - **Optimized Loading:** Leveraging the plugin protocol allows for lazy-loading; commands like `lychd import` execute without initializing the heavy database connection pool required by the web server.
        - **Unified Artifact:** A single entry point (`lychd`) serves as both the Server and the Tool.

## Decision Outcome

**Litestar's integrated CLI framework** is adopted as the foundation for the command-line interface. The CLI serves as the "Ritualistic Interface"—the physical hands manipulating the environment that the daemon inhabits.

### Scope and Capabilities

The CLI is organized into discrete functional groups ("Rituals"):

#### 1. Lifecycle Management ("The Pulse")

Wrappers around host system tools to control the daemon's state.

- **`lychd start` / `stop`:** Interfaces with `systemctl` to control the background service.
- **`lychd status`:** Aggregates health checks from the container runtime and the `active` volume.
- **`lychd logs`:** Wraps `journalctl -f -u lychd` to stream daemon logs to the console.

#### 2. Structure & Binding

- **`lychd init`:** Initializes the `active` Btrfs subvolume and strictly defined directory structure.
- **`lychd bind`:** Compiles the configuration into Systemd Quadlet files and performs the daemon-reload.

#### 3. Matter Transfer ("The Bridge")

These commands are the *only* supported method for moving files across the Hermetic Seal.

- **`lychd import <file>`:** Safely copies and sanitizes files from the Host into the Agent's **Lab** (`active/lab`).
- **`lychd export <file>`:** Extracts artifacts from the Agent's **Lab** to the Host.

#### 4. Autopoiesis

- **`lychd snapshot`:** Orchestrates the atomic freeze and backup of the `active` subvolume (implementing ADR 0008).
- **`lychd evolve`:** Pulls the latest container images, applies database migrations, and restarts the daemon.

### Consequences

!!! success "Positive"
    - **Hermetic Integrity:** The Air-Gap is enforced by design. The Agent has no permission to mount host directories; the CLI (running as the user) actively pushes/pulls data on demand.
    - **UX Consistency:** The complexity of Btrfs subvolume management and Systemd unit generation is completely hidden behind a consistent `lychd` command set.
    - **Code Maintainability:** A single codebase ensures that the CLI always understands the current directory layout and configuration schema.

!!! failure "Negative"
    - **Operational Friction:** Moving files requires an explicit command (`lychd import`) rather than a convenient drag-and-drop into a mounted folder. This is a deliberate trade-off for security.
