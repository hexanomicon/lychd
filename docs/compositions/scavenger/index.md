---
title: Scavenger
icon: material/magnify
---

# :material-magnify: Scavenger

Scavenger turns one bounded acquisition campaign through listings and sellers into an
evidence-backed decision. It scavenges a finite market; it is not [Hunter](../../sepulcher/extensions/shadow/hunter.md),
which adversarially challenges one already formed candidate.

## Contract

| Field | Reference contract |
| --- | --- |
| **Identity** | `scavenger` revision `2` |
| **Principal Pattern** | `scavenger.plan_campaign@1` |
| **Begins with** | a revisioned subject profile, concrete need, known inventory, budget, deadline, region, evidence standard, source policy, and autonomy ceiling |
| **Can return** | a durable campaign, evidence-bound shortlist, seller thread, negotiated outcome, commitment, parcel result, or diligence packet |
| **Stops before** | unbounded scraping, spam, false identity or leverage, hidden criteria changes, professional certification, unapproved commitment, payment, deposit, signature, or settlement |

Scavenger owns campaigns, criteria, observations, evidence, rankings, seller threads, offers,
commitments, parcels, inspections, and diligence packets. Scout owns bounded acquisition and
interaction receipts. The Magus owns private disclosure, final commitment, payment, acceptance,
dispute, and every property transaction.

Its Patterns are `scavenger.plan_campaign@1`, `scavenger.observe_market@1`,
`scavenger.qualify_candidate@1`, `scavenger.rank_candidates@1`, `scavenger.negotiate@1`,
`scavenger.commit@1`, and `scavenger.receive@1`.

## Open the campaign

- [Campaign](campaign.md) fixes the subject, evidence standard, budget, mode, and stopping line.
- [Market](market.md) admits finite listing evidence and produces an inspectable shortlist.
- [Bargain](bargain.md) governs seller questions, offers, disclosure, and uncertain sends.
- [Acquisition](acquisition.md) covers commitment, property diligence, parcels, inspection, and recovery.

Related: [Composition Portfolio](../index.md) · [Workflow](../../adr/28-workflow.md)
