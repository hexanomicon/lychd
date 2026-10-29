---
title: Continuity
icon: material/backup-restore
---

# :material-backup-restore: Continuity

The server accepted a block, but the adapter disappeared before receiving acknowledgement. On return, Blockworld must discover that consequence before advancing or repeating anything. A remembered story and a paused process cannot answer for the world.

## Four homes

| Truth | Home |
| --- | --- |
| Blocks, entities, inventory, game time | Managed world volume and Sentinel journal, or authoritative attached server. |
| Inhabitant, relationships, projects, memory candidates and meaning | Blockworld application records. |
| Mission cursor, budgets, pending work and action receipts | Blockworld mission and action records in [Phylactery](../../adr/06-persistence.md), bound to the exact Run and Pattern revision. |
| Socket, pathing, animation and unacknowledged buffers | Volatile adapter state. |

Boot reconciles server identity, world epoch, Sentinel cursor, bot UUID, and the last receipt before a [Mission](mission.md) resumes. [Sentinel](sentinel.md) resolves missing acknowledgement first. An `unverified_effect` cannot become permission to repeat.

## One action across a pause

Revision `2` retains one native action record for the prepared placement. Blockworld owns its meaning and lifecycle; Phylactery owns its durable schema and transaction boundaries. The record holds the immutable command and disclosure-approved review binding, its Consent identity, issuance disposition, and eventual receipt or exact non-completion. Core's Run ledger continues to own Run identity and status. A Graph checkpoint carries the reference and expected binding; deleting that checkpoint cannot delete the action's recovery truth.

Run and Consent identities remain immutable references in the retained action. Their deletion does not erase the frozen command, review binding, issuance judgment, or recovery disposition. A prepared action whose Run or Consent is unavailable cannot issue. On re-entry, an action that has acquired its pending claim can only reconcile, including when its checkpoint or Core records are gone. The first bounded placement schema retains mission and action records until a separately owned export or deletion operation exists.

Commit preparation and its one Consent binding together before exposing the review or parking Graph. Any consumed preauthorization belongs to the same transaction. This gives re-entry one identity to recover: the same native action resolves the committed preparation and Consent, while changed content conflicts instead of replacing them.

Repeated validation of the same call returns those retained records without minting another action. If the commit itself is unconfirmed, reconcile it by that identity before admitting further work.

Before invoking the adapter, conditionally mark the exact action pending against the current mission cursor and limits. Competing resumptions must recover that claim rather than acquire another one for the action or cursor.

The database transaction cannot include the server effect. Once invocation may have begun, a pending or unknown acknowledgement therefore requires reconciliation of the same action. A new Graph hop or missing reply cannot authorize another placement.

A matching response plus either an authoritative event or sufficient resulting-state proof permits verified settlement. The receipt and its corresponding mission cursor and budget update commit together; repeated settlement returns the same result. An observed adapter invocation, a completed Run, or the desired block appearing without sufficient attribution cannot manufacture that receipt. Missing proof remains exact non-completion.

## Restoration changes the ground

A managed cold backup follows orderly save and stop. Only the Magus restores a named snapshot; restoration increments the world epoch and invalidates old leases and assumptions. An attached client cannot snapshot or restore the server. It detects external generation change, invalidates leases, and obtains newly attested truth.

Recovery must also check compatibility across independently versioned server, protocol, Sentinel, adapter, controller, Pattern, and application schemas. Incompatible parked work drains, migrates explicitly, or settles non-complete.

For export or deletion, inventory both application custody and material derived from the world. Deleting a relationship cannot erase a world event from the journal. Restoring the blocks likewise cannot rewrite the purpose for which a mission existed.

## Proving return

Use a flat private world, server-enforced `7×7` plot, non-operator bot, controlled chest, and reviewed blueprint. Expose the exact five reads and five effects. Verify placements from Sentinel sequence and final plot diff, then interrupt after accepted placement but before acknowledgement. Recovery must create one receipt and no duplicate block. Repeat against an attached fixture with no console, files, lifecycle, snapshot, or mod capability; unsupported administration must refuse before a request reaches the server.

[Blockworld](index.md) · [Workflow](../../adr/28-workflow.md) · [Security](../../adr/09-security.md)
