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
| **Identity** | `game.foundry` revision `3` |
| **Principal Pattern** | `game.build_playable_slice@2` |
| **Begins with** | an admitted design contract, pinned source revision, engine profile, tests, and optional visual, music, timed-language, or other exact asset bundles |
| **Can return** | one attributable `PlayableBuildBundle@1`, or an exact non-completion |
| **Stops before** | deciding what is fun, autonomous project direction, public multiplayer, signing, upload, or store release |

Revision `3` supersedes the Designed-only revision `2` because the principal journey and asset
import now admit role-qualified music, timed-language, and other exact bundles instead of silently
reinterpreting the former visual/sonic input contract. The former
`game.build_playable_slice@1` and `game.import_asset_bundle@1` meanings remain historical; revision
`3` uses `@2`. No Portfolio registry or Run used revision `2`, so no executable migration exists.

Foundry owns design, version-controlled source, worlds, scenes, resources, imports, tests, build
recipes, playtests, balance evidence, local release candidates, and their receipts. It does not own
Voidlight's visual lineage, Riffmaw's musical lineage, Language Edition's timed-language lineage, the game
engine, a store account, or another workflow jurisdiction.

An XR build remains a Foundry candidate. [Spectre](../spectre/index.md) may later use that exact
candidate to admit a VR Habitat and open bounded Encounters, but it does not inherit project
source, engine-world meaning, controller implementation, playtest evidence, or build authority.

The principal Pattern coordinates proposed semantic Spell placements; none of these names is a
Dispatcher capability or delivered implementation:

| Kind | Contract | Office |
| --- | --- | --- |
| Pattern | `game.build_playable_slice@2` | complete bounded journey from admitted project intent to attributable local candidate |
| Spell | `game.bootstrap_project@1` | establish project custody and pinned engine boundary |
| Spell | `game.import_asset_bundle@2` | admit and import exact visual, music, dialogue, and other role-qualified assets |
| Spell | `game.assemble_world@1`, `game.bake_world@1`, `game.validate_world@1` | compile and validate engine-world meaning |
| Spell | `game.playtest_candidate@1` | execute one bounded gameplay scenario |
| Spell | `game.balance_from_evidence@1` | propose one forward revision from attributed observations |
| Spell | `game.build_candidate@1`, `game.prepare_release@1` | produce and freeze a local handoff candidate without publication |

## Enter the workshop

- [Project](project.md) fixes design, source, engine, dependencies, and one bounded change.
- [Assets](assets.md) admits role-qualified visual, music, dialogue, and game-sound material without
  rewriting producer lineage.
- [World](world.md) assembles engine scenes, collision, navigation, physics, controllers,
  procedural rules, gameplay, and bounded actor policies.
- [Playtest](playtest.md) gathers bounded game evidence without pretending to decide fun.
- [Build](build.md) creates, reviews, recovers, and optionally prepares a release candidate.

Related: [Voidlight](../voidlight/index.md) · [Riffmaw](../riffmaw/index.md) ·
[Language Edition](../language-edition/index.md) ·
[Spectre](../spectre/index.md) ·
[Composition Portfolio](../index.md) · [Workflow](../../adr/28-workflow.md)
