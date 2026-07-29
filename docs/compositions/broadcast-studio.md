---
title: Broadcast Studio
icon: material/broadcast
---

# :material-broadcast: Broadcast Studio

!!! warning "Accepted architecture — not a delivered publisher"
    Broadcast Studio is an accepted Reference Composition. LychD does not currently ship its
    Pattern pack, source and claim schemas, editorial workspace, render environment, platform
    adapters, Suite registry, or publication reconciliation. [State of
    Work](../state-of-the-work.md) remains the delivery authority.

**Broadcast Studio** turns an approved source dossier and immutable creative assets into
source-grounded articles, scripts, podcasts, videos, captions, and platform-specific publication
candidates. It owns editorial truth from source to public claim; the Magus remains editor and
publisher.

Broadcast does not generate every asset itself. [Voidlight Studio](voidlight-studio.md) owns
creative development and returns a typed immutable `CreativeAssetBundle@1`. Broadcast verifies that
bundle against the editorial purpose, places accepted assets into a deterministic timeline, and
owns the resulting publication package. Platform-specific delivery enters through replaceable
adapters; model choices enter through Runes. Neither becomes the Composition's identity.

## Composition descriptor

| Field | Accepted design value |
| --- | --- |
| Stable id / revision | `broadcast.studio` / `1` |
| Specification owner | `project:lychd`; a future executable contribution may be `extension:broadcast` |
| Maturity / support | Accepted architecture-only Reference Composition; unsupported |
| Purpose | Build, review, render, and deliberately publish attributable editorial packages |
| Default manual Pattern | `broadcast.build_local_package@1` |
| Principal Suite | `voidlight.broadcast-suite` |
| Primary projection | Future Loom editorial board, timeline, review, and publication receipts |
| Provider binding | Operator-owned Runes selected by capability |
| Principal non-goal | Unattended public posting or engagement farming |

The descriptor advertises Pattern ids, typed handoff ports, policy demand, and safe projection
metadata. It does not embed credentials, schedules, channel ids, model names, personal voice
fixtures, or mutable platform settings.

## The Broadcast Suite

Suites are selected by intent rather than defined by one permanent nesting tree.
`voidlight.broadcast-suite` is the accepted operator-visible graph for turning creative assets
into source-grounded media:

```mermaid
flowchart LR
    B["Broadcast Studio<br/>sources, claims, editorial package, publication"] -->|CreativeAssetRequest@1| V["Voidlight Studio<br/>creative development and immutable assets"]
    V -->|CreativeAssetBundle@1| B
    B -->|Campaign or trailer brief| V
```

A **Suite** is a typed graph and shared Loom navigation over several independently owned
Compositions. It explains related applications and their admissible handoffs. It is not a
super-Composition, ambient authority bundle, shared database, or hidden workflow engine.

Today the arrows mean explicit artifact handoff between separately admitted Invocations. A
Broadcast run may emit a `CreativeAssetRequest@1`, stop or park at a declared boundary, and later
admit an immutable Voidlight result by digest. Drawing the Compositions in one Loom frame does
not call one Pattern from another, inherit consent, share a model lease, or make failure atomic
across them.

A content Intent may let the **Call**—the Manas correspondence—open eligible Composition and
handoff routes, then produce an attributable inert **charcoal** Suite draft. The Call is not a
literal routing service and does not establish truth, authority, or executability. Deterministic
validation, reviewers operating in the office of the **Blade**, and the Magus must cut or refine
the candidate; Weaver alone may validate and admit a resulting immutable Suite descriptor under
its law.

A future governed Suite execution could admit and observe an end-to-end run only after
[Weaver law](../adr/28-workflow.md) defines nested or callable Pattern identity, typed cut sets,
effect ownership, cancellation, Stasis, resume, and checkpoint compatibility. Until then,
Suite-level orchestration remains an explicit sequence of ordinary Invocations and receipts.

## Visible outcome and non-goals

One successful local build should yield a versioned publication package containing:

- frozen source snapshots and a claim ledger;
- an approved canonical article and one or more derived scripts;
- storyboard, audio rundown, social cut plan, and explicit asset requirements;
- admitted immutable creative assets with rights and derivation receipts;
- narration, captions, transcript, chapters, credits, citations, thumbnails, and descriptions;
- deterministic editorial timelines and probed article, audio, and video outputs;
- bounded factual, editorial, accessibility, technical, and rights review findings; and
- draft or public publication candidates without silently publishing them.

