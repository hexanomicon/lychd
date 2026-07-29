---
title: Bazaar Haggler
icon: material/handshake-outline
---

# :material-handshake-outline: Bazaar Haggler

!!! warning "Candidate study — not accepted architecture or delivered software"
    Bazaar Haggler explores one reusable marketplace-negotiation application above Scout,
    domain-qualified candidates, and separately authorized messaging effects. Current LychD has no
    Scout provider, marketplace session, Haggler registry, seller-thread ledger, or messaging
    effect. Nothing on this page authorizes contact, impersonation, address disclosure, purchase,
    payment, reservation, or contract formation.

**Bazaar Haggler** would receive one exact negotiation mandate from a domain Composition, conduct
a finite and truthful seller conversation inside that mandate, and return attributable terms,
evidence, refusal, uncertainty, or non-completion.

Its office begins only after acquisition and domain qualification:

```text
Scout observation
→ domain Composition qualifies the candidate and mints a mandate
→ Bazaar Haggler conducts bounded dialogue
→ domain Composition accepts, rejects, or authorizes an exact closure
```

> Negotiate what was authorized. Invent no leverage. Cross no ceiling. Preserve every refusal.

## Why this may be a Composition

Search, crawl, extraction, saved queries, deduplication, and change observation remain Scout
machinery. Haggler has a different operator-visible purpose and lifecycle: open mandates, seller
threads, questions, offers, counteroffers, timeouts, stop signals, prepared sends, unknown-send
reconciliation, accepted terms, and closure receipts.

That state can serve Tech Scavenger, Lifestyle Steward, or another marketplace application without
owning their domain judgment. A hardware buyer and a figurine buyer may share truthful
conversation mechanics while retaining different evidence, price, safety, and commitment law.

## Candidate descriptor

| Field | Candidate value |
| --- | --- |
| Stable id / revision | `bazaar.haggler` / `1` |
| Default manual Pattern | `haggler.open_mandate@1` |
| Principal active Pattern | `haggler.negotiate@1` |
| Optional exact closure Pattern | `haggler.close_cod@1` |
| Primary projection | Open mandates, seller threads, permitted questions, offers/counteroffers, stop state, accepted terms, unknown sends, and closure receipts |
| Principal non-goal | Listing discovery, compatibility or suitability judgment, autonomous price policy, seller identity proof, credential custody, payment, or an unrestricted sales bot |

## Ownership boundary

| Concern | Owner |
| --- | --- |
| Search, fetch, extract, render, interact, session, and message-send effect | Scout under separate grants |
| Origin credentials and session references | Ward plus Scout session custody |
| Compatibility, suitability, evidence profile, value interval, and maximum price | Calling domain Composition |
| Thread strategy inside the exact mandate | Bazaar Haggler |
| Deterministic money arithmetic and mandate validation | Domain tools |
| Consent, standing authority, address-disclosure authority, and purchase count | Calling Composition, Ward, and HitL |
| Payment or settlement rail | Future Toll; never implied by negotiation |
| Seller-thread, send, reply, offer, outcome, and reconciliation records | Bazaar Haggler's Phylactery schema |

## Typed mandates

`NegotiationMandate@1` pins:

- calling Composition, Pattern, Invocation, principal, purpose, and expiry;
- exact listing observation and seller-thread reference;
- material questions and acceptable evidence request;
- opening offer, hard item-price and all-in ceilings, currency, delivery constraints, and permitted
  concessions;
- message, follow-up, counteroffer, time, disclosure, and retry caps;
- truthfulness template, automation disclosure, prohibited claims, and stop signals;
- consent or standing-authority reference for each eligible effect class; and
- the exact outcome schema the caller can understand.

Haggler cannot widen this envelope, infer a higher ceiling from enthusiasm, trade private data for
a discount, invent defects or competing buyers, or continue after refusal, opt-out, changed item,
changed payment rail, abuse, expiry, or exhausted caps.

`NegotiationOutcome@1` returns the exact quoted terms, attributed seller claims, requested and
received evidence references, unresolved contradictions, prepared/send receipts, accepted or
rejected offers, stop reason, and uncertainty. It is not a purchase commitment.

An optional `CodClosureMandate@1` arrives only after the calling Composition has revalidated the
candidate, budget, evidence, thread identity, parcel exposure, and authority. It pins one accepted
deal, maximum all-in amount, delivery method, opaque delivery-profile reference, exact disclosure
fields, payload template, expiry, and one-send authority.

## Candidate Patterns

```text
haggler.open_mandate@1

ValidateCallingCompositionAndSchema
→ PinListingThreadTermsAndCaps
→ SeparateQuestionsOffersAndClosureAuthority
→ PresentMandateForRequiredReview
→ CommitOpenMandate
```

```text
haggler.negotiate@1

LoadExactOpenMandateAndThread
→ ObserveLatestReplyThroughScout
→ ClassifyClaimsRefusalAndChangedTerms
→ DraftOneGroundedMessageInsideMandate
→ DeterministicallyValidatePriceDisclosureAndCaps
→ AuthorizeAndSendOnceThroughScout
→ ReconcileAcknowledgedUnknownOrFailedSend
→ AwaitReply | ReturnAcceptedTerms | Refuse | Expire
```

```text
haggler.close_cod@1

AdmitExactCodClosureMandate
→ RevalidateAcceptedTermsThreadAndExpiry
→ ResolveDeliveryProfileOutsideTheMind
→ ConstructAndDigestMinimumDisclosurePayload
→ ReauthorizeAndSendOnceThroughScout
→ ReconcileSendAndReturnClosureReceipt
```

The Mind may draft and classify. Deterministic code validates all money, caps, required phrases,
payload fields, effect identity, and state transitions. Raw address and phone data never enter
model prompts; only the final deterministic sender may resolve an opaque delivery profile after
fresh authority.

## Candidate handoff with Tech Scavenger

```text
Tech Scavenger
→ qualified component + NegotiationMandate@1
→ Bazaar Haggler
→ NegotiationOutcome@1
→ Tech Scavenger revalidates compatibility, evidence, budget, and consent
→ optional CodClosureMandate@1
→ Bazaar Haggler sends the exact closure once
→ closure receipt + expected-parcel handoff
```

The round trip does not let Haggler choose a component, redefine a test, raise the ceiling, reserve
campaign budget, or mark the parcel acceptable. It owns conversation; Tech Scavenger owns the
purchase campaign and received-item judgment.

Property negotiation is not automatically eligible. Home Seeker would require separate
property-specific law before it could issue any Haggler mandate involving an offer, reservation,
deposit, representation, or contract.

## Smallest proving slice

The first slice is fixture-bound and cannot send:

1. one qualified synthetic RAM listing plus exact evidence questions and price envelope;
2. seller fixtures for available, incomplete, counteroffer, refusal, sold, changed item, changed
   payment rail, abuse, and silence;
3. deterministic enforcement of caps, stop signals, all-in arithmetic, and automation disclosure;
4. one simulated lost acknowledgement producing `unknown_send` without automatic resend;
5. one accepted term set returned to a fake Tech Scavenger consumer; and
6. no live site, credential, address, purchase, payment, or parcel effect.

## Continue

- Read [Scout](../sepulcher/extensions/scout.md) for source, session, interaction, and send effects.
- Read [Tech Scavenger](tech-scavenger.md) for the first candidate caller.
- Read [Ward](../sepulcher/extensions/ward.md), [HitL](../adr/25-hitl.md), and
  [Toll](../sepulcher/extensions/toll.md) before any consequential effect.
- Return to the [Composition Portfolio](index.md).
