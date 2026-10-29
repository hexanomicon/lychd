---
title: Assets
icon: material/treasure-chest-outline
---

# :material-treasure-chest-outline: Assets

A visual asset can be approved by its director and still fail an engine import. Foundry judges the target use and preserves the producer's exact material so a technical failure can return as evidence rather than become a silent source repair.

`game.import_asset_bundle@3` admits `VisualAssetBundle@1`, `MusicAssetBundle@1`, and optional `TimedLanguageAssetBundle@2` against project roles, target, formats, rights, and spatial/temporal limits. Source manifests remain with Atelier, Riffmaw, Language Edition, or their exact producer. Foundry owns the engine-native imports and caches.

## Source to engine derivative

An import must explain how the producer's material became an engine derivative. `AssetImportReceipt@1` binds that source to the importer, target, transformations, outputs, and checks. For spatial material, admission records source units/axes/origin/scale, coordinate transforms, materials/textures, skeleton/animation mappings, generated collision/LOD/engine derivatives, importer/engine revisions, warnings, validation, and performance.

If those checks expose a problem, return it as `AssetFindingSet@1`. The producer receives attributable correction evidence while its lineage and creative approval remain unchanged.

A glTF/GLB can combine mesh, PBR appearance, skeleton, skinning, and animation. Point clouds, Gaussian/radiance forms, neutral voxels, game block grids, and portable assemblies require their own supported import forms. Unsupported forms fail or return findings. [Prism Form](../../sepulcher/extensions/prism/form.md#one-form-job-explicit-operation) owns admitted source-form conversion and declared loss; an engine importer cannot quietly mesh, rig, voxelize, or bake the source.

One asset's collider, LOD, skeleton/material/animation map belongs to its import. World-wide collision layers/masks, navigation joins, spawn, streaming, interaction roles, actor bindings, and controller use belong to the [World](world.md) bake. Reusing a derivative changes neither receipt's ownership.

For motion, begin with the exact accepted animation. Admission pins its target Form rig digest when rig-bound and the Kinesis `MotionAssetSet@1`/retarget receipt when used. [Kinesis](../../sepulcher/extensions/prism/kinesis.md) retains the portable curves, mapping, root/contact semantics, and technical validation. Foundry then owns the choices that make it run in the game: clip compression, engine controllers/state machines, blending, gameplay root motion, and playtest. Passing the import checks cannot certify the source rig or creative choice.

## Distinct sound and world boundaries

[World Sound](sound.md) uses `game.import_world_sound@1` and `WorldSoundImportReceipt@1`; it does not widen the spatial meaning of `AssetImportReceipt@1`. A separately owned reusable pack retains producer lineage, while project-specific event/space/runtime sound stays Foundry truth.

A `.schem` or block grid can enter a project/map asset. Live placement still requires a [Blockworld mission](../blockworld/mission.md), its epoch, lease, inventory, Sentinel, and receipts. A Suite can correlate handoffs and Runs but cannot merge member databases, Sigils, secrets, sessions, approvals, budget judgment, or release authority.

An [Atelier studio](../products-and-suites.md#atelier-riffmaw-language-edition-and-broadcast)
could propose generated material during play. Its creative acceptance and engine import do not
prove live activation. A future hotload contract must bind the exact target-runtime state, reject
stale outputs, distinguish acknowledged, partial, unknown, and reverted application, and preserve
the prior usable revision for bounded recovery. A lost acknowledgement requires reconciliation
before retry. The present import/build contract does not establish that live route.

[Project](project.md) keeps custody; [Build](build.md) seals the candidate using these derivatives.
