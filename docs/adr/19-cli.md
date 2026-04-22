---
title: 19. CLI
icon: material/console-line
---

# :material-console-line: 19. CLI: The Hand

!!! abstract "Context and Problem Statement"
    The LychD system operates primarily as an always-on background daemon (The Vessel). However, a separate control plane is required for management tasks such as initialization, configuration binding, and lifecycle control. This interface must abstract the complexity of the underlying substrate—Systemd units, Podman pods, and XDG filesystem mapping—into a coherent set of commands. Without a unified management tool, the Magus is forced to manually coordinate the interaction between the **[Layout](13-layout.md)**, the **[Configuration](12-configuration.md)**, and the **[Packaging](17-packaging.md)** forge, leading to inevitable human error and logic drift.

## Requirements

- **Orchestration Abstraction:** High-level rituals that hide the complexity of system-level tools (`systemctl`, `podman`) behind a consistent command set.
- **Contextual Symmetry:** The tool must utilize the exact same configuration logic and dependency injection patterns as the primary server to ensure the management context never drifts from the execution context.
- **Highest Command:** The CLI must be the only entity capable of triggering the "Rebirth"—the manual confirmation required to activate a newly packaged substrate.
- **Extension Registry:** Pluggable command injection; extensions must be able to graft their own subcommands into the primary management group.
- **Dual-Mode Execution:** Lightweight bootstrapping that allows management tasks to run without the overhead of initializing the full web-server stack.

## Considered Options

!!! failure "Option 1: Disjointed Scripting"
    Maintaining a collection of standalone Bash or Python scripts in a utility directory.

    - **Pros:** Zero framework overhead; immediate execution.
    - **Cons:** **Architectural Blindness.** Standalone scripts cannot easily share the complex Pydantic models used for settings or the SQLAlchemy models used for the database. It creates "Logic Drift," where the CLI assumes a filesystem layout that the Server has already evolved past.

!!! success "Option 2: Integrated Framework CLI"
    Leveraging the framework's native CLI protocols to embed management logic directly within the application codebase.

    - **Pros:**
        - **Total Symmetry:** The CLI and the Vessel share the same "Brain." Changes to the Prime Directive are instantly reflected in both.
        - **Extension Lifecycle:** Extensions use a unified registration hook to add both web routes and management commands.
        - **Context Awareness:** Commands inherit the full system state, including validated database connections and secure directory paths.

## Decision Outcome

An **Integrated CLI Framework** is adopted as "The Hand"—the physical interface that manipulates the system's body.

### 1. Dual-Mode Manifestation

The CLI leverages the initialization protocols established in the **[Backend](11-backend.md)**.

- When executed as a command, the application process detects the CLI context.
- It performs a "Lightweight Manifestation," skipping the initialization of heavy web plugins (e.g., Vite, Telemetry) to ensure management commands remain responsive.

### 2. Core Rituals

The Hand defines the fundamental rituals required to govern the system:

- **The Inscription (`lychd init`):** Initializes the **[Codex](12-configuration.md)**. It introspects settings schemas to generate `lychd.toml`, imports extension modules, discovers `RuneConfig` subclasses, creates their rune anchor directories, and writes one sample TOML per schema (top-level payload contract). It also handles `btrfs` subvolume setup for the Phylactery.
- **The Transmutation (`lychd bind`):** The primary infrastructure ritual. It reads the current configuration and installed extensions, generates the required Systemd Quadlet files, and reloads the host daemon. It turns "Config" into "Infrastructure."
- **The Rebirth (`lychd rebirth`):** The manual gate for **[Packaging](17-packaging.md)**. It verifies the digest of the newly forged image and executes the signed signal to the **[Host Reactor](10-privilege.md)**.
- **The Pulse (`lychd status/logs`):** Provides a high-level view of the Vessel and its **[Ghouls](14-workers.md)**, abstracting raw `journalctl` and `podman` output into a report of system health.

