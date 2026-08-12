---
title: Market
icon: material/storefront-outline
---

# :material-storefront-outline: Market

`scavenger.observe_market@1` admits finite source snapshots, normalizes and deduplicates listings,
and retains retrieval time and source claims. Scheduled observations coalesce instead of building
an unbounded backlog.

Each Scout profile fixes permitted origins and paths, user agent, pacing, concurrency, byte and
page caps, expiry, robots decision, selectors, session needs, CAPTCHA handling, fixtures, and a
kill switch. A `bazos.sk` adapter can observe a listing; it cannot choose the subject, pass a hard
gate, bargain by default, or own the campaign.

## Evidence before preference

`scavenger.qualify_candidate@1` applies profile hard gates first: `false` rejects, `true` admits,
and `unknown` remains visible. A model cannot invent an address, fee, area, socket, clearance,
firmware, condition, serial, stock state, or seller fact.

`scavenger.rank_candidates@1` then orders only eligible candidates from declared weights and dated
evidence:

```text
known utility = Σ(known weight × normalized preference)
lower bound   = known utility / total configured weight
upper bound   = (known utility + unknown weight) / total configured weight
```

## The whole candidate field is the review surface

The ordinary market view can teach preference without asking the Magus to leave the work and fill
an abstract training form. The whole normalized snapshot remains inspectable. Hard-false
candidates stay in an attributable rejected lane, unknowns remain visible, and eligible candidates
receive one proposed order.

The Magus may then:

- move a candidate higher or lower;
- assign a score and an application-specific state such as `contact`, `watch`, `ask`, or `reject`;
- choose a structured reason and add a short explanation;
- mark an exact region in a listing image, state what is observable there, and distinguish evidence
  from suspicion; and
- revise the judgment when a seller answer or later outcome changes the evidence.

Each explicit action appends a `CandidateJudgment@1` rather than mutating chat history. A completed
`RankingReview@1` pins the source snapshot, the system's initial order, the reviewed order, the
judged subset, unjudged candidates, and all judgment references. Scavenger may derive a
`PreferenceRevision@1` containing scoped weights, rules, examples, exceptions, provenance, and
confidence. That revision is Scavenger-owned decision memory, not general
[Archive memory](../../adr/27-memory.md) or a silent model-weight update. The next ranking pins the
exact accepted preference revision it used and explains which evidence and preference affected
each score.

Repeated review therefore stays reversible. A later revision may improve the proposed order, but
the full candidate field remains available for inspection and correction every time.

## Bazaar worked example: a daily vehicle market

A seven-day automotive Bazaar campaign can observe one finite Bazoš search each morning. The new
snapshot records newly listed, removed, relisted, repriced, reworded, and rephotographed vehicles
against the previous day. The diagnostic view shows the complete field rather than only a
shortlist.

The Magus reorders vehicles, scores them, assigns `contact`, `watch`, `ask`, or `reject`, and records
the deciding reason. On a photograph, the Magus can mark the exact region that deserves attention
and explain what should be checked. Missing VIN, service history, condition detail, photograph, or
video can become an approved question through [Bargain](bargain.md). A reply updates attributed
evidence and may change qualification, score, state, and order; it never becomes permission to buy
or negotiate outside the campaign envelope.

The next morning Scavenger proposes a new full-list order from the accepted preference revision.
The person can still move any vehicle, correct the inferred reason, or leave it unjudged. The same
review contract applies to technology, property, equipment, collectibles, and other finite markets;
the subject profile supplies the domain criteria.

## Images, messages, and learned contact style

An image judgment keeps source identity, digest, exact region, observed cue, interpretation,
confidence, and correction. A model-highlighted region is a proposal, not proof of damage,
condition, identity, or value. If source and egress policy permit it, a public listing image may be
sent to a named remote vision provider for bounded inference with provider and model provenance.
Public availability does not make the image model-training material or grant a right to republish
it.

Scavenger may also compare which already approved questions and truthful automation disclosures
produce decision-useful answers. [Bargain](bargain.md) still owns every send, limit, stop signal,
unknown acknowledgement, and seller thread. Phone numbers, private replies, credentials, and
private anchors never enter a preference revision as ambient context.

## Prove that preference learning earns its cost

The first snapshot establishes an unaided ranking baseline. Intermediate snapshots collect human
corrections. A final held-out snapshot measures whether the accepted preference revision improves:

- agreement between the proposed and reviewed order;
- the number and size of manual moves and score corrections;
- agreement on stated reasons and image regions, including calibrated uncertainty;
- the share of seller answers that materially change a candidate judgment; and
- human review time compared with the baseline.

A representative seven-day pilot can target at least 50 explicit candidate judgments and 30 to 60
image-region corrections, while each campaign declares its own evidence minimum. Continue only
when held-out ordering or decision time improves without hiding unknowns or increasing annotation
cost beyond the saved work. Otherwise retain the evidence, reject the preference revision, and
change or stop the pilot.

Price remains an attributable interval across condition, warranty, age, bundle value, fees, and
uncertainty. A route observation proves access at one time, not title, structural condition,
financing, insurance, future development, or final transaction cost.

School, work, family, health, routine, exact address, and phone data receive least-data handling.
Sources see only the coarse region, opaque anchor, or derived observation required by the admitted
step. Listings and seller claims are evidence, not preference memory or training material by
default. Only admitted human judgments and accepted application revisions enter decision memory;
changing provider model weights is a separate, explicit [Training](../../adr/33-training.md)
workflow outside this Pattern.

Continue with [Bargain](bargain.md) or end with an evidence-bound shortlist.
