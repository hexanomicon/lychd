---
title: Lifestyle Steward
icon: material/cart-heart
---

# :material-cart-heart: Lifestyle Steward

**Turn a receipt, store choice, and household intention into an editable daily-life record: what was bought, where, at what price, what may be on hand, and whether a practical trip or cart is worth reviewing.**

| Local maturity | Identity | Default Pattern | Scope |
| --- | --- | --- | --- |
| **Accepted Reference Composition** | lifestyle.steward/rev1 | lifestyle.ingest_receipt@1 | household evidence, not an ambient life agent |

## Arithmetic with human terms

    ADD       receipt + catalogue + inventory + preference + route
    MULTIPLY  a cheap item × actual need × taste fit × permitted health fit
    SUBTRACT  travel friction + uncertain stock + likely waste + delivery cost
    DIVIDE    one friendly view across the offices that own each truth

This is not “always buy the cheapest basket.” The Magus can use four scenarios: receipt as ground truth; a practical trip rather than a theoretical itinerary; uncertain inventory rather than invented quantity; and an online decision whose checkout remains separate.

Lifestyle owns receipt/product identity/prices, inventory, stores/routes/trips, carts/orders/delivery. HFM owns meals, wellness and private reflection; Tech Scavenger owns hardware campaigns and seller evidence. The Mind proposes/extracts/explains only. The Magus accepts corrections, plans, carts, disclosure, and checkout.

## Eight finite scores

| Pattern | Result and boundary |
| --- | --- |
| lifestyle.bootstrap_market@1 | Select core, market pack, household binding, sources, consent, privacy and budgets; no automatic activation. |
| lifestyle.ingest_receipt@1 | Admit artifact → retain immutable image/OCR geometry → candidate → correction/accept/reject; one evidence ledger. |
| lifestyle.review_spending@1 | Exact observed price/purchase trend, never household income, addiction, health, waste, inflation cause, or virtue. |
| lifestyle.reconcile_inventory@1 | Event projection from acquisition/confirmation/consumption/disposal/transfer/correction with visible uncertainty. |
| lifestyle.refresh_catalogues@1 | Bounded admitted-source refresh; an offer is never shelf stock, checkout price, menu availability, or ingredient closure. |
| lifestyle.plan_shop@1 | Practical store/trip proposal with savings, friction, uncertainty and missing items; Magus decides. |
| lifestyle.choose_meal_out@1 | Fresh permitted menu/routing proposal; no booking, call, order, allergen-safety certification, or kitchen truth. |
| lifestyle.build_cart@1 / lifestyle.checkout@1 | Reviewable cart then separate revalidated, submit-once purchase effect. |

Patterns are immutable under [Workflow](../adr/28-workflow.md). Refreshes coalesce by source/validity; schedules cannot create receipt, consumption, visit, cart, or order. Invocation budgets bind bytes, pages, sources, candidates, model calls, route pairs, stops, cart mutations, checkout attempts, money, exposure, and retries.

## Receipt is evidence, not a convenient blob

No opaque receipt JSON. Original image/text and OCR polygons/crops are immutable; corrections append a reviewer decision. Money uses integer minor units or exact decimal, explicit currency and rounding.

| Layer | Needed record |
| --- | --- |
| Source | digest, media type/capture, transform chain, OCR/schema provider/revision, retention |
| Merchant/transaction | merchant/store candidate, time, currency, receipt number, subtotal/discount/deposit/tax/rounding/grand total, redacted payment descriptor |
| Line | original text, polygon/crop, quantity/unit, unit/line price, discounts/deposits, printed code, confidence |
| Identity/reconciliation | candidate/package/brand/variant/unit basis/alias/reviewer; equation, discrepancy, unresolved fields, correction, revision |

The identity ladder is exact GTIN/SKU → merchant product → exact named package → product family → unresolved. A model cannot invent a barcode, merge sizes, or decide private labels match. Reconciliation keeps discrepancy visible, including coupons, multipacks, weighed goods, loyalty prices, deposits, returns, voids, and ambiguous abbreviations; it never asks a model to make the sum work.

## Three truths do not collapse

| History | What establishes it |
| --- | --- |
| Price and purchase | accepted receipt/e-receipt, confirmed order, or attributable offer |
| Household availability | count/scan plus acquisition, consumption, disposal, transfer, correction, and explicit inference |
| Eating and wellness | Magus-confirmed HFM check-in or journal, under HFM ownership |

