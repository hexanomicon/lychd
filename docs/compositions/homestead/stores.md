---
title: Stores
icon: material/fridge-outline
---

# :material-fridge-outline: Stores

The receipt says two packages; the photograph leaves their size uncertain. Stores keeps the evidence and a quantity interval until a correction resolves it. Pantry, fridge, freezer, cellar, and prepared food share this attributable custody without becoming advice about what a person should eat.

## Evidence before quantity

`homestead.ingest_receipt@1` retains the admitted image or text, OCR geometry, merchant and transaction fields, exact money, line evidence, corrections, equations, and discrepancies. OCR is a proposal. A model cannot invent a barcode, merge package sizes, or force totals to balance.

Resolve product identity through GTIN or SKU, merchant product, named package, product family, then unresolved. Each lot keeps its source, location class, quantity interval, acquisition or harvest event, expiry evidence, storage uncertainty, and disposition.

`homestead.reconcile_stores@1` projects acquisition, harvest, confirmed consumption, disposal, transfer, correction, and preparation events into those intervals. Confirmed cooking may remove inputs and add a prepared output to household custody. It still says nothing about who ate it. A purchase, recipe, available ingredient, or silence proves neither consumption nor food safety.

## Minimal view for Wellbeing

[Wellbeing](../wellbeing/eating.md) receives only `InventorySnapshot@1`: attributed food identity, quantity interval, location class, expiry/freshness evidence, storage-condition uncertainty, and provenance. Merchant credentials, payment, addresses, whole receipts, and unrelated stock do not cross.

An explicit confirmed-consumption event may return for reconciliation. Journals, measurements, symptoms, diagnoses, medication, clinical records, movement history, and genetics have no place in the stores ledger. Unknown identity, quantity, condition, and expiry remain visible, and restart duplicates neither receipt acceptance nor reconciliation.

Return to [Homestead](index.md).