The initial Composition is not a newswire, autonomous content farm, synthetic popularity engine,
copyright-clearing oracle, moderation bypass, credential store, comment bot, or guarantee that a
platform will accept or retain an upload. Publication, correction, takedown, and community
interaction remain distinct effects with distinct authority.

## Ownership

| Concern | Owner |
| --- | --- |
| Commission, Pattern revision, admission, logical schedule, dependency, and budget | Weaver |
| Source acquisition and public-web policy | Scout through typed source tools |
| Source snapshots, claim ledger, article, script, storyboard, timeline, review, and publication schemas | Future Broadcast application owner |
| Creative direction, asset generation or admission, asset lineage, and `CreativeAssetBundle@1` | Voidlight Studio |
| Game integration, playable builds, captures, playtests, and game release | [Game Foundry](game-foundry.md) |
| Model-capability selection | Dispatcher and operator-owned Runes |
| Model readiness, leases, placement, and unload | Orchestrator |
| Immutable media bytes and manifests | Reliquary-backed artifact custody |
| Run, approval, effect, and reconciliation receipts | Phylactery |
| Platform credentials and secrets | Ward |
| Editorial truth, voice or likeness consent, channel identity, and public release | Magus through HitL |
| Composition, Pattern, Suite, timeline, review, and receipt projection | Loom |

Broadcast may reference Voidlight artifacts by immutable digest and declared manifest revision. It
does not mutate Voidlight's accepted asset, rewrite its generation history, or infer missing
rights. Editorial placement, crop, mix, caption, and export create Broadcast-owned derived
artifacts with parent lineage.

## Pattern catalogue

### `broadcast.build_local_package@1`

```text
AdmitCommission
→ FreezeSourceDossier
→ ExtractSourceEvidence
→ BuildClaimLedger
→ DraftCanonicalArticle
→ VerifyArticleClaims
→ DeriveFormatScripts
→ AwaitEditorialApproval
→ BuildStoryboardAndRundown
→ ResolveCreativeAssets
→ AdmitCreativeAssetBundleV1
→ RecordNarration
→ BackTranscribeAndAlign
→ AssembleExplicitTimelines
→ RenderLocalPackage
→ ReviewPackage
→ RepairOnce?
→ SealPublicationCandidate
→ End
```

The graph is finite. One optional repair pass receives a frozen finding set, affected artifact
ids, and a bounded budget. Unsupported claims, absent rights, failed accessibility checks, or
unreconciled render effects end in truthful non-completion or a Magus decision rather than an
unbounded self-review loop.

`ResolveCreativeAssets` may reuse an already approved bundle or emit a typed
`CreativeAssetRequest@1`. It does not implicitly invoke Voidlight. If new creative work is needed,
an explicit Voidlight Invocation produces the bundle and a later Broadcast Invocation or declared
resume boundary admits it.

### Independent Patterns

| Pattern | Purpose | Effect class |
| --- | --- | --- |
| `broadcast.review_package@1` | Re-evaluate an immutable package against a pinned rubric | Read-only plus review artifacts |
| `broadcast.revise_from_correction@1` | Amend a source or claim and invalidate affected derivations | New local revision |
| `broadcast.publish_draft@1` | Create or reconcile a private, unlisted, scheduled, or platform draft | External effect; exact approval |
| `broadcast.publish_public@1` | Make one exact candidate public on declared destinations | High-consequence external effect; fresh live approval |
| `broadcast.correct_publication@1` | Publish a correction or replacement with explicit lineage | External effect; fresh live approval |
| `broadcast.takedown@1` | Remove owned remote objects where the platform permits it | Destructive external effect; fresh live approval |

A single approval does not authorize the whole catalogue. A local package approval does not
authorize upload; a draft approval does not authorize public visibility; one platform approval
does not authorize every configured destination.

## Editorial truth and claim lineage

