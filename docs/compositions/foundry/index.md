---
title: Foundry
icon: material/gamepad-variant
---

# :material-gamepad-variant: Foundry

Foundry carries one game idea far enough that a person can play and inspect it. It keeps the
project, imported assets, tests, controller observations, and build evidence that make the result
repeatable.

## Contract

| Field | Reference contract |
| --- | --- |
| **Identity** | `game.foundry` revision `2` |
| **Principal Pattern** | `game.build_playable_slice@1` |
| **Begins with** | an admitted design contract, pinned source revision, engine profile, tests, and optional visual or sonic bundles |
| **Can return** | one attributable `PlayableBuildBundle@1`, or an exact non-completion |
| **Stops before** | deciding what is fun, autonomous project direction, public multiplayer, signing, upload, or store release |

Foundry owns design, version-controlled source, scenes, resources, imports, tests, build recipes,
playtests, balance evidence, release candidates, and distribution receipts. It does not own
Voidlight's visual lineage, Riffmaw's sonic lineage, the game engine, a store account, or another
workflow jurisdiction.

## Enter the workshop

- [Project](project.md) fixes design, source, engine, dependencies, and one bounded change.
- [Assets](assets.md) admits visual and sonic bundles without rewriting their lineage.
- [Playtest](playtest.md) gathers bounded game evidence without pretending to decide fun.
- [Build](build.md) creates, reviews, recovers, and optionally prepares a release candidate.

Related: [Voidlight](../voidlight/index.md) · [Riffmaw](../riffmaw/index.md) ·
[Composition Portfolio](../index.md) · [Workflow](../../adr/28-workflow.md)
