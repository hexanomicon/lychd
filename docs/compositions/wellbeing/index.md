---
title: Wellbeing
icon: material/heart-pulse
---

# :material-heart-pulse: Wellbeing

A plan must fit the person who will live it. Wellbeing helps one consenting adult choose food and ordinary movement, revise those choices, and record what actually happened. An impossible plan can end as honest infeasibility. A skipped activity can remain a skip without becoming a verdict about the person.

Imagine planning the next three days with limited time, a small kitchen, and food already in the house. [Profile](profile.md) establishes the reviewed restrictions and preferences. [Eating](eating.md) checks meals and preparation; [Fitness](fitness.md) fits movement into the same person's limits. [Journal](journal.md) receives confirmed events and the Magus's own words after the day is lived.

## Contract

`wellbeing` revision `1` publishes principal Pattern `wellbeing.plan_cycle@1`. Planning begins with a consented adult profile, enabled modes, hard restrictions, soft preferences, time, equipment, and an attributable `InventorySnapshot@1` when availability matters. It can return an editable food-and-movement plan, infeasibility, or a purpose-limited `FoodNeed@1`.

The Composition also keeps confirmed check-ins and reflection through the separate Patterns described in [Journal](journal.md). Confirmation of eating or movement comes through an explicit `wellbeing.check_in@1`; planning cannot supply it.

Wellbeing owns profile and plan revisions, restrictions, preferences, journals, check-ins, schedules, exports, and deletion records. The Magus approves each profile, plan, share, external use, export, and deletion. A Mind proposes and explains; deterministic tools check units, ingredient closure, hard constraints, typed handoffs, and deletion.

## One person's cycle

An approved meal may reveal missing ingredients. Only the minimal food need crosses to [Homestead](../homestead/index.md), which owns stock, recurring provision, and confirmed preparation transformations. Wellbeing chooses what fits the person; it neither sources products nor changes household stock, carts, checkout, or payment. Taste remains corrigible testimony.

This application makes no diagnosis, treatment, clinical or supplement recommendation, or claim that food or movement is safe. Children, pregnancy and postpartum, eating-disorder support, rehabilitation, clinical conditions, biomarkers, medication interactions, and emergencies require separately governed applications. Private health material never follows a shopping request.

## Proving the cycle

A network-disabled synthetic adult fixture should produce a three-day plan from a reviewed food catalogue and inventory snapshot. It must expose ingredient and activity conflicts, unresolved units and infeasibility; permit edit and approval; pass only minimal `FoodNeed@1`; and preserve confirmed and skipped check-ins through restart, export, and deletion without duplicates. No real person, merchant, account, receipt, address, payment, health record, or external lookup enters that proof.

[Composition Portfolio](../index.md) · [Workflow](../../adr/28-workflow.md)
