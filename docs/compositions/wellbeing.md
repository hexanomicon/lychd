---
title: Wellbeing
icon: material/scale-balance
---

# :material-scale-balance: Wellbeing

Wellbeing joins the ordinary daily loop: decide what food and movement fit, see what is probably on
hand, plan a trip or cart, record what was actually bought, and correct the next plan. A supermarket
catalogue, receipt, skipped walk, or private reflection remains evidence of one thing—not a verdict
about the person.

!!! note "Current material"
    No Wellbeing Pattern, consented profile store, meal or movement solver, receipt/OCR ledger,
    catalogue source, household inventory, cart, checkout effect, reflection ledger, or schedule is
    registered or executable. Vision has no delivered OCR/custody path and Scout has no delivered
    acquisition path.

[State of Work](../state-of-the-work.md#composition-portfolio-delivery) owns the delivery boundary for this reference.

## Contract

| Field | Reference contract |
| --- | --- |
| **Identity** | `wellbeing` revision `1` |
| **Principal Pattern** | `wellbeing.plan_cycle@1` |
| **Application begins with** | A consented adult profile, household binding, selected modes, hard restrictions, soft preferences, time, equipment, admitted sources, privacy class, and explicit budgets |
| **Application can return** | An editable food and ordinary-movement plan, honest infeasibility, corrected receipt evidence, uncertain inventory, reviewable shop or cart, acknowledged, refused, or unknown checkout outcome, or confirmed check-in |
| **Application stops before** | Diagnosis, treatment, clinical or supplement advice, claims that food or movement is safe, hidden health or address disclosure, source escalation, and checkout without fresh authority |

Wellbeing owns profile and plan revisions, restrictions, preferences, receipts, product identity,
inventory events, observed offers, stores, trips, carts, orders, delivery, journals, check-ins,
schedules, exports, and deletion records. The Magus approves every profile, plan, correction,
share, cart, disclosure, checkout, export, and deletion. A Mind may extract, propose, and explain;
deterministic tools own units, ingredient closure, hard constraints, money, reconciliation, route
arithmetic, cart predicates, effect identity, and deletion verification.

Its other Patterns are `wellbeing.profile@1`, `wellbeing.ingest_receipt@1`,
`wellbeing.reconcile_inventory@1`, `wellbeing.observe_shops@1`, `wellbeing.plan_shop@1`,
`wellbeing.build_cart@1`, `wellbeing.checkout@1`, `wellbeing.check_in@1`,
`wellbeing.journal@1`, `wellbeing.export@1`, and `wellbeing.delete@1`.

## Plan, provision, correct

1. `wellbeing.profile@1` creates an immutable, reviewed profile from restrictions, preferences,
   time, equipment, enabled modes, household binding, sources, consent, privacy, and budgets.
   Relaxing a hard restriction requires a confirmed successor profile.
2. `wellbeing.plan_cycle@1` pins profile, consent, policy, Pattern, catalogue, tool, and provider
   revisions. Deterministic checks preserve units, traverse ingredients to a finite depth, and mark
   candidates `blocked`, `unresolved`, or `eligible`; eligible never renders as “safe.”
3. The solver enforces exclusions, equipment, time windows, and operator maxima before softer
   preferences such as variety, convenience, and cost. It returns no feasible plan instead of
   violating a hard rule. The Magus edits, approves, or rejects every result.
4. `wellbeing.plan_shop@1` turns an approved plan and uncertain inventory into a reviewable list,
   trip, meal-out option, or source query. It does not book, call, order, or certify allergen safety.
5. `wellbeing.observe_shops@1` admits bounded, dated offers from explicitly enabled store profiles.
   Kaufland, Lidl, or any later shop remains a configurable source—not the Composition identity and
   never an ambient right to browse, authenticate, or send data.
6. `wellbeing.build_cart@1` creates a reviewable cart. `wellbeing.checkout@1` separately
   revalidates seller, product, package, price, stock, fees, delivery, substitutions, recurring
   terms, permitted disclosure, and worst-case budget before one authorized submission.
7. `wellbeing.ingest_receipt@1` keeps the admitted source and OCR geometry immutable, proposes
   merchant, transaction, and line fields, reconciles exact totals, then asks the Magus to correct,
   accept, or reject the candidate.
8. `wellbeing.reconcile_inventory@1` projects acquisition, confirmed consumption, disposal,
   transfer, and correction events. A receipt does not prove consumption, and uncertainty never
   becomes invented grams.
9. `wellbeing.check_in@1` records only confirmed completion, skip, substitution, duration, or
   reflection. `wellbeing.journal@1` preserves operator words; review may report neutral counts but
   cannot silently change the next plan.

Unit conversion uses decimal arithmetic and rejects incompatible dimensions. Volume becomes mass
only with sourced ingredient-specific density; serving, 100 g, and whole-package bases remain
distinct. Exact product identity follows GTIN or SKU, merchant product, named package, product
family, then unresolved. A model cannot invent a barcode, merge package sizes, force arithmetic to
agree, or infer eating from purchase.

## The privacy seam inside one application

One Composition does not mean one undifferentiated record. Wellbeing keeps sensitive profile,
journal, check-in, and movement truth apart from household receipt, inventory, offer, trip, cart,
order, and delivery histories. A purpose- and expiry-bound `ProvisionConstraintSet@1` is the only
bridge into shopping work: declared exclusions, enabled patterns or target intervals, selected
variety or preparation needs, privacy class, and unresolved-source flags.

Journals, measurements, symptoms, diagnoses, medication, clinical records, movement history, and
genetics do not enter shop queries, catalogues, carts, providers, or merchant messages. Store
profiles receive only the product or offer fields needed for an admitted observation. Taste is
corrigible testimony, not compliance; purchase evidence is not a health fact.

Records distinguish `user_entered`, `source_imported`, `model_proposed`,
`deterministically_derived`, and `user_confirmed`. Source releases keep identity, retrieval and
release time, digest, schema, licence, locale, normalizer revision, quality flags, and
supersession. Refresh imports beside old releases so old plans and carts remain reproducible.

## Medical, payment, and recovery lines

Children, pregnancy and postpartum, eating-disorder support, rehabilitation, clinical conditions,
biomarkers, medication interactions, and emergencies require separately governed applications.
Wellbeing does not diagnose, certify kitchen cross-contact, infer calorie expenditure, analyze gait
or form, contact clinicians, share automatically, punish a skipped activity, or read silence as
success. “My knee hurt” remains operator-authored and halts automated progression without
inferring injury, cause, adherence, or treatment.

Public fetch, rendering, authenticated interaction, sessions, cart mutation, address disclosure,
order submission, and payment are distinct source powers and effects. Raw addresses, payment data,
credentials, and one-time codes never enter prompts. A material checkout change returns to the
Magus. A missing acknowledgement becomes an unknown checkout or payment result; retries close
until reconciliation establishes what happened.

Storage and inference are local by default. Remote providers, lookup, reminders, retained media,
calorie or weight features, imports, sharing, checkout, export, or research use require revocable,
purpose-specific consent. Restart resumes only compatible pinned work and never duplicates receipt
acceptance, cart mutation, submission, or notification. Deletion fences admission, disables
schedules and checkout authority, surfaces open orders, drains atomic work, removes permitted
records and derivatives, verifies absence, and leaves a content-free receipt; merchant-held records
remain outside that claim.

## Proving the cycle

Use a network-disabled synthetic adult profile, a small reviewed catalogue, and straight and
skewed receipt fixtures. Prove hard ingredient and activity conflicts, unresolved units, a
three-day editable plan, a bounded grocery list, exact receipt totals and corrections, acquisition
without inferred consumption, unknown-checkout recovery, export, deletion, and restart without
duplicates. Use no real person, receipt, account, address, payment, route provider, shop session,
health record, or external lookup.

Related: [Composition Portfolio](index.md) · [Workflow](../adr/28-workflow.md)