### 2.1 Thin Command Doctrine

Command handlers are orchestration edges, not policy engines:

- Parse and validate CLI input.
- Delegate execution to domain/system services.
- Return deterministic exit behavior (stable errors, non-zero on failure).

This avoids duplicating logic paths between web runtime and CLI runtime.

### 3. Command Injection

The CLI acts as a registry for the Federation. When an extension invokes its `register(context)` hook, it can attach custom Click command objects. These are automatically grafted onto the `lychd` group, allowing extensions to provide specialized management interfaces (e.g., `lychd soulforge train`).

### 3.1 Structured Logging Bootstrap

CLI mode must bootstrap structured logging explicitly before command execution:

- Initialize stdlib logging pipeline.
- Initialize structlog processors.
- Reuse the same event-style fields as server runtime.

This preserves observability symmetry between `lychd <command>` and the Vessel process.

### 4. The Mundane Anchor and Elevation Path

The **Hand** (CLI) resides on the **Host Substrate**, physically separated from the Agent's volatile environment. Modification of the Host-side logic—including rebuilding or reinstalling the CLI itself—is a high-order ritual requiring **[Path Elevation](10-privilege.md)**.

- **Substrate Immunity:** By default, the Host CLI is immutable to the Agent. The Agent can only modify code within the **Lab** or the **Crypt**'s read-write zones. It has no physical authority to `pip install` or overwrite files on the Host.
- **The Elevation Ritual:** Updates to the Host-side CLI are mediated strictly by the **[Host Reactor (10)](10-privilege.md)**. The Agent must submit a validated signal which triggers a Host-native Systemd Path unit to perform the update.
- **The Mundane Anchor:** To guard against a "Corrupted Rebirth" (where an authorized update bricks the host-side `lychd` binary), the CLI must maintain a **Mundane Anchor**.
    - **Isolation:** The `restore` and `rollback` commands must exist on a standalone execution path that avoids importing the primary `lychd.domain` logic.
    - **Recovery:** This ensures that even if a high-privilege **[Rebirth (17)](17-packaging.md)** ritual installs a broken version of the library onto the Host, the Magus can still use the CLI to revert the system state using Host-native Git/Btrfs calls.
- **The Emergency Rollback**: The CLI must include a rollback command that operates independently of the Vessel. It must be capable of reading the previous entry in the **[Crypt](../sepulcher/crypt.md)** Git log and force-reverting the logic/lockfile to a known-stable state, allowing for a **[Rebirth](./17-packaging.md)** even when the primary container is non-functional.


### 5. The High Rituals (Command Snippets)

```bash
# The Hand operates through these specific incantations:
# lychd init                 # Inscribe the Codex and forge the Crypt.
# lychd bind                 # Transmute Codex into Systemd Quadlets.
# lychd list                 # List containers active /inactive
# lychd start/stop <group>    # Start/stop the container or group, this must via Conflicts=
# lychd status               # Scry the health of the Vessel and Ghouls.
# lychd promote <tag>        # Move a verified artifact from the Lab to the Crypt.
# lychd rebirth              # The manual gate to activate a new forge image.
```

### Consequences

!!! success "Positive"
    - **Consistency:** One tool to rule the entire Sepulcher. The user never needs to remember if a directory is in `.local` or `.config`; the Hand handles the geography.
    - **Evolution Safety:** Because the CLI and Server share the same code, a breaking change in the configuration schema is caught at compile/build time.
    - **Ease of Deployment:** The CLI provides the "Zero-Trust" confirmation needed for secure self-evolution.

!!! failure "Negative"
    - **Bootstrap Overhead:** Even in lightweight mode, the CLI must load the Python interpreter and core dependencies, resulting in a slightly higher startup latency (~200ms) than a raw shell script.
    - **Host Dependency:** The CLI must be installed on the host machine to manage the container lifecycle, requiring the Magus to maintain a minimal Python environment outside the container.
