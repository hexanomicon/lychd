---
title: Homestead
icon: material/solar-power
---

# :material-solar-power: Homestead

Homestead keeps one house, well, solar field, battery, garden, network, camera set, and small droid
fleet legible as a bounded place. It helps the Magus plan and operate that place locally while the
controller nearest a physical consequence keeps the final power to refuse.

!!! note "Current material"
    No Homestead Pattern, site/resource ledger, device or sensor adapter, safety controller,
    camera path, droid profile, or physical effect is registered or executable. Legion, Tether,
    remote IAM, and visual custody remain Designed or Partial common substrate.

[State of Work](../state-of-the-work.md#composition-portfolio-delivery) owns the delivery boundary for this reference.

## Contract

| Field | Reference contract |
| --- | --- |
| **Identity** | `homestead.steward` revision `1` |
| **Principal Pattern** | `homestead.map_site@1` |
| **Application begins with** | A reviewed site boundary, asset and resource evidence, responsible people, hazards, policy, and commissioned device limits |
| **Application can return** | `HomesteadPlan@1`, a freshness-visible resource ledger, bounded work or control intents, alerts, and effect receipts |
| **Application stops before** | Design certification, permits, construction, potability claims, unsafe energization, interlock bypass, hazardous repair, or general robot authority |

Homestead owns the property model, resource policy, observations, forecasts, plans, alerts,
maintenance, work orders, and admission of homestead effects. Professionals, manufacturers,
utilities, local controllers, and the Magus retain their own judgment. A Mind may interpret or
propose; deterministic tools own units, thresholds, resource balance, freshness, set-point limits,
exclusion windows, effect predicates, and idempotency.

There is no accepted general smart-home or physical-actuator Domain. [Legion](../adr/42-legion.md)
owns designed law for robots and embedded bodies; Workflow, Security, IAM, Vision, and host owners
retain their boundaries. This page cannot authorize a device path.

## Ground to bounded intent

1. `homestead.map_site@1` maps buildings, plots, water points, circuits, critical loads,
   generation, storage, network zones, cameras, devices, droid work zones, hazards, unknowns, and
   professional or permit needs into a reviewable `HomesteadPlan@1`.
2. `homestead.observe_cycle@1` admits fresh bounded telemetry and weather observations, checks
   attribution, calibration, staleness, and contradiction, then updates resource ledgers or shows
   an honest gap. It never actuates.
3. `homestead.balance_energy@1` combines critical-load policy with PV, load, battery, grid, alarm,
   and forecast evidence. It may return reserve-aware advice or an exact set-point intent inside
   inverter, BMS, anti-islanding, thermal, fire, and electrician-set protection.
4. `homestead.guard_water@1` combines well, tank, pressure, quality, weather, and allocation
   evidence. Any pump or valve intent stays inside dry-run, pressure, level, freeze, contamination,
   and reserve interlocks; no sensor result becomes a potability claim.
5. `homestead.tend_land@1` produces explainable human or droid work orders from plot, crop, soil,
   weather, and resource state. Pesticide, livestock, and food-safety authority are absent by
   default.
6. `homestead.maintain_site@1` turns alarms, inspections, runtime, or calendar evidence into
   containment advice, research needs, scheduled work, verification, and an unresolved state when
   silence or weak evidence cannot close the fault.

Every request states one of four postures: observe; advise; bounded stewardship inside a live,
commissioned envelope; or deterministic safe containment. Schedules create finite Occurrences,
not an always-awake model.

## Resource ledgers and Portfolio handoffs

Energy, water, land, habitat, network, camera, and embodied-node ledgers remain separate. A device
report becomes an attributed observation, then a calibrated derivation, then a reconciled resource
estimate; none of those stages is silently collapsed into “home state.” Records append independent
revisions for observations, calibration, forecasts, plans, alerts, approvals, commands,
controller receipts, maintenance, laboratory evidence, professional documents, and configuration.

| Handoff | Boundary |
| --- | --- |
| Requirements → [Tech Scavenger](tech-scavenger.md) | Homestead states compatibility, certification, serviceability, environment, budget, and evidence needs; Tech returns dated candidate and seller evidence, never commissioning authority. |
| Harvest or acquisition → [Lifestyle Steward](lifestyle-steward.md) | Lifestyle may admit household inventory; Homestead keeps plot, crop, resource, and work truth. Harvest does not prove safe food or consumption. |
| Product or site request → Scout | Scout acquires attributed observations; web text cannot become a physical instruction. |
| Typed work → a Legion node | The droid receives a fenced task, zone, resources, expiry, and stop conditions—not shell access or a general farm mandate. |

[Tether](../sepulcher/extensions/tether.md) may eventually carry private inspection and exact
approved controls, but tunnel possession supplies no Principal or effect authority and never falls
back to a public dashboard.

## Physical veto and rupture

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
Deletion revokes grants, disables schedules, drains or contains admitted motion, inventories
hazards and third-party handoffs, and removes permitted artifacts; it cannot erase external records.

## Proving cottage

Use a network-disabled synthetic cottage with one PV array, critical and deferrable loads, battery
and BMS fixtures, a well pump and calibrated tank, two beds, weather and soil fixtures, segmented
device identities, one masked camera fixture, and one simulated watering droid. Prove stale and
contradictory sensor refusal, reserve-aware advice, one bounded irrigation effect,
lost-acknowledgement reconciliation, emergency-stop priority, restart without duplicate command,
and complete export and deletion. No live mains, battery, pump, well, camera, network, robot,
product crawl, message, permit, or construction effect enters the slice.

Related: [Composition Portfolio](index.md) · [Legion](../sepulcher/extensions/legion.md) ·
[Workflow](../adr/28-workflow.md)