The source dossier freezes exact operator-provided or lawfully acquired inputs before drafting.
Each source record includes content digest, origin, acquisition time, author or publisher when
known, publication time when known, source class, license or use basis, excerpt map, and
availability state. A URL alone is neither a snapshot nor evidence that use is permitted.

The claim ledger records:

- stable claim id and normalized wording;
- exact supporting or contradicting source spans;
- factual, attributed-opinion, synthesis, prediction, or creative framing class;
- support status, uncertainty, reviewer, and last verification time;
- article, script, narration, caption, chapter, scene, thumbnail, and description references; and
- stale, corrected, withdrawn, or disputed state without erasing history.

```text
frozen source span → claim → article span → format script beat
                   → narration/transcript/caption span
                   → storyboard beat → timeline range → published object revision
```

Article prose is canonical for an essay commission. Podcast and video scripts may adapt delivery
but cannot silently strengthen claims. Social captions and thumbnails are editorial objects too:
their compressed form does not exempt them from claim, disclosure, rights, or correction law.
Changing a source or claim marks every dependent object stale and produces a new revision; it
never mutates the prior public record.

## Typed Suite handoffs

### `CreativeAssetRequest@1`

The Broadcast-owned request contains an immutable request id, editorial package revision,
storyboard beat ids, required media roles, dimensions or duration, safe text and reference
artifacts, style constraints, prohibited content, rights target, territory, platform classes,
privacy ceiling, generation budget, and due boundary. It contains no publishing secret or ambient
permission to inspect the Broadcast project.

### `CreativeAssetBundle@1`

Voidlight owns the bundle schema and returns, at minimum:

- immutable bundle id, schema revision, manifest digest, and parent request id;
- accepted asset ids and content digests with media probes;
- source, license, consent, model, prompt, seed, provider, edit, and derivation receipts as
  applicable;
- declared permitted and prohibited uses, territory, attribution, expiry, and takedown hooks;
- rejected or omitted requirements and unresolved rights or quality findings; and
- safe preview projection separate from full private bytes.

Broadcast admits the whole manifest against its request and target destinations. A missing,
ambiguous, expired, or incompatible permission fails closed. The language model cannot “reason”
an absent license or likeness consent into existence.

### Broadcast outputs

`EditorialPackage@1`, `PublicationCandidate@1`, and `PublicationReceipt@1` are distinct immutable
objects. A candidate names exact article, audio, video, metadata, destination, visibility,
schedule, adapter revision, and content digests. A receipt records the idempotency key, remote
account and object ids, final visibility, platform response, timestamps, and reconciliation
state. Receipts never contain raw credentials.

## Deterministic assembly

Generative and editorial decisions may be stochastic; final assembly must be explicit. Each
timeline records ordered tracks, clips, source ranges, transforms, transitions, captions,
chapters, loudness targets, fonts, credits, and output profiles. The authoritative render pins:

- artifact digests and immutable timeline revision;
- renderer and codec build or container digest;
- filter graph, fonts, color and audio settings, stream map, and command;
- output probe, checksum, duration, dimensions, codecs, and loudness measurements; and
- non-deterministic inputs or hardware differences that prevent byte-identical reproduction.

A failed render never promotes a partial file. Unknown render completion is reconciled by output
digest and effect receipt before retry. Podcast feeds, article HTML or Markdown, captions, and
platform metadata are rendered from versioned templates and schemas rather than copied from an
untracked model response.

## Capability, provider, and adapter boundaries

Broadcast declares semantic requirements such as structured drafting, source comparison,
multimodal review, local transcription, forced alignment, narration, image inspection, and
typed tool execution. Runes bind eligible local Soulstones or opted-in Portals. A Pattern never
identifies itself as Qwen, Gemma, Whisper, or another provider, and switching an eligible model
does not change editorial ownership.

Deterministic typed tools may include:

| Family | Example contract |
| --- | --- |
| Sources | `source.acquire`, `source.snapshot`, `source.extract` |
| Evidence | `claim.validate`, `citation.resolve` |
| Media | `media.probe`, `audio.align`, `image.inspect` |
| Assembly | `article.render`, `timeline.render`, `caption.mux`, `feed.render` |
| Platform effects | `platform.create_draft`, `platform.publish`, `platform.correct`, `platform.remove` |

