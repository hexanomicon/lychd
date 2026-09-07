---
title: Market
icon: material/storefront-outline
---

# :material-storefront-outline: Market

Each morning brings a changed market: new, removed, relisted, repriced, reworded, and rephotographed candidates. The useful view shows the whole field, including the reasons some listings cannot qualify. A shortlist alone would hide the evidence needed to correct it.

`scavenger.observe_market@1` admits finite snapshots, normalizes and deduplicates listings, and preserves retrieval time and source claims. Scheduled observations coalesce rather than accumulate an endless backlog. The Scout profile fixes origins/paths, user agent, pacing, concurrency, bytes/pages, expiry, robots decision, selectors, sessions, CAPTCHA handling, fixtures, and kill switch. A `bazos.sk` adapter observes a source; the campaign decides what it means.

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

An image judgment binds source identity/digest, region, observed cue, interpretation, confidence, and correction. A model highlight proposes a place to inspect; it proves no damage, identity, condition, or value. Eligible public listing images may cross an exact source/egress policy to a named remote vision provider for bounded inference with provider/model provenance. Public availability grants neither training nor republication rights.

Already approved questions and truthful automation disclosures can be compared for decision-useful answers. Bargain still owns every send, limit, stop signal, uncertain acknowledgement, and seller thread. Phone numbers, private replies, credentials, and private anchors never enter a preference revision as ambient context.

## Prove that preference learning earns its cost

Take the first snapshot as an unaided baseline, collect intermediate corrections, and test the accepted revision on a held-out final snapshot. Measure order agreement, manual move/score correction effort, reason and image-region agreement with calibrated uncertainty, seller answers that change judgments, and human review time.

A representative seven-day pilot may target at least 50 explicit candidate judgments and 30 to 60 image-region corrections; the campaign declares its own minimum. Continue only when held-out ordering or decision time improves without hiding unknowns or spending more annotation effort than it saves. Otherwise retain the evidence, reject the revision, and change or stop the pilot.

School, work, family, health, routine, exact address, and phone data receive least-data treatment. Sources receive only the needed coarse region, opaque anchor, or derived observation. Listings and replies remain evidence; only admitted human judgments and accepted application revisions enter decision memory. Model-weight changes require a separate [Training](../../adr/33-training.md) admission and promotion.

Continue with [Bargain](bargain.md), or finish with the evidence-bound shortlist.
