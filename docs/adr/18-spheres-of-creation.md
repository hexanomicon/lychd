---
title: 18. Spheres of Creation
icon: material/earth
---

# :material-earth: 18. The Spheres of Creation

!!! abstract "Context and Problem Statement"
    The LychD Agent is an Artificer designed to generate code and manipulate files. However, granting an AI agent direct write access to the host's personal directories creates an unacceptable risk.

    We need a filesystem architecture that creates a "Hermetic Seal." The Agent must be able to accept inputs and produce outputs, but it must never touch original user data directly. Furthermore, all Agent state must reside within the `active` Btrfs subvolume (ADR 0008) to ensure atomic snapshots, even though the Agent must not have write access to all of it.

## Decision Drivers

- **Safety via Isolation:** The Agent operates in an air-gapped environment relative to the host's personal files.
- **The Copy Principle:** The Agent only works on *copies* of data, never the originals.
- **Unified Storage:** All Agent state (Lab, Extensions, DB) must reside within the `active` subvolume to ensure atomic snapshots work.
- **Granular Permissions:** While the `active` subvolume contains all state, the Agent must only have Write access to specific parts of it to prevent self-destruction.

## Considered Options

!!! failure "Option 1: Host Bind Mounts"
    Mount specific host directories (e.g., `~/Documents`) directly into the container.

    - **Pros:** Immediate access.
    - **Cons:** Dangerous. Accidental deletion is permanent.

!!! failure "Option 2: Single Root Mount"
    Mount the entire `active` subvolume as Read-Write.

    - **Pros:** Simple Quadlet configuration.
    - **Cons:** Unsafe. The Agent could delete its own Extensions or corrupt the Database via the filesystem.

!!! success "Option 3: The Hermetic Spheres (Surgical Mounts)"
    All data lives in `active`, but we mount sub-directories individually to enforce permissions (RW vs RO).

    - **Pros:** Maximum safety. Perfect compatibility with Btrfs snapshots. Prevents the Agent from modifying "Living Tissue" (Extensions) directly at runtime.
    - **Cons:** Slightly more verbose Quadlet configuration.

## Decision Outcome

We define four distinct spheres of file interaction. All distinct spheres reside physically within the `~/.local/share/lychd/active/` subvolume on the Host (except Core), but are mounted surgically into the Container.

### I. The Outer Sphere: The Laboratory (Read-Write)

This sphere encompasses the Agent's workspace. It is the **only** place where the Agent can create or modify files.

- **Host Path:** `active/lab/`
- **Container Path:** `/app/lab` (Mounted **RW**)
- **Workflow:**
    1. **Import:** The user runs `lychd import <file>` to copy data into the Lab.
    2. **Fabrication:** The Agent reads the copy, modifies it, or generates new code.
    3. **Export:** The user runs `lychd export <file>` to retrieve the result.

### II. The Inner Sphere: Extensions (Read-Only)

This sphere encompasses the code that extends the Agent's own functionality.

- **Host Path:** `active/extensions/`
- **Container Path:** `/app/extensions` (Mounted **RO**)
- **Autopoiesis:** To update an extension, the Agent writes code to the **Laboratory**, then triggers a CLI ritual (via Systemd Path Unit) to stop the service, snapshot, and promote the code from Lab to Extensions.

### III. The Core Sphere: Mutations (Read-Only)

This sphere encompasses the LychD source code itself and the Container Image.

- **Location:** `/app/src` (Inside Container Image).
- **Constraint:** Strictly Read-Only.
- **Autopoiesis:**
    1. Agent reads its own source code from `/app/src`.
    2. Agent modifies copies in the **Laboratory**.
    3. Agent triggers a **Rebuild Ritual**.
    4. Host Systemd triggers a `podman build` using the modified code in the Lab, then restarts the service.

### IV. The Library Sphere: Reference (Read-Only)

This sphere allows the user to grant read access to large external datasets without copying them.

- **Host Path:** Defined in `lychd.toml` (e.g., `~/Books`, `~/Photos`).
- **Container Path:** `/app/library/<name>` (Mounted **RO**)
- **Constraint:** The Agent can read but never touch these files. To edit a file, it must be copied to the Lab.

### Consequences

!!! success "Positive"
    - **Absolute Safety:** The Agent cannot physically delete user data on the host. It cannot delete its own extensions or source code.
    - **Snapshot Integrity:** Because `lab` and `extensions` both live in `active`, a single Btrfs snapshot captures the entire state of the system.
    - **Clear Rituals:** The flow of data is explicit. `lychd import` and `lychd export` make data movement intentional.

!!! failure "Negative"
    - **Friction:** The user cannot edit a file "in place" and have the Agent see it instantly; they must re-import the updated copy or work entirely within the Lab via the CLI.
