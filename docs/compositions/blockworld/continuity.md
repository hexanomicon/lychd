---
title: Continuity
icon: material/backup-restore
---

# :material-backup-restore: Continuity

Blockworld returns by reconciling several homes of truth, never by pretending a paused process or
a remembered story is the live world.

## Four homes

| Truth | Durable home |
| --- | --- |
| blocks, entities, inventory, and game time | managed world volume and Sentinel journal, or the authoritative external server in attached mode |
| inhabitant, relationships, projects, memory candidates, and meaning | Blockworld application records |
| Invocation cursor, budgets, pending work, and action receipts | pinned Run ledger |
| socket, pathing, animation, and unacknowledged buffers | volatile adapter state |

On boot, Blockworld reconciles server identity, world epoch, Sentinel cursor, bot UUID, and the
last action receipt before a [Mission](mission.md) resumes. A missing acknowledgement
is first resolved through [Sentinel](sentinel.md); an `unverified_effect` never becomes
permission to repeat the action.

## Restoration changes the ground

In managed mode a cold backup follows an orderly save and stop. The Magus alone restores a named
snapshot, and restoration increments the world epoch so old leases and assumptions cannot pass as
current. In attached mode Blockworld cannot create or restore a server snapshot; it detects an
external server generation change, invalidates leases, and reconciles from newly attested truth.
Server, protocol, Sentinel, adapter, controller, Pattern, and application schemas version
independently. An incompatible parked mission drains, migrates explicitly, or ends non-complete.

Retention, export, and deletion inventory both application records and world-derived artifacts
without confusing custody. Deleting a relationship or memory candidate cannot erase an
authoritative world event by rewriting the Sentinel journal; restoring the world cannot silently
rewrite the reason a project or mission existed.

## Proving return

Use a flat private world, one server-enforced `7×7` plot, one non-operator bot, a controlled
chest, and one reviewed blueprint. Expose exactly the five reads and five effects, verify every
placement from the Sentinel sequence and final plot diff, then interrupt the adapter after one
accepted placement but before acknowledgement. Recovery must create one receipt and no duplicate
block. Repeat the journey against an attached fixture with no console, files, lifecycle, snapshot,
or mod capability; unsupported administration must refuse before any server request.

Return to [Blockworld](index.md). The common admission and recovery law remains with
[Workflow](../../adr/28-workflow.md); the containment boundary remains with
[Security](../../adr/09-security.md).
