---
title: Assets
icon: material/cube-outline
---

# :material-cube-outline: Assets

`game.import_asset_bundle@1` admits exact `VisualAssetBundle@1` and `SonicAssetBundle@1` inputs
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

Continue with [Project](project.md) for project custody or [Build](build.md) for the candidate that
uses the admitted assets.
