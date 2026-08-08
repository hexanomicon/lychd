---
title: Assets
icon: material/treasure-chest-outline
---

# :material-treasure-chest-outline: Assets

The proposed Spell `game.import_asset_bundle@1` admits exact `VisualAssetBundle@1` and `SonicAssetBundle@1` inputs
against the project target, semantic roles, formats, rights posture, and spatial or temporal limits.
Foundry may transform them into engine-native imports, but it cannot rewrite the producer's source
lineage.

| Record | Custody |
| --- | --- |
| source bundle manifests | Voidlight or Riffmaw, admitted by exact digest |
| engine-native imports and caches | Foundry |
| `AssetImportReceipt@1` | exact source, importer, target, transformations, outputs, and checks |
| `AssetFindingSet@1` | attributable correction evidence returned to the producing Composition |

A rejected import returns findings; it does not silently repair or replace source assets. A Suite
may retain bundle handoff and Run correlation, but never merges databases, Sigils, secrets,
provider sessions, approval, budget judgment, or release authority.

Spatial admission names the exact facet set and target-engine profile. A glTF/GLB container may
combine mesh, PBR appearance, skeleton, skinning, and animation facets; Foundry admits the exact
combination rather than treating "PBR" and "rigged" as mutually exclusive formats. Point cloud,
Gaussian form, radiance checkpoint, neutral voxel grid, game-specific block grid, and portable
scene assembly remain distinct import forms. An unsupported form fails or
returns an attributed finding. Prism Form owns any admitted source-form conversion and returns its
derivative and declared loss; Foundry owns only target-engine import derivatives. The importer
never silently meshes, rigs, voxelizes, or bakes a source form.

`AssetImportReceipt@1` additionally pins source units, axes, origin and scale; applied coordinate
transforms; material and texture mapping; skeleton and animation mapping; generated collision,
LOD, and engine-native derivatives; importer and engine revisions; warnings; and validation and
performance results. Creative approval remains with Voidlight even when Foundry returns a
technical correction finding.

One asset's importer-level collider, LOD, skeleton map, material conversion, or animation mapping
belongs here. World-wide collision layers and masks, navigation joins, spawn, streaming,
interaction roles, actor binding, and animation-controller use belong to the
[World](world.md) bake. Reusing the asset derivative neither rewrites its source receipt nor grants
the world compiler authority to repair the producer's asset silently.

For motion, Foundry consumes an exact accepted animation revision, target Form rig digest when the
clip is rig-bound, and its Prism [Kinesis](../../sepulcher/extensions/prism/kinesis.md)
`MotionAssetSet@1` and retarget receipt when those technical derivatives participated. Kinesis
owns portable curves, mapping, root/contact semantics, and technical validation; Foundry owns
engine-native import, clip compression, controller or state-machine mapping, blending, gameplay
root-motion use, and playtest. Import success cannot retroactively prove the source rig, clip, or
creative choice correct.

A Sponge `.schem` or exact block grid may be admitted as a project or map asset. That import says
nothing about a live server. Placement into an inhabited world is a separately admitted
[Blockworld mission](../blockworld/mission.md) and remains subject to its world epoch, region lease,
inventory, Sentinel, and effect receipts.

Continue with [Project](project.md) for project custody or [Build](build.md) for the candidate that
uses the admitted assets.
