---
title: 19. CLI
icon: material/console-line
---

# :material-console-line: 19. CLI: The Pulse

!!! abstract "Context and Problem Statement"
    The LychD system operates primarily as an always-on background daemon (The Vessel). However, a separate control plane is required for management tasks such as initialization, configuration binding, and lifecycle control. This interface must abstract the complexity of the underlying substrate—Systemd units, Podman pods, and XDG filesystem mapping—into a coherent set of commands. Without a unified management tool, the Magus is forced to manually coordinate the interaction between the **[Layout](13-layout.md)**, the **[Configuration](12-configuration.md)**, and the **[Packaging](17-packaging.md)** forge, leading to inevitable human error and logic drift.

## Requirements

- **Orchestration Abstraction:** High-level rituals that hide the complexity of system-level tools (`systemctl`, `podman`) behind a consistent command set.
- **Contextual Symmetry:** The tool must reuse the same settings and domain/system services as the primary server without requiring the ASGI application to exist for local management commands.
- **Highest Command:** The CLI must be the only entity capable of triggering the "Rebirth"—the manual confirmation required to activate a newly packaged substrate.
- **Extension Registry:** Pluggable command injection; extensions must be able to graft their own subcommands into the primary management group.
- **Dual-Mode Execution:** Lightweight bootstrapping that allows management tasks to run without the overhead of initializing the full web-server stack.
- **Reversible Inscription:** Each initialization or destruction dry run must inspect through the
  same planner its execution path consumes, while deletion authority comes from exact ownership
  receipts rather than known path geography.

## Considered Options

!!! failure "Option 1: Disjointed Scripting"
    Maintaining a collection of standalone Bash or Python scripts in a utility directory.

    - **Pros:** Zero framework overhead; immediate execution.
    - **Cons:** **Architectural Blindness.** Standalone scripts cannot easily share the complex Pydantic models used for settings or the SQLAlchemy models used for the database. It creates "Logic Drift," where the CLI assumes a filesystem layout that the Server has already evolved past.

!!! success "Option 2: Native Root with Lazy Framework Bridges"
    Owning the installed command with a small Click root, while entering Litestar lazily only for commands that actually require the ASGI/database application context.

    - **Pros:**
        - **Bootstrap Independence:** Help, initialization, binding, diagnosis, and inspection work before an ASGI app or database is available.
        - **Shared Laws:** Commands still reuse the same settings, extension assembly, and system services as the Vessel.
        - **Bounded Framework Entry:** Server and migration features retain Litestar's supported CLI surfaces without making them the root command.

## Decision Outcome

A **native Click root with lazy framework bridges** is adopted as "The Pulse"—the rhythm by which the Magus drives the system's body.

!!! note "Ruling: the binary is `lychd` (DOC-R1)"
    The installed command is **`lychd`** everywhere — `lychd init`, `lychd bind`, `lychd animators`. This settles the doc-time split (`lych` vs `lychd`): the entry point shipped in `pyproject.toml` is `lychd`, and all documentation and examples use `lychd` verbatim. No `lych` alias is promised.

### 1. Bootstrap and ASGI Separation

The `lychd` entry point owns its root command. Importing it does not construct the Litestar
application and does not connect to Postgres, start SAQ, initialize Pydantic AI, or load Vite.

- `init`, `destroy`, `bind`, `doctor`, `animators`, and `--help` execute through local command
  services.
- `serve` imports Litestar only inside its callback and delegates to the supported ASGI `run`
  surface.
- `database` imports Litestar only inside its callback and delegates to its database lifecycle
  surface (for example, `lychd database upgrade`).

This is a process boundary, not an environment heuristic: local commands do not instantiate a
"light" web application. They simply never enter the ASGI composition path.

### 2. Core Rituals

The Pulse defines the fundamental rituals required to govern the system:

- **The Inscription (`lychd init`):** Initializes the **[Codex](12-configuration.md)** and layout. It generates a round-trippable `lychd.toml`, assembles enabled extensions, creates rune anchors, and writes marked sample TOML without overwriting existing intent. `lychd init --dry-run` executes the same planning boundary and reports `WOULD CREATE`, `PRESERVE`, and `BLOCKED` without changing files, modes, mounts, services, or secrets.
- **The Dissolution (`lychd destroy`):** Reverses only the inactive host inscription that LychD can
  prove it owns. It removes exact Scribe-manifest binding files and unchanged files recorded by
  initialization, then removes recorded directories only when empty. Modified or unsafe recorded
  state blocks the whole plan; pre-existing and foreign state, mounts, Postgres data, model
  shelves, and secrets are preserved. This is not Python-package uninstallation and it is not a
  data-purge command. `lychd destroy --dry-run` uses the same plan as execution; `--yes` confirms a
  safe plan non-interactively but never bypasses a blocker.
