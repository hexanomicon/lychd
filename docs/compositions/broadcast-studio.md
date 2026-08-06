---
title: Broadcast
icon: material/broadcast
---

# :material-broadcast: Broadcast

Broadcast turns an admitted dossier into a publication candidate whose claims, words,
voice, captions, and cuts can be traced to their source. It gives an editor enough evidence to
approve, correct, or refuse the work before any platform receives it.

!!! note "Current material"
    Broadcast is a Native Reference Composition, not an executable publishing application today.
    No Broadcast Pattern, claim ledger, narration and caption pipeline, deterministic renderer,
    platform adapter, or publication effect is registered. Bridge text and Partial Audio admission
    do not constitute this application.

[State of Work](../state-of-the-work.md#composition-portfolio-delivery) owns the delivery boundary for this reference.

## Contract

| Field | Reference contract |
| --- | --- |
| **Identity** | `broadcast.studio` revision `1` |
| **Principal Pattern** | `broadcast.build_local_package@1` |
| **Application begins with** | a frozen source dossier, editorial brief, target profile, and admitted creative assets |
| **Application can return** | local `EditorialPackage@1` and `PublicationCandidate@1`; `PublicationReceipt@1` only after a separate effect |
| **Application stops before** | unattended publication, engagement farming, borrowed asset authority, or unreviewed external egress |

Broadcast owns dossiers, source snapshots, claims, articles, scripts, storyboards, narration,
captions, timelines, local renders, publication candidates, corrections, and destination receipts.
[Voidlight](voidlight-studio.md) retains the lineage of creative source assets. A platform
adapter delivers an approved payload; it has no editorial authority.

## Dossier to local candidate

1. **Freeze the dossier.** Pin exact source snapshots, rights posture, intended audience, target,
   disclosures, and retention before claims are extracted.
2. **Build the claim ledger.** Bind each factual claim to a source span, extraction or
   interpretation status, confidence, reviewer, and every article or script object that depends on
   it.
3. **Approve the words.** Produce the canonical article and formatted scripts before narration,
   captions, or timeline assembly can conceal uncertainty.
4. **Admit creative assets.** Match each `CreativeAssetBundle@1` digest, semantic role, constraints,
   provenance, rights, validators, findings, and approval to this exact project.
5. **Assemble locally.** Create narration and a back-transcript, captions, storyboard, and an
   explicit timeline; render with pinned inputs, fonts, codecs, filters, loudness, colour settings,
   command, probes, and checksum.
6. **Review and package.** One bounded forward repair may answer a finding. The accepted result is
   a local `EditorialPackage@1` and `PublicationCandidate@1`, still without permission to publish.

The lineage remains visible from `source span → claim → article/script → narration, caption, or
storyboard → timeline → published revision`. A correction appends a corrected or withdrawn state
and stales dependants; it never rewrites the historical claim or receipt.

## Claim lineage and creative handoff

| Record or Pattern | Office |
| --- | --- |
| `CreativeAssetRequest@1` | asks for an editorial role, profile, timing, constraints, rights, likeness requirements, and request digest |
| Asset-admission receipt | records Broadcast's validation of one immutable `CreativeAssetBundle@1` |
| `broadcast.review_package@1` | returns attributed findings without changing accepted material |
| `broadcast.revise_from_correction@1` | admits a new forward correction |
| `broadcast.publish_draft@1` / `broadcast.publish_public@1` | perform separately authorized destination effects |
| `broadcast.correct_publication@1` / `broadcast.takedown@1` | correct or request removal without erasing prior history |

The handoff shares no Sigil, secret, provider session, approval, or downstream authority. Voidlight
cannot publish through an asset request, and Broadcast cannot amend Voidlight's provenance after
admitting a bundle.

## Publication gates and correction

Source rights, claim review, voice and likeness, privacy and Portal use, accessibility, asset
admission, render validation, and destination release each have an exact gate. Publication also
pins the candidate digest, audience, visibility, schedule, disclosures, and money. An ungrounded or
low-quality draft ends as a candidate, correction request, or refusal.

Rendering, draft publication, public release, correction, and takedown are separate effects. Each
uses an idempotency key, request digest, destination identity, lookup material, and receipt. Lost
acknowledgement produces an **unknown** effect; reconciliation must precede retry, and browser
automation cannot become an untyped fallback.

Restart resumes only with the pinned Pattern, dossier, handoff, timeline, renderer, adapter, and
receipt revisions. Source snapshots, rejected renders, candidates, destination receipts, and
analytics receive separate retention. Deletion inventories derivatives and requests remote
takedown while preserving a content-free receipt; it cannot promise that caches or feeds forgot a
published copy.

## Proving package

Build a three-to-five-minute local package from a small frozen dossier: source-linked claims, an
article and script, local narration with back-transcript, captions, an explicit timeline,
deterministic render, one bounded repair, and final `EditorialPackage@1` plus
`PublicationCandidate@1`. The proof makes no platform call.

Related: [Voidlight](voidlight-studio.md) · [Workflow](../adr/28-workflow.md) ·
[Audio](../adr/37-audio.md) · [Composition portfolio](index.md)
