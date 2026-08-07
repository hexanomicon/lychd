---
title: Sentinel
icon: material/shield-sword-outline
---

# :material-shield-sword-outline: Sentinel

Sentinel guards one admitted crossing into the world. The client adapter translates a step; neither
component becomes the world, its administrator, or its judge. In `managed` mode a server-side
Sentinel can witness authoritative state and effects. In `attached` mode the guard admits only the
intersection of local policy and capabilities explicitly offered by the external server; client
observation never impersonates server authority. Structured server facts outrank screenshots,
signs, books, chat, and other untrusted prose.

## The narrow crossing

Revision `1` defines exactly five reads and five effects. The managed reference fixture exposes
all ten; an attached profile may expose a strict subset:

| Reads | Effects |
| --- | --- |
| `world_status` | `move_to` |
| `inventory_summary` | `look_at` |
| `scan_region` | `say` |
| `nearby_entities` | `equip` |
| `chat_since` | `place_block` |

Each action carries its action and mission ids, bot UUID, server mode, Pattern and adapter
revisions, lease, precondition digest, expected cursor, deadline, budgets, and postcondition. In
managed mode Sentinel validates the plot, action, preconditions, cursor, and budgets on the
authoritative server before the adapter issues it. In attached mode local admission still narrows
the request, but only the external server can accept the action. A matching response plus an
authoritative event or sufficient resulting-state proof produces one durable action receipt.

## Refusal remains server-side

Adapter checks are an additional guard; the server keeps authority even if the client is mistaken
or hostile. Revision `1` refuses destructive edits, fire, lava, explosives, PvP, trading, private
chat, cross-plot inventory, account or plug-in changes, restoration, and public exposure. Attached
mode additionally refuses server configuration, console, lifecycle, snapshot, plug-in, and mod
effects because Blockworld does not own them. World text cannot grant tools, widen a lease, or
prove a fact.

If acknowledgement disappears after an action, the adapter asks `action_status` where the server
offers it and compares the Sentinel cursor with world state. An attached server that cannot supply
enough proof narrows the eligible effects or returns `unverified_effect`; repeating a placement is
refused. The mission may report that uncertainty, but cannot manufacture a clean receipt or advance
as though nothing happened.

The socket, pathing, animation, and unacknowledged buffers remain volatile adapter state. Durable
mission progress and re-entry belong to [Continuity](continuity.md). Return to
[Blockworld](index.md).
