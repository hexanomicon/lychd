---
title: Voidlight Studio
icon: material/camera-timer
---

# :material-camera-timer: Voidlight Studio

A commission enters Voidlight as a pile of references, questions, and taste. It leaves only when
those things have become a named, inspectable creative lineage that another craft can safely use.
The Magus remains the creative director; the Studio makes the work legible enough to revise without
pretending that a prompt was a pedigree.

| Maturity | Accepted Reference Composition — architecture, not delivery; [State of Work](../state-of-the-work.md) owns what runs |
| --- | --- |
| Identity | `voidlight.studio` revision `2` |
| Principal Pattern | `voidlight.build_asset_package@1` |
| Result | `CreativeAssetBundle@1`, immutable and rights-aware |

Voidlight owns commissions, reference dossiers, style and asset specifications, accepted creative
artifacts, provenance, and packages. It is neither workflow engine nor model host, game engine,
editorial publisher, rights-clearing oracle, or infinite repair machine. [Game Foundry](game-foundry.md)
owns engine-native imports, gameplay, builds, playtests, and releases. [Broadcast Studio](broadcast-studio.md)
owns claims, articles, scripts, timelines, final renders, and publication.

## The commission becomes a package

`voidlight.build_asset_package@1` freezes admitted references and dossier; records the brief and
style revision; plans typed assets; acquires or creates candidates; probes, normalizes, and
packages deterministically; then permits bounded review and repair before an explicit handoff.
The normal path is:

```text
FreezeReferences → SetBriefAndStyle → SpecifyAssets → ProduceOrAcquire
→ ProbeAndNormalize → Review → RepairOnceOrRefuse → Accept → Package → Handoff
```

The family remains intentionally separate:
`voidlight.establish_style_bible@1`, `voidlight.forge_concept_set@1`,
`voidlight.forge_sprite_set@1`, `voidlight.forge_texture_set@1`,
`voidlight.forge_model_asset@1`, `voidlight.forge_dialogue_pack@1`,
`voidlight.forge_audio_pack@1`, and `voidlight.forge_cutscene_sources@1` produce their own typed
work; `voidlight.export_asset_package@1` assembles the contract.
`voidlight.review_asset_package@1`, `voidlight.revise_from_correction@1`, and
`voidlight.presenter_calibration@1` remain distinct: a finding is evidence, a repair is a new
forward attempt, and calibration can alter no accepted history.

Each asset keeps immutable ids and revisions, semantic role, target profile, source and derivative
digests, creator and tool receipts, prompt/seed where applicable, transforms, review and approval,
rights/consent scope, and invalidation links. A later bad reference, revoked consent, or failed
finding marks dependent material stale; it never rewrites the earlier record into a nicer past.

## Boundaries and custody

| Concern | Owner |
| --- | --- |
| Pattern selection, budget, gates, pinned Invocation | Weaver under [Workflow](../adr/28-workflow.md) |
| Creative judgment and review proposals | bounded Agents; Magus accepts |
| Capability binding and physical readiness | Dispatcher / Runes and Orchestrator |
| Bytes, manifests, provenance, and retention | Studio artifact custody and its durable records |
| Consumer-derived engine or editorial objects | the consuming Composition |

The Studio asks for image, text, audio, video, transform, probe, and export *capabilities*, never a
provider as its identity. A model, Portal, or local tool contributes a versioned receipt and cannot
quietly take authority. Pattern schema, artifact schema, receipt schema, and tool environment each
version independently.

Normalization and packaging pin the transformer/container digest, command or configuration, input
digests, output digest, probes, and target profile. A stochastic creation may be irreproducible;
the final transform must still be attributable. A transform with no final answer is reconciled by
request and output digest before it can be retried.

## The handoff is a two-sided contract

`CreativeAssetBundle@1` carries a bundle id, revision, digest, target profile, immutable asset
manifest, semantic and spatial/temporal constraints, rights/provenance, validators, findings, and
approval. Voidlight validates that the package says what it contains; a consumer validates its own
profile before admission. Neither check writes the other's records or confers Sigils, secrets, or
effect authority. A Suite may display this typed edge, but its durable graph/run coordination never
becomes a shared Studio database.

## Gates, effects, and honest stops

Reference rights and classification are checked before use. Portal use, plan and budget, likeness
or voice, licensing, replacement of accepted material, target validation, and final handoff each
have an exact gate. Consent is scoped to the identity, intended use, territory, duration, and
revocation rule; an asset approval does not authorize a new use.

Paid generation and external handoff are effects. They carry an idempotency key and a request
digest; lost acknowledgement is **unknown**, not permission to buy or send again. Reconciliation
uses the provider or consumer result plus the exact digest. Exhausted repair, denied rights,
unmet profile, invalid source, or unresolved effect ends with a stated non-completion.

## Lifecycle and smallest proof

Studio records outlive a Run; a Graph checkpoint is not the asset ledger. Retention is selected per
reference, candidate, raw media, accepted artifact, and receipt. Export preserves permitted files,
manifests, approvals, lineage, and checksums. Deletion inventories derivatives and consumer
handoffs, asks downstream owners to take down what they own, and leaves a content-free record of
what cannot simply vanish. Parked runs retain pinned Pattern, schema, receipt, and tool revisions;
they drain, migrate explicitly, or fail honestly.

The proving slice is a local style-led 2D pack: licensed reference dossier, one style bible,
concept and sprite/texture assets, deterministic probe/normalization, one bounded repair, and an
accepted `CreativeAssetBundle@1`. It performs no engine import, channel render, Portal call, paid
effect, or public release.

Continue with [Workflow](../adr/28-workflow.md) and the [Composition portfolio](index.md).
