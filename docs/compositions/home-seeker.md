---
title: Home Seeker
icon: material/home-search
---

# :material-home-search: Home Seeker

Home Seeker turns a private housing brief into a reproducible shortlist whose rankings can be
explained line by line. It helps the Magus compare dated property evidence; it does not disguise a
listing, route estimate, or attractive photograph as legal, financial, or structural diligence.

!!! note "Current material"
    No Home Seeker Pattern, campaign ledger, Scout source, geocoder/router, schedule, ranking
    projection, or due-diligence packet path is registered or executable.

[State of Work](../state-of-the-work.md#composition-portfolio-delivery) owns the delivery boundary for this reference.

## Contract

| Field | Reference contract |
| --- | --- |
| **Identity** | `home.seeker` revision `1` |
| **Principal Pattern** | `home.plan_search@1` |
| **Application begins with** | A purchase or rental brief, hard criteria, weighted preferences, private anchors, deadline, source policy, and explicit travel semantics |
| **Application can return** | A durable search campaign, evidence-bound ranked digest, or human due-diligence packet |
| **Application stops before** | Contact, viewing booking, offer, reservation, deposit, signature, settlement, professional judgment, or certification |

Home Seeker owns campaign criteria, listing observations, location resolution, route and amenity
derivations, rankings, shortlists, and diligence questions. Scout and geo providers own bounded
acquisition observations; the Magus owns criteria, weights, anchor disclosure, shortlist, and every
transaction step. A Mind may extract an ambiguous phrase or explain a result, but deterministic
tools own filters, scoring, route arithmetic, freshness, and tie-breaks.

Its other Patterns are `home.daily_search@1` and `home.prepare_due_diligence@1`.

## Criteria to shortlist

1. `home.plan_search@1` records transaction type, property type, rooms, usable area, listing or
   all-in maximum, localities, deadline, required features, and selected travel-time maxima.
2. The Magus chooses how “near” is measured and what “between A and B” means: lowest worse
   journey, lowest total, lowest imbalance, or a route corridor. Straight-line distance is never
   presented as travel time.
3. `home.daily_search@1` admits permitted listing observations with source, retrieval time,
   freshness, address precision, claims, and contradictions, then applies every hard predicate.
4. For a hard predicate, `false` rejects, `true` admits, and `unknown` enters review. A model cannot
   convert an unknown address, fee, area, route, or amenity into a pass.
5. Known preferences receive non-negative weights and normalize to `[0, 1]`. The projection shows
   known utility, a conservative lower bound, an upper bound that includes unknown weight, and the
   exact revision and inputs behind the ordering.
6. The digest orders candidates by hard eligibility, location and evidence sufficiency, lower
   bound, then declared price and freshness. `home.prepare_due_diligence@1` turns a human shortlist
   into a viewing checklist, claims-versus-evidence ledger, professional needs, and questions.

The score remains inspectable:

```text
eligible      = all mandatory predicates are supported
known utility = Σ(known weight × normalized preference)
lower bound   = known utility / total configured weight
upper bound   = (known utility + unknown weight) / total configured weight
```

## Evidence and reusable acquisition

Each rank pins criteria, listing observation, location resolution, geocoder, route and amenity
sources, observation times, raw measurements, transforms, weights, ranges, unknowns, score
interval, and ranking revision. Listing claims, geocoder derivations, route observations, official
records, and professional verdicts remain separate evidence classes.

Home Seeker may reuse Scout acquisition, finite Occurrences, source snapshots, normalization,
deduplication, freshness, and explainable score machinery also used by [Tech
Scavenger](tech-scavenger.md). Property criteria and location diligence never cross into hardware
compatibility or purchase records. Revision one sends no `NegotiationMandate@1` to [Bazaar
Haggler](bazaar-haggler.md); it ends at ranking and diligence preparation.

## Private anchors and recovery

School, work, family, health, and routine anchors receive least-data handling. Prompts, traces, and
sources see only the coarse region, opaque anchor reference, or derived observation required by an
admitted step. Ranking must not use protected characteristics or demographic proxies.

A route observation proves only derived access at that time. The shortlist proves nothing about
title, liens, unauthorized alterations, structural condition, noise, flood, future development,
financing, insurance, tax, or final transaction cost. Unknowns remain visible and can stop
automatic ranking or require review.

Scheduled searches are bounded and coalesce rather than creating a backlog. Restart reuses pinned
observations and idempotency keys, producing neither duplicate observation nor notification.
Changed or missing source state parks the occurrence; it never authorizes contact or a transaction
effect.

## Proving search

Use offline Slovak fixtures for one two-room campaign with a price ceiling, school and shopping
anchors, and one explicit balancing rule. Prove exact-street through deleted listings,
deterministic extraction, offline walking and geocode uncertainty, reproducible hard verdicts and
score intervals, crash recovery without duplicates, and a human shortlist with due-diligence
questions. Include no live crawl, contact, private coordinate query, legal query, booking, offer,
reservation, deposit, signature, or payment.

Related: [Composition Portfolio](index.md) · [Workflow](../adr/28-workflow.md)
