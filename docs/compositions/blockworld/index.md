---
title: Blockworld
icon: material/cube-scan
---

# :material-cube-scan: Blockworld

The inhabitant wakes for one mission. When its Mind goes quiet, the wall it placed may remain. Blockworld keeps the purpose, lease, placements, and receipts beside that consequence so the next awakening can begin from reconciled world truth.

A reviewed blueprint on a private plot is the first journey: establish the finite mission and its memory, have Sentinel guard each crossing into the server, then reconcile world truth after interruption or restoration.

## Contract

`blockworld.inhabitant` revision `2` publishes `blockworld.bounded_mission@2`. Admission binds a finite mission, server mode, authenticated bot, exact world epoch and capabilities, plot lease, blueprint, tools, and budgets. Its return is verified action receipts, a durable mission cursor, and completion or exact non-completion. Public autonomy, unrestricted exploration, administrator commands, remote shell, and cross-plot power remain outside the mission.

Revision `1` and `blockworld.bounded_mission@1` remain historical design contracts, retired in favour of revision `2`. Their mission authority, five reads and five effects, verified receipts, and refusal to repeat an uncertain placement remain unchanged. Revision `2` adds required preparation, exact command/review binding, and native action continuity for the bounded placement operation. These requirements do not reinterpret revision `1` or establish parked-state compatibility. This design retirement defines no executable migration; [State of Work](../../state-of-the-work.md#composition-portfolio-delivery) owns registration and delivery.

The bounded-mission code slice is an inactive, one-block test workflow assembled explicitly with
inert effects. It is not registered at normal boot and does not connect to Minecraft. The separate
[Horizon-assist profile](horizon-assist.md) supplies an experimental attached-client passage.
[State of Work](../../state-of-the-work.md#composition-portfolio-delivery) keeps their evidence and
remaining game checks distinct.

Blockworld owns inhabitant, mission, world-local relationship, project, memory-candidate, lease, action, and receipt records. The server owns blocks, entities, inventory, and game time. An [Avatar](../avatar/index.md) can project the Lich through the inhabitant without acquiring any mission, inventory, lease, or world effect.

## Your Minecraft client

[Prism Launcher](https://prismlauncher.org/wiki/getting-started/create-instance/) manages your
Minecraft client instances, including the game version and modloader. In this design, you join
the world through that human client; the inhabitant connects separately through an admitted bot
identity and client adapter. The server owns the world, and [Sentinel](sentinel.md) guards
admitted effects.

A singleplayer world opened to LAN, or an existing external server, can be considered for
`attached` mode only when its endpoint is reachable and bot access is explicitly authorized.
Admission remains limited to the capabilities the server actually offers; client observation
cannot supply missing server proof. The first managed fixture below remains the proving target.

A [Prism Launcher client on macOS](https://prismlauncher.org/download/macos/) is separate from
[LychD's Linux host requirement](../../adr/08-containers.md#supported-host-policy). LychD
[Prism](../../sepulcher/extensions/prism/voxel-and-block-export.md) is a different component: its
designed block-export path supplies blueprints for separate mission admission. An existing launcher
instance does not establish game/modpack compatibility or provide Blockworld integration;
[State of Work](../../state-of-the-work.md#composition-portfolio-delivery) records delivery.

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

[Companion lab](companion-lab.md) develops a separate opt-in Fabric NPC actuator with native
command admission, a finite operator queue and CPU-ready speech. Its actor and experimental
delivery boundary do not replace the authenticated-player bounded mission.

[Horizon assist](horizon-assist.md) defines the separate experimental attached-client passage
for bounded spoken or typed actions. It does not weaken the managed mission's receipt contract.
[Playing with a companion](horizon-play.md) gives user stories, acceptance trials and the order
of preparation for multilingual voice, following and shared building.

[Mission](mission.md) defines the work the inhabitant may attempt. [Sentinel](sentinel.md)
guards each crossing into the server. After interruption or restoration,
[Continuity](continuity.md) reconciles what remains before another awakening begins.

[Workflow](../../adr/28-workflow.md) · [Containers](../../adr/08-containers.md) · [Security](../../adr/09-security.md) · [Composition Portfolio](../index.md)
