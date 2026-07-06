---
title: Summoning
icon: material/fire
---

# :material-fire: The Summoning Rite

This is the rite that wakes the daemon. Follow it top to bottom and you will end with a
local model streaming its first reply to you on the Bridge (the Altar's chat instrument).

The rite has five stages. Each stage is one page, each page ends with a command that
proves it worked, and each failure links into the [Exorcism](../praxis/exorcism.md)
troubleshooting guide.

| Stage | You will | Page |
| :--- | :--- | :--- |
| 1. Grounds | Confirm the host can carry the daemon (Linux, podman, systemd, a GPU, Postgres). | [The Grounds](grounds.md) |
| 2. Desecration | Install the `lychd` command-line tool. | [The Desecration](desecration.md) |
| 3. Inscription | Run `lychd init` and understand the Codex and the Crypt. | [The Inscription](inscription.md) |
| 4. First Soulstone | Write your first Soulstone Rune (a local model service) and bind it. | [The First Soulstone](first-soulstone.md) |
| 5. First Breath | Start the daemon, open the Altar, and exchange the first message. | [The First Breath](first-breath.md) |

!!! note "Time estimate"
    Budget about 30 minutes if podman and Postgres are already running, plus however long
    it takes to download your first model weights.

!!! warning "The host is Linux"
    LychD binds to a Linux host with a rootless podman + systemd user session. macOS and
    Windows are development platforms for the code, not summoning grounds for the daemon.
    See [The Grounds](grounds.md) for the full list.

When you finish, the daemon is alive on your iron. From there, the [Praxis](../praxis/index.md)
teaches you the rites of daily use: opening Portals to remote providers, managing coven
swaps, and reading the instruments of the [Altar](../divination/altar/index.md).
