---
title: Harvest
icon: material/basket
---

# Harvest

The first basket is collected while the rest of the crop remains growing. A receipt must preserve
that partial result even if accepting the basket into household stores fails.

## Collection evidence

`cultivator.record_harvest@1` produces `CultivatorHarvestReceipt@1`.
Each receipt identifies the source culture and cycle, collection event, effective and
recorded times, actor, material identity, quantity, unit, uncertainty, condition, and disposition.
Repeated partial collections receive distinct event identities and preserve the
source culture unless explicit evidence ends it.

Estimated yield, collected harvest, accepted stock, and consumption are separate
claims. Collection does not establish food safety. Amendments preserve the earlier
claim and identify the corrected evidence.

## Store acceptance

[Homestead stores](../homestead/stores.md) may accept an exact harvest receipt once
as a source-lot event. Collection and store acceptance are tracked independently.
An unaccepted collection remains collected; accepted quantity requires the store
owner's evidence.

Duplicate import must resolve to the same source event without adding stock again.
A corrected receipt requires explicit delta reconciliation against prior acceptance,
including quantity, units, and disposition changes; replacing the latest view alone
cannot repair inventory. Correlation and exact receipt references preserve that chain.

A failed or lost acknowledgment leaves acceptance unknown. Reconcile the store event
before resending or amending; never recut the crop to repair a message failure.
Partial acceptance retains both the collected amount and the independently accepted
amount, with the remaining disposition unresolved or explicitly recorded.

Return to [Cultivator](index.md).
