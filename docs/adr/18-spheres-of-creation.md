---
title: 18. Spheres of Creation
icon: material/earth
---

# :material-earth: 18. The Spheres of Creation

!!! abstract "Context and Problem Statement"
    The [Lich](../sepulcher/lich.md) functions as an autonomous Artificer capable of generating code and manipulating files. However, granting a stochastic AI process direct write access to the host's personal filesystem creates an unacceptable risk of data loss. A filesystem architecture is required to facilitate file manipulation and [Autopoietic](../divination/transcendence/immortality.md) self-evolution while strictly enforcing a "Hermetic Seal" between the Agent's workspace and the user's original data.

## Decision Drivers

- **Safety via Isolation:** The Agent must operate in an air-gapped environment relative to the host's personal files, preventing accidental deletion or corruption.
- **Unified Storage for Atomicity:** All Agent state (Lab, Extensions, DB) must reside physically within the single `active` Btrfs subvolume (as defined in ADR 0008) to ensure that atomic snapshots capture the complete system state.
- **Granular Permissions:** While the `active` subvolume contains the entire state, the Agent must only possess Write access to specific, volatile areas to prevent self-destruction (e.g., deleting its own source code).
- **The Copy Principle:** The Agent must operate exclusively on *copies* of data, never the originals.

## Considered Options

!!! failure "Option 1: Host Bind Mounts"
    Mount specific host directories (e.g., `~/Documents`) directly into the container as Read-Write.

    - **Pros:** Immediate access for the user.
    - **Cons:** **Catastrophic Risk.** Accidental deletion by the Agent is permanent and affects original user files.

!!! failure "Option 2: Single Root Mount"
    Mount the entire `active` subvolume into the container as Read-Write.

    - **Pros:** Simplified Podman Quadlet configuration.
    - **Cons:** **Internal Instability.** The Agent could accidentally delete installed Extensions or corrupt the Database files directly via the filesystem, bypassing the database engine.

!!! success "Option 3: The Hermetic Spheres (Surgical Mounts)"
    All state resides physically in `active`, but sub-directories are mounted surgically into the container with enforced permissions (RW vs RO).

    - **Pros:** **Maximum Safety.** Prevents the Agent from modifying "Living Tissue" (Extensions) directly at runtime. Ensures perfect compatibility with Btrfs snapshots.
    - **Cons:** Requires a more verbose Quadlet configuration to map individual paths.

## Decision Outcome

Four distinct spheres of file interaction are defined. While the data for the Laboratory and Extensions resides physically within the `~/.local/share/lychd/active/` subvolume on the Host, they are mounted surgically into the Container to enforce the Hermetic Seal.

### I. The Outer Sphere: The Laboratory (Read-Write)

This sphere encompasses the Agent's workspace. It is the **only** location where the Agent is permitted to create or modify files. It serves as both the Input and Output buffer.

- **Host Path:** `active/lab/`
- **Container Path:** `/app/lab` (Mounted **RW**)
- **Workflow:**
    1. **Import:** The user transfers matter via `lychd import doc.pdf`. The CLI sanitizes the file and places a copy into the **Lab**.
    2. **Fabrication:** The Agent reads the copy, modifies it, or generates new code within the container.
    3. **Export:** The user retrieves the result via `lychd export result.py`.
- **Execution (The Sandbox):**
    - To fulfill the **xDDD** workflow, the Agent is granted the capability to spawn **isolated subprocesses** rooted in this directory.
    - The Agent runs `pytest` or executes scripts here to validate logic *before* attempting installation.
    - **Safety:** Because these run as detached child processes, a segfault, panic, or crash in the Lab code **does not** kill the main Daemon.

### II. The Inner Sphere: Extensions (Read-Only)

This sphere encompasses the user-defined code that extends the Agent's capabilities.

- **Host Path:** `active/extensions/`
- **Container Path:** `/app/extensions` (Mounted **RO**)
- **Autopoiesis:** To update an extension, the Agent writes code to the **Laboratory**, then triggers a CLI ritual (via Systemd Path Unit) to stop the service, snapshot the system, and promote the code from Lab to Extensions.

### III. The Core Sphere: Mutations (Read-Only)

This sphere encompasses the LychD source code itself and the Container Image assets.

- **Location:** `/app/src` (Inside Container Image).
- **Constraint:** Strictly Read-Only.
- **Autopoiesis:**
    1. Agent reads its own source code from `/app/src`.
    2. Agent modifies copies in the **Laboratory**.
    3. Agent triggers a **Rebuild Ritual**.
    4. Host Systemd triggers a `podman build` using the modified code in the Lab, then restarts the service.

### IV. The Library Sphere: Reference (Read-Only)

This sphere allows the user to grant read access to large external datasets without copying them into the Crypt.

- **Host Path:** Defined in `lychd.toml` (e.g., `~/Books`, `~/Photos`).
- **Container Path:** `/app/library` (Mounted **RO**)
- **Constraint:** The Agent can read but never touch these files. To edit a file, it must first copy it to the Laboratory.

### Consequences

!!! success "Positive"
    - **Absolute Safety:** The Agent is physically incapable of deleting user data on the host, and it cannot accidentally delete its own extensions or source code during runtime.
    - **Snapshot Integrity:** Because both `lab` and `extensions` reside within the `active` subvolume, a single Btrfs snapshot captures the entire state of the system—both the "Work in Progress" and the "Installed Capabilities."
    - **Explicit Data Flow:** The flow of data is intentional. The usage of [CLI Rituals](./12-cli-interface.md) (`lychd import`/`export`) forces a conscious decision to move data across the barrier.

!!! failure "Negative"
    - **Operational Friction:** The user cannot edit a file "in place" on the host and have the Agent see it instantly; they must re-import the updated copy or work entirely within the Lab via the CLI.
