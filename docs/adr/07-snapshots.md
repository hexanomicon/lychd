---
title: 7. Snapshots
icon: material/camera-timer
---

# :material-camera-timer: 7. Snapshots: Atomic State Synchronization

!!! abstract "Context and Problem Statement"
    The LychD system possesses the capability for self-directed evolution—altering its own source code and persistent memory simultaneously. This dual evolution introduces a critical synchronization risk: if the logic of the machine (the code) is reverted to a previous version while the memory (the database) remains in a later state, the Daemon encounters schema mismatches and catastrophic logic failures upon awakening. A mechanism is required to ensure that every capture of the system's state represents a mathematically exact, synchronized union of both the logic and the data, preventing the "drift" between the body and the soul.

## Requirements

- **Atomic Consistency:** A snapshot must represent a synchronized state of the filesystem (VCS/Lockfile) and the database (Postgres). Restoring one without the other is strictly forbidden.
- **Federated Coherence:** The strategy must account for the distributed nature of extensions, capturing the exact versions of the Core and all installed organs as a single, unified signature.
- **Performance and Immediacy:** State capture must be near-instantaneous to minimize system suspension during autonomous creation rituals.
- **Hybrid Infrastructure Support:** Mandatory utilization of accelerated snapshots on Copy-on-Write (COW) filesystems (e.g., Btrfs) for maximum performance, while maintaining functional fallback compatibility with standard filesystems.
- **Integrity of Provenance:** Every snapshot must include a manifest that allows the system to verify that the physical body of the Daemon matches the captured instructions before reanimation.

## Considered Options

!!! failure "Option 1: Unsynchronized Backups"
    Running periodic VCS snapshots (Git/JJ) and independent database dumps.

    -   **Cons:** **Race Conditions.** There is no guarantee that the code state matches the database state at that exact second. Restoring a future schema to an older code version leads to immediate systemic failure.

!!! failure "Option 2: Database-Only Storage"
    Storing code extensions inside the database as binary objects (BLOBs).

    -   **Pros:** Simplifies snapshots to a single database operation.

    -   **Cons:** **Tooling Breakage.** This removes the ability to use standard VCS tools (Git/JJ), linters, and IDEs on extension code, violating the principle of deep integration with the developer workflow and engineering rigor.

!!! success "Option 3: The Checkpoint Protocol (Jujutsu + Btrfs)"
    A coordinated signal that freezes execution, locks the code state via a federated manifest anchored to Jujutsu's immutable Commit IDs, and snapshots the data and code repository states simultaneously via a Btrfs Copy-on-Write driver.

    -   **Pros:**
        -   **Total Recall:** Guarantees that code, version-control state, and data are always bit-perfectly in sync.
        -   **Performance:** Leverages kernel-level features like Btrfs subvolumes for O(1) snapshot speed.
        -   **Mathematical Rigour:** Decouples mutable conceptual changes from the frozen file-tree state, preventing metadata corruption.

## Decision Outcome

A **Hybrid Snapshot Strategy** governed by a **Checkpoint Protocol** is adopted. This ensures the Daemon can "blink" its current reality into permanence without risk of corruption.

!!! note "Replay Is Not Snapshot Rollback"
    Workflow replay is normally a Phylactery concern: Postgres records queue rows, graph checkpoints, traces, committed outputs, and recovery markers so work can resume from the last declared safe boundary. Snapshot rollback is heavier. It restores whole reality when the Body (code, lockfiles, VCS state) and Soul (database state) must move together after Creation, Assimilation, Evolution, migration, or failed promotion. Postgres is authoritative for replaying work; Snapshots are authoritative for restoring body/soul coherence.

### 1. The Checkpoint Protocol (The Freeze)

To guarantee consistency during self-modification, the system defines an atomic "Freeze" ritual that must occur before any destructive operation or state capture.

1. **Suspend:** The machine's active task queues are paused, ensuring the database is quiet and no new writes are in flight.
2. **Lock (The Body Signature):** The system scans the Core and all Extensions. It generates a `lychd.lock` file recording the current **VCS Revision Hash** of every active repository within the Federation.
3. **Snapshot (The Soul):** The persistent storage driver executes a data backup synchronized with the generation of the lockfile.
4. **Resume:** Normal operation continues.

### 2. Logic Persistence: The Federated Manifest and the Hexadecimal Mandate

