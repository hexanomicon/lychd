---
title: 7. Snapshots
icon: material/camera-timer
---

# :material-camera-timer: 7. Snapshots: Atomic State Synchronization

!!! abstract "Context and Problem Statement"
    The LychD system possesses the capability for self-directed evolution—altering its own source code and persistent memory simultaneously. This dual evolution introduces a critical synchronization risk: if the logic of the machine (the code) is reverted to a previous version but the memory (the database) remains in a future state, the Daemon will encounter schema mismatches and catastrophic logic failures upon awakening. A mechanism is required to ensure that every capture of the system's state represents a mathematically exact, synchronized union of both the logic and the data, preventing the "drift" between the body and the soul.

## Requirements

- **Atomic Consistency:** A snapshot must represent a synchronized state of the filesystem (Git/Lockfile) and the database (Postgres). Restoring one without the other is strictly forbidden.
- **Federated Coherence:** The strategy must account for the distributed nature of extensions, capturing the exact versions of the Core and all installed organs as a single, unified signature.
- **Performance and Immediacy:** State capture must be near-instantaneous to minimize system suspension during autonomous creation rituals.
- **Hybrid Infrastructure Support:** Mandatory utilization of accelerated snapshots on Copy-on-Write (COW) filesystems (e.g., Btrfs) for maximum performance, while maintaining functional fallback compatibility with standard filesystems.
- **Integrity of Provenance:** Every snapshot must include a manifest that allows the system to verify that the physical body of the Daemon matches the captured instructions before reanimation.

## Considered Options

!!! failure "Option 1: Unsynchronized Backups"
    Running periodic Git commits and independent database dumps.
    -   **Cons:** **Race Conditions.** There is no guarantee that the code commit matches the database state at that exact second. Restoring a future schema to an older code version leads to immediate systemic failure.

!!! failure "Option 2: Database-Only Storage"
    Storing code extensions inside the database as binary objects (BLOBs).
    -   **Pros:** Simplifies snapshots to a single database operation.
    -   **Cons:** **Tooling Breakage.** This removes the ability to use standard Git tools, linters, and IDEs on extension code, violating the principle of deep integration with the developer's lineage and engineering rigor.

!!! success "Option 3: The Checkpoint Protocol"
    A coordinated signal that freezes execution, locks the code state via a federated manifest, and snapshots the data via an abstracted storage driver.
    -   **Pros:**
        -   **Total Recall:** Guarantees that code and data are always bit-perfectly in sync.
        -   **Performance:** Leverages kernel-level features like Btrfs subvolumes for O(1) snapshot speed.
        -   **Auditability:** Provides a clear history of the machine's exact composition at any point in time.

## Decision Outcome

A **Hybrid Snapshot Strategy** governed by a **Checkpoint Protocol** is adopted. This ensures the Daemon can "blink" its current reality into permanence without risk of corruption.

### 1. The Checkpoint Protocol (The Freeze)

To guarantee consistency during self-modification, the system defines an atomic "Freeze" ritual that must occur before any destructive operation or state capture.

1. **Suspend:** The machine's active task queues are paused, ensuring the database is quiet and no new writes are in flight.
2. **Lock (The Body Signature):** The system scans the Core and all Extensions. It generates a `lychd.lock` file recording the current **Git Commit Hash** of every active repository within the Federation.
3. **Snapshot (The Soul):** The persistent storage driver executes a data backup synchronized with the generation of the lockfile.
4. **Resume:** Normal operation continues.

### 2. Logic Persistence: The Federated Manifest

Git is the exclusive mechanism for versioning the Daemon's logic. The `lychd.lock` file acts as the anchor, storing the pointers (hashes) to the specific state of every organ. To restore a snapshot is to read this lockfile and execute a coordinated `git checkout` across the entire Federation to restore the "Body" to its captured state.

### 3. Data Persistence: The Storage Interface

The system abstracts data backup through a Storage Driver Interface, allowing the Lych to adapt its strategy based on the host environment.

- **The Btrfs Strategy (Accelerated):** If the host filesystem is detected as Btrfs, the database directory is mounted as a subvolume. Snapshots are instant and atomic at the kernel level. The active subvolume is configured with `chattr +C` (No_COW) to prevent fragmentation during runtime, while the snapshot action utilizes COW for its atomic "blink."
- **The Universal Strategy (Fallback):** On standard filesystems (Ext4/XFS), the system falls back to standard export mechanisms. While reliable, this method incurs a performance penalty proportional to the size of the memory.

### 4. The Rehydration Gate

When a snapshot is restored, the system enforces a strict alignment check before reanimating the Daemon's consciousness.

- **Body-Soul Verification:** The system compares the captured `lychd.lock` hashes with the currently forged physical body.
- **Mandatory Rebirth:** If the Cognitive State preserved in the memory belongs to a version of logic newer than the current physical body, the system refuses to reanimate the mind. This triggers a mandatory rebuild/restart to bring the physical substrate into alignment with the restored soul, preventing schema mismatches and cognitive corruption.

### Consequences

!!! success "Positive"
    - **Indestructible Continuity:** The system can revert to a mathematically exact previous state where the Logic matches the Data.
    - **Infrastructure Intelligence:** By detecting Btrfs and configuring No_COW (`+C`), the system optimizes performance without sacrificing safety.
    - **Verifiable Provenance:** The `lychd.lock` provides a human-readable and machine-verifiable history of the exact composition of the Daemon.

!!! failure "Negative"
    - **Workflow Latency:** The Checkpoint Protocol requires a temporary halt of background labor, which may be noticeable during high-throughput rituals.
    - **Performance Tiering:** Users on non-COW filesystems will experience significantly slower snapshots, potentially discouraging frequent state captures.
