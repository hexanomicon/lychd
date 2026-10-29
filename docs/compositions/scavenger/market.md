---
title: Market
icon: material/storefront-outline
---

# :material-storefront-outline: Market

Each morning brings a changed market: new, removed, relisted, repriced, reworded, and rephotographed candidates. The useful view shows the whole field, including the reasons some listings cannot qualify. A shortlist alone would hide the evidence needed to correct it.

`scavenger.observe_market@2` admits finite snapshots, normalizes and deduplicates listings, and preserves retrieval time and source claims. Scheduled observations coalesce rather than accumulate an endless backlog. The Scout profile fixes origins/paths, user agent, pacing, concurrency, bytes/pages, expiry, robots decision, selectors, sessions, CAPTCHA handling, fixtures, and kill switch. A `bazos.sk` adapter observes a source; the campaign decides what it means.

## Finite feed observation {#finite-feed-observation}

Scavenger revision 3 selects `scavenger.observe_market@2` with the explicit
`bazos-pc-title-link@1` profile. It accepts one complete immutable `CampaignSeed@1` and one exact
public feed declaration. The seed pins subject/profile revision, concrete need, inventory, hard
criteria, weighted preferences, budget, deadline, region, evidence standard, travel/delivery
semantics, source/disclosure policy, learning mode and a `Watch` autonomy ceiling. Admission
retains the seed before held Run publication; it does not execute `plan_campaign`.

This profile permits one bounded RSS Fetch/Extract and a local title/link projection. It admits
no model call, qualification, ranking, item acquisition, seller contact, purchase, polling or
preference learning. The source profile fixes the exact advertised Bazoš PC feed, the native RSS
media/extraction profile and finite effect ceilings. A public declaration remains an authenticated
operator assertion, not a technical proof of publicness or a reusable contact grant.

### Initial seed encoding

`CampaignSeed@1` requires every fact explicitly, including empty inventory, hard-criteria and
preference arrays. `subject_profile` is `Bazaar@1` or `Technology@1`; `need` is nonblank bounded
text. Inventory, hard criteria and preferences each permit at most 16 entries. A preference
carries nonblank `criterion` text and a nonnegative integer `weight`; this profile does not
normalize, rank or learn from it. `budget_minor` is a nonnegative integer number of EUR cents or
explicit `null` (not assessed), with `currency: EUR`. `region` is bounded nonblank text or explicit
`null`; neither unknown establishes eligibility. `deadline` carries a timezone; admission checks
its current validity without making historical seed decoding depend on wall time.

`evidence_standard` and `travel_delivery` are required nonblank descriptions, never grants.
`source_policy: admitted-public-feed-only@1`, `disclosure_policy: none`, `learning_mode: none`
and `operating_mode: Watch` close this initial profile. Need text permits 2048 UTF-8 bytes;
individual inventory/criterion/preference/evidence/travel values permit 1024 bytes and region 256.
The complete 16 KiB bound still applies. No complete seed is copied into Run or consent facts.

### Whole field and local views

Retain the response in an immutable `MarketObservation@1` owned by Scavenger. Its exact
subject/request binds the canonical seed digest, Run and selected Composition/Pattern/manifest,
source and acquisition profiles, purpose, retention profile and initial filter revision. Replaying
that exact binding resolves the same admission/result; a changed binding refuses. The first
profile allows only one pending or retained observation per selected profile database and creates
no additional Scout allowance store.

The whole field contains every item returned by the admitted bounded extraction, in source order,
including unmatched, duplicate and unjudged occurrences. Each occurrence retains an internal
identity, source ordinal, duplicate grouping, optional original plain title, inert original item
link and source-record identity. Deduplication groups exact item locators without erasing their
occurrences or query/path spelling. Missing values and unresolved facts remain visible; no
eligibility or seller judgment is inferred. This field is the finite response, not the source's
entire market.

Keep the field within the qualified RSS mechanism's limits: at most 100 observations, titles of
at most 1024 UTF-8 bytes, and links of at most 4096 bytes. The complete seed is bounded to 16 KiB
and the canonical application observation to 256 KiB. If the result overflows, refuse it whole
rather than hide items or shorten fields.

To show what the field represents, retain the requested/contacted locator, retrieval time, Scout
receipt, source/record/field digests, selected profiles, omissions, duplicate/missing counts and
declared coverage. Source dates/GUIDs alone establish neither identity nor freshness.

Only the admitted title/link field and necessary attribution survive in application custody.
Feed bodies, channel text, summaries, images, publisher dates/identifiers and separate contact
fields are discarded after transient consumption. Titles and links are deliberately retained
source claims; the profile does not promise that source text contains no personal information.
Run/Graph state, generic events/logs and Bridge history carry opaque references, safe counts/status
and closed reasons, never item values or a copied campaign seed. Scout retains its independently
owned contact attribution and positively selected extraction metadata, not this field.

An authorized read returns the complete field. A bounded literal, versioned case-folded substring
filter over retained title/link values derives a local view of that same field digest. It is not
regex, semantic ranking or qualification. The view reports total, visible, unmatched, duplicate
and missing counts and keeps an all-observations view available. A new filter changes no field
and performs no acquisition. Read and re-filter require current application retrieval authority;
a receipt or opaque UUID supplies neither.

### Retention, deletion and recovery

Retain this one field until its owner explicitly deletes it. Deletion is a distinct current-authority
operation over the exact observation identity/digest, available only after acquisition and result
disposition are proved terminal. Pending work must be cancelled through the Run owner first;
unknown acquisition cannot be declared settled by deletion. The first profile supplies no
automatic unknown-attempt reconciliation.

