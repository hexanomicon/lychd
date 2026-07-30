---
title: Home Seeker
icon: material/home-search
---

# :material-home-search: Home Seeker

**Candidate question:** can a private, location-aware search rank property evidence transparently
without pretending to perform legal, financial, structural, or transaction diligence?

> “Over the next three months, find me a two-room apartment below €220,000. Prefer places within
> fifteen minutes on foot of this school and a shopping centre, or reasonably positioned between
> school and work. Search daily and show exactly why every candidate ranks where it does.”

| Local maturity | Identity | Patterns | Never does |
| --- | --- | --- | --- |
| **Unaccepted candidate study** | `home.seeker/rev1` | `home.plan_search@1`, `home.daily_search@1`, `home.prepare_due_diligence@1` | contact, book, offer, reserve, deposit, sign, settle, or certify |

## Criteria before photographs

Hard filters cover purchase/rent, property type, rooms, usable area, listing/all-in maximum,
localities, deadline, required features, and selected travel-time maxima. Preferences weight price
headroom, area fit, access to each private anchor/amenity, a chosen between-destinations rule,
freshness, and evidence completeness. Uncertainty includes fees, address precision, stale routes
or amenities, contradictory area, and unsupported claims.

For a hard predicate, `false` rejects, `true` admits, and `unknown` enters review—not a pass
because a model likes the photographs. “Near” pins mode, time window, target, and maximum
duration. “Between A and B” chooses one meaning: lowest worse journey, lowest total, lowest
imbalance, or route corridor. Straight-line distance is never presented as travel time.

## Three small scores

```text
home.plan_search@1: intent → constraints → private/public anchors → travel/between semantics
                    → weights + unknown policy → source/privacy/schedule review → campaign

home.daily_search@1: occurrence → permitted property observations → provenance/freshness
                     → hard checks → available-precision location → permitted geo observations
                     → derived routes/amenities without anchor leak → ranking → digest

home.prepare_due_diligence@1: human shortlist → viewing checklist → claims versus evidence
                              → legal/technical/financial questions → professional needs → packet
```

Each rank pins criteria, listing observation, location resolution, geocoder/route/amenity sources,
times, raw measurements, transforms, weights, ranges, unknowns, score interval, and ranking
revision. Every preference has a non-negative weight and normalization to `[0, 1]`:

```text
eligible      = all mandatory predicates are supported
known utility = Σ(known weight × normalized preference)
lower bound   = known utility / total configured weight
upper bound   = (known utility + unknown weight) / total configured weight
```

Order by hard eligibility, location/evidence sufficiency, conservative lower bound, then declared
price and freshness tie-breakers. A model can extract an ambiguous Slovak phrase or explain
arithmetic; it cannot invent coordinates, adjust weights, turn unknown into pass, or rank a
neighbourhood through protected characteristics or demographic proxies.

## Keep the anchors private

School, work, family, health, and routine anchors receive least-data handling. Sources, prompts,
and traces get only a coarse region, derivation, observation, or opaque anchor reference needed
for the admitted step. The evidence chain is explicit:

```text
listing observation ≠ seller claim ≠ geocoder derivation
≠ route/amenity observation ≠ official record ≠ professional verdict
```

School access proves only the derived access observed then. A shortlist proves neither title,
liens, alterations, structural condition, noise, flood/future development, financing, insurance,
tax, nor final transaction cost. Those need other evidence and qualified human review.

## Smallest proof

Use offline Slovak fixtures only: one two-room campaign with price ceiling, school/shop anchors,
and explicit balancing rule; exact-street through deleted listings; deterministic extraction;
offline walking/geocode fixtures with visible uncertainty; a daily digest reproducing hard
verdicts, components, intervals, and caveats; crash recovery without duplicate observation or
notification; and a human shortlist/due-diligence checklist. No live crawl/contact/private
coordinate/legal query/booking/offer/reservation/deposit/signature/payment enters the proof.

Return to the [Composition Portfolio](index.md).
