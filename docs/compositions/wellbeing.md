---
title: Wellbeing
icon: material/scale-balance
---

# :material-scale-balance: Wellbeing

Wellbeing helps one consenting adult decide what food and ordinary movement fit, then record what
actually happened without turning either into a verdict about the person. It plans and reflects;
it neither owns the kitchen stores nor acquires what the household lacks.

## Contract

| Field | Reference contract |
| --- | --- |
| **Identity** | `wellbeing` revision `1` |
| **Principal Pattern** | `wellbeing.plan_cycle@1` |
| **Application begins with** | A consented adult profile, selected modes, hard restrictions, soft preferences, time, equipment, and an attributable `InventorySnapshot@1` when food availability matters |
| **Application can return** | An editable food and ordinary-movement plan, honest infeasibility, purpose-limited `FoodNeed@1`, or confirmed check-in and reflection |
| **Application stops before** | Diagnosis, treatment, clinical or supplement advice, claims that food or movement is safe, household-stock mutation, sourcing, cart creation, checkout, payment, or hidden health disclosure |

Wellbeing owns profile and plan revisions, restrictions, preferences, journals, check-ins,
schedules, exports, and deletion records. [Homestead](homestead.md) owns household stores and
recurring provision. The Magus approves every profile, plan, share, external use, export, and
deletion. A Mind may propose and explain; deterministic tools own units, ingredient closure, hard
constraints, typed handoffs, and deletion verification.

Its other Patterns are `wellbeing.profile@1`, `wellbeing.check_in@1`,
`wellbeing.journal@1`, `wellbeing.review_cycle@1`, `wellbeing.export@1`, and
`wellbeing.delete@1`.

## Plan and check in

1. `wellbeing.profile@1` creates an immutable, reviewed profile from restrictions, preferences,
   time, equipment, enabled modes, consent, and privacy. Relaxing a hard restriction requires a
   confirmed successor profile.
2. `wellbeing.plan_cycle@1` pins profile, consent, policy, Pattern, food catalogue, tool, provider,
   and any `InventorySnapshot@1` revision. Deterministic checks preserve units, traverse
   ingredients to a finite depth, and mark candidates `blocked`, `unresolved`, or `eligible`;
   eligible never renders as “safe.”
3. The solver enforces exclusions, equipment, time windows, and operator maxima before softer
   preferences such as variety, convenience, and cost. It returns no feasible plan instead of
   violating a hard rule. The Magus edits, approves, or rejects every result.
4. When available food cannot support an approved plan, Wellbeing may emit `FoodNeed@1`. It states
   quantities, declared exclusions, useful product traits, expiry, privacy class, and unresolved
   flags—not a diagnosis, journal, measurement history, or merchant instruction.
5. `wellbeing.check_in@1` records only confirmed eating, completion, skip, substitution, duration,
   or reflection. A confirmed food event may be returned to Homestead for stock reconciliation;
   silence, a plan, or a receipt never proves consumption.
6. `wellbeing.journal@1` preserves operator words. `wellbeing.review_cycle@1` may report neutral
   counts and propose the next manual intent, but cannot silently change the next plan or order
   household goods.

Unit conversion uses decimal arithmetic and rejects incompatible dimensions. Volume becomes mass
only with sourced ingredient-specific density; serving, 100 g, and whole-package bases remain
distinct. A model cannot invent food identity, fill an unknown quantity, or infer eating from
availability, purchase, or silence.

## Homestead handoff

Homestead may provide only a versioned, freshness-visible `InventorySnapshot@1`: food identity,
quantity interval, location class, expiry or freshness evidence, storage-condition uncertainty,
and provenance. Wellbeing does not receive merchant credentials, payment data, delivery addresses,
whole receipts, or unrelated household stock.

Wellbeing returns only `FoodNeed@1` and explicit confirmed-consumption events. Journals,
measurements, symptoms, diagnoses, medication, clinical records, movement history, and genetics do
not enter Homestead, shop queries, catalogues, carts, providers, or merchant messages. Taste remains
corrigible testimony, not a household purchasing rule.

Profiles, sources, plan revisions, decisions, check-ins, journals, derived summaries, schedules,
exports, deletion fences, and deletion receipts remain separately attributable. Records distinguish
`user_entered`, `source_imported`, `model_proposed`, `deterministically_derived`, and
`user_confirmed`; one generic health blob owns none of them.

## Medical, time, and recovery lines

Children, pregnancy and postpartum, eating-disorder support, rehabilitation, clinical conditions,
biomarkers, medication interactions, and emergencies require separately governed applications.
Wellbeing does not diagnose, certify kitchen cross-contact, infer calorie expenditure, analyze gait
or form, contact clinicians, share automatically, punish a skipped activity, or read silence as
success. “My knee hurt” remains operator-authored and halts automated progression without
inferring injury, cause, adherence, or treatment.

Storage and inference are local by default. Remote providers, lookup, reminders, retained media,
calorie or weight features, imports, sharing, export, or research use require revocable,
purpose-specific consent. Schedules are opt-in, timezone-aware, bounded, pausable, and revocable;
missed reminders expire and reviews coalesce. Restart resumes only compatible pinned work. Deletion
fences admission, disables schedules, drains atomic work, removes permitted records and
derivatives, verifies absence, and leaves a content-free receipt; restored backups reapply
tombstones before reopening data.

## Proving the cycle

Use a network-disabled synthetic adult profile, a small reviewed food catalogue, and an attributed
inventory snapshot to produce a three-day plan. Prove hard ingredient and activity conflicts,
unresolved units, edit and approval, honest infeasibility, minimal `FoodNeed@1`, confirmed and
skipped check-ins, export, deletion, and restart without duplicates. Use no real person, merchant,
account, receipt, address, payment, health record, or external lookup.

Related: [Composition Portfolio](index.md) · [Workflow](../adr/28-workflow.md)
