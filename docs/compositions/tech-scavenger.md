---
title: Tech Scavenger
icon: material/chip
---

# :material-chip: Tech Scavenger

Tech Scavenger turns a computer outcome, budget, deadline, region, and evidence standard into a
finite equipment campaign. It watches and qualifies dated offers without treating a socket match,
seller claim, screenshot, COD label, or successful boot as proof of the whole machine.

!!! note "Current material"
    No Tech Scavenger Pattern, campaign ledger, schedule, Scout acquisition, seller-message,
    purchase, parcel, or inspection path is registered or executable. Scout itself has no
    delivered web-acquisition capability.

[State of Work](../state-of-the-work.md#composition-portfolio-delivery) owns the delivery boundary for this reference.

## Contract

| Field | Reference contract |
| --- | --- |
| **Identity** | `scavenger.tech` revision `1` |
| **Principal Pattern** | `scavenger.plan_campaign@1` |
| **Application begins with** | A hardware outcome, known inventory, budget, deadline, region, compatibility needs, evidence tier, delivery terms, and autonomy ceiling |
| **Application can return** | A versioned campaign, qualified candidate or seller thread, commitment record, expected parcel, and inspection outcome |
| **Application stops before** | Unbounded scraping, spam, false identity or leverage, widened compatibility or price limits, autonomous payment, and resale |

Tech owns campaign, build and slot state, compatibility, value, evidence profiles, seller threads,
offers, commitments, parcels, and inspection. Scout adapters own acquisition and interaction
receipts. The Magus owns exceptions, final commitment and disclosure, payment at the door,
acceptance, and dispute. A Mind may extract, draft, and explain; deterministic tools own
compatibility gates, money, caps, idempotency, address insertion, and state transitions.

The remaining Patterns are `scavenger.daily_watch@1`, `scavenger.qualify_listing@1`,
`scavenger.negotiate_and_commit_cod@1`, and `scavenger.receive_and_verify@1`.

## Campaign to parcel decision

1. `scavenger.plan_campaign@1` records the outcome and existing inventory, then creates durable
   component slots, substitutions, budgets, evidence and delivery requirements, disclosure policy,
   and one of three modes: Watch, Concierge, or fully pinned Bounded Autopilot.
2. `scavenger.daily_watch@1` admits finite `ListingObservationBatch@1` source snapshots,
   normalizes and deduplicates them, rejects hard incompatibilities, computes landed-cost and value
   intervals, and emits a coalesced digest or qualified thread.
3. Compatibility checks exact CPU, board, BIOS, cooling, memory, GPU, storage, case, and PSU
   constraints before preferences. Unknown inventory or catalog facts block or ask; the model
   cannot invent socket, clearance, power, firmware, memory, or connector facts.
4. `scavenger.qualify_listing@1` pins the listing and missing facts, asks only for the selected
   evidence, parses the reply deterministically, then qualifies, follows up once, rejects, or
   expires. Evidence from a listing, seller, diagnostic, or inspection remains separately
   attributable.
5. `scavenger.negotiate_and_commit_cod@1` validates exact terms, reserves one slot and its budget,
   confirms the all-in ceiling and approved payment rail, then may disclose the minimum delivery
   fields and send once. Changed facts fall back to Concierge or refusal.
6. `scavenger.receive_and_verify@1` compares carrier, tracking, expected amount, item, and package
   notes before money moves, then records acceptance, rejection, dispute, return, or loss. COD does
   not prove contents; an unrecognized parcel or mismatched amount is refused.

Evidence tiers progress from listing and photos, through exact labels and bounded diagnostics, to a
fresh identity-to-result path and finally personal or trusted-shop inspection. Every test reduces a
named uncertainty; none creates a universal “healthy” verdict. Price remains an attributable
interval across new retail, comparable used observations, condition, warranty, age, and bundle
value rather than one invented fair price.

## Campaign evidence and Haggler handoff

Campaigns, builds, inventory, slots, compatibility edges, substitutions, reservations, schedules,
listing observations, evidence, seller messages, contradictions, consent, offers, commitments,
disclosures, parcels, tracking, inspections, disputes, returns, and losses are versioned records.
Checkpoints pin Pattern, source adapter, selector, catalogue, evidence parser, template, and policy;
they never replace the campaign or inbox.

Each Scout profile fixes permitted origins and paths, user agent, pacing, concurrency, page and byte
caps, cache and expiry, policy and robots decision, selectors, fixtures, session needs, CAPTCHA and
block handling, and a kill switch. Search and observation do not own application judgment.

For [Bazaar Haggler](bazaar-haggler.md), Tech may issue an exact `NegotiationMandate@1` and receive
`NegotiationOutcome@1`. Only after fresh compatibility, evidence, budget, exposure, and authority
checks may Tech issue `CodClosureMandate@1`. Tech retains slot, reservation, purchase count, parcel,
and inspection judgment; the source adapter still performs the send.

## Messaging, privacy, and reconciliation

Budgets cap money, purchases, concurrent COD exposure, distance, contacts, follow-ups, evidence
bytes, retries, pages, listings, and model calls. Urgency widens none of those limits. Messages
disclose automation, state their evidence basis, invent no competitor, defect, urgency, or human
sender, and stop on refusal, opt-out, abuse, silence, sale, changed item, changed payment rail,
failed evidence, or cap exhaustion.

Raw address and phone stay behind an opaque `delivery_profile_id`; only a deterministic sender may
resolve it after fresh authority. Prompts, queries, ranking artifacts, and ordinary traces never
receive those fields. Coarse search location, seller contact, serial fragments, messages, and
evidence are private and are not memory or training data.

Every send has a stable effect identity and postcondition receipt. A missing acknowledgement
becomes `unknown_send`: the thread, slot, reservation, disclosure, tracking, and payment-at-door
state park until reconciliation, and restart never resends or creates a second commitment.
Deletion disables schedules and sessions, inventories open parcels and disputes, revokes profile
access, removes permitted records and artifacts, and does not claim to erase seller messages.

## Proving watch

Use a network-disabled synthetic 32 GB RAM campaign with source and selector fixtures. Prove
DDR4/DDR5 and SODIMM/UDIMM rejection, a dated price interval, a daily coalesced shortlist, bounded
Slovak extraction, and restart without duplicate observation or notification. No seller message,
address disclosure, commitment, parcel, or payment enters this first slice.

Related: [Composition Portfolio](index.md) · [Bazaar Haggler](bazaar-haggler.md) ·
[Workflow](../adr/28-workflow.md)
