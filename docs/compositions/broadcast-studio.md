---
title: Broadcast Studio
icon: material/broadcast
---

# :material-broadcast: Broadcast Studio

Broadcast Studio makes a public candidate answerable to the material beneath it. A sentence,
voiceover, caption, and cut on the timeline should be traceable back to a source span—or visibly
marked as interpretation—before it is ever asked to leave the workshop.

| Maturity | Accepted Reference Composition — architecture, not delivery; [State of Work](../state-of-the-work.md) owns what runs |
| --- | --- |
| Identity | `broadcast.studio` revision `1` |
| Principal Pattern | `broadcast.build_local_package@1` |
| Local outputs | `EditorialPackage@1`, `PublicationCandidate@1`, then a `PublicationReceipt@1` only after an effect |

Broadcast owns source dossiers, claims, articles, scripts, storyboards, timelines, local candidates,
and publication receipts. [Voidlight Studio](voidlight-studio.md) owns creative source assets and
their lineage; Game Foundry owns games. A platform adapter is a replaceable delivery mechanism,
not editorial authority, and the Studio is neither engagement farm nor unattended publisher.

## The exact chain

The principal score moves a frozen dossier through a claim ledger, canonical article and formatted
scripts, an asset request/admission boundary, narration/back-transcript/captions, an explicit
timeline, deterministic render, review, and a bounded repair into a local candidate:

```text
FreezeDossier → ExtractClaims → ApproveArticleAndScripts → RequestOrAdmitAssets
→ NarrateAndBacktranscribe → Caption → AssembleTimeline → RenderLocally
→ Review → RepairOnceOrRefuse → PackageCandidate
```

The protected lineage is:

```text
source span → claim → article/script → narration/caption/storyboard → timeline → published revision
```

Claims name source, exact span, extraction/interpretation status, confidence, review, and dependent
objects. A correction appends a corrected or withdrawn state and stales its dependants; it does not
replace historical claim, article, caption, or receipt. This permits the distinct Patterns for
`broadcast.review_package@1`, `broadcast.revise_from_correction@1`,
`broadcast.publish_draft@1`, `broadcast.publish_public@1`,
`broadcast.correct_publication@1`, and `broadcast.takedown@1` to mean something different rather
than becoming one button.

## Handoffs, without borrowed authority

Broadcast may issue `CreativeAssetRequest@1` with the editorial role, target profile, timing,
constraints, rights/likeness requirements, and request digest. It admits `CreativeAssetBundle@1`
only after checking bundle id/revision/digest, semantic role, spatial/temporal constraints,
provenance/rights, validators/findings, and approval against the exact project. Its result is a
consumer admission receipt; neither side writes the other's domain truth.

| Record | Owner and use |
| --- | --- |
| Dossier, source snapshot, claim, article, script, storyboard | Broadcast editorial truth |
| Creative request and bundle-admission receipt | Broadcast's side of a typed handoff |
| Narration, back-transcript, captions, timeline, render candidate | Broadcast production truth |
| `EditorialPackage@1` / `PublicationCandidate@1` | immutable local outputs |
| `PublicationReceipt@1` | destination effect evidence, not a credential |

A Suite can retain a durable graph/run correlation and immutable handoffs, but members retain
their records, Sigils, secrets, budget judgment, gates, and effect authority. A request gives
Voidlight no authority to publish; admitting a bundle gives Broadcast no right to amend its
lineage.

## Deterministic assembly and gates

A timeline pins ordered tracks, clip ranges, transforms, transitions, captions, chapters, fonts,
credits, loudness, and output profile. Rendering pins input/timeline digests, renderer and codec
environment, filter configuration, fonts, color/audio settings, command, probe results, checksum,
and any hardware variance that prevents byte identity. Unknown completion reconciles by request
and output digest before retry.

Gates cover source rights, claim review, voice and likeness, privacy/Portal, accessibility, asset
admission, target and render validation, and fresh consent for the exact destination, visibility,
candidate digest, schedule, disclosures, and money. A low-quality or ungrounded draft ends as a
candidate or refusal. Publishing draft, public release, correction, and takedown are independent
effects: each has an idempotency key, destination/object lookup, receipt, and unknown-effect
reconciliation. Browser automation cannot become an untyped fallback or authority.

## Lifecycle and smallest proof

Durable editorial records are separate from Graph checkpoints and raw bytes. Source snapshots,
draft narration, rejected renders, candidates, remote receipts, and analytics each receive an
explicit retention rule. Exports contain permitted sources, claim ledgers, scripts, asset refs,
timelines, approvals, render facts, and checksums. Deletion inventories drafts and derivatives;
published deletion requests a remote takedown and retains a content-free receipt rather than
promising copies, caches, or feeds will vanish. Pattern, schema, handoff, timeline, renderer,
adapter, and receipt versions migrate independently; parked runs drain, explicitly migrate, or
end honestly.

The proving slice builds a three-to-five-minute source-grounded local package from a small frozen
dossier: claims, article/script, local narration with back-transcript and captions, deterministic
timeline/render, one bounded repair, and `EditorialPackage@1` plus `PublicationCandidate@1`. It makes
no platform call.

Continue with [Voidlight Studio](voidlight-studio.md), [Workflow](../adr/28-workflow.md), and the
[Composition portfolio](index.md).
