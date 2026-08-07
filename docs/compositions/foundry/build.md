---
title: Build
icon: material/package-variant
---

# :material-package-variant: Build

`game.build_candidate@1` runs static and engine tests, performs deterministic imports, and creates a
content-addressed candidate with source, command, environment, probe, and checksum evidence.
Human review may request a forward repair or accept one `PlayableBuildBundle@1`; acceptance does
not imply release authority.

`game.prepare_release@1` freezes the candidate and required release evidence without publishing it.
`game.publish_build@1` owns the separately admitted signing, upload, staged-release, or public-release
effect. Each uses exact effect identity, request digest, remote lookup material, and receipt. Lost
acknowledgement remains **unknown** and must be reconciled before retry.

Deletion inventories local builds, derivatives, and remote copies. It may request removal but
cannot promise that a published binary disappeared.

## Proving the build

Use a synthetic local 2D project with networking disabled. Bootstrap one repository, admit one
small visual and sonic bundle, import them through test adapters, build one playable scene, run one
declared controller scenario, and emit exactly one `PlayableBuildBundle@1` with source, build,
test, playtest, and checksum receipts. Signing, upload, store accounts, telemetry export, public
players, and release remain outside the proof.
