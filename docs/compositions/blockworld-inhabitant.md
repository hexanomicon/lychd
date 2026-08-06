---
title: Blockworld Inhabitant
icon: material/cube-outline
---

# :material-cube-outline: Blockworld Inhabitant

The inhabitant wakes for one bounded mission and leaves consequences in a world that persists
after its Mind goes quiet. A wall may remain, but its purpose, authority, and exact placements must
remain inspectable too. Each return begins from reconciled world truth rather than imagined
continuity.

!!! note "Current material"
    Blockworld Inhabitant is a Native Reference Composition, not an executable embodied Agent
    today. No Blockworld Pattern, world adapter, embodiment journal, mission ledger, or server
    fixture is registered. Legion remains Designed and supplies no owned-node or robot path.

[State of Work](../state-of-the-work.md#composition-portfolio-delivery) owns the delivery boundary for this reference.

## Contract

| Field | Reference contract |
| --- | --- |
| **Identity** | `blockworld.inhabitant` revision `1` |
| **Principal Pattern** | `blockworld.bounded_mission@1` |
| **Application begins with** | an admitted finite mission, authenticated bot, exact world epoch, plot lease, blueprint, tools, and budgets |
| **Application can return** | verified action receipts, an updated mission cursor, and completion or exact non-completion |
| **Application stops before** | public autonomy, unrestricted exploration, administrator commands, remote shell, or cross-plot power |

The first world is a private, allowlisted, online-mode server fixture with a dedicated non-operator
bot. The Composition owns inhabitant identity, mission, memory-candidate, project, lease, and
receipt records. The server remains authoritative for blocks, entities, inventory, and game time.

## One finite awakening

1. **Admit the mission.** Pin the Pattern and bridge revisions, authenticated bot UUID, world
   identity and epoch, region lease, blueprint, budgets, deadline, and permitted reads and effects.
2. **Observe structured truth.** Read bounded world status, inventory, region, nearby entities,
   and recent chat. Server facts outrank screenshots, signs, books, and untrusted prose.
3. **Recall only relevant context.** Bring forward the admitted project and memory records needed
   for this mission, not an endless hidden session.
4. **Propose one step.** The Mind chooses one typed action; Sentinel validates plot, action,
   precondition digest, expected cursor, and budgets before the bridge issues it.
5. **Verify the consequence.** Match the response to Sentinel sequence and the resulting world
   event or diff, then commit one receipt and advance the durable cursor.
6. **Continue or end.** Repeat within the finite mission, reflect and finish, or state the exact
   reason the work is incomplete.

## Four homes of continuity

| Truth | Durable home |
| --- | --- |
| blocks, entities, inventory, and game time | authoritative world volume and Sentinel event journal |
| identity, vows, relationships, memories, projects, and meaning | inhabitant application records |
| Invocation cursor, budgets, pending work, and action receipts | pinned Run ledger |
| socket, pathing, animation, and unacknowledged buffers | volatile bridge state |

The first bridge may read only `world_status`, `inventory_summary`, `scan_region`,
`nearby_entities`, and `chat_since`. It may effect only `move_to`, `look_at`, `say`, `equip`, and
`place_block`. Every action carries its id, mission id, bot UUID, Pattern and bridge revisions,
lease, precondition digest, expected cursor, deadline, budgets, and postcondition.

## World authority and return

Sentinel enforces authority on the server; bridge checks are an additional guard. Destructive
edits, fire, lava, explosives, PvP, trading, private chat, cross-plot inventory, account or plug-in
changes, restoration, and public exposure are outside revision `1`. Chat and world text are
untrusted input and cannot grant tools, widen a lease, or prove a fact.

If acknowledgement is lost after an action, the bridge asks `action_status` and compares the
server cursor and world state. An unresolved result is `unverified_effect`; repeating a placement
is refused. On boot, the system reconciles server identity, world epoch, Sentinel cursor, bot UUID,
and the last action receipt before resuming.

Cold backup follows an orderly save and stop. The Magus alone restores a named snapshot; restoration
increments the world epoch and invalidates old leases and assumptions. Server, protocol, Sentinel,
bridge, controller, Pattern, and application schemas version independently. Incompatible parked
missions drain, migrate explicitly, or end non-complete.

Retention, export, and deletion inventory both the inhabitant records and world-derived artifacts
without confusing their custody. Deleting an application record cannot erase an authoritative
world event by editing the Sentinel journal.

## Proving mission

Use a flat private world, one server-enforced `7×7` plot, one non-operator bot, a controlled chest,
and one reviewed blueprint. Expose exactly the five reads and five effects above, verify every
placement from Sentinel sequence and the final plot diff, then interrupt the bridge after one
accepted placement but before acknowledgement. Recovery must create one receipt and no duplicate
block.

Related: [Workflow](../adr/28-workflow.md) · [Security](../adr/09-security.md) ·
[Reach](reach.md) · [Composition portfolio](index.md)
