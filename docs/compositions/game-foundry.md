---
title: Foundry
icon: material/gamepad-variant
---

# :material-gamepad-variant: Foundry

Foundry carries one game idea far enough that a person can play and inspect it. It keeps the
source, engine recipe, tests, controller observations, and build evidence that make the result
repeatable. A convincing story about an Agent making a game is not a playable build.

!!! note "Current material"
    Foundry is a Native Reference Composition, not an executable build pipeline today. No
    Foundry Pattern, engine adapter, project ledger, playtest harness, or
    `PlayableBuildBundle@1` path is registered; LychD's own packaging evidence proves none of them.

[State of Work](../state-of-the-work.md#composition-portfolio-delivery) owns the delivery boundary for this reference.

## Contract

| Field | Reference contract |
| --- | --- |
| **Identity** | `game.foundry` revision `1` |
| **Principal Pattern** | `game.build_playable_slice@1` |
| **Application begins with** | an admitted design contract, pinned source revision, engine profile, tests, and optional `CreativeAssetBundle@1` |
| **Application can return** | one attributable `PlayableBuildBundle@1`, or an exact non-completion |
| **Application stops before** | deciding what is fun, autonomous project direction, public multiplayer, signing, upload, or store release |

Foundry owns design, version-controlled source, scenes, resources, imports, tests, build recipes,
playtests, balance evidence, release candidates, and distribution receipts. It does not own
Voidlight's asset lineage, a game engine, a store account, or another workflow jurisdiction.

## Project to playable slice

1. **Freeze the project.** Pin the design, repository revision, dependencies, engine and adapter
   versions, environment, build recipe, declared scenario, and acceptance checks.
2. **Admit assets.** Validate an exact `CreativeAssetBundle@1` against the project target, rights,
   semantic role, and spatial or temporal limits; return findings instead of editing the bundle.
3. **Change one slice.** Modify only the bounded feature named by the Invocation and preserve the
   source diff that produced it.
4. **Build locally.** Run static and engine tests, perform deterministic imports, and create a
   content-addressed candidate with source, command, environment, probe, and checksum evidence.
5. **Play the declared scenario.** A constrained controller acts within time, action, observation,
   and cost budgets. Structured engine observations take precedence over screenshots.
6. **Review and package.** Human judgment accepts the evidence or requests a new forward repair;
   an accepted slice becomes `PlayableBuildBundle@1` without implying release authority.

The remaining scores keep distinct work distinct: `game.bootstrap_project@1`,
`game.import_creative_bundle@1`, `game.build_candidate@1`,
`game.playtest_candidate@1`, `game.balance_from_evidence@1`,
`game.prepare_release@1`, and `game.publish_build@1`. Each has its own inputs, outputs, gates,
receipts, and terminal non-completion.

## Project custody and Studio handoff

| Record | Custody and use |
| --- | --- |
| Project truth | Foundry design, source, scenes, resources, settings, tests, and build recipe |
| Source asset | Voidlight's immutable bundle manifest, admitted by exact digest |
| `AssetImportReceipt@1` / `AssetFindingSet@1` | Foundry's import result and any correction evidence returned to the producer |
| Build and playtest evidence | source lock, dependencies, engine, adapter, environment, tests, scenario, observations, and findings |
| `PlayableBuildBundle@1` | immutable candidate plus build, test, playtest, and checksum receipts |

Engine-native imports and rebuildable caches remain Foundry records. A Suite may retain the typed
bundle handoff and run correlation, but never merges member databases, Sigils, secrets, provider
sessions, approval, budget judgment, or release authority.

## Playtest, release, and recovery

An `EngineAdapter` exposes project, import, test, build, and observation operations. A separate
`ControllerAdapter` exposes only bounded game inputs. Neither supplies a generic shell, debug
console, anti-cheat bypass, public-server access, or authority to deceive players. The scenario
author, controller, and player remain different roles; humans decide whether the evidence is fun.

License acceptance, destructive source changes, build, signing, upload, staged release, and public
release are independent gates. Upload and publication use exact effect identities, request
digests, remote lookup material, and receipts. Lost acknowledgement leaves an **unknown** effect
that must be reconciled before any retry.

Restart resolves the pinned Pattern, source, engine, adapter, environment, receipt, and artifact
formats. Incompatible parked work drains, migrates through an explicit adapter, or ends honestly.
Deletion inventories local builds, derivatives, and remote copies; it may request removal, but it
cannot promise that a published binary disappeared.

## Proving build

Use a synthetic local 2D project with networking disabled. Bootstrap one repository, admit one
small creative bundle, import it through a test adapter, build one playable scene, run one declared
controller scenario, and emit exactly one `PlayableBuildBundle@1` with source, build, test, and
playtest receipts. Signing, upload, store accounts, telemetry export, public players, and release
remain outside the proof.

Related: [Voidlight](voidlight-studio.md) · [Workflow](../adr/28-workflow.md) ·
[Composition portfolio](index.md)
