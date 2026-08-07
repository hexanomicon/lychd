---
title: Stores
icon: material/fridge-outline
---

# :material-fridge-outline: Stores

Stores keeps pantry, fridge, freezer, cellar, and other household stock attributable. It knows
what may be present and how that estimate changed; it does not decide what a person should eat.

## Evidence before quantity

`homestead.ingest_receipt@1` admits a receipt without laundering OCR into truth. The record keeps
the admitted image or text, OCR geometry, merchant and transaction fields, exact money, line
evidence, corrections, equations, and discrepancies. A model cannot invent a barcode, merge
package sizes, or force totals to agree.

Exact product identity follows GTIN or SKU, merchant product, named package, product family, then
unresolved. Lots retain source, location class, quantity interval, acquisition or harvest event,
expiry evidence, storage-condition uncertainty, and disposition.

`homestead.reconcile_stores@1` projects harvest, acquisition, confirmed consumption, disposal,
transfer, correction, and preparation events into quantity intervals. Cooking is a household
stock transformation only when confirmed inputs leave stores and a prepared output enters custody;
it is not evidence that anyone ate it. Purchase, availability, a recipe, and silence likewise
prove no consumption or food safety.

## Minimal view for Wellbeing

Stores may send [Wellbeing](../wellbeing/eating.md) only a versioned `InventorySnapshot@1`:
attributed food identity, quantity interval, location class, expiry or freshness evidence,
storage-condition uncertainty, and provenance. It never exposes merchant credentials, payment,
delivery addresses, whole receipts, or unrelated household stock.

Wellbeing may return an explicit confirmed-consumption event for reconciliation. Journals,
measurements, symptoms, diagnoses, medication, clinical records, movement history, and genetics do
not enter household stock. Unknown identity, quantity, condition, or expiry remains visible.

Restart never duplicates receipt acceptance or stock reconciliation. Return to
[Homestead](index.md).