Once terminal disposition permits deletion, atomically remove the application seed, item payload
and content projections. Keep only a content-free tombstone and necessary immutable execution/
Scout receipts, whose contact metadata is not erased. The tombstone fences late writes and exact
replay so neither can recreate the payload. Report deletion distinctly from an empty market and
do not imply backup erasure.

Reopening the application slot does not reset spent counters, unknown reservations or an issued
claim. To replace an observation, visibly delete it and obtain a fresh request and consent.

Recovery depends on whether acquisition has been claimed. Before claim, the exact retained
consent may resume under current authority and expiry. After claim or an uncertain acknowledgement,
lost transient material cannot be reconstructed or refetched.

After current CONSUME and result-adoption checks, commit the entire consumer field once, atomically
under its request/claim identity. If settlement has no confirmed consumer commit, return material
unavailable unless that same key proves a committed result. Reconcile a lost commit acknowledgement
against the same key/digest; ambiguity remains unknown and creates no acquisition. Once committed,
the field supports fresh authorized reads/re-filters after restart. Once deleted, that identity
stays deleted.

The first native profile uses one active Scout binding in a fresh profile database. Existing page
budget rows refuse a page/RSS switch or coexistence without mutation. This is an explicit initial
compatibility boundary, not a reset, migration or second budget store.

The Altar presents source/time/coverage, omissions, total/filtered counts, complete title/link rows,
unknown/refused/deleted states and distinct new-fetch, local-filter and terminal-delete actions.
Item links remain displayed data, with no automatic preview/contact. The native source and
[State](../../state-of-the-work.md#composition-portfolio-delivery) must prove these operations before
the interface can claim they are available.

## Evidence before preference

`scavenger.qualify_candidate@1` applies hard gates: `false` rejects, `true` admits, and `unknown` stays visible. No model may invent an address, fee, area, socket, clearance, firmware, condition, serial, stock, or seller fact. Only eligible candidates enter the proposed order from `scavenger.rank_candidates@1`:

```text
known utility = Σ(known weight × normalized preference)
lower bound   = known utility / total configured weight
upper bound   = (known utility + unknown weight) / total configured weight
```

These bounds assume finite, nonnegative configured weights with a positive total, and preference values normalized to `[0, 1]`. They apply only when the selected profile establishes those conditions. Here, unknown weight is the configured preference weight whose candidate value is still unknown. The lower bound counts only known utility; the upper bound shows the contribution those unresolved preferences could still make. Neither bound changes hard eligibility.

Price itself remains an attributable interval across condition, warranty, age, bundle value, fees, and uncertainty. A route observation proves access at one time, not title, structural condition, financing, insurance, development, or final transaction cost.

## The whole candidate field is the review surface

The Magus can move a candidate, score it, assign `contact`, `watch`, `ask`, or `reject`, choose a reason, and explain a judgment. A marked image region keeps observable evidence separate from suspicion. Later seller answers or outcomes can revise the judgment.

Each action appends `CandidateJudgment@1`. `RankingReview@1` seals the snapshot, original system order, reviewed order, judged subset, unjudged candidates, and judgment references. Hard-false candidates remain in a rejected lane; unknowns and unjudged material remain inspectable.

A derived `PreferenceRevision@1` may contain scoped weights, rules, examples, exceptions, provenance, and confidence. It is Scavenger decision memory, separate from [Archive](../../adr/27-memory.md) and model weights. The next ranking pins the accepted revision and explains which evidence and preferences affected each score. The person can still correct any candidate or inferred reason.

## Bazaar worked example: a daily vehicle market

A seven-day automotive campaign observes one finite Bazoš search each morning. The diagnostic view retains all changes from yesterday. The Magus reorders vehicles, scores them, marks image regions worth checking, and chooses what to contact, watch, ask, or reject.

A missing VIN, service history, condition detail, photo, or video can become an approved [Bargain](bargain.md) question. Its reply updates attributed evidence and may change qualification and order. It cannot authorize purchase or widen negotiation. Tomorrow's order uses the accepted preference revision; today's rejected and unjudged cars remain available for inspection. Technology, property, equipment, collectibles, and other finite markets use the same review contract with their own subject criteria.

## Images, messages, and learned contact style

For an image judgment, retain the source identity/digest, region, observed cue, interpretation, confidence, and correction. This keeps a model's suggested inspection region separate from proof of damage, identity, condition, or value. Eligible public listing images may go to a named remote vision provider only under an exact source/egress policy, for bounded inference with provider/model provenance. Public availability grants no training or republication rights.

Already approved questions and truthful automation disclosures can be compared for decision-useful answers. Bargain still owns every send, limit, stop signal, uncertain acknowledgement, and seller thread. Phone numbers, private replies, credentials, and private anchors never enter a preference revision as ambient context.

## Prove that preference learning earns its cost

Take the first snapshot as an unaided baseline, collect intermediate corrections, and test the accepted revision on a held-out final snapshot. Measure order agreement, manual move/score correction effort, reason and image-region agreement with calibrated uncertainty, seller answers that change judgments, and human review time.

A representative seven-day pilot may target at least 50 explicit candidate judgments and 30 to 60 image-region corrections; the campaign declares its own minimum. Continue only when held-out ordering or decision time improves without hiding unknowns or spending more annotation effort than it saves. Otherwise retain the evidence, reject the revision, and change or stop the pilot.

School, work, family, health, routine, exact address, and phone data receive least-data treatment. Sources receive only the needed coarse region, opaque anchor, or derived observation. Listings and replies remain evidence; only admitted human judgments and accepted application revisions enter decision memory. Model-weight changes require a separate [Training](../../adr/33-training.md) admission and promotion.

Continue with [Bargain](bargain.md), or finish with the evidence-bound shortlist.
