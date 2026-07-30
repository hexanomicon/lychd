---
title: Tech Scavenger
icon: material/chip
---

# :material-chip: Tech Scavenger

**Describe the computer outcome, money, month, distance, and proof wanted; receive a finite, evidence-bound equipment campaign.** “A 1080p gaming PC within a month, at most €900; search daily, prefer Bratislava within 50 km, accept shipping for RAM and SSDs; ask only for my chosen tests and never cross all-in limits” is enough to begin.

| Local maturity | Identity | Patterns | Principal non-goal |
| --- | --- | --- | --- |
| **Accepted Reference Composition** | scavenger.tech/rev1 | scavenger.plan_campaign@1; scavenger.daily_watch@1 | unbounded scraping, spam, undisclosed impersonation, autonomous payment, resale |

## The campaign, not a crawler

Campaign setup captures hardware outcome and existing inventory, budget/deadline/radius, evidence and delivery requirements, and autonomy. It creates durable component slots with a versioned shopping plan, not a price promise. Unknown inventory blocks compatibility or asks a question; a model guess never becomes a socket, clearance, power, firmware, or memory fact.

| Mode | Allowed action |
| --- | --- |
| Watch | Acquire, normalize, score, notify—no sends. |
| Concierge | Draft and, when separately authorized, send bounded test questions/offers; Magus approves final price, delivery, and disclosure. |
| Bounded Autopilot | Transparent messages, negotiation, one slot reservation, and one approved profile only when every predicate holds. |

Autopilot pins campaign/slot, all-in cap, condition/evidence tier, delivery method, seller-risk floor, address profile, expiry, concurrent parcel exposure, and purchase count. Any changed fact falls back to Concierge or refusal. Campaign and daily Occurrences are durable: periodic runs coalesce, consume bounded budgets, and have no duplicate effect on restart. A slot moves from open through candidate, evidence pending, offer open, reserved, committed, in transit, received, and accepted.

Rejection, expiry, withdrawal, delivery refusal, failed inspection, cancellation, and unknown message/shipment remain explicit. Only one active commitment slot exists; unknown holds reconciliation rather than creating a duplicate.

## Five scores

| Pattern | Essential route |
| --- | --- |
| scavenger.plan_campaign@1 | outcome/inventory → budget/deadline/region → compatibility → build/substitutions → evidence/delivery → autonomy/disclosure → campaign + schedule |
| scavenger.daily_watch@1 | Occurrence → slots/budgets → permitted listings → normalize/deduplicate → hard compatibility → price interval → evidence/distance/landed cost → digest or qualified thread |
| scavenger.qualify_listing@1 | pin listing → missing facts → evidence profile → transparent question → send once → reply/evidence → deterministic parse → qualify/follow-up/reject/expire |
| scavenger.negotiate_and_commit_cod@1 | qualified candidate → opening/max all-in → grounded offer/send/reconcile → validate deal → reserve slot/budget → authority → deterministic address insertion/send once → expected parcel |
| scavenger.receive_and_verify@1 | tracking/expected total → delivery decision → inspect against evidence → outcome/dispute/return/loss → release slot/budget |

COD does not prove contents: an unrecognized parcel or mismatched amount is refused. The delivery card shows seller, carrier, tracking, expected amount, component, and package notes before money moves.

## Divided owners and hard gates

Tech owns campaign, compatibility, value, evidence profiles, seller threads/offers/commitments, parcels, and inspection. The source adapter owns acquisition, normalization, interaction, and effect receipts; deterministic tools own compatibility, arithmetic, offer predicates, idempotency, and address insertion; the Magus owns policy, exceptions, commitment/disclosure, payment at door, acceptance, and dispute. Listing, seller statement/rating, screenshot/diagnostic, COD label, and boot are different evidence.

Compatibility is hard before preference. The catalogue models CPU socket/chipset/BIOS/cooling/power; memory generation/form factor/capacity/rank/kit/speed/slot plan; GPU dimensions/connectors/PSU/clearance/outputs; storage interface/keying/lane-SATA/form/capacity/endurance/boot; case clearances; and exact PSU model/revision/rails/connectors/age/exclusions. Facts carry source, date/version, and confidence. A socket match never proves all surrounding conditions.

Price is an attributable interval: new retail, comparable used, sold/withdrawn observations, condition, warranty, age, and bundle value do not collapse into invented “fair price.” Landed cost is agreed price plus shipping, cash-on-delivery fee, and configured travel cost.

After compatibility, rank expected value, evidence, delivery fit, distance, urgency, and visible risk reserve. Budgets cap money, purchases, COD exposure, distance, contacts, follow-ups, evidence bytes, retries, pages, listings, and model calls; urgency widens none of price, messaging, privacy, or address authority.

## Evidence asks a bounded question

