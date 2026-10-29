---
title: Foundry
icon: material/gamepad-variant
---

# :material-gamepad-variant: Foundry

A game idea becomes useful evidence when another person can load the build and try the intended interaction. Foundry keeps the design, source, imported assets, worlds, scenarios, controller observations, and build receipts needed to repeat that experience.

## Enter the workshop

Start with the bounded change in [Project](project.md). What interaction should someone be
able to try? [Assets](assets.md) admits the exact visual, musical, and dialogue work needed to
make it, preserving each producer's contribution.

[World](world.md) assembles the scene, physics, navigation, controllers, and gameplay.
[World Sound](sound.md) binds sound to events and listeners within that world.
[Playtest](playtest.md) tries an exact scenario; [Build](build.md) seals the local candidate so
that the experience can be repeated.

## Contract

`game.foundry` revision `4` publishes `game.build_playable_slice@3` and the independent `game.design_world_sound@1`. The build starts from an admitted design/source/engine contract and may return `PlayableBuildBundle@1`. Sound starts from `WorldSoundBrief@1` plus exact project/world revisions and may return `WorldSoundBundle@1`. Either can end with exact non-completion.

The Patterns place the following proposed semantic Spells. These contracts are neither Dispatcher capabilities nor delivered implementations.

For a playable slice, the principal build Pattern takes the project through these Spells toward `PlayableBuildBundle@1`:

| Spell | Work it places |
| --- | --- |
| `game.bootstrap_project@1` | Establish project custody and the pinned engine environment. |
| `game.import_asset_bundle@3` | Admit exact producer bundles and create engine imports. |
| `game.assemble_world@1`, `game.bake_world@1`, `game.validate_world@1` | Assemble, compile, and validate the world candidate. |
| `game.playtest_candidate@1` | Try one declared scenario against the exact candidate. |
| `game.balance_from_evidence@1` | Propose a bounded successor from attributed observations. |
| `game.build_candidate@1`, `game.prepare_release@1` | Build and freeze the local candidate and its handoff. |

For interactive sound, the independent Pattern takes its admitted layers through these Spells toward `WorldSoundBundle@1`:

| Spell | Work it places |
| --- | --- |
| `game.import_world_sound@1` | Create sound-specific engine imports. |
| `game.bind_world_sound@1` | Bind admitted sound to exact world events, states, zones, listeners, and runtime behavior. |
| `game.validate_world_sound@1` | Check those sound bindings through their own observations and findings. |

Foundry retains the project source/design, scenes/worlds, interactive sound, resources/imports, tests, recipes, playtests, balance evidence, and local candidates/receipts needed to assess the build. Each producer retains the lineage of its visual, music, or timed-language contribution, while engines and store accounts remain external.

The local finish does not establish fun or authorize autonomous project direction, universal sound libraries, public multiplayer, signing, upload, or store release. To use an XR candidate as a lived place, obtain [Spectre](../spectre/index.md) Habitat and Encounter admission separately.

## Revision continuity

??? info "Earlier designs and their exact successors"

    Revision `3` replaced revision `2` with role-qualified music/language inputs and `@2` successors to `game.build_playable_slice@1` and `game.import_asset_bundle@1`. Revision `4` adds the independent world-sound Pattern/record family and advances build/import to `@3` for `TimedLanguageAssetBundle@2`, preserving the frozen `@2` meanings. No Portfolio registry or Run used revisions `2` or `3`; there is no executable migration.

[Composition Portfolio](../index.md) · [Workflow](../../adr/28-workflow.md)
