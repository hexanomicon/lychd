---
title: 8. Btrfs Snapshots
icon: material/camera-timer
---

# :material-camera-timer: 8. Btrfs for Atomic Snapshots and Rollbacks

!!! abstract "Context and Problem Statement"
    The LychD system architecture centers on "[Autopoiesis](../divination/transcendence/immortality.md)"—the capacity for the system to modify its own code and state. This operation presents a high risk of corruption; a failure during an agent-led operation could leave the database and source files in an inconsistent or unrecoverable state.

## Decision Drivers

- **Autopoietic Safety:** A mechanism is required to snapshot the entire LychD Crypt (`~/.local/share/lychd`) before self-modification, ensuring a safe, complete fallback point exists.
- **Operational Performance:** Snapshot creation must be effectively instantaneous (O(1)). Furthermore, the mechanism must function with zero performance overhead on the live database during normal operation.
- **Application Consistency:** Snapshots must represent a clean, consistent state of the database (quiesced), rather than a crash-consistent copy.
- **Atomicity:** Snapshot and rollback operations must be atomic (all-or-nothing).
- **Storage Efficiency:** The mechanism must utilize Copy-on-Write (CoW) to minimize storage consumption.

## Considered Options

!!! failure "Option 1: Filesystem-Agnostic Tools (`rsync`/`tar`)"
    Use standard file-copying utilities to back up the data directory before operations.

    - **Pros:** Universally compatible with any filesystem (ext4, xfs, etc.).
    - **Cons:** Fundamentally unsuited for the use case. Copying is slow (O(n)) and storage intensive. Crucially, it lacks atomicity; backing up a live database via file copying guarantees corruption unless the service is stopped, which causes unacceptable downtime.

!!! success "Option 2: Btrfs Subvolume Snapshots"
    Mandate that the LychD Crypt directory resides on a Btrfs filesystem.

    - **Pros:** Aligns perfectly with all decision drivers. `btrfs subvolume snapshot` is instantaneous and atomic. It allows for advanced tuning, such as selective disabling of Copy-on-Write for performance-critical database files, while retaining checksumming for code and vectors.
    - **Cons:** Introduces a hard dependency on a specific filesystem, requiring configuration from users on standard ext4 systems.

## Decision Outcome

The `LYCH_CRYPT` data directory is mandated to reside on a **Btrfs filesystem**. This is a non-negotiable technical requirement to support the project's core self-healing capabilities.

### 1. Filesystem Layout and CoW Policy

The `lychd init` process constructs the following subvolume layout:

```text
~/.local/share/lychd/
├── active/         <-- Btrfs subvolume for live data
│   ├── postgres/   <-- Directory with CoW DISABLED (nodatacow)
│   └── ...         <-- Other data (code, vectors) with CoW ENABLED
└── snapshots/      <-- Directory to store read-only snapshots
```

**Performance Note:** To prevent database fragmentation, `lychd init` applies the `chattr +C` attribute to the `postgres` directory immediately upon creation. This disables Copy-on-Write for the database files while retaining it for the rest of the system.

### 2. Application-Consistent Snapshot Process ("The Ritual")

Snapshots are orchestrated via a dedicated sequence ensuring database integrity:

1. **Quiesce:** A connection is made to Postgres to execute `pg_start_backup()`, flushing WAL buffers and freezing filesystem I/O.
2. **Snap:** The command `btrfs subvolume snapshot -r` is executed, creating an atomic point-in-time copy of the `active` subvolume.
3. **Resume:** The connection executes `pg_stop_backup()`, returning the database to normal operation.

This sequence completes in milliseconds.

### 3. Compliance Strategies for Non-Btrfs Systems

Users on systems formatted with `ext4` or `xfs` must satisfy this dependency using one of the following methods:

**Method A: Dedicated Partition (Performance)**
A physical partition is formatted as Btrfs and mounted at `~/.local/share/lychd`.

**Method B: Loopback Adapter (Compatibility)**
A simplified method for standard installations. A large file is created on the host filesystem and formatted as Btrfs:

```bash
truncate -s 20G lychd.img
mkfs.btrfs lychd.img
mount -o loop lychd.img ~/.local/share/lychd
```

## Consequences

!!! success "Positive"
    - **Guaranteed Consistency:** The system achieves application-consistent, atomic snapshots, enabling safe "[Autopoiesis](../divination/transcendence/immortality.md)" rollbacks without data corruption.
    - **Optimized Database Performance:** By selectively disabling CoW for the Postgres directory, the system avoids the write-amplification and fragmentation penalties typically associated with databases on CoW filesystems.
    - **Data Integrity:** Static assets (code, vector stores) benefit from Btrfs native checksumming and bit-rot detection.

!!! failure "Negative"
    - **Infrastructure Dependency:** This decision imposes a strict filesystem requirement. While valid workarounds exist (loopback files), it increases the initial setup complexity for users not already running Btrfs.
