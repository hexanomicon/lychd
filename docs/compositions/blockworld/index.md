---
title: Blockworld
icon: material/cube-scan
---

# :material-cube-scan: Blockworld

The inhabitant wakes for one mission. When its Mind goes quiet, the wall it placed may remain. Blockworld keeps the purpose, lease, placements, and receipts beside that consequence so the next awakening can begin from reconciled world truth.

A reviewed blueprint on a private plot is the first journey: establish the finite mission and its memory, have Sentinel guard each crossing into the server, then reconcile world truth after interruption or restoration.

## Contract

`blockworld.inhabitant` revision `1` publishes `blockworld.bounded_mission@1`. Admission binds a finite mission, server mode, authenticated bot, exact world epoch and capabilities, plot lease, blueprint, tools, and budgets. Its return is verified action receipts, a durable mission cursor, and completion or exact non-completion. Public autonomy, unrestricted exploration, administrator commands, remote shell, and cross-plot power remain outside the mission.

Blockworld owns inhabitant, mission, world-local relationship, project, memory-candidate, lease, and receipt records. The server owns blocks, entities, inventory, and game time. An [Avatar](../avatar/index.md) can project the Lich through the inhabitant without acquiring any mission, inventory, lease, or world effect.

## Server

Choose one closed mode before admission:

```toml
[blockworld.server]
mode = "managed" # managed | attached
```

| Mode | Admitted control | Limit |
| --- | --- | --- |
| **`managed`** | Rootless server Quadlet, declared world volume, configuration, exact mod/plug-in set, lifecycle and recovery receipts. | Server or modpack changes require a separately admitted deployment and operator approval. The bot receives no administrator power. |
| **`attached`** | Bot identity, endpoint, credentials and client adapter. | No server files, console, lifecycle, snapshot, plug-in or mod authority. Admit only capabilities the external server offers. |

The first fixture is managed: private, allowlisted, online-mode, and operated through a dedicated non-operator bot. An attached server may offer weaker observation or verification. Mode, server identity, protocol, capability/modpack revision, and Sentinel availability are pinned before the bot wakes. Changing mode drains missions and creates a new server generation and world epoch.

## Enter by question

[Mission](mission.md) · [Sentinel](sentinel.md) · [Continuity](continuity.md)

[Workflow](../../adr/28-workflow.md) · [Containers](../../adr/08-containers.md) · [Security](../../adr/09-security.md) · [Composition Portfolio](../index.md)
