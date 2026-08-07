---
title: World Bridge
icon: material/bridge
---

# :material-bridge: World Bridge

The bridge translates one admitted step; it does not become the world, its administrator, or its
judge. Structured server facts outrank screenshots, signs, books, chat, and other untrusted prose.

## The narrow crossing

Revision `1` exposes exactly five reads and five effects:

| Reads | Effects |
| --- | --- |
| `world_status` | `move_to` |
| `inventory_summary` | `look_at` |
| `scan_region` | `say` |
| `nearby_entities` | `equip` |
| `chat_since` | `place_block` |

Each action carries its action and mission ids, bot UUID, Pattern and bridge revisions, lease,
precondition digest, expected cursor, deadline, budgets, and postcondition. Sentinel validates the
plot, action, preconditions, cursor, and budgets on the authoritative server before the bridge
issues it. A matching response plus resulting world event or diff produces one durable action
receipt.

## Refusal belongs server-side

Bridge checks are an additional guard; Sentinel keeps authority even if the client is mistaken or
hostile. Revision `1` refuses destructive edits, fire, lava, explosives, PvP, trading, private
chat, cross-plot inventory, account or plug-in changes, restoration, and public exposure. World
text cannot grant tools, widen a lease, or prove a fact.

If acknowledgement disappears after an action, the bridge asks `action_status` and compares the
Sentinel cursor with world state. An unresolved consequence is `unverified_effect`; repeating a
placement is refused. The mission may report that uncertainty, but cannot manufacture a clean
receipt or advance as though nothing happened.

The socket, pathing, animation, and unacknowledged buffers remain volatile bridge state. Durable
mission progress and re-entry belong to [Continuity](continuity.md). Return to
[Blockworld](index.md).