Platform adapters are separate from model providers and from the editorial core. A YouTube
adapter knows upload sessions, visibility, playlists, chapters, thumbnails, processing state, and
remote ids. An RSS host adapter knows feed and enclosure rules. A site or CMS adapter knows draft
and revision semantics. A social adapter knows that destination's media, text, disclosure,
scheduling, and deletion contract.

Every adapter pins its origin, API and schema revision, eligible account, terms and policy research
date, rate and size limits, idempotency strategy, reconciliation lookup, and fixtures. Browser
interaction is not a universal fallback: it requires an admitted Scout interaction policy,
authorized session, stable typed effect, and current conformance evidence. No adapter bypasses
rate limits, access controls, platform safeguards, disclosure rules, or account restrictions.

## Rights, safety, privacy, and consent

Required gates include:

1. source acquisition and quoted-material review;
2. unsupported, disputed, sensitive, or high-impact claim review;
3. explicit Portal egress for private sources or media;
4. voice, likeness, trademark, music, font, footage, and generated-asset rights;
5. editorial and storyboard approval before expensive creation;
6. acceptance of the exact `CreativeAssetBundle@1`;
7. final factual, accessibility, technical, and destination-policy review;
8. exact draft or public publication approval; and
9. correction, replacement, or takedown approval.

Synthetic voices or likenesses require attributable consent scoped to identity, use, territory,
duration, and revocation behavior. A valid asset consent does not authorize a new political,
sexual, medical, deceptive, or reputation-sensitive context. Private sources, unpublished media,
credentials, analytics, audience identities, and personal voice fixtures carry separate
classification and retention.

Public publishing always presents the exact candidate, destination accounts, visibility,
scheduled time, money, disclosures, rights findings, and immutable digests to HitL. Retries
reconcile by destination and idempotency key; acknowledgement loss never permits a duplicate post.
Autonomous engagement, impersonation, astroturfing, purchased attention, or manipulation of
platform metrics is outside the Composition.

## Work policy, budgets, and Loom

| Work class | Target priority | Overlap and preemption |
| --- | ---: | --- |
| Cancel, correction, takedown, or safety intervention | `100` | Explicit break-glass path; reconcile effects first |
| Interactive editing and review | `70` | One editor per package revision; stop after an atomic save |
| Commissioned build and render | `50` | Queue by package revision; preempt after accepted artifact or effect receipt |
| Proxies, transcription indexes, and archive preparation | `20` | Coalesce or skip; never force disruptive residency |

Every Pattern declares ceilings for source bytes, model calls, tokens, generated assets, audio or
video minutes, render wall time, storage, Portal spend, platform effects, retries, and repair
passes. Reaching a limit parks for an explicit scope change or ends truthfully. A schedule may
refresh sources, prepare proxies, or build an already approved local package; it may never
schedule public publication.

The future Loom projects:

- `voidlight.broadcast-suite` as a navigable graph of Compositions and typed handoffs;
- Broadcast Pattern families and exact immutable revisions;
- source and claim support, stale derivations, rights, budgets, gates, and review findings;
- storyboard, asset request, admitted bundle, timeline, render, and publication receipts; and
- safe remote-object status and correction or takedown options.

Loom reads registered descriptors and durable evidence. It does not infer a Suite by scanning
folders, make a canvas group executable, expose private source bytes, or turn a visible
publication button into authority.

## Data lifecycle and recovery

- **Durable owner:** the future Broadcast application owns commission, dossier, claim, article,
  script, storyboard, timeline, review, approval, candidate, destination, and publication
  schemas. Reliquary owns immutable bytes; checkpoints are not the editorial database.
- **Versioning:** application schema, Pattern revision, handoff schema, render environment,
  platform adapter, template, and provider receipt are versioned independently.
- **Retention:** the Magus configures source, draft, rejected render, raw narration, analytics,
  remote receipt, and final package retention within source, platform, and rights constraints.
- **Export:** an export includes permitted source snapshots, claims, editorial objects, timelines,
  creative bundle references, manifests, approvals, render facts, publication receipts, and
  checksums.
- **Deletion:** unpublished deletion inventories derived bytes and remote drafts. Published
  deletion needs explicit remote takedown and a content-free receipt; it cannot promise deletion
  of copies, caches, quotations, feeds, or archives outside the account's control.
