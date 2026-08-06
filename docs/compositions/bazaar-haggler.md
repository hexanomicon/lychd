---
title: Bazaar Haggler
icon: material/handshake-outline
---

# :material-handshake-outline: Bazaar Haggler

Bazaar Haggler carries one finite, truthful seller conversation after another Composition has
qualified the subject. It can ask approved questions and negotiate inside a closed envelope, but
it cannot select the item, judge the domain, or turn accepted terms into a purchase.

!!! note "Current material"
    No Haggler Pattern, mandate ledger, seller-thread adapter, deterministic sender, or negotiation
    effect is registered or executable. No live fixture proves the messaging and unknown-send
    boundary.

[State of Work](../state-of-the-work.md#composition-portfolio-delivery) owns the delivery boundary for this reference.

## Contract

| Field | Reference contract |
| --- | --- |
| **Identity** | `bazaar.haggler` revision `1` |
| **Principal Pattern** | `haggler.open_mandate@1` |
| **Application begins with** | A caller-qualified listing and thread plus exact questions, evidence needs, offer limits, disclosure, consent, caps, expiry, and stop signals |
| **Application can return** | `NegotiationOutcome@1`: attributable terms, claims, evidence, contradictions, receipts, accepted or rejected offers, stop reason, and uncertainty |
| **Application stops before** | Domain selection, compatibility or suitability judgment, value policy, credential ownership, commitment, purchase, payment, or parcel creation |

The calling Composition owns qualification, domain limits, budget reservation, commitment, and
the consequences of the outcome. Haggler owns the mandate, thread progression, prepared messages,
offers and counteroffers, timeout, refusal, send receipts, and reconciliation. A Mind drafts and
classifies; deterministic tools validate money, caps, prohibited phrases, payload fields, effect
identity, and state. The source adapter owns transport identity and remote receipts.

Its other Patterns are `haggler.negotiate@1` and `haggler.close_cod@1`.

## Mandate to outcome

1. `haggler.open_mandate@1` validates caller and outcome schema, then pins the Principal,
   Invocation, listing observation, thread, material questions, desired evidence, opening offer,
   item and all-in ceilings, currency, delivery constraints, concessions, caps, truthful template,
   automation disclosure, prohibited claims, authority, expiry, and stop signals.
2. `haggler.negotiate@1` loads that immutable envelope and observes the next reply through Scout.
   It classifies attributed claims, evidence, refusal, contradiction, changed item or rail, abuse,
   silence, and expiry without redefining the caller's domain judgment.
3. The Mind may draft one grounded question, offer, or response. Deterministic checks reject a
   private-data bargain, fabricated leverage, widened price, unapproved concession, missing
   disclosure, exhausted cap, or forbidden follow-up.
4. The admitted sender transmits once and records the exact effect identity, template revision,
   redacted payload digest, authority, and remote postcondition.
5. Haggler returns `NegotiationOutcome@1` when the thread succeeds, refuses, expires, or reaches a
   stopping condition. The caller must freshly revalidate everything before any commitment.
6. Only then may the caller issue `CodClosureMandate@1` for one deal, maximum all-in amount,
   delivery method, opaque delivery profile, exact permitted fields and template, expiry, and one
   send; `haggler.close_cod@1` does not create the expected parcel.

## Closed envelope and Tech handoff

`NegotiationMandate@1` is a closed envelope, not permission to improvise. It cannot widen for
enthusiasm, private-data barter, a changed item or payment rail, seller pressure, expiry, refusal,
abuse, or exhausted caps. `NegotiationOutcome@1` keeps terms, claims, evidence, contradictions,
prepared and completed sends, decisions, stop reason, and uncertainty attributable to the thread.

For [Tech Scavenger](tech-scavenger.md), the handoff is qualified component plus mandate → Haggler
outcome → Tech revalidation of compatibility, evidence, budget, consent, and parcel exposure →
optional closure mandate → reconciled receipt. Tech retains evidence and price ceilings,
reservation, purchase count, parcel, inspection, and dispute. Home Seeker has no revision-one
Haggler handoff.

## Send boundaries and return

Haggler neither searches nor crawls; Scout owns acquisition, normalization, deduplication, and
change observation. It neither holds seller credentials nor resolves raw delivery data in a
prompt. Only the deterministic sender may resolve an opaque delivery profile after fresh
authority, and it discloses the minimum approved fields.

Refusal, opt-out, abuse, silence, sale, changed subject, changed payment rail, failed evidence,
expiry, and exhausted caps close automatic messaging. A missing acknowledgement becomes
`unknown_send`: the exact effect parks and cannot be resent on restart until the source is
reconciled. The caller creates an expected parcel only after acknowledged closure.

Private seller data, messages, serial fragments, evidence, and delivery fields keep narrow
purpose and retention. Export keeps mandate, attributable transcript, decisions, approvals,
receipts, and checksums; deletion revokes adapter authority and removes permitted local records but
cannot erase the seller's copy.

## Proving negotiation

Use a sendless synthetic RAM-listing thread with available, incomplete, counteroffer, refusal,
sold, changed-item, changed-rail, abuse, and silence replies. Prove item and all-in caps, truthful
disclosure, stop rules, a simulated lost acknowledgement, restart without resend, and an accepted
term set returned to a fake Tech consumer. No live seller, credential, message, delivery profile,
parcel, purchase, or payment enters the slice.

Related: [Composition Portfolio](index.md) · [Tech Scavenger](tech-scavenger.md) ·
[Workflow](../adr/28-workflow.md)