Jujutsu (`jj`) is the exclusive mechanism for versioning the Daemon's logic. Unlike standard Git, which conflates change tracking and snapshots, Jujutsu maintains **two distinct identifiers** for every state transition:
- **Change ID (Alphabetic, e.g., `qzmzpxyl`):** A stable identifier that tracks a conceptual task. This ID remains constant across amends, rebases, and modifications.
- **Commit ID (Hexadecimal, e.g., `bc915fcd`):** An immutable, cryptographic hash of the exact state of the file tree at a frozen moment in time.

!!! important "The Hexadecimal Mandate"
    The Checkpoint Protocol MUST strictly capture and record the **hexadecimal Commit ID** within the `lychd.lock` file. Anchoring the manifest to the alphabetic Change ID is forbidden. Because Change IDs represent mutable, evolving timelines, using them for snapshots would cause the restored code to drift from the static database state if the change concept evolved after the snapshot was taken.

### 3. Data & VCS Coherence: Btrfs Integration

To achieve instant, transactional rollbacks of both memory (database) and mind (version control graph), LychD marries Btrfs Copy-on-Write (COW) subvolumes with Jujutsu's SQLite-backed repository state.

- **The Btrfs Subvolume Layout:** Both the `crypt/` (Postgres application database) and the `.jj/` (Jujutsu's internal SQLite state-graph) exist on Btrfs subvolumes.
- **Coordinated Blink:** When the Checkpoint Protocol is triggered, Btrfs executes a coordinated COW snapshot of both the Postgres tables and the SQLite version-control graph. The entire repository state is physically captured in a single, ACID-compliant database snapshot on disk.

The system abstracts data backup through a Storage Driver Interface, allowing the Lich to adapt its strategy based on the host environment.

- **The Btrfs Strategy (Accelerated):** If the host filesystem is detected as Btrfs, the database directory is mounted as a subvolume. Snapshots are instant and atomic at the kernel level. The active subvolume is configured with `chattr +C` (No_COW) to prevent fragmentation during runtime, while the snapshot action utilizes COW for its atomic "blink."
- **The Universal Strategy (Fallback):** On standard filesystems (Ext4/XFS), the system falls back to standard export mechanisms. While reliable, this method incurs a performance penalty proportional to the size of the memory.
- **The ZFS Contingency (Future Evolution):** While Btrfs serves as the primary native accelerator, the system recognizes the merit of the Zettabyte File System (ZFS) for high-availability environments. The Storage Driver Interface is architected to eventually embrace ZFS dataset snapshots. This "future-gate" allows the Daemon to leverage ZFS's superior self-healing and "send/receive" capabilities. Because the Checkpoint Protocol is agnostic to the underlying shell commands, adding ZFS support is a matter of logical mapping, not a core re-write.

### 4. The Rehydration Gate

When a snapshot is restored, the system enforces a strict alignment check before reanimating the Daemon's consciousness.

- **Body-Soul Verification:** The system compares the captured `lychd.lock` hexadecimal Commit IDs with the current physical body.
- **The Jujutsu Warp:** Restoring the code is not a simple file overwrite. The system executes `jj edit <Commit_ID>`. This physically warps Jujutsu’s working copy commit (`@`) of the workspace back to the frozen node in the graph, making it active.
- **Mandatory Rebirth:** If the Cognitive State preserved in the memory belongs to a version of logic newer than the current physical body, the system refuses to reanimate the mind. This triggers a mandatory rebuild/restart to bring the physical substrate into alignment with the restored soul, preventing schema mismatches and cognitive corruption.
- **Rehydration Ritual**: Restoring a snapshot is the Reanimation of the machine. The storage driver physically resets the database directory using the Btrfs or Postgres snapshot. Simultaneously, the `jj edit` command aligns the codebase. This ensures the Soul (Data) is physically identical to the moment the Body (Code) was captured, bypassing the risk of schema drift entirely.


### Consequences

!!! success "Positive"
    - **Indestructible Continuity:** The system can revert to a mathematically exact previous state where the Logic matches the Data.

    - **Infrastructure Intelligence:** By detecting Btrfs and configuring No_COW (`+C`), the system optimizes performance without sacrificing safety.

    -   **Verifiable Provenance:** The `lychd.lock` provides a human-readable and machine-verifiable history of the exact composition of the Daemon, captured via VCS.

!!! failure "Negative"
    - **Workflow Latency:** The Checkpoint Protocol requires a temporary halt of background labor, which may be noticeable during high-throughput rituals.

    - **Performance Tiering:** Users on non-COW filesystems experience significantly slower snapshots, potentially discouraging frequent state captures.
