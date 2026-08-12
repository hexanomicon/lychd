---
title: Homestead
icon: material/solar-power
---

# :material-solar-power: Homestead

Homestead keeps one household—city flat or cottage—legible as a bounded place. What arrives from
Kaufland, Lidl, a local market, or the household's own field enters the same attributable custody;
the source does not change who owns the stock.

## Contract

| Field | Reference contract |
| --- | --- |
| **Identity** | `homestead.steward` revision `1` |
| **Patterns** | `homestead.map_site@1`, `homestead.reconcile_stores@1`, `homestead.plan_provision@1`, `homestead.tend_land@1`, and `homestead.maintain_site@1` |
| **Application begins with** | A reviewed household boundary, asset and resource evidence, responsible people, recurring provision policy, hazards, budgets, and commissioned device limits |
| **Application can return** | `HomesteadPlan@1`, freshness-visible resource and stores ledgers, `InventorySnapshot@1`, a reviewable provision plan or cart, acknowledged, refused, or unknown checkout result, bounded work or control intents, alerts, and effect receipts |
| **Application stops before** | Health or consumption judgment, unapproved purchase or disclosure, irregular high-value acquisition, design certification, permits, construction, potability claims, unsafe energization, interlock bypass, hazardous repair, or general robot authority |

## The household

- [Utilities](utilities.md) maps and observes energy, water, gas or stored fuel, network, devices,
  and their bounded controls.
- [Stores](stores.md) keeps pantry, fridge, freezer, cellar, receipt, lot, and stock-transformation
  truth.
- [Provision](provision.md) observes ordinary suppliers, prepares replenishment, builds carts, and
  reconciles checkout.
- [Cultivation](cultivation.md) turns land, soil, crop, weather, and resource evidence into bounded
  tending work and attributable harvest.
- [Maintenance](maintenance.md) turns faults and inspections into containment, repair research,
  scheduled work, and verified closure.

Homestead owns the household model, resource policy, stores, recurring provision, forecasts,
alerts, maintenance, work orders, and admission of homestead effects. Professionals,
manufacturers, utilities, merchants, local controllers, and the Magus retain their judgment. A
Mind may interpret or propose; deterministic tools own units, identity gates, money, stock
reconciliation, thresholds, resource balance, freshness, set-point limits, effect predicates, and
idempotency.

Every request declares one posture: observe; advise; bounded stewardship inside a live,
commissioned envelope; or deterministic safe containment. Schedules create finite Occurrences,
not an always-awake model. There is no accepted general smart-home or physical-actuator Domain;
[Legion](../../adr/42-legion.md), Workflow, Security, IAM, Vision, and host owners retain those
boundaries.

Those Pattern names identify separately invocable household journeys. The more granular versioned
names on the leaf pages—observation, balancing, receipt ingestion, shop observation, cart build,
checkout, and guarded controls—are proposed Spell contracts placed by one of those Patterns. A
single `map_site` casting cannot truthfully claim the whole application finish set.

## Portfolio seams

[Wellbeing](../wellbeing/index.md) chooses what a consenting adult eats and how they move;
Homestead keeps household custody and provision. [Scavenger](../scavenger/index.md) keeps irregular,
high-value, compatibility-heavy, property, and seller-negotiated acquisition. Typed requirements,
inventory snapshots, food needs, provision results, and confirmed consumption cross these seams;
credentials, private records, and effect authority do not.

Research about household goods or a site crosses to Scout as attributed observations; web text
never becomes a physical instruction.

Coordinates, floor plans, camera material, and device access remain restricted. Deletion revokes
grants, disables schedules and checkout authority, drains or contains admitted motion, inventories
hazards, open orders, and third-party handoffs, and removes permitted records and artifacts. It
cannot erase merchant-held or other external records.

## Proving the household

Use one network-disabled fixture spanning a city flat and a cottage: pantry, cold stores, a
synthetic receipt, bounded Kaufland/Lidl offer snapshots, one garden harvest, PV, battery and BMS,
a well and tank, soil observations, segmented device identities, and one watering droid. Prove
receipt correction, acquisition without inferred consumption, minimal Wellbeing handoffs,
unknown-checkout recovery, stale-sensor refusal, reserve-aware advice, one bounded irrigation
effect, restart without duplicate command or order, and complete export and deletion. No live
merchant, account, address, payment, mains, battery, pump, well, camera, network, robot, permit, or
construction effect enters the slice.

Related: [Composition Portfolio](../index.md) · [Workflow](../../adr/28-workflow.md)