- **The Transmutation (`lychd bind`):** The primary infrastructure ritual. It reads the current configuration and installed extensions, generates the required Systemd Quadlet files, and reloads the host daemon. It turns "Config" into "Infrastructure."
- **The Examination (`lychd doctor`):** Performs a read-only preflight over Codex permissions, runes, host tools, secret references, and the selected caged/uncaged deployment shape.
- **The Census (`lychd animators`):** Lists declared Animator capabilities and their observed readiness without changing lifecycle state.
- **The Migration Bridge (`lychd database ...`):** Enters Litestar's database commands lazily. `lychd database upgrade` is the explicit uncaged/development migration path when database credentials are supplied. The normal Quadlet deployment uses its generated migration unit before the Vessel.
- **The Foreground Vessel (`lychd serve ...`):** Enters Litestar's ASGI runner lazily for development and uncaged operation. There is no `lychd run` command.
- **The Rebirth (`lychd rebirth`):** The manual gate for **[Packaging](17-packaging.md)**. It verifies the digest of the newly forged image and executes the signed signal to the **[Host Reactor](10-privilege.md)**.
- **Status and Logs (`lychd status/logs`):** Provides a high-level view of the Vessel and its **[Ghouls](14-workers.md)**, abstracting raw `journalctl` and `podman` output into a report of system health.

### 2.1 Thin Command Doctrine

Command handlers are orchestration edges, not policy engines:

- Parse and validate CLI input.
- Delegate execution to domain/system services.
- Return deterministic exit behavior (stable errors, non-zero on failure).

This avoids duplicating logic paths between web runtime and CLI runtime.

### 3. Command Injection

The CLI is expected to participate in the broader extension architecture, but the active `ExtensionContext` surface does not currently expose a command store. Specialized command injection therefore remains a doctrine target for a richer future registration surface, not a concrete capability of the current source.

### 3.1 Structured Logging Bootstrap

CLI mode must bootstrap structured logging explicitly before command execution:

- Initialize stdlib logging pipeline.
- Initialize structlog processors.
- Reuse the same event-style fields as server runtime.

This preserves observability symmetry between `lychd <command>` and the Vessel process.

### 4. The Mundane Anchor and Elevation Path

The **Pulse** (CLI) resides on the **Host Substrate**, physically separated from the Agent's volatile environment. Modification of the Host-side logic—including rebuilding or reinstalling the CLI itself—is a high-order ritual requiring **[Path Elevation](10-privilege.md)**.

- **Substrate Immunity:** By default, the Host CLI is immutable to the Agent. The Agent can only modify code within the **Lab** or the **Crypt**'s read-write zones. It has no physical authority to `pip install` or overwrite files on the Host.
- **The Elevation Ritual:** Updates to the Host-side CLI are mediated strictly by the **[Host Reactor (10)](10-privilege.md)**. The Agent must submit a validated signal which triggers a Host-native Systemd Path unit to perform the update.
- **The Mundane Anchor:** To guard against a "Corrupted Rebirth" (where an authorized update bricks the host-side `lychd` binary), the CLI must maintain a **Mundane Anchor**.
    - **Isolation:** The `restore` and `rollback` commands must exist on a standalone execution path that avoids importing the primary `lychd.domain` logic.
    - **Recovery:** This ensures that even if a high-privilege **[Rebirth (17)](17-packaging.md)** ritual installs a broken version of the library onto the Host, the Magus can still use the CLI to revert the system state using Host-native Git/Btrfs calls.
- **The Emergency Rollback**: The CLI must include a rollback command that operates independently of the Vessel. It must be capable of reading the previous entry in the **[Crypt](../sepulcher/crypt.md)** Git log and force-reverting the logic/lockfile to a known-stable state, allowing for a **[Rebirth](./17-packaging.md)** even when the primary container is non-functional.


### 5. The High Rituals (Command Snippets)