A receipt may add acquired inventory; it does not create consumption. An HFM plan may create planned need; it does not subtract food. Projected inventory shows original acquisition, event quantities, confirmed/inferred/unknown status, observed printed expiry, and any visible depletion assumption. “Probably low” is useful; fabricated grams are not.

## Narrow health handoff, local market law

HFM may supply a minimal, versioned, purpose/expiry-bound ProvisionConstraintSet: declared exclusions, enabled dietary pattern/target interval, variety/preparation needs, privacy class, and unresolved-source flags. No journals, weight, measurements, symptoms, diagnoses, medication, movement/clinical records, or genetics cross. Taste remains corrigible testimony—liked, disliked, tired of, texture, cuisine, effort, variety—not compliance.

| Layer | Owns | Cannot own |
| --- | --- | --- |
| Core | receipt/product/offer/inventory/trip/cart/order/money/provenance/uncertainty schemas and reusable Patterns | country merchants/selectors, address, credentials |
| Market pack | locale/currency/tax-deposit-unit law, merchants, public profiles, grammar, aliases, adapters, fixtures, policy evidence | household history/secrets/payment/activation |
| Household binding | stores, private anchors/route derivations, loyalty booleans, preferences/budgets, enabled sources, retention | shared defaults or another household's authority |

Source profiles distinguish public fetch, rendering, authenticated interaction, session, and credentials. A source cannot upgrade itself. The least powerful permitted source wins for catalogues and menus; claims retain scope, validity, provenance, terms, price/stock/allergen uncertainty. Exact address stays behind location authority; prompts see store ids, coarse region, or derived route time. A worthwhile detour is a visible utility decision, never hidden health/time/pleasure-to-euro conversion.

## Cart and checkout are different effects

Search, fetch, cart mutation, address disclosure, order submission, and payment are separate. A product page, CAPTCHA, login, discount, countdown, stock badge, redirect, or recommendation cannot authorize the next effect. An approved cart is revalidated for seller, variant, price, stock, fees/tax, delivery, substitutions, recurring terms and worst-case budget; any material change returns to the Magus. It then reauthorizes delivery and checkout, submits once, and reconciles order/payment/unknown result before creating an expected delivery.

No card, raw merchant credential, one-time code, or raw address enters prompts. Exact repeat grocery replenishment may later have bounded standing authority for a named merchant/SKU/price/quantity/window/substitution/spend/expiry—not “anything healthy,” “whatever is discounted,” a novel seller, or a changed item.

## Durable, private, recoverable

Records cover receipt evidence/corrections, product/aliases, merchants/stores/routes/preferences, offers/menus, inventory events, intents/constraints/trips/carts/approvals/orders/deliveries/refunds/disputes. Checkpoints pin pattern, OCR/schema, catalogue, adapter, route, policy and tools; parser upgrades import beside old observations, aliases never rewrite receipt text, and a route change never rewrites an old decision. Unknown checkout/payment closes retries until reconciliation.

Receipts remain restricted:

- minimize or redact loyalty, payment, location, barcodes, faces, backgrounds, and ordinary traces;
- require purpose-, field-, retention-, and duration-specific consent for remote OCR, vision, routes,
  or catalogues;
- never treat third-party seller or menu data as memory or training;
- expire indexes and caches with their source, and reapply tombstones after backup restore;
- export accepted lineage and checksums, with raw image, location, health, session, and delivery
  compartments separately encrypted and opt-in; and
- on deletion, disable schedules and checkout authority, surface orders, revoke access, drain atomic
  effects, remove records, derivatives, and artifacts, and write a content-free receipt.

Retention remains per class. Deletion cannot erase external merchant records.

The smallest proof is local and synthetic: straight and skewed receipt images; pinned OCR with polygons; merchant/date/currency/five lines/discount/deposit/total; an unresolved mismatch; correction crops; product/store trends; acquisition without consumption; restart without duplicate acceptance; full export/delete/absence. No real receipt, health profile, catalogue, merchant login, address, order, payment, route service, remote provider, or personal data.

Return to the [Composition Portfolio](index.md) or [Health, Food & Movement](health-food-and-movement.md).
