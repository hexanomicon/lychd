---
title: Game Foundry
icon: material/gamepad-variant
---

# :material-gamepad-variant: Game Foundry

Game Foundry is where a playable thing earns the right to be called one. It keeps the evidence that
a scene was built from particular source, that a controller did what was observed, and that a build
can be repeated—not merely a pleasant account of an Agent making a game.

| Maturity | Accepted Reference Composition — architecture, not delivery; [State of Work](../state-of-the-work.md) owns what runs |
| --- | --- |
| Identity | `game.foundry` revision `1` |
| Principal Pattern | `game.build_playable_slice@1` |
| Result | `PlayableBuildBundle@1` |

It owns game design, version-controlled source, scenes/resources, imports, tests, build recipes,
playtests, balance evidence, releases, and effect receipts. It does not own Voidlight's asset
lineage or Broadcast's editorial/publication truth, and it is not a game engine, autonomous game
director, store account, or second workflow engine.

## Project truth and the Studio boundary

| Class | Custody |
| --- | --- |
| Design, source, scenes, resources, settings, tests, build recipe | Foundry durable project records and VCS |
| Admitted source asset | immutable `CreativeAssetBundle@1` manifest held by Voidlight |
| Engine-native import and derived cache | Foundry; reproducible from source plus pinned adapter |
| Candidate build and external release | Foundry artifact records and effect receipts |
| Invocation, Graph, and queue work | run/execution truth, never the project ledger |

Foundry admits a bundle by digest and validates its target contract, rights, semantic role, and
spatial/temporal limits. It returns `AssetImportReceipt@1` and `AssetFindingSet@1`; it never writes
Voidlight's database or silently amends an asset. A Suite is a durable graph of such typed,
immutable handoffs. It does not share member Sigils, provider sessions, secrets, approvals, or
effect authority.

## The Pattern set

The immutable Pattern revisions are **bootstrap**, **import**, **playable slice**, **build
candidate**, **playtest candidate**, **balance from evidence**, **prepare release**, and
**publish**:

| Pattern | Purpose |
| --- | --- |
| `game.bootstrap_project@1` | admit a design contract, pinned engine profile, repository, and acceptance tests |
| `game.import_creative_bundle@1` | validate a `CreativeAssetBundle@1`, derive imports, return receipt/findings |
| `game.build_playable_slice@1` | make one bounded feature demonstrable and yield `PlayableBuildBundle@1` |
| `game.build_candidate@1` | produce a content-addressed candidate from pinned source and recipe |
| `game.playtest_candidate@1` | execute declared scenarios and collect evidence |
| `game.balance_from_evidence@1` | propose a reviewable balance revision from attributed observations |
| `game.prepare_release@1` | assemble a release candidate and checklists |
| `game.publish_build@1` | perform a separately gated distribution effect |

`game.build_playable_slice@1` follows a narrow score:

```text
FreezeDesignAndSource → AdmitAssets → ChangeOneSlice → StaticAndEngineTests
→ BuildLocally → PlayDeclaredScenario → ReviewEvidence → PackageBuild → End
```

Every Pattern has its own immutable id/revision, input and output contracts, gates, receipts, and
terminal non-completion. A repair is a new forward invocation; evidence may invalidate a candidate
but cannot repaint its previous source or playtest.

## Engine, controller, and playtest discipline

An `EngineAdapter` describes project, import, test, build, and observation mechanisms. A separate
`ControllerAdapter` describes isolated movement and inputs. This separation makes controller
observations and effects inspectable, keeps the engine's debug surfaces out of the Agent's hands,
and permits conformance tests without naming a provider as Foundry identity.

Scenario author, controller, and player are different roles. Agentic sessions are bounded by a
declared scenario, time, action, observation, and cost budget. Structured engine observations
outrank screenshots; screenshots are supporting evidence, not hidden game truth. A session cannot
deceive people, join public multiplayer, bypass anti-cheat, use unrestricted shells, or decide
what is fun. Humans judge that from the recordings, telemetry, findings, and their own play.

## Effects, promotion, and recovery

Builds preserve source revision, dependency lock, engine and adapter versions, build recipe,
environment/container digest, input/output hashes, test results, and probe facts. Promotion,
license acceptance, destructive repository change, build, signing, upload, staged release, and
public release are distinct gates. Signing has an explicit digest boundary; upload and publication
are effects with idempotency keys, remote lookup material, receipts, and unknown-state
reconciliation. A lost acknowledgement never permits a duplicate upload or public release.

The Foundry keeps explicit project, import, source-lock, build, test, playtest, observation,
finding, balance, approval, release, and effect-receipt records. Pattern, schema, engine,
adapter, build environment, receipt, and artifact formats migrate independently. Retention can
discard rebuildable caches while preserving admissible source and receipts; export includes design,
source pointers, manifests, recipes, evidence, and checksums. Deletion inventories builds,
derivatives, and remote copies, then requests downstream removal rather than promising to erase a
published binary. Parked runs pin their revisions and drain, migrate through an explicit adapter,
or end honestly.

## Smallest proving slice

Use a synthetic local 2D project with network disabled: bootstrap one repository, admit one small
bundle, import it through a test adapter, build a single playable scene, run a declared controller
scenario, and emit exactly one `PlayableBuildBundle@1` with source/build/test/playtest receipts.
No signing, upload, store account, telemetry export, public player, or release belongs in this
proof.

Continue with [Voidlight Studio](voidlight-studio.md), [Workflow](../adr/28-workflow.md), and the
[Composition portfolio](index.md).