```bash
# The Pulse operates through these specific incantations:
lychd init                   # Inscribe the Codex and establish the layout.
lychd init --dry-run         # Preview the same Inscription plan without effects.
lychd destroy --dry-run      # Preview exact, ownership-bounded Dissolution.
lychd destroy                # Remove only an inactive, pristine inscription.
lychd doctor                 # Read-only foundation preflight.
lychd animators              # Inspect declared capability/readiness truth.
lychd bind                   # Transmute validated intent into units.
lychd database upgrade       # Explicit uncaged/development migration.
lychd serve --host 127.0.0.1 # Foreground uncaged/development Vessel.
```

### 6. The Arbitration Doctrine

The Pulse and the Vessel can both actuate the same Covens. Two wills issuing `systemctl` verbs against the same targets at once would break the **Law of Exclusivity**'s assumption of a single physical will. The Pulse therefore distinguishes **observation** from **actuation**.

- **Observation commands** (`list`, `status`, `logs`, `animators`) act directly. Reading the substrate contends with nothing.
- **Actuation commands** (`start`, `stop`, `promote`, `rebirth`) SHALL first attempt the Vessel API—while the Vessel lives, its Orchestrator is the sole physical will (**[Orchestrator (23)](23-orchestrator.md)**)—and act directly only when the Vessel is provably down.
- **Bootstrap lifecycle commands** (`init`, `destroy`) operate outside the Vessel. `destroy` may
  remove bound source files only after every exact receipt-derived runtime unit is both inactive
  and disabled; otherwise it fails closed. It never stops or disables a unit on the operator's
  behalf, so it cannot become a competing physical will. Real `init`, `bind`, and `destroy`
  serialize their host effects through one interprocess lifecycle lock; previews create no lock
  file and perform no effect.
- **The Mundane Anchor path** (`restore`, `rollback`) is exempt by design. It exists precisely for the dead-Vessel case (see [§4](#4-the-mundane-anchor-and-elevation-path)) and must never route through a Vessel it may be recovering.

### 7. Implementation Status

xDDD permits doctrine-first specification, but the Logos should state which limbs of the Pulse exist today. The following is the current status of the rituals:

| Command | Status | Notes |
| :--- | :--- | :--- |
| `init` | Implemented | Inscribes the Codex, discovers `RuneConfig` schemas, writes samples, forges the Crypt; `--dry-run` previews the same plan without effects. |
| `destroy` | Implemented | Removes only inactive exact Scribe-owned bindings plus pristine receipt-owned init files and empty recorded directories; `--dry-run` previews and `--yes` confirms without weakening blockers. |
| `bind` | Implemented | Transmutes Codex into Systemd Quadlets and reloads the host daemon. |
| `doctor` | Implemented | Read-only validation of the minimum runnable foundation. |
| `animators` | Implemented | Read-only capability probes over declared animators. |
| `database` | Implemented bridge | Lazily delegates database lifecycle commands to Litestar. |
| `serve` | Implemented bridge | Lazily delegates foreground ASGI execution to Litestar. |
| `runs approve/deny` | Implemented | Records a consent verdict and re-enqueues a durable parked run. |
| `list` | Specified | Observation command; not yet built. |
| `status` / `logs` | Specified | Health observation; not yet built. |
| `start` / `stop` | Specified | Actuation; bound by the Arbitration Doctrine when built. |
| `promote` | Specified | Actuation; Lab → Crypt move, hard-gated. |
| `rebirth` | Specified | Actuation; the manual gate to a new forge image. |
| `restore` / `rollback` | Specified | The Mundane Anchor; must avoid importing `lychd.domain`. |

The native root and the commands marked implemented above are the foundation. Extension command
injection, CLI/Rebirth use of Host Reactor mediation, service lifecycle actuation commands
(`start`/`stop`), Rebirth, and the independent Mundane Anchor remain later work; prose in §3–§6
defines their constraints, not their present availability.

### Consequences

!!! success "Positive"
    - **Consistency:** One tool owns the Sepulcher's geography. The user never needs to remember if a directory is in `.local` or `.config`; the Pulse handles the map.
    - **Evolution Safety:** Because the CLI and Server share the same code, a breaking change in the configuration schema is caught at compile/build time.
    - **Ease of Deployment:** The CLI provides the "Zero-Trust" confirmation needed for secure self-evolution.

!!! failure "Negative"
    - **Bootstrap Overhead:** Even in lightweight mode, the CLI must load the Python interpreter and core dependencies, resulting in a slightly higher startup latency (~200ms) than a raw shell script.
    - **Host Dependency:** The CLI must be installed on the host machine to manage the container lifecycle, requiring the Magus to maintain a minimal Python environment outside the container.
