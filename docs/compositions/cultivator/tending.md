---
title: Tending
icon: material/watering-can
---

# Tending

A bed needs water, but the latest tank reading is stale. Tending must preserve the need and the
resource uncertainty together until a reviewed plan can name feasible work.

## Assessed work

`cultivator.plan_tending@1` produces `CultivatorTendingPlan@1` and
`CultivatorSupplyNeed@1`. A coherent assessed plan links subjects, placement,
source evidence, and reviewed profile revision to watering, resource, substrate,
repotting, or pruning work.

Each action carries its own safe bounds, due window, expiry, stop conditions, and
expected evidence. Unknown or stale evidence cannot silently satisfy those bounds.
Planning may refuse an action or record infeasibility rather than manufacture care
advice.

A supply need binds its originating owner and revision and records minimum necessary quantity,
unit, product traits, constraints, purpose, validity/expiry, privacy class, and unknowns.
[Homestead stores](../homestead/stores.md) may return an exact `SupplySnapshot@1`, while
[Provision](../homestead/provision.md) returns `ProvisionResult@1`. These establish stock or
availability, not biological suitability or completed use.
A material substitution returns for Cultivator review before changing the plan or submitting an
order; availability cannot weaken the reviewed culture requirements.

## Execution and results

`cultivator.record_work@1` produces `CultivatorWorkEvent@1` and
`CultivatorWorkResult@1`. Record the actual action, actor, effective and recorded
times, quantity and unit uncertainty, evidence, plan reference, and outcome. Partial
work retains its actual result and unresolved remainder. Stock use is reconciled and
deduplicated by event; a plan or provision receipt does not imply consumption.

When Homestead supplies water, its actual resource limits remain decisive. Automatic actuation requires a separately
admitted owner, current evidence, and applicable vetoes. A missing acknowledgment
means unknown execution; do not retry an action merely because its reply was lost.

Any exact [Legion](../../adr/42-legion.md) request passes through the commissioned owner with a fenced task,
zone, resources, expiry, and stop conditions. The body retains a fresh veto. Such a
request grants no general robot authority.

## Finite recovery

A work attempt records completed, refused, infeasible, partial, unknown, or interrupted
results as applicable. Restart uses event identity, owner evidence, and acknowledgments
to establish what occurred before deciding further work. Cancellation settles only the admitted
work and preserves any performed effect; disabling future schedule Occurrences is a separate act.
Cross-owner live recovery follows
the [Suite boundary](../products-and-suites.md); settled receipt exchange alone does
not require a Suite.

Return to [Cultivator](index.md).
