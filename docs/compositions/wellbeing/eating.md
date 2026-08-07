---
title: Eating
icon: material/food-apple-outline
---

# :material-food-apple-outline: Eating

Eating helps the Magus choose meals and preparation steps. It may consider attributed household
availability, but it never sources products, mutates stores, builds a cart, pays, or treats a meal
suggestion as evidence of cooking or consumption.

## Plan under hard constraints

For its food mode, `wellbeing.plan_cycle@1` pins profile, consent, policy, Pattern, reviewed food
catalogue, tool, provider, and any `InventorySnapshot@1` revision. Deterministic checks preserve
units, traverse ingredients to a finite depth, and mark candidates `blocked`, `unresolved`, or
`eligible`; eligible never renders as “safe.”

The solver enforces exclusions, equipment, time windows, and operator maxima before softer
preferences such as variety, convenience, and cost. It returns no feasible plan instead of
violating a hard rule. The Magus edits, approves, or rejects every meal and its preparation
guidance.

Unit conversion uses decimal arithmetic and rejects incompatible dimensions. Volume becomes mass
only with sourced ingredient-specific density; serving, 100 g, and whole-package bases remain
distinct. A model cannot invent food identity, fill an unknown quantity, or infer eating from
availability, purchase, preparation, or silence.

Eating does not certify kitchen cross-contact or claim that any ingredient, meal, or preparation
is medically safe.

## Minimal Homestead handoff

[Homestead Stores](../homestead/stores.md) may provide only `InventorySnapshot@1`: food identity,
quantity interval, location class, expiry or freshness evidence, storage-condition uncertainty,
and provenance. Whole receipts, credentials, payment, addresses, and unrelated stock stay behind.

When availability cannot support an approved plan, Eating may emit `FoodNeed@1` with quantities,
declared exclusions, useful product traits, expiry, privacy class, and unresolved flags. It carries
no diagnosis, journal, measurements, medication, genetics, movement history, or merchant
instruction. [Provision](../homestead/provision.md) may return `ProvisionResult@1`; Eating then
decides whether the plan still fits without claiming health, purchase, or adherence.

Only an explicit `wellbeing.check_in@1` may confirm eating or substitution and return a minimal
consumption event for stock reconciliation. A recipe, plan, prepared household lot, receipt, or
silence does not.

Return to [Wellbeing](index.md).
