---
title: 17. Extensions
icon: material/toy-brick-outline
---

# :material-toy-brick-outline: 17. Extension Architecture for User-Defined Capabilities

!!! abstract "Context and Problem Statement"
    Users of LychD require the ability to expand the daemon's capabilities to suit their specific needs (e.g., custom agents, specific hardware integrations).

    However, allowing the Agent to modify its own source code or plugins at runtime is a path to instability. A syntax error written to a live python module can cause the application to crash immediately and enter a restart loop, requiring manual intervention to fix.

    We need a plugin architecture that enables "Autopoiesis" (the creation of new capabilities) without creating a "Self-Destruct Button." The system must distinguish between the **Laboratory** (where unstable code is written) and the **Live Tissue** (where stable code runs).

## Decision Drivers

- **Runtime Stability:** The running application must never be able to crash itself by modifying its own loaded code.
- **Atomic Upgrades:** Changes to extensions should happen transactionally, ideally when the service is stopped.
- **Safety via Isolation:** Development of new features happens in a sandbox; installation is a deliberate, reversible act.
- **Deep Integration:** Despite the isolation, installed extensions need deep access to the Core (Database, Web, CLI).

## Considered Options

!!! failure "Option 1: Read-Write Extension Directory"
    Mount the `extensions/` directory as Read-Write into the container.

    - **Pros:** Immediate feedback. The Agent edits a file, and the auto-reloader updates the app.
    - **Cons:** Extremely dangerous. A single bad write (e.g., deleting `__init__.py` or writing a syntax error) crashes the container. Recovery requires the user to manually fix files on the host.

!!! failure "Option 2: Magic Variable Scanning"
    The loader scans extension files for global variables like `router` or `cli_app` and automatically mounts them.

    - **Pros:** Low boilerplate.
    - **Cons:** Implicit behavior is hard to debug. Lacks a clear contract for advanced features.

!!! success "Option 3: The Lab-to-Live Workflow (Read-Only Mounts)"
    The `extensions/` directory is mounted **Read-Only**. New extensions are built in the **Lab** (Read-Write). A host-side "Ritual" (CLI command) handles the promotion of code from Lab to Live.

    - **Pros:**
        - **Crash Proof:** The Agent cannot break the running service.
        - **Transactional:** Upgrades involve a Stop -> Snapshot -> Replace -> Restart cycle.
        - **Verification:** The "Promotion" step allows for human review or automated testing before code goes live.

## Decision Outcome

We will implement a **Read-Only Extension Architecture** with a **Promotional Workflow**.

### 1. The Physical Layer

- **Live Tissue (`extensions/`):**
    - **Host:** `~/.local/share/lychd/active/extensions/`.
    - **Container:** Mounted to `/app/extensions` as **Read-Only**.
    - **Purpose:** Contains the currently installed, working plugins.

- **The Laboratory (`lab/`):**
    - **Host:** `~/.local/share/lychd/active/lab/`.
    - **Container:** Mounted to `/app/lab` as **Read-Write**.
    - **Purpose:** The workspace where the Agent generates, edits, and tests new plugin code.

### 2. The Promotion Ritual

To install or update an extension, a transition of matter must occur. This is orchestrated by the Host CLI (`lychd extension install`).

**The Workflow:**

1. **Fabrication:** The Agent builds a new plugin in `/app/lab/my_new_agent`.
2. **Request:** The Agent triggers an installation request (via the Systemd Path Unit mechanism defined in ADR 0007).
3. **Transmutation (Host Side):**
    - **Stop:** The LychD service is stopped.
    - **Snapshot:** A Btrfs snapshot of the `active` subvolume is taken (ADR 0008).
    - **Replace:** The code is moved from `active/lab/` to `active/extensions/`.
    - **Restart:** The LychD service is started.
4. **Result:** The container boots with the new code. If it fails, the Snapshot allows an instant rollback.

### 3. The Registration Protocol

Extensions integrate via an **Explicit Registration Hook**. Every valid extension must expose a function with the following signature:

```python
from lychd.core.interface import ExtensionContext

def register(ctx: ExtensionContext) -> None:
    """Entry point for the extension."""
    ctx.add_router(...)
    ctx.add_command(...)
```

### Consequences

!!! success "Positive"
    - **Stability:** It is physically impossible for the Agent to crash the live system by writing bad code, as it cannot write to `extensions/`.
    - **Safety:** Every update is automatically backed up via Btrfs snapshots.
    - **Review:** The separation of "Building" and "Installing" creates a natural checkpoint for human oversight.

!!! failure "Negative"
    - **Development Friction:** The Agent cannot simply "hot reload" changes. It must go through the restart cycle to see changes take effect in the main application.
