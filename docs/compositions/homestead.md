---
title: Homestead
icon: material/solar-power
---

# :material-solar-power: Homestead

Homestead keeps one household—city flat or cottage—legible as a bounded place. Pantry, fridge,
freezer, recurring supplies, garden harvest, water, energy, network, devices, and work all enter as
attributable resource events. The place may be provisioned from Kaufland, Lidl, a local market, or
its own field; source changes do not change who owns the household stock.

!!! note "Current material"
    No Homestead Pattern, site/resource or household-stores ledger, receipt/OCR path, shop source,
    cart, checkout effect, device or sensor adapter, safety controller, camera path, droid profile,
    or physical effect is registered or executable. Legion, Tether, Scout, Vision, remote IAM, and
    visual custody remain Designed or Partial common substrate.

[State of Work](../state-of-the-work.md#composition-portfolio-delivery) owns the delivery boundary for this reference.

## Contract

| Field | Reference contract |
| --- | --- |
| **Identity** | `homestead.steward` revision `1` |
| **Principal Pattern** | `homestead.map_site@1` |
| **Application begins with** | A reviewed household boundary, asset and resource evidence, responsible people, recurring provision policy, hazards, budgets, and commissioned device limits |
| **Application can return** | `HomesteadPlan@1`, freshness-visible resource and stores ledgers, `InventorySnapshot@1`, a reviewable provision plan or cart, acknowledged, refused, or unknown checkout result, bounded work or control intents, alerts, and effect receipts |
| **Application stops before** | Health or consumption judgment, unapproved purchase or disclosure, irregular high-value acquisition, design certification, permits, construction, potability claims, unsafe energization, interlock bypass, hazardous repair, or general robot authority |

Homestead owns the household model, resource policy, pantry and cold-store locations, food and
recurring-supply lots, inventory events, receipts, observed offers, provision plans, carts, orders,
deliveries, forecasts, alerts, maintenance, work orders, and admission of homestead effects.
Professionals, manufacturers, utilities, merchants, local controllers, and the Magus retain their
own judgment. A Mind may interpret or propose; deterministic tools own units, identity gates,
money, stock reconciliation, thresholds, resource balance, freshness, set-point limits, effect
predicates, and idempotency.

Its provision Patterns are `homestead.ingest_receipt@1`, `homestead.reconcile_stores@1`,
`homestead.observe_shops@1`, `homestead.plan_provision@1`, `homestead.build_cart@1`, and
`homestead.checkout@1`. They join the site Patterns below without granting a merchant or device
authority to one another.

There is no accepted general smart-home or physical-actuator Domain. [Legion](../adr/42-legion.md)
owns designed law for robots and embedded bodies; Workflow, Security, IAM, Vision, and host owners
retain their boundaries. This page cannot authorize a device path.

## Place and provision to bounded intent

1. `homestead.map_site@1` maps the dwelling, pantry, fridge, freezer, cellar, plots, water points,
   circuits, critical loads, generation, storage, network zones, devices, work zones, hazards,
   unknowns, and professional or permit needs into a reviewable `HomesteadPlan@1`.
2. `homestead.observe_cycle@1` admits fresh bounded telemetry and weather observations, checks
   attribution, calibration, staleness, and contradiction, then updates resource ledgers or shows
   an honest gap. It never actuates.
3. `homestead.reconcile_stores@1` projects harvest, acquisition, confirmed consumption, disposal,
   transfer, and correction events into quantity intervals. A harvest or receipt proves neither
   safe food nor consumption; unknown identity, quantity, storage condition, or expiry stays
   visible.
4. `homestead.plan_provision@1` combines household policy, a purpose-limited `FoodNeed@1`, stores,
   budgets, and admitted offers into a reviewable replenishment plan. `homestead.build_cart@1`
   creates a cart; `homestead.checkout@1` separately revalidates merchant, product, package, price,
   stock, fees, delivery, substitutions, recurring terms, disclosure, and worst-case budget before
   one authorized submission.
5. `homestead.balance_energy@1` combines critical-load policy with PV, load, battery, grid, alarm,
   and forecast evidence. It may return reserve-aware advice or an exact set-point intent inside
   inverter, BMS, anti-islanding, thermal, fire, and electrician-set protection.
6. `homestead.guard_water@1` combines well, tank, pressure, quality, weather, and allocation
   evidence. Any pump or valve intent stays inside dry-run, pressure, level, freeze, contamination,
   and reserve interlocks; no sensor result becomes a potability claim.
7. `homestead.tend_land@1` produces explainable human or droid work orders from plot, crop, soil,
   weather, and resource state. Pesticide, livestock, and food-safety authority are absent by
   default.
8. `homestead.maintain_site@1` turns alarms, inspections, runtime, or calendar evidence into
   containment advice, research needs, scheduled work, verification, and an unresolved state when
   silence or weak evidence cannot close the fault.

Every request states one of four postures: observe; advise; bounded stewardship inside a live,
commissioned envelope; or deterministic safe containment. Schedules create finite Occurrences,
not an always-awake model.

## Stores and recurring provision

Exact product identity follows GTIN or SKU, merchant product, named package, product family, then
unresolved. Receipt records keep the admitted image or text, OCR geometry, merchant and transaction
fields, exact money, line evidence, corrections, equations, and discrepancies. Lots retain source,
location class, quantity interval, acquisition or harvest event, expiry evidence, storage-condition
uncertainty, and disposition. A model cannot invent a barcode, merge package sizes, force totals to
agree, or turn purchase into consumption.

Shop profiles are explicit and independently revocable. Kaufland, Lidl, a later merchant, and a
garden harvest are sources—not Composition identities and never ambient rights to browse,
authenticate, disclose, or buy. Public fetch, rendered observation, authenticated session, cart
mutation, address disclosure, order submission, and payment are distinct powers and effects.

This office is limited to recurring household provision: food, cleaning goods, toiletries, and
ordinary consumables entering shared household custody. [Scavenger](scavenger.md) keeps irregular,
high-value, compatibility-heavy, property, and seller-negotiated acquisition. Eating out and
personal food or movement judgment remain with [Wellbeing](wellbeing.md).

## Resource ledgers and Portfolio handoffs

Energy, water, land, food stores, recurring supplies, habitat, network, camera, and embodied-node
ledgers remain separate. A device report becomes an attributed observation, then a calibrated
derivation, then a reconciled resource
estimate; none of those stages is silently collapsed into “home state.” Records append independent
revisions for observations, calibration, forecasts, plans, alerts, approvals, commands,
controller receipts, receipts, lots, carts, orders, deliveries, maintenance, laboratory evidence,
professional documents, and configuration.

| Handoff | Boundary |
| --- | --- |
| Requirements → [Scavenger](scavenger.md) | Homestead states compatibility, certification, serviceability, environment, budget, and evidence needs; Scavenger returns dated candidate and seller evidence, never commissioning authority. |
| `InventorySnapshot@1` → [Wellbeing](wellbeing.md) | Homestead exposes only attributed food identity, quantity interval, location class, expiry or freshness, storage uncertainty, and provenance—never merchant credentials, payment, address, whole receipts, or unrelated stock. |
| `FoodNeed@1` ← [Wellbeing](wellbeing.md) | Wellbeing may state quantities, declared exclusions, useful product traits, expiry, privacy class, and unresolved flags; diagnosis, journal, measurements, medication, genetics, and movement history do not cross. |
| `ProvisionResult@1` → [Wellbeing](wellbeing.md) | Homestead returns what became available, unavailable, substituted, refused, or uncertain; it makes no health, eating, or adherence claim. |
| Product or site request → Scout | Scout acquires attributed observations; web text cannot become a physical instruction. |
| Typed work → a Legion node | The droid receives a fenced task, zone, resources, expiry, and stop conditions—not shell access or a general farm mandate. |

[Tether](../sepulcher/extensions/tether.md) may eventually carry private inspection and exact
approved controls, but tunnel possession supplies no Principal or effect authority and never falls
back to a public dashboard.

## Effects, recovery, and physical veto

Raw addresses, payment data, credentials, and one-time codes never enter prompts. A material cart
or checkout change returns to the Magus. A missing merchant acknowledgement becomes an unknown
checkout or payment result: retries close until reconciliation establishes what happened. Restart
never duplicates receipt acceptance, cart mutation, order submission, notification, or stock
reconciliation.

BMS, inverter protection, pump control, float and pressure protection, fire systems, droid
emergency stops, and fenced work-zone controllers always retain the freshest veto. Each effect
binds asset and controller identity, configuration generation, commissioned envelope, live
observations, preconditions, expiry, local reservation, expected postcondition, and compensation or
containment. LychD sends typed requests, never arbitrary shell, bus, GPIO, relay, or manufacturer
API commands through a prompt.

The homestead must remain safe without internet, Wi-Fi, Master, model, or cloud. Lost
acknowledgement is an unknown physical effect: recovery reads the exact controller and independent
sensors before any repeat. Restore closes admission until clocks, controller generations, safety
envelopes, pending effects, alarms, and current local state reconcile. Replaced devices and changed
calibration create new evidence rather than rewriting history.

Coordinates, floor plans, camera material, and device access are restricted. Cameras require named
purposes, privacy masks, active hours, viewers, and retention; face recognition, neighbour
surveillance, ambient audio, public streaming, and indefinite retention are absent by default.
Deletion revokes grants, disables schedules and checkout authority, drains or contains admitted
motion, inventories hazards, open orders, and third-party handoffs, and removes permitted records
and artifacts. It cannot erase merchant-held or other external records.

## Proving household

Use network-disabled household fixtures that cover a city flat and a cottage: pantry, fridge and
freezer lots; one synthetic receipt; bounded Kaufland/Lidl offer snapshots; one garden harvest;
PV, battery and BMS; a well and tank; soil observations; segmented device identities; and one
watering droid. Prove receipt correction, acquisition without inferred consumption, minimal
Wellbeing handoffs, unknown-checkout recovery, stale-sensor refusal, reserve-aware advice, one
bounded irrigation effect, restart without duplicate command or order, and complete export and
deletion. No live merchant, account, address, payment, mains, battery, pump, well, camera, network,
robot, permit, or construction effect enters the slice.

Related: [Composition Portfolio](index.md) · [Legion](../sepulcher/extensions/legion.md) ·
[Workflow](../adr/28-workflow.md)
