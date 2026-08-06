---
title: Lifestyle Steward
icon: material/cart-heart
---

# :material-cart-heart: Lifestyle Steward

Lifestyle Steward turns receipts, store observations, household intentions, and explicit
preferences into an editable account of daily provision. It can show what was bought, what may be
on hand, and whether a trip or cart is worth review without pretending that an offer is stock or
that a purchase proves consumption.

!!! note "Current material"
    No Lifestyle Pattern, receipt/OCR ledger, catalogue refresh, household inventory, route
    planner, cart, or checkout effect is registered or executable. Vision has no delivered
    OCR/custody path and Scout has no delivered acquisition path.

[State of Work](../state-of-the-work.md#composition-portfolio-delivery) owns the delivery boundary for this reference.

## Contract

| Field | Reference contract |
| --- | --- |
| **Identity** | `lifestyle.steward` revision `1` |
| **Principal Pattern** | `lifestyle.ingest_receipt@1` |
| **Application begins with** | An admitted receipt or source observation, household binding, consent, privacy class, and explicit budgets |
| **Application can return** | Correctable purchase evidence, uncertain inventory, a reviewable trip, meal-out, or cart proposal, or an acknowledged, refused, or unknown checkout outcome |
| **Application stops before** | Invented product identity, health judgment, hidden address disclosure, automatic source escalation, and checkout without fresh authority |

Lifestyle owns receipt and product identity, observed prices, inventory events, stores, routes,
trips, carts, orders, and delivery. HFM owns meal, wellness, and private-reflection truth; Tech
Scavenger owns hardware campaigns and seller evidence. The Magus accepts corrections, plans,
carts, disclosure, and checkout. A Mind may extract, propose, and explain; deterministic tools own
money, reconciliation equations, identity gates, route arithmetic, cart predicates, and effect
idempotency.

The full Pattern set is `lifestyle.bootstrap_market@1`, `lifestyle.ingest_receipt@1`,
`lifestyle.review_spending@1`, `lifestyle.reconcile_inventory@1`,
`lifestyle.refresh_catalogues@1`, `lifestyle.plan_shop@1`,
`lifestyle.choose_meal_out@1`, `lifestyle.build_cart@1`, and `lifestyle.checkout@1`.

## Receipt to household decision

1. `lifestyle.bootstrap_market@1` selects the core, market pack, household binding, sources,
   consent, privacy, and budgets without activating them automatically.
2. `lifestyle.ingest_receipt@1` keeps the original image or text and OCR geometry immutable,
   proposes merchant, transaction, and line fields, reconciles totals, then asks the Magus to
   correct, accept, or reject the candidate.
3. Identity follows exact GTIN or SKU, merchant product, exact named package, product family, then
   unresolved. A model cannot invent a barcode, merge package sizes, or force arithmetic to agree.
4. `lifestyle.reconcile_inventory@1` projects acquisition, confirmed consumption, disposal,
   transfer, and correction events. It may say “probably low”; it cannot fabricate grams or infer
   eating from a receipt.
5. `lifestyle.refresh_catalogues@1` admits bounded source observations. Offers retain source,
   validity, licence, scope, and price, stock, menu, and ingredient uncertainty.
6. `lifestyle.plan_shop@1` or `lifestyle.choose_meal_out@1` presents savings, travel friction,
   missing items, and uncertainty without booking, calling, ordering, or certifying allergen safety.
7. `lifestyle.build_cart@1` creates a reviewable cart. `lifestyle.checkout@1` separately revalidates
   seller, variant, price, stock, fees, delivery, substitutions, recurring terms, and worst-case
   budget before one authorized submission.

`lifestyle.review_spending@1` may calculate exact observed price and purchase trends. It does not
infer income, addiction, health, waste, inflation causes, or virtue.

## Three histories and health handoff

Receipt records keep source digest, capture and transform chain, OCR/schema revision, merchant and
transaction fields, exact money, line text and polygons, identity candidates, corrections,
reconciliation equations, discrepancies, and unresolved fields. Inventory, offers, menus, trips,
carts, approvals, orders, deliveries, refunds, and disputes remain independent histories.

The core owns reusable receipt, offer, inventory, trip, cart, order, money, provenance, and
uncertainty schemas. A market pack owns locale, tax/deposit/unit law, public source profiles,
aliases, adapters, and fixtures. The household binding alone owns private stores, route anchors,
preferences, budgets, retention, and enabled sources.

[Health, Food & Movement](health-food-and-movement.md) may supply only a versioned,
purpose- and expiry-bound `ProvisionConstraintSet`. It can contain declared exclusions, enabled
patterns or target intervals, preparation and variety needs, privacy class, and unresolved-source
flags; no journal, measurement, symptom, diagnosis, medication, movement, clinical, or genetic
record crosses. Taste remains corrigible testimony, not compliance.

## Checkout, privacy, and return

Public fetch, rendering, authenticated interaction, sessions, and credentials are separate source
powers; a source cannot upgrade itself. Exact addresses stay behind location authority, and raw
addresses, payment data, credentials, or one-time codes never enter prompts. Search, cart mutation,
address disclosure, order submission, and payment are distinct effects.

A material checkout change returns to the Magus. A missing remote acknowledgement becomes an
unknown checkout or payment result: retries close until reconciliation establishes what happened.
Restart resumes pinned compatible work and never duplicates receipt acceptance, cart mutation, or
submission. Schedules may refresh or remind, but cannot create purchases, visits, consumption,
carts, or orders.

Receipts and household traces are restricted. Export separates raw images, location, health,
sessions, and delivery data; deletion disables schedules and checkout authority, surfaces open
orders, drains atomic effects, removes permitted records and derivatives, and writes a
content-free receipt. It cannot erase merchant-held records.

## Proving receipt

Use synthetic straight and skewed receipt images with pinned OCR polygons: merchant, date,
currency, five lines, discount, deposit, total, one unresolved mismatch, and correction crops.
Prove exact trends, acquisition without consumption, restart without duplicate acceptance, full
export, deletion, and absence. Use no real receipt, health profile, catalogue, merchant login,
address, order, payment, route service, remote provider, or personal data.

Related: [Composition Portfolio](index.md) · [Health, Food & Movement](health-food-and-movement.md) ·
[Workflow](../adr/28-workflow.md)
