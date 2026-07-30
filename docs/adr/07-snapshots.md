---
title: 7. Snapshots
icon: material/camera-timer
---

# :material-camera-timer: 7. Snapshots

!!! abstract "Context"
    A checkpoint is a whole-body cut, not a convenient backup. It binds the body revision, its
    configuration and extensions, durable stores, and the admitted work that may survive recovery.
    Workflow replay inside one revision remains Phylactery work; this Covenant decides the heavier
    cut between body revisions and durable reality.

## Decision: the Checkpoint Protocol

The coordinator performs this order without omission:

1. close admission for the affected body;
2. drain work to a declared boundary, park it, or mark it for abandonment;
3. quiesce queue, graph, migration, and application writers;
4. write a manifest; capture every durable store at its own consistency boundary; then seal the
   manifest and captures as one checkpoint;
5. resume admission only after that seal succeeds or the freeze is explicitly aborted.

A failure writes no valid seal. The body returns to its pre-capture state when it can, otherwise
remains paused for repair. A capture is therefore never inferred from a collection of nearby
backups.

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

Restore enters an inactive target. It verifies the seal and manifest, supplies the exact revision
and locks, restores stores through the recorded driver, verifies schema/configuration/artifact/
extension/storage identity, rebuilds only where the manifest says a rebuild is required, and then
reconciles. Admission opens last. A mismatch stops reanimation; migration to a newer body is an
[Evolution](18-evolution.md) act, not restore.

Reconciliation revokes vanished leases and worker attachments, re-admits only work parked at a
declared checkpoint edge, and marks all other in-flight work `abandoned`. It identifies external
commitments beyond captured custody—messages, payments, host transitions, and outside writes—taints
the related work, and refuses unsafe replay pending explicit review. Local restoration never
pretends to rewind an external effect.

The recovered cut is the sole durable truth. Work admitted after it is absent and must be
resubmitted, never reconstructed.

The coordinator composes, rather than absorbs, the owners of queue claim and retry
([Workers](14-workers.md)), graph re-admission ([Graph](24-graph.md)), physical convergence
([Orchestrator](23-orchestrator.md)), and source selection ([Evolution](18-evolution.md)).

## Delivery boundary

This protocol is designed. Filesystem preparation does not prove freeze, PostgreSQL capture,
restore, or reconciliation. [State of Work](../state-of-the-work.md#whole-body-snapshot-restore)
is the delivery authority.

## Consequences

Whole-body recovery has one verifiable cut, at the cost of a bounded admission freeze and explicit
operator review wherever local custody cannot settle an external effect.
