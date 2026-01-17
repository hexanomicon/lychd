---
title: 8. Btrfs Snapshots
icon: material/camera-timer
---

# :material-camera-timer: 8. Btrfs for Atomic Snapshots and Rollbacks

!!! abstract "Context and Problem Statement"
    A core ambition of LychD is "Autopoiesis"—the ability to safely modify its own code and state. This process is inherently high-risk. A failure during an agent-led operation could leave the system's database and files in a corrupted, inconsistent state.

    To mitigate this, we need a mechanism to create an instantaneous, application-consistent snapshot of the entire LychD Crypt (`~/.local/share/lychd`). This snapshot must be created with zero performance overhead and allow for a perfect, atomic rollback. Furthermore, the underlying storage for the live database must be configured for maximum performance, avoiding issues like fragmentation under heavy write loads.

## Decision Drivers

- **Application Consistency:** Snapshots must represent a clean, consistent state of the database, not just a crash-consistent copy of its files.
- **Atomicity:** The snapshot and rollback operations must be all-or-nothing.
- **Performance:** Snapshot creation must be nearly instantaneous. The live database must not suffer from filesystem-induced performance degradation.
- **Storage Efficiency:** Snapshots must be space-efficient, using a copy-on-write mechanism.
- **Data Integrity:** The solution should leverage features like checksumming for static assets where appropriate.

## Considered Options

!!! failure "Option 1: Filesystem-Agnostic Tools (`rsync`)"
    Use standard file-copying utilities to back up the data directory.

    - **Pros:** Works on any filesystem.
    - **Cons:** Fatally flawed. Not atomic and cannot create a consistent backup of a live database, leading to guaranteed corruption. It is also slow and storage-inefficient.

!!! success "Option 2: BTRFS Subvolume Snapshots"
    Require the LychD Crypt directory to be located on a BTRFS filesystem.

    - **Pros:** Perfectly matches all decision drivers. `btrfs subvolume snapshot` is instantaneous and atomic. With proper orchestration, it can produce application-consistent backups. It also allows for fine-grained tuning, like disabling Copy-on-Write (CoW) for performance-critical data.
    - **Cons:** It creates a hard dependency on a specific filesystem.

## Decision Outcome

We will mandate that the `LYCH_CRYPT` data directory resides on a **BTRFS filesystem**. This is a non-negotiable technical requirement, as it provides fundamental capabilities essential to the project's design.

### 1. Filesystem Layout and CoW Policy

The `lychd init` command will construct the following layout:

```text
~/.local/share/lychd/
├── active/         <-- BTRFS subvolume for live data
│   ├── postgres/  <-- Directory with CoW DISABLED
│   └── ...             <-- Other data (code, vectors) with CoW ENABLED
└── snapshots/      <-- Directory to store read-only snapshots
```

Critically, to ensure peak database performance, `lychd init` will disable CoW (`chattr +C`) **only on the `postgres_data` directory** while it is empty, before Postgres is initialized. This prevents database file fragmentation. Other data will retain CoW to benefit from BTRFS's data checksumming and integrity features.

### 2. Application-Consistent Snapshot Process (The Ritual)

Snapshots will be orchestrated via a dedicated `lychd` command that performs these steps in rapid succession:

1. **Quiesce:** Connect to Postgres and run `pg_start_backup()`. This flushes all in-memory data to disk, preparing it for a safe backup.
2. **Snap:** Execute `btrfs subvolume snapshot -r ...` to create an instantaneous, read-only, atomic snapshot of the `active` subvolume.
3. **Resume:** Immediately connect back to Postgres and run `pg_stop_backup()` to return the database to normal operation.

This entire sequence is expected to complete in under one second.

### 3. Satisfying the Requirement

Users on non-BTRFS systems can meet this dependency via two documented methods:

1. **Dedicated Partition (Recommended):** Create a new partition, format it as BTRFS, and mount it at `~/.local/share/lychd`.
2. **Loopback File (Easy Method):** Create a file on an existing `ext4` filesystem and mount it as a BTRFS volume using `mount -o loop`.

## Consequences

!!! success "Positive"
    - **Consistency:** We achieve guaranteed application-consistent, atomic snapshots for safe autopoiesis rollbacks.
    - **Performance:** The live database operates at maximum performance by disabling CoW where needed.
    - **Integrity:** We retain BTRFS data integrity features (checksums) for other critical assets like code.

!!! failure "Negative"
    - **Hard Dependency:** Imposes a hard filesystem dependency on the user. This is a deliberate trade-off for a vastly superior and safer system, and the provided mitigation paths are straightforward.
