---
title: 17. Extensions
icon: material/toy-brick-outline
---

# :material-toy-brick-outline: 17. Extension Architecture for User-Defined Capabilities

!!! abstract "Context and Problem Statement"
    The LychD architecture is designed as a foundational platform for autonomous agents, functioning analogously to a web framework like Django. To serve as a versatile "Operating System for Intelligence," the system requires a standardized extension protocol.

    This protocol must allow users to define and inject custom capabilities—ranging from specific database models and CLI commands to specialized agentic workflows—without modifying the core daemon. These user-defined extensions exist independently of the system's own source code, effectively acting as "Applications" running on top of the LychD platform.

## Decision Drivers

- **Secure Extensibility:** A mechanism is required to enable deep system extension—allowing users to add private CLI commands or database models—while strictly isolating the stable, running service from the volatile nature of code development.
- **Deep Integration:** Extensions must be able to hook into all four pillars of the application:
    1. **The Pulse (CLI):** Registering new `lychd` commands.
    2. **The Altar (Web):** Adding new routes and HTML templates.
    3. **The Brain (Agents):** Defining PydanticAI graphs and SAQ job handlers.
    4. **The Phylactery (DB):** Defining SQLAlchemy models and Alembic migrations.
- **Runtime Stability:** The running application must be physically incapable of modifying its own executable code to prevent self-inflicted crashes.
- **Transactional Upgrades:** The promotion of code from the development environment to the live environment must be an atomic operation that includes a system snapshot, ensuring that any failed upgrade can be instantly rolled back.

## Considered Options

!!! failure "Option 1: Read-Write Extension Directory"
    Mount the `extensions/` directory as Read-Write into the container.

    - **Pros:** Immediate feedback via hot-reloading.
    - **Cons:** **Fragile.** A single bad write (e.g., a syntax error in `__init__.py`) crashes the container instantly. Recovery requires manual intervention on the host filesystem, violating the "Daemon as Appliance" philosophy.

!!! failure "Option 2: Magic Variable Scanning"
    The loader scans extension files for global variables like `router` or `cli_app` and automatically mounts them.

    - **Pros:** Low boilerplate for simple scripts.
    - **Cons:** **Implicit Behavior.** Lacks a clear contract for advanced features like database migrations or complex agent setups. Hard to debug when things fail silently.

!!! success "Option 3: The Lab-to-Live Workflow (Read-Only Mounts)"
    The `extensions/` directory is mounted **Read-Only**. New extensions are built in the **Lab** (Read-Write). A host-side "Ritual" (CLI command) handles the promotion of code from Lab to Live.

    - **Pros:**
        - **Crash Proof:** The Agent cannot break the running service.
        - **Transactional:** Upgrades involve a Stop -> Snapshot -> Replace -> Restart cycle.
        - **Verification:** The "Promotion" step allows for automated testing or human review before code becomes part of the executable.

## Decision Outcome

We will implement a **Read-Only Extension Architecture** with a **Promotional Workflow**.

### 1. The Physical Layer

- **Live Tissue (`extensions/`):**
    - **Host Path:** `~/.local/share/lychd/active/extensions/`
    - **Container Path:** `/app/extensions` (**Read-Only**)
    - **Purpose:** Contains the currently installed, working plugins.

- **The Laboratory (`lab/`):**
    - **Host Path:** `~/.local/share/lychd/active/lab/`
    - **Container Path:** `/app/lab` (**Read-Write**)
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

### 3. The Trial (Validation Strategy)

To address the tension between **Stability** (Read-Only Isolation) and **Velocity** (Fast Feedback), a strict validation step is mandated prior to the Promotion Ritual.

**The Problem:** Restarting the entire service to test a simple syntax error is inefficient. However, loading untrusted code into the main process during development risks crashing the daemon.

**The Solution:** **Sacrificial Subprocesses**.

Before code is accepted for promotion, it must pass a "Trial" within the Laboratory.

- **Mechanism:** The Agent spawns an ephemeral Python subprocess (e.g., invoking `pytest` or a verification script) strictly isolated from the main daemon's memory space.
- **Action:** This process attempts to import the candidate extension and execute its logic against a mock context.
- **Outcome:**
    - **Failure:** The subprocess crashes. The Agent captures the error (stderr) and iterates on the code. The Main Daemon remains alive.
    - **Success:** The code is deemed syntactically valid and the Agent may proceed to trigger the **Promotion Ritual**.

*Note: This replaces "Hot Reloading" with "Fast Pre-Validation," strictly adhering to the "Appliance" philosophy while allowing rapid iteration.*

### 4. The Registration Protocol

Extensions integrate via an **Explicit Registration Hook**. Every valid extension must expose a function with the following signature:

```python
from lychd.core.interface import ExtensionContext

def register(ctx: ExtensionContext) -> None:
    """Entry point for the extension."""
    # 1. The Altar (Web)
    ctx.add_router(my_router)

    # 2. The Pulse (CLI)
    ctx.add_command(my_cli_command)

    # 3. The Brain (Agents)
    ctx.add_agent(my_pydantic_graph)
    ctx.add_worker_functions([my_saq_job])

    # 4. The Phylactery (DB)
    # Note: Alembic migrations are auto-detected if models inherit from Base
    ctx.add_models([MyModel])
```

### Consequences

!!! success "Positive"
    - **Stability Assurance:** It is physically impossible for the Agent to crash the live system by writing bad code, as it lacks write permissions to `extensions/`.
    - **Safe Velocity:** The **Trial mechanism** (sacrificial subprocess) allows the Agent to validate code syntax and logic in milliseconds. This preserves the speed of the "write-test-debug" loop without risking the daemon's uptime.
    - **Atomic Safety:** Every update is automatically backed up via Btrfs snapshots, ensuring that a failed upgrade is never fatal.

!!! failure "Negative"
    - **Deployment Latency:** While testing is fast, **true Hot-Reloading of the live service is explicitly rejected.** To make an extension "Live" and usable by the full system, a service restart (via the Promotion Ritual) is still mandatory. We accept this specific friction to guarantee consistent state.
