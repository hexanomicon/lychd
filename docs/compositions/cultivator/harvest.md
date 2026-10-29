---
title: Harvest
icon: material/basket
---

# Harvest

The first basket is collected while the rest of the crop remains growing. A receipt must preserve
that partial result even if accepting the basket into household stores fails.

## Collection evidence

Use `cultivator.record_harvest@1` to record a collection in `CultivatorHarvestReceipt@1`. Identify
the source culture and cycle, collection event, effective and recorded times, actor, material
identity, quantity, unit, uncertainty, condition, and disposition. When collection happens in
several parts, give each part a distinct event identity. The source culture continues unless
explicit evidence ends it.

Estimated yield, collected harvest, accepted stock, and consumption are separate
claims. Collection does not establish food safety. Amendments preserve the earlier
claim and identify the corrected evidence.

## Store acceptance

[Homestead stores](../homestead/stores.md) may accept an exact harvest receipt once
as a source-lot event. Collection and store acceptance are tracked independently.
An unaccepted collection remains collected; accepted quantity requires the store
owner's evidence.

On import, use correlation and the exact receipt references to find the original source event.
A duplicate must resolve to that event without adding stock again. If the receipt was corrected,
reconcile its delta against prior acceptance, including changes to quantity, units, and
disposition. Merely replacing the latest receipt view cannot repair inventory already accepted.

A failed or lost acknowledgment leaves acceptance unknown. Reconcile the store event
before resending or amending; never recut the crop to repair a message failure.
Partial acceptance retains both the collected amount and the independently accepted
amount, with the remaining disposition unresolved or explicitly recorded.

Return to [Cultivator](index.md).
