---
title: Blockworld
icon: material/cube-scan
---

# :material-cube-scan: Blockworld

The inhabitant wakes for one bounded mission and leaves consequences in a world that persists
after its Mind goes quiet. A wall may remain, but its purpose, authority, and exact placements must
remain inspectable too. Each return begins from reconciled world truth rather than imagined
continuity.

## Contract

| Field | Reference contract |
| --- | --- |
| **Identity** | `blockworld.inhabitant` revision `1` |
| **Principal Pattern** | `blockworld.bounded_mission@1` |
| **Application begins with** | an admitted finite mission, selected server mode, authenticated bot, exact world epoch and capabilities, plot lease, blueprint, tools, and budgets |
| **Application can return** | verified action receipts, an updated mission cursor, and completion or exact non-completion |
| **Application stops before** | public autonomy, unrestricted exploration, administrator commands, remote shell, or cross-plot power |

The first world is a private, allowlisted, online-mode server fixture with a dedicated non-operator
bot. Blockworld owns its inhabitant, mission, relationship, project, memory-candidate, lease, and
receipt records. The server remains authoritative for blocks, entities, inventory, and game time.

## Server

A Blockworld profile selects one closed mode:

```toml
[blockworld.server]
mode = "managed" # managed | attached
```

| Mode | Blockworld controls | Hard boundary |
| --- | --- | --- |
| **`managed`** | a rootless server Quadlet, declared world volume, server configuration, exact mod or plug-in set, lifecycle, and recovery receipts | server or modpack changes require a separate admitted deployment with operator approval; an inhabitant mission never inherits administrator power |
| **`attached`** | bot identity, endpoint, credentials, and client adapter only | no server files, console, lifecycle, snapshot, plug-in, or mod authority; only capabilities explicitly offered by the external server may be admitted |

The mode, server identity, protocol, modpack or capability revision, and Sentinel availability are
pinned before a mission starts. Changing mode drains active missions and establishes a new server
generation and world epoch; it cannot silently widen a running bot's authority. `managed` is the
reference fixture, while `attached` must remain honest about weaker observation or verification.

## Enter by question

- [Mission](mission.md) — what may wake the inhabitant, what it may pursue, and
  where the work must stop.
- [Sentinel](sentinel.md) — which observations and effects may cross the server boundary,
  and how one consequence becomes verified.
- [Continuity](continuity.md) — what survives interruption or restoration, where each truth lives,
  and what proves recovery.

Related: [Workflow](../../adr/28-workflow.md) · [Containers](../../adr/08-containers.md) ·
[Security](../../adr/09-security.md) · [Reach](../reach/index.md) ·
[Composition portfolio](../index.md)
