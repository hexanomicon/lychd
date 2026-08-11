---
title: Reach
icon: material/hand-back-right-outline
---

# :material-hand-back-right-outline: Reach

Reach lets one revision-pinned Persona answer in an external social place without handing that
place LychD's authority. A mention, command, or admitted presence event creates one finite
awakening; the platform account never becomes the Lich.

| Field | Reference contract |
| --- | --- |
| **Identity** | `reach.discord` revision `1` |
| **Patterns** | `reach.external_converse@1`, `reach.external_summon@1`, `reach.external_presence@1` |
| **Begins with** | one allowlisted mention, guild command, or policy-admitted internal event |
| **Can return** | `ReachTurn@1` and optional `ReachDelivery@1` |
| **Stops before** | moderation, ambient surveillance, attachments, DMs, remote shell, deployment, or platform-settled consent |

- [Habitat](habitat.md) defines the admitted social place, caller boundary, and cross-world continuity.
- [Turn](turn.md) carries one event through Context, committed result, delivery, and recovery.

[Avatar](../avatar/index.md) may bind one Lich projection into a Habitat, but Reach still owns the
platform event, audience, turn, delivery, and reply receipt. Avatar receives only those attributed
results; the platform account never becomes the Lich or grants the next projection.

Related: [Composition Portfolio](../index.md) · [Workflow](../../adr/28-workflow.md)
