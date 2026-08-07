---
title: Sentinel
icon: material/shield-sword-outline
---

# :material-shield-sword-outline: Sentinel

Sentinel guards one admitted crossing into the world. The client adapter translates a step; neither
component becomes the world, its administrator, or its judge. Structured server facts outrank
screenshots, signs, books, chat, and other untrusted prose.

## The narrow crossing

Revision `1` exposes exactly five reads and five effects:

| Reads | Effects |
| --- | --- |
| `world_status` | `move_to` |
| `inventory_summary` | `look_at` |
| `scan_region` | `say` |
| `nearby_entities` | `equip` |
| `chat_since` | `place_block` |

Each action carries its action and mission ids, bot UUID, Pattern and adapter revisions, lease,
precondition digest, expected cursor, deadline, budgets, and postcondition. Sentinel validates the
plot, action, preconditions, cursor, and budgets on the authoritative server before the adapter
issues it. A matching response plus resulting world event or diff produces one durable action
receipt.

## Refusal remains server-side

Adapter checks are an additional guard; Sentinel keeps authority even if the client is mistaken or
hostile. Revision `1` refuses destructive edits, fire, lava, explosives, PvP, trading, private
chat, cross-plot inventory, account or plug-in changes, restoration, and public exposure. World
text cannot grant tools, widen a lease, or prove a fact.

If acknowledgement disappears after an action, the adapter asks `action_status` and compares the
Sentinel cursor with world state. An unresolved consequence is `unverified_effect`; repeating a
placement is refused. The mission may report that uncertainty, but cannot manufacture a clean
receipt or advance as though nothing happened.

The socket, pathing, animation, and unacknowledged buffers remain volatile adapter state. Durable
mission progress and re-entry belong to [Continuity](continuity.md). Return to
[Blockworld](index.md).
