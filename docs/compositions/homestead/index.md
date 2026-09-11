---
title: Homestead
icon: material/solar-power
---

# :material-solar-power: Homestead

A shop receipt and a confirmed harvest arrive by different roads, but both change what the household may have in its stores. Homestead keeps the place and its material custody legible across a city flat or cottage: equipment, resources, ordinary provision, maintenance, and the observations behind them. It works with manual records as well as commissioned devices.

The Magus can enter through a practical question:

- [Stores](stores.md): what is present, and which receipt, harvest, transfer, or correction changed the estimate?
- [Provision](provision.md): what ordinary supplies are missing, and what happened to the cart or order?
- [Utilities](utilities.md): which resources are available, uncertain, or reserved, and which commissioned controls may be requested?
- [Maintenance](maintenance.md): which fault remains open, and what evidence would close it?

[Keeper](../keeper/index.md) owns animal and colony care; [Cultivator](../cultivator/index.md) owns growing cultures and their tending. Their needs and confirmed yields can enter Homestead without transferring biological judgment.

## Contract

`homestead.steward` revision `2` publishes five independently invocable Patterns:

| Pattern | Bounded result |
| --- | --- |
| `homestead.map_site@1` | `HomesteadPlan@1` and freshness-visible resource evidence |
| `homestead.reconcile_stores@2` | reconciled lots, `InventorySnapshot@1`, or purpose-limited `SupplySnapshot@1` |
| `homestead.plan_provision@2` | provision plan, cart, or `ProvisionResult@1` from an admitted need |
| `homestead.apply_environment@1` | `HomesteadEnvironmentResult@1` for one bounded resource or commissioned control request |
| `homestead.maintain_site@1` | bounded work order, verification, or unresolved fault |

The finer observation, balance, receipt, shop, cart, checkout, and control names remain proposed Spell contracts placed by these Patterns. One `map_site` casting cannot claim every household outcome.

Admission fixes a reviewed household boundary, assets and resource evidence, responsible people, provision policy, hazards, budgets, and commissioned device limits. Depending on its Pattern, the result may be `HomesteadPlan@1`, freshness-visible resource or stores ledgers, `InventorySnapshot@1`, a provision plan or cart, acknowledged/refused/unknown checkout, bounded work or control intents, alerts, or effect receipts.

## The household

Every request declares its posture: observe, advise, bounded stewardship inside a live commissioned envelope, or deterministic safe containment. A Mind interprets and proposes. Deterministic tools check units, identities, money, reconciliation, freshness, thresholds, resource balance, set-point limits, effect predicates, and idempotency. Professionals, manufacturers, utilities, merchants, controllers, and the Magus retain their own judgment. Schedules create finite Occurrences.

Homestead owns household models, physical asset identity, resource policy, stores, recurring provision, forecasts, alerts, maintenance, work orders, and admission of its effects. Keeper and Cultivator retain care profiles, living-subject histories, biological suitability, and care outcomes. Homestead provides no health or consumption judgment, unapproved purchase/disclosure, design certification, permits, construction, potability claim, unsafe energization, interlock bypass, hazardous repair, or general robot authority. No general smart-home or physical-actuator Domain is accepted; [Legion](../../adr/42-legion.md), Workflow, Security, IAM, Vision, and host owners keep their boundaries.

## Portfolio seams

[Wellbeing](../wellbeing/index.md) decides what fits a consenting adult's eating and movement. [Scavenger](../scavenger/index.md) handles irregular, high-value, compatibility-heavy, property, and seller-negotiated acquisition. Exact inventory, needs, provision results, requirements, and confirmed consumption cross these seams. Credentials, private records, and authority stay with their owners. Scout supplies attributed research observations, never physical instructions.

Keeper and Cultivator may reference the same enclosure, greenhouse, tank, or circuit. Their placements and requirements remain separately owned. [Utilities](utilities.md#meet-an-environment-request) checks the joint commissioned envelope; a technical acknowledgement establishes no animal or plant care outcome. Settled needs, yields, and receipts need no Suite. Starting and recovering several owners' live work follows the [Suite boundary](../products-and-suites.md#homestead-keeper-and-cultivator).

Coordinates, plans, camera material, and device access remain restricted. Deletion revokes grants, disables schedules and checkout, drains or contains admitted motion, inventories hazards, orders, and handoffs, then removes permitted material. External merchant and other custody remains explicit.

## Proving the household

The required network-disabled flat-and-cottage fixture combines pantry/cold stores, feed and substrate lots, a synthetic receipt, bounded Kaufland/Lidl offers, attributed yield receipts, PV/battery/BMS, well/tank, segmented devices, and a watering droid. Follow these linked checks:

- Reconcile stores and provision through receipt correction without inferred consumption, minimal Wellbeing handoffs, and unknown-checkout recovery.
- Import a yield twice and correct it without duplicate stock; keep feed issued distinct from animal consumption.
- Test shared-enclosure demands through conflicting requirements, stale-sensor refusal, reserve-aware advice, and bounded irrigation without assuming biological success.
- Restart without duplicate commands or orders, then complete export and deletion.

Live merchants, accounts, addresses, payments, mains, batteries, pumps, wells, cameras, networks, robots, permits, and construction remain outside the slice.

## Revision continuity

Revision `2` retains Homestead's place, stores, provision, and maintenance ownership. It retires Designed revision `1`: cultivation is extracted into the new `cultivator.cultivation` identity, and `homestead.tend_land@1` has no executable alias. [The former cultivation route](cultivation.md) preserves that boundary. Keeper's animal-care contract is new work, not a renamed Homestead Pattern.

The new stores and provision Pattern revisions admit attributed care supplies and yield handoffs; `InventorySnapshot@1` and `ProvisionResult@1` keep their existing meaning. Existing Product, Suite, or profile pins require explicit review before selecting revision `2`; no pin silently follows the successor. Revision `1`, including its original five-Pattern catalogue, remains meaningful in history. No registry, Run, or stored Composition record used it, so there is no executable data migration. [State of Work](../../state-of-the-work.md#composition-portfolio-delivery) owns delivery evidence.

[Composition Portfolio](../index.md) · [Workflow](../../adr/28-workflow.md)
