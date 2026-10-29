---
title: Eating
icon: material/food-apple-outline
---

# :material-food-apple-outline: Eating

A cupboard can contain ingredients without containing a feasible meal. Eating turns reviewed restrictions, available food, time, and equipment into choices the Magus can edit, approve, or reject. It also provides preparation guidance; a suggestion records neither cooking nor consumption.

## Plan under hard constraints

The food mode of `wellbeing.plan_cycle@1` pins profile, consent, policy, Pattern, reviewed food catalogue, tools, provider, and any `InventorySnapshot@1`. Deterministic checks traverse ingredients to a finite depth and classify each candidate as `blocked`, `unresolved`, or `eligible`. The interface never translates eligible into “safe.”

An unknown package quantity stays unknown. Decimal arithmetic preserves dimensions; volume becomes mass only through sourced ingredient-specific density. Serving, 100 g, and whole-package bases remain distinct. Neither a model nor a convenient recipe may invent identity or quantity to make the arithmetic close.

Exclusions, equipment, time windows, and operator maxima are hard gates. Variety, convenience, and cost influence the remaining choices. When no choice passes, the result is no feasible plan. Eating does not certify kitchen cross-contact or medical safety.

## Minimal Homestead handoff

[Stores](../homestead/stores.md) supplies only the food identity, quantity interval, location class, freshness or expiry evidence, storage-condition uncertainty, and provenance in `InventorySnapshot@1`. Whole receipts, credentials, payment, addresses, and unrelated stock remain at home with their owner.

If an approved plan lacks ingredients, send only what [Provision](../homestead/provision.md) needs in `FoodNeed@1`: quantities, declared exclusions, useful product traits, expiry, privacy class, and unresolved flags. Keep diagnosis, journal, measurement, medication, genetics, movement history, and merchant instructions out of it. When `ProvisionResult@1` returns, Eating uses its availability evidence to decide whether the plan still fits.

After the meal, only an explicit `wellbeing.check_in@1` can confirm eating or substitution and send a minimal consumption event for stock reconciliation. A purchase, recipe, prepared household lot, plan, or silence cannot establish what the person ate. Eating itself never sources products, mutates stores, builds carts, or pays.

Return to [Wellbeing](index.md).