| Tier | Evidence |
| --- | --- |
| E0 | Listing and photos only: useful for alerting, never automatic remote commitment |
| E1 | Exact label, condition/accessory photos, and the relevant purchase claim |
| E2 | Complete legible diagnostic with identity, tool/version, time, and context |
| E3 | Fresh thread nonce and an uncut identity-to-result path |
| E4 | Personal or trusted-shop inspection |

A test reduces named uncertainty; it never produces a universal healthy verdict.

- Storage reports can be reset or forged, and a RAM pass is board-specific.
- A GPU test misses intermittent, repaired, and shipping failures.
- CPU, board, and PSU defects often need physical testing.
- A whole PC can hide weak power, tuning, licenses, or untested faults.

Serials are minimized but sufficient to join evidence. Anomalies are risk signals, not accusations.

Each source is an admitted Scout profile: origins/public paths, user agent/pacing/concurrency/page and byte caps/cache/expiry; policy/robots decision; selectors/fixtures; least-powerful adequate route; session/contact requirements; caps/CAPTCHA/block recovery; kill switch. It produces a pinned ListingObservationBatch@1. Acquisition is not application judgment; observation stores URL/id, time, extraction revision, digest, price/locality, and deletion/change. No origin is a permission exception.

## Truthful conversation and COD

The first Slovak message truthfully says it is an automated buying assistant and asks whether the offer is current, exact model, and bounded test. An offer states its evidence basis and exact price/all-in cap—never fake competitors, defects, urgency, or a human sender. One material follow-up is allowed; refusal, opt-out, abuse, silence, sold/changed item/payment rail, failed evidence, or cap exhaustion closes automatic messaging. Per-origin/seller caps prevent spam.

> Dobrý deň, píšem v mene kupujúceho ako automatizovaný nákupný asistent. Je ponuka ešte aktuálna?
> Pred rozhodnutím by sme potrebovali overiť presný model a tento test: {bounded request}.

> Ak stav a výsledok testu sedia, môžeme ponúknuť {price} €; maximálny dohodnutý súčet vrátane
> dopravy a dobierky musí zostať do {all_in_cap} €.

Every send records the thread, template revision, redacted payload digest, action class, authority,
and postcondition receipt. A missing acknowledgement is `unknown_send`: park, reconcile, never
resend.

Before COD disclosure, the seller must confirm:

- the exact item, accessories, condition, and evidence;
- item, shipping, COD, and all-in price;
- carrier, window, and tracking; and
- no deposit, link payment, remote access, crypto, gift card, or changed rail.

At effect time, recheck freshness, thread and slot, compatibility, evidence, cap, exposure, count,
and live or exact standing authority.

Only a deterministic sender resolves opaque delivery_profile_id; raw address/phone never appear in prompts, queries, ranking artifacts, or ordinary traces. It discloses only minimum carrier fields, preferably locker/pickup/alias, and records thread, disclosed fields, policy/approval, payload digest, remote result, expected parcel, and revocation—not address telemetry.

[Bazaar Haggler](bazaar-haggler.md) is candidate-only: it may receive a
`NegotiationMandate@1` and return a `NegotiationOutcome@1`; only after Tech revalidates can it
receive an exact `CodClosureMandate@1`. Tech keeps compatibility, evidence/value ceilings,
budget/reservation, purchase count, parcel, and inspection; the source adapter still sends.

## Durable, private, provable

Versioned records cover campaigns/builds/inventory/slots/edges/substitutions/reservations/schedules;
listing/evidence/thread/message/contradiction; consent/offer/commitment/disclosure; and parcel,
tracking, receipt, inspection, dispute, return/loss. Corrections append. Checkpoints pin Pattern,
adapter, selector, catalogue, evidence/parser/template/policy and never replace campaign or inbox.
Crash recovery reconciles unknown sends, slot reservations, address disclosures, tracking, and
payment-at-door outcomes before any repeat effect.

Coarse search origin is distinct from field-encrypted/narrow delivery data. Seller contact, ratings, messages, serial fragments, and evidence are private third-party data, not memory/training. Retention expires rejected bodies/contact as selected while keeping redacted accountability receipts. Export has plan, permitted observations, rationale, transcript, lineage, approvals/receipts/checksums; address is separate encrypted opt-in. Deletion disables schedules/sessions, inventories parcels and disputes, revokes profile access, removes permitted rows/artifacts, and never claims to erase seller messages.

The minimum proof is a network-disabled synthetic 32 GB RAM campaign: source/selector fixtures, DDR4/DDR5/SODIMM/UDIMM rejection, price interval, daily coalesced shortlist, optional bounded Slovak extraction, and crash recovery without duplicate observation/notification—no message.

Return to the [Composition Portfolio](index.md) or [Bazaar Haggler](bazaar-haggler.md).
