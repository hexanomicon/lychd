---
title: Cultivator
icon: material/sprout
---

# Cultivator

A plant changes pots; a bed produces several partial harvests. Cultivator keeps the growing
subject, its conditions, and the work behind each result connected across those changes.
The Native Reference Composition identity is `cultivator.cultivation`, revision `1`.
It covers plants and cultivated fungi for ornament, food, seed, or propagation; purpose is
independent of taxonomy and place.

## Contract and map

This is a designed contract. No models, migrations, runtime, or fixtures are delivered
here. [Composition portfolio delivery](../../state-of-the-work.md#composition-portfolio-delivery)
owns delivery status. [Persistence law](../../adr/06-persistence.md) and
[workflow law](../../adr/28-workflow.md) govern implementation.

| Pattern | Durable records |
| --- | --- |
| [`cultivator.record_culture@1`](cultures.md) | `CultivatorCulture@1`, `CultivatorObservation@1`, `CultivatorGrowingProfile@1` |
| [`cultivator.assess_space@1`](growing-space.md) | `CultivatorGrowingSpace@1`, `CultivatorPlacement@1`, `CultivatorEnvironmentNeed@1` |
| [`cultivator.review_cycle@1`](lifecycle.md) | `CultivatorCycle@1` |
| [`cultivator.plan_tending@1`](tending.md) | `CultivatorTendingPlan@1`, `CultivatorSupplyNeed@1` |
| [`cultivator.record_work@1`](tending.md#execution-and-results) | `CultivatorWorkEvent@1`, `CultivatorWorkResult@1` |
| [`cultivator.record_harvest@1`](harvest.md) | `CultivatorHarvestReceipt@1` |

These six Patterns are independently invocable. Enter through a culture's identity, its growing
space or lifecycle, the tending work due, or a collected harvest.

## Boundaries and admission

[Keeper](../keeper/index.md) owns animals and colonies; Cultivator owns plants and cultivated fungi.
[Homestead](../homestead/index.md) retains infrastructure, stores, and utilities.
Cultivator owns the cultivation capability extracted into its new identity; retired
`homestead.tend_land@1` is neither an alias nor reinterpreted history.

Admission fixes the responsible grower and permissions, exact culture/placement/profile revisions,
requested observe/advise/record work, source evidence, hazards, resource limits, and permitted
disclosure. Missing identity may permit an uncertain observation while blocking a specific action.

Manual evidence and human work remain valid without Homestead. Automation requires
separate admission by the owner of the actual controls. Deterministic safety checks
cannot establish biological appropriateness. Diagnostic authority, pesticide approval,
agricultural treatment permits, and food-safety certification remain outside this contract.

Use a [Suite](../products-and-suites.md) only for live start, await, retry, cancel,
or recovery across multiple owners. Settled references and receipts alone need no Suite.

## Privacy and recovery

Records remain local, Composition-owned PostgreSQL records under persistence law;
these logical contracts define record meaning and links, not physical tables or migrations.
Sharing selects exact records and purposes; there is no ambient database sharing. Media references
carry retention purpose because images can expose people and locations.

Each Invocation settles a proposed plan, recorded completion, refusal, infeasibility, partial,
unknown, or interrupted result as applicable. Recovery reconciles exact events and
acknowledgments before new action. Export preserves identifiers, corrections, evidence references,
and custody metadata without stopping care. Deletion, or an explicitly admitted custody migration,
must close affected schedules and resolve or hand off outstanding care and effect custody according
to retention and owner contracts. Closing a record does not remove a plant or dismantle its environment.

## First proof

A designed falsifying fixture should preserve an ornamental plant through repotting
and movement; split a seed batch into bed cohorts; refuse watering on unknown sensor
or reserve evidence; reconcile repeated partial harvest, duplicate import, and a
correction; exercise a perennial or fungi profile without universal stages; and recover
lost action acknowledgment after restart. Export must leave care active; deletion must close
affected schedules and settle or hand off custody. This fixture is a proof target, not delivered evidence.

Return to [Compositions](../index.md).
