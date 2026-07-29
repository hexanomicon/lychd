---
title: Home Seeker
icon: material/home-search
---

# :material-home-search: Home Seeker

!!! warning "Candidate study — not accepted architecture or a working property buyer"
    Home Seeker explores private, location-aware apartment search as a separate Composition.
    Current LychD has no property campaign, geocoder, route or amenity provider, cadastral
    integration, viewing workflow, professional-review path, or real-estate transaction support.
    Nothing on this page is valuation, legal, structural, mortgage, insurance, or tax advice.

The visible promise is simple:

> “Over the next three months, find me a two-room apartment below €220,000. Prefer places within
> fifteen minutes on foot of this school and a shopping centre, or reasonably positioned between
> school and work. Search daily and show exactly why every candidate ranks where it does.”

Home Seeker does not belong inside Tech Scavenger. Hardware compatibility, component tests,
parcels, and cash-on-delivery commitments have different truth and risk from title, building
condition, financing, private routines, and a life-changing property purchase.

## Candidate descriptor

| Field | Candidate value |
| --- | --- |
| Stable id / revision | `home.seeker` / `1` |
| Default manual Pattern | `home.plan_search@1` |
| Default scheduled Pattern | `home.daily_search@1` |
| Primary projection | Candidate map, hard-filter verdicts, score components and intervals, location uncertainty, shortlist, and due-diligence checklist |
| Acquisition dependency | Scout marketplace and geo-source observations under separate grants |
| Principal non-goal | Autonomous offer, viewing booking, reservation, deposit, contract, signature, settlement, or professional certification |

## Criteria are law, preference, or uncertainty

The setup separates:

- **Hard filters:** purchase or rent, property type, room count, minimum usable area, maximum
  listing or all-in price, admitted localities, deadline, required features, and
  operator-selected maximum travel times.
- **Weighted preferences:** price headroom, area fit, route time to each private anchor, access to
  selected amenity categories, position between destinations, freshness, and evidence
  completeness.
- **Uncertainty:** missing fees, incomplete address, locality-only geocode, stale route or amenity
  observation, contradictory area, and unsupported seller claims.

For a hard predicate, `false` rejects, `true` admits, and `unknown` enters review. It never passes
because a model likes the photographs.

“Near” is configured by travel mode, time window, target, and maximum duration. “Between A and B”
requires one selected meaning: minimize the worse journey, minimize total journey, minimize
imbalance, or remain near a route corridor. Straight-line distance is never presented as travel
time.

## Pattern shapes

```text
home.plan_search@1

CapturePurchaseIntent
→ NormalizeHardConstraints
→ CapturePublicAndPrivateAnchors
→ DefineTravelAndBetweenSemantics
→ ConfigureWeightsAndUnknownPolicy
→ ReviewSourcesPrivacyAndSchedule
→ CommitCampaign
```

```text
home.daily_search@1

AdmitDailyOccurrence
→ RequestPermittedPropertyObservationsFromScout
→ ValidateSourceProvenanceAndFreshness
→ EvaluateHardConstraints
→ ResolveLocationAtAvailablePrecision
→ RequestPermittedGeoObservationsFromScout
→ JoinAmenitiesAndRoutesWithoutLeakingPrivateAnchors
→ ComputeTransparentRanking
→ CommitDailyDigest
```

```text
home.prepare_due_diligence@1

LoadHumanShortlist
→ BuildViewingChecklist
→ SeparateSellerClaimsFromEvidence
→ IdentifyLegalTechnicalAndFinancialQuestions
→ RecordProfessionalReviewNeeds
→ ProduceHumanDecisionPacket
→ End
```

There is no purchase or reservation Pattern in this candidate. Messaging may be studied only
after watch-only ranking is proved; any offer, reservation agreement, deposit, mortgage,
signature, or settlement requires new law and fresh live HitL.

## Transparent ranking

Every rank pins the campaign criteria, listing observation, location resolution, geocoder, route
and amenity sources, observation times, raw measurements, transforms, weights, unknowns, score
interval, and ranking revision.

```text
eligible = all mandatory predicates are supported

known utility = Σ(known weight × normalized preference)
lower bound   = known utility / total configured weight
upper bound   = (known utility + unknown weight) / total configured weight
```

The default order is hard eligibility, location/evidence sufficiency, conservative lower bound,
then declared price and freshness tie-breakers. A model may extract an ambiguous Slovak phrase or
explain the arithmetic. It cannot invent coordinates, change weights, convert unknown into pass,
or call a neighbourhood desirable from demographic proxies.

## Location privacy and evidence

School, work, family, health, and routine anchors are sensitive. Exact private anchors remain
behind application-owned location authority. Scout source adapters, source queries, model prompts, and
ordinary traces receive only the minimum coarse region, derived route request, observation, or
opaque anchor reference needed for their admitted step.

The evidence chain remains explicit:

```text
listing observation
≠ seller claim
≠ geocoder derivation
≠ route or amenity observation
≠ official record
≠ professional verdict
```

School proximity proves only derived access to one observed place. It does not establish
enrolment, quality, safety, future operation, or suitability. Protected characteristics and
demographic proxies must not rank neighbourhoods.

A shortlist does not prove title, liens, permitted alterations, structural condition, noise,
flood exposure, future development, financing, insurance, tax, or final transaction cost. Those
questions remain separate evidence paths with qualified human review.

## Smallest proving slice

Use only fixed synthetic or reviewed fixtures:

1. one Slovak two-room campaign with a hard price ceiling, school anchor, shopping anchor, and
   explicit two-destination balancing rule;
2. Bazoš Reality fixtures containing exact-street, street-only, locality-only, ambiguous, changed,
   duplicate, and deleted listings;
3. deterministic extraction of id, rooms, price, area, raw location, and provenance;
4. an offline geocode and walking-route fixture with visible precision and uncertainty;
5. a daily digest reproducing every hard verdict, score component, interval, and caveat;
6. crash recovery without duplicate observation or notification; and
7. a human-selected shortlist and due-diligence checklist.

No live crawl, seller contact, private coordinate disclosure, legal query, viewing booking, offer,
reservation, deposit, signature, or payment belongs in this slice.

## Continue

- Read [Scout](../sepulcher/extensions/scout.md) for marketplace, map, route, and amenity
  acquisition.
- Read [Tech Scavenger](tech-scavenger.md) for the hardware sibling.
- Read [Lifestyle Steward](lifestyle-steward.md) for private-anchor and route-planning pressure.
- Return to the [Composition Portfolio](index.md).
