---
title: Build
icon: material/package-variant
---

# :material-package-variant: Build

The local candidate is ready when someone else can identify its source, reproduce the admitted checks, and inspect its playtest evidence. `game.build_candidate@1` runs static/engine tests, performs reproducible imports where the exact profile proves them, and returns content-addressed bytes with source, command, environment, probes, and checksum.

Human review can accept `PlayableBuildBundle@1` or request a forward repair. `game.prepare_release@1` freezes that candidate, compatibility statement, evidence, and handoff. Neither step signs, uploads, opens public multiplayer, controls store accounts, exports telemetry, rolls out, corrects, takes down, or reconciles remote copies. Those effects require a future release/distribution owner.

Deletion inventories local candidates, imports, caches, and derivatives. An exported handoff is recorded, without a promise that the consumer's copy was recalled.

## Proving the build

A network-disabled synthetic 2D project should bootstrap a repository, admit small visual/music bundles, import through test adapters, build a scene, and run one controller scenario. Emit exactly one `PlayableBuildBundle@1` with source, build, test, playtest, and checksum receipts. Signing, upload, store accounts, telemetry, public players, and release remain outside it.

A separate 3D fixture adds validated GLB, collision, baked navigation, accepted Kinesis clip/controller, an interaction, headless logic checks, and a real renderer/hardware playtest receipt. It proves no hostile-project execution, open-world streaming, model-driven actor, networking, or other engine profile.
