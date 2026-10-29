---
title: Stores
icon: material/fridge-outline
---

# :material-fridge-outline: Stores

The receipt says two packages; the photograph leaves their size uncertain. Stores keeps the evidence and a quantity interval until a correction resolves it. Pantry, fridge, freezer, cellar, and prepared food share this attributable custody. Feed, seed, substrate, and other care supplies keep their own identity, purpose, and storage constraints; their presence establishes no suitability for a person, animal, or culture.

## Evidence before quantity

`homestead.ingest_receipt@1` retains the admitted image or text, OCR geometry, merchant and transaction fields, exact money, line evidence, corrections, equations, and discrepancies. OCR is a proposal. A model cannot invent a barcode, merge package sizes, or force totals to balance.

Resolve product identity through GTIN or SKU, merchant product, named package, product family, then unresolved. Each lot keeps its source, location class, quantity interval, acquisition or harvest event, expiry evidence, storage uncertainty, and disposition.

`homestead.reconcile_stores@2` projects acquisition, accepted yield, confirmed consumption, disposal, transfer, correction, and preparation events into those intervals. Confirmed cooking may remove inputs and add a prepared output to household custody. It still says nothing about who ate it. A purchase, recipe, available ingredient, or silence proves neither consumption nor food safety.

## Care supplies and collected yields

`SupplySnapshot@1` exposes only the requested material identity, lot reference, quantity interval and units, purpose class, storage/expiry uncertainty, provenance, and snapshot revision/time. [Keeper](../keeper/feeding.md) and [Cultivator](../cultivator/tending.md) assess suitability from this minimal view; the human-food `InventorySnapshot@1` below remains unchanged. Credentials, receipts, unrelated lots, and private care records do not travel with either projection.

When an exact `KeeperCareEvent@1` or `CultivatorWorkEvent@1` confirms material issued from a named lot, reconcile it by source owner/event/revision and quantity with units. Repeated delivery of the event cannot remove stock twice. Likewise, the separate observations of feed offered, feed eaten, and leftovers disposed must not each deduct the original serving. Apply a later correction as an attributable adjustment, not another full deduction.

To bring collected material into stores, separately accept its exact `KeeperYieldReceipt@1` or `CultivatorHarvestReceipt@1` as a sourced lot. The receipt identifies source subject/culture, collection time, material, quantity interval/unit, condition uncertainty, and disposition. Deduplicate by source owner and collection-event identity, retain its revision, and reconcile amendments against the quantity already accepted.

Collection may have succeeded while stock acceptance is still pending. A missing import acknowledgement therefore never authorizes collecting again. Nor do live subjects, births, deaths, or projected yields automatically become stock. Even accepted custody supplies no food-safety, treatment, or consumption verdict.

## Minimal view for Wellbeing

[Wellbeing](../wellbeing/eating.md) receives only `InventorySnapshot@1`: attributed food identity, quantity interval, location class, expiry/freshness evidence, storage-condition uncertainty, and provenance. Merchant credentials, payment, addresses, whole receipts, and unrelated stock do not cross.

An explicit confirmed-consumption event may return for reconciliation. Journals, measurements, symptoms, diagnoses, medication, clinical records, movement history, and genetics have no place in the stores ledger. Unknown identity, quantity, condition, and expiry remain visible, and restart duplicates neither receipt acceptance nor reconciliation.

Return to [Homestead](index.md).
