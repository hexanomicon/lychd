---
title: Campaign
icon: material/compass-outline
---

# :material-compass-outline: Campaign

Before opening a listing, decide what an acquisition would accomplish and how far this campaign may go. `scavenger.plan_campaign@1` pins the desired result, existing inventory, hard criteria, weighted preferences, budget, deadline, region, evidence tier, travel/delivery semantics, disclosure policy, and operating mode.

The revision-3 [finite feed observation](market.md#finite-feed-observation) also accepts a
complete immutable campaign seed directly. Its admission retains and validates those facts before
publishing the held Run; it neither invokes `plan_campaign` nor fabricates a completed planning
Run. Missing budget, deadline, region or policy is not inferred. Explicit empty or not-assessed
values are permitted only by the seed schema and establish no suitability or eligibility.

## Subject profiles

| Profile | Evidence and judgment | Revision-one consequence |
| --- | --- | --- |
| **Bazaar** | Item identity, condition, attributed seller claims, landed cost and bounded bargaining for Bazoš-style listings. | Terms, one approved cash-on-delivery (COD) commitment, parcel inspection, dispute or refusal. |
| **Technology** | Exact CPU, board, BIOS, cooling, memory, GPU, storage, case, PSU, firmware and connector compatibility. | Bazaar consequence after fresh compatibility and evidence checks. |
| **Property** | Transaction type, area, rooms, locality, route/amenity observations, contradictions and professional questions. | Shortlist and diligence only: no contact, viewing, offer, reservation, deposit, signature or payment. |

Choose these versioned Scavenger rules according to the subject being acquired. Technology may refine Bazaar, while property rules cannot silently become parcel or hardware judgment. Selecting a profile creates neither a Composition nor a source adapter, and supplies no source, credential, private anchor, money, or effect authority.

`Watch` observes and reports. `Concierge` prepares questions and offers for review. `Bounded Autopilot` acts only within its fully pinned envelope. Changing subject, ceilings, permitted disclosure, payment rail, evidence requirement, or deadline creates a successor campaign revision.

## Preference within the boundary

A candidate may meet every hard gate and still be unattractive to the buyer. `PreferenceRevision@1` can refine that soft ordering while retaining the reviewed field, admitted judgments, scope, provenance, and predecessor. It cannot repair a failed hard gate, widen budget or authority, change disclosure, or rewrite earlier rankings.

Before the next observation uses a reviewed preference revision, check the campaign's declared learning mode. If that mode does not allow activation, keep the revision as a proposal awaiting explicit acceptance. [Market](market.md) exposes the full candidate field so the person can assess what the learning changed.