- **Recovery:** accepted immutable artifacts and manifests allow assembly to resume without
  regenerating assets. Unknown platform effects reconcile by remote object id or idempotency key.
- **Compatibility:** parked runs remain pinned to Pattern, handoff, checkpoint, adapter, and
  manifest revisions. Incompatible changes drain, explicitly migrate, or fail honestly.

## Adversarial conformance cases

The first implementation must prove refusal and recovery for at least:

- a source URL whose content changes after the dossier is frozen;
- a model draft that invents support or strengthens a qualified claim;
- a social caption or thumbnail that contradicts the approved article;
- a creative bundle with a missing parent request, digest mismatch, expired license, or absent
  likeness consent;
- a stale asset after a claim correction;
- malformed captions, clipped narration, missing credits, or a non-conforming output probe;
- a platform timeout after remote creation but before the local acknowledgement;
- a duplicate publish request with a changed visibility or artifact digest;
- a credential or private source accidentally proposed for model or Loom projection;
- a schedule attempting public publication;
- a Suite drawing interpreted as permission to invoke another Composition; and
- a parked Invocation resumed under an incompatible Pattern or handoff revision.

## Smallest proving slice

The first useful slice is one source-grounded three-to-five-minute essay package, built locally:

1. freeze three to five operator-approved sources;
2. produce a claim ledger, canonical article, short narration script, and approved storyboard;
3. admit one small prebuilt `CreativeAssetBundle@1` from Voidlight by manifest and digest;
4. record or synthesize narration, back-transcribe it, and derive accessible captions;
5. assemble one explicit still-image video timeline and one podcast audio export;
6. render article, audio, video, thumbnail, description, chapters, citations, and credits;
7. run one bounded factual, rights, accessibility, audio, visual, and technical review pass; and
8. seal a local `PublicationCandidate@1` without contacting any platform.

This proves the Composition boundary, editorial lineage, typed Suite handoff, deterministic
assembly, and recovery before account credentials or irreversible public effects obscure the
harder law.

## Staged roadmap

1. **Schemas and fixtures:** dossier, claim, editorial, storyboard, timeline, review, candidate,
   handoff, and receipt corpora with Slovak and English examples.
2. **Local article and podcast:** deterministic text/audio packages, transcript, captions,
   citations, credits, export, and deletion.
3. **Voidlight handoff:** `CreativeAssetRequest@1` and `CreativeAssetBundle@1` conformance,
   rights validation, invalidation, and recovery.
4. **Still-video assembly:** explicit timeline, thumbnail, chapters, pinned render environment,
   output probes, and one bounded review pass.
5. **Loom board and Suite projection:** source-to-claim view, editorial board, handoff state,
   timeline, findings, budgets, and safe receipts.
6. **Draft adapters:** one platform at a time with current policy fixtures, exact account scope,
   idempotency, processing-state reconciliation, and remote draft cleanup.
7. **Public publication:** separate fresh approval, correction, replacement, takedown, and
   cross-destination partial-failure handling.
8. **Additional formats:** motion assets, interviews, episodic podcasts, feeds, localized
   derivatives, trailers, and game-build captures without weakening source or rights law.
9. **Governed Suite execution:** only after Weaver accepts callable Pattern and cross-Composition
   continuity law; never inferred from Loom layout.

## Current delivery gaps

Core currently proves neither a Composition or Suite registry nor Broadcast schemas, typed
cross-Composition handoffs, source/claim lineage, creative-bundle conformance, deterministic
publication manifests, editorial Loom surfaces, platform adapters, or publication reconciliation.
The existing Pattern registry, durable consent boundary, capability grants, artifact concepts,
and static Loom topology are useful substrate, not a working Broadcast Studio.

## Continue

- Return to the [Composition Portfolio](index.md).
- Enter [Voidlight Studio](voidlight-studio.md) for creative asset production.
- Enter [Game Foundry](game-foundry.md) for game integration, builds, and playtests.
- Read [Weaver](../sepulcher/extensions/weaver.md) and [Workflow](../adr/28-workflow.md) before
  treating a Suite handoff as runtime behavior.
- Read [HitL](../adr/25-hitl.md) before adding any publication, correction, or takedown effect.
