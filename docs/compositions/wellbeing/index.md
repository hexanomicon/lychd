---
title: Wellbeing
icon: material/scale-balance
---

# :material-scale-balance: Wellbeing

Wellbeing helps one consenting adult decide what food and ordinary movement fit, then record what
actually happened without turning either into a verdict about the person. It plans and reflects;
it does not own household stores or acquire what is missing.

## Contract

| Field | Reference contract |
| --- | --- |
| **Identity** | `wellbeing` revision `1` |
| **Principal Pattern** | `wellbeing.plan_cycle@1` |
| **Application begins with** | A consented adult profile, selected modes, hard restrictions, soft preferences, time, equipment, and an attributable `InventorySnapshot@1` when food availability matters |
| **Application can return** | An editable food and ordinary-movement plan, honest infeasibility, purpose-limited `FoodNeed@1`, or confirmed check-in and reflection |
| **Application stops before** | Diagnosis, treatment, clinical or supplement advice, claims that food or movement is safe, household-stock mutation, sourcing, cart creation, checkout, payment, or hidden health disclosure |

## One person's cycle

- [Profile](profile.md) keeps reviewed needs, restrictions, preferences, consent, and lifecycle.
- [Eating](eating.md) chooses meals and preparation guidance, checks hard food constraints, and
  exchanges only minimal typed needs and availability with Homestead.
- [Fitness](fitness.md) plans ordinary movement inside declared time, equipment, and personal
  limits.
- [Journal](journal.md) keeps confirmed check-ins, the Magus's own words, neutral review, export,
  and deletion.

Wellbeing owns profile and plan revisions, restrictions, preferences, journals, check-ins,
schedules, exports, and deletion records. The Magus approves every profile, plan, share, external
use, export, and deletion. A Mind may propose and explain; deterministic tools own units,
ingredient closure, hard constraints, typed handoffs, and deletion verification.

[Homestead](../homestead/index.md) owns household stores, recurring provision, and confirmed stock
transformation. Taste remains corrigible testimony, not a household purchasing rule. Children,
pregnancy and postpartum, eating-disorder support, rehabilitation, clinical conditions,
biomarkers, medication interactions, and emergencies require separately governed applications.

## Proving the cycle

Use a network-disabled synthetic adult profile, a small reviewed food catalogue, and an
attributed inventory snapshot to produce a three-day plan. Prove hard ingredient and activity
conflicts, unresolved units, edit and approval, honest infeasibility, minimal `FoodNeed@1`,
confirmed and skipped check-ins, export, deletion, and restart without duplicates. Use no real
person, merchant, account, receipt, address, payment, health record, or external lookup.

Related: [Composition Portfolio](../index.md) · [Workflow](../../adr/28-workflow.md)
