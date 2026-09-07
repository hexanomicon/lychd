---
title: Sentinel
icon: material/shield-sword-outline
---

# :material-shield-sword-outline: Sentinel

One proposed placement crosses from an inhabitant's intention into a server's world. Sentinel validates that crossing; the client adapter translates it. Structured server facts supply the evidence. Screenshots, signs, books, chat, and other world prose remain untrusted observations.

In `managed` mode, the server-side Sentinel can witness authoritative state and effects. In `attached` mode, admission is the intersection of local policy and explicitly offered server capabilities. Client observation cannot fill a missing server guarantee.

## The narrow crossing

Revision `1` defines five reads and five effects. The managed fixture exposes all ten; an attached profile may offer fewer.

| Reads | Effects |
| --- | --- |
| `world_status` | `move_to` |
| `inventory_summary` | `look_at` |
| `scan_region` | `say` |
| `nearby_entities` | `equip` |
| `chat_since` | `place_block` |

Every action carries action/mission ids, bot UUID, server mode, Pattern/adapter revisions, lease, precondition digest, expected cursor, deadline, budgets, and postcondition. Managed Sentinel checks the plot, preconditions, cursor, and budgets on the authoritative server before issuance. Attached-mode local checks narrow the request; the external server still decides whether to accept it. A matching response and authoritative event or sufficient resulting-state proof produce one durable receipt.

## Refusal remains server-side

Revision `1` excludes destructive edits, fire, lava, explosives, PvP, trading, private chat, cross-plot inventory, account/plug-in changes, restoration, and public exposure. Attached mode also excludes server configuration, console, lifecycle, snapshot, plug-in, and mod effects. A mistaken or hostile adapter cannot make server authority disappear.

If acknowledgement is lost, query `action_status` where available and compare the Sentinel cursor with resulting world state. Insufficient attached-server proof narrows eligible effects or returns `unverified_effect`. It never licenses another placement to obtain a cleaner answer. Socket, pathing, animation, and unacknowledged buffers remain volatile; [Continuity](continuity.md) owns durable re-entry.

Return to [Blockworld](index.md).
