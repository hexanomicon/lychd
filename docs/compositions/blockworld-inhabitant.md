---
title: Blockworld Inhabitant
icon: material/cube-outline
---

# :material-cube-outline: Blockworld Inhabitant

> _A life in the world is not one endless thought. It is a history of finite awakenings and
> consequences that remain._

The inhabitant may leave a small wall standing after its Mind has gone quiet. That is the point:
the world remembers material consequence, while a separate accountable record remembers what the
work was meant to be.

| Maturity | Accepted Reference Composition — architecture, not delivery; [State of Work](../state-of-the-work.md) owns what runs |
| --- | --- |
| Identity | `blockworld.inhabitant` revision `1` |
| Principal Pattern | `blockworld.bounded_mission@1` |
| First world | private, allowlisted, non-operator server fixture |

It is not a public autonomous server, generic Minecraft console, unrestricted survival bot, remote
shell, or unbounded computer-use surface.

## Four places where continuity lives

| Truth | Durable home |
| --- | --- |
| Blocks, entities, inventory, and game time | authoritative world volume |
| Identity, vows, relationships, memories, projects, and meaning | inhabitant application records |
| Invocation cursor, budgets, pending work, and action receipts | pinned Run and its durable ledger |
| Socket state, pathing, animation, and unacknowledged buffers | volatile bridge state |

The server and its Sentinel are persistent workloads. The bridge is a Tool Animator; it translates
typed observations and constrained actions but does not deliberate. The Mind deliberates only over
a bounded mission. Structured server truth outranks vision, screenshots, chat, signs, books, or
any other untrusted text. No prose memory proves a placed block, and a world snapshot alone does
not decide what an act meant.

## One mission, exact tools

`blockworld.bounded_mission@1` is a finite score:

```text
AdmitMission → ObserveWorld → RecallBoundedContext → DeliberateOneStep
→ ValidateProposal → Gate → IssueAction → VerifyEventOrWorldDiff
→ CommitReceiptAndCursor → Continue | ReflectAndEnd | EndNonComplete
```

The first bridge may read only `world_status`, `inventory_summary`, `scan_region`,
`nearby_entities`, and `chat_since`. It may effect only `move_to`, `look_at`, `say`, `equip`, and
`place_block`. There is no generic server command, RCON, console, packet injector, script runner,
or administrator tool.

Every action declares its id, mission id, authenticated bot UUID, Pattern and bridge revisions,
region/plot lease, precondition digest, expected cursor, deadline, budgets, and postcondition. If
the bridge loses an acknowledgement, it asks `action_status`, then compares the server cursor and
world. An unresolved reply is an `unverified_effect`, never a reason to repeat a placement.

## Authority, lifecycle, and recovery

Sentinel enforces plot and action scopes on the server; bridge checks are only a second line.
Destructive edits, fire/lava/explosives, PvP, trading, private chat, cross-plot inventory, account
or plugin change, restore, and public exposure are separate capabilities requiring their own law
and consent. The first server is private, allowlisted, online-mode, and uses a dedicated
non-operator bot.

Cold backup follows orderly save and stop. Restoration requires the Magus, restores a named world
and snapshot, increments the world epoch, and invalidates old leases and assumptions. On every
boot the system reconciles server identity, world epoch, Sentinel cursor, bot UUID, and final
action receipt before any resumption. Server, protocol, Sentinel, bridge, controller, Pattern, and
application schemas version independently; incompatible parked missions drain, migrate through an
explicit adapter, or end non-complete.

The Composition owns identity, mission, memory-candidate, project, lease, and receipt schemas;
world files remain world custody and Sentinel owns its event journal. Retention/export/deletion
must preserve that separation. A deletion request inventories both records and world-derived
artifacts; it cannot erase an authoritative event by editing a journal entry.

## Smallest proving slice

Use a flat private world, one server-enforced `7×7` plot, one non-op bot, a controlled chest, and
one reviewed blueprint. Admit a mission that exposes precisely the five reads and five effects
above, verify each placement from Sentinel sequence plus final plot diff, then interrupt the bridge
after an accepted placement and before acknowledgement. Recovery must produce one receipt and no
duplicate block. This proves finite awakening, persistent consequence, and reconciliation before
open exploration or sociable life.

Continue with [Workflow](../adr/28-workflow.md), [Security](../adr/09-security.md), and the
[Composition portfolio](index.md).
