---
title: 7. Snapshots
icon: material/camera-timer
---

# :material-camera-timer: 7. Snapshots

!!! abstract "Context"
    A whole-body checkpoint binds the body revision, its configuration and extensions, durable
    stores, and the admitted work that may survive recovery. Workflow checkpoints support replay
    inside one revision through the Phylactery. This Covenant governs the coordinated capture and
    restore of the body itself.

## Decision: the Checkpoint Protocol

The coordinator performs this order without omission:

1. close admission for the affected body;
2. drain work to a declared boundary, park it, or mark it for abandonment;
3. quiesce queue, graph, migration, and application writers;
4. write a manifest; capture every durable store at its own consistency boundary; then seal the
   manifest and captures as one checkpoint;
5. resume admission only after that seal succeeds or the freeze is explicitly aborted.

Only a successful seal establishes a capture. If capture fails, no valid seal is written; the
body returns to its pre-capture state where possible and otherwise stays paused for repair.
A set of nearby backups cannot substitute for that coordinated result.

## Manifest and capture

Every source repository names an immutable revision: a Git commit object, or Jujutsu's hexadecimal
**Commit ID**, never its mutable alphabetic Change ID. The manifest also fixes lockfile digests,
image or built-artifact digests where relevant, active extension identities, Rune/configuration
provenance, schema revision, and storage-driver identity, version, and parameters. An annotation
may name a Jujutsu Change ID, but restore identity may not.

PostgreSQL consistency comes first. A Btrfs driver may then accelerate the dedicated-subvolume
capture and records filesystem UUID, subvolume ID, generation, mount identity, and database
recovery metadata. A Btrfs snapshot is neither a general transaction nor a substitute for a
database boundary. A portable driver instead uses a PostgreSQL-supported physical or logical
capture and staged, integrity-checked copies of manifest-bound files. Other drivers may implement
the protocol without altering its restore semantics.

## Rehydration and reckoning

Restore begins with an inactive target and opens admission last. First it verifies the seal and
manifest, supplies the exact revision and locks, and restores stores through the recorded driver.
It then verifies schema/configuration/artifact/extension/storage identity, performs only the
rebuilds required by the manifest, and reconciles. Any mismatch stops reanimation. Moving to a
newer body requires an [Evolution](18-evolution.md) act rather than being treated as restore.

Reconciliation revokes vanished leases and worker attachments, re-admits only work parked at a
declared checkpoint edge, and marks all other in-flight work `abandoned`. It identifies external
commitments beyond captured custody—messages, payments, host transitions, and outside writes—taints
the related work, and refuses unsafe replay pending explicit review. Local restoration never
pretends to rewind an external effect.

The recovered cut is the sole durable truth. Work admitted after it is absent and must be
resubmitted, never reconstructed.

That cut cannot override a separate store's surviving deletion or hold authority. The initial
[Reliquary custody profile](06-persistence.md#backup-and-restore-boundary) admits no restore or
clone activation: an older capture cannot revive material by omitting a later tombstone or hold.
Known loss or uncertainty of that control history keeps the store inactive. A future restore must
reconcile independently retained, nonrollback authority before opening admission; inode, UUID and
in-root hash checks alone do not establish that freshness.

Each participating owner keeps its responsibility during recovery: [Workers](14-workers.md)
owns queue claim and retry, [Graph](24-graph.md) owns graph re-admission,
[Orchestrator](23-orchestrator.md) owns physical convergence, and [Evolution](18-evolution.md)
owns source selection. The coordinator composes their work without absorbing their authority.

## Delivery boundary

This protocol is designed. Filesystem preparation does not prove freeze, PostgreSQL capture,
restore, or reconciliation. [State of Work](../state-of-the-work.md#whole-body-snapshot-restore)
is the delivery authority.

## Consequences

Whole-body recovery has one verifiable cut, at the cost of a bounded admission freeze and explicit
operator review wherever local custody cannot settle an external effect.
