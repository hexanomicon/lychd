---
title: Health, Food & Movement
icon: material/scale-balance
---

# :material-scale-balance: Health, Food & Movement

Health, Food & Movement helps one consenting adult turn declared restrictions, preferences, time,
equipment, and a pinned local catalogue into an editable plan. It can keep private reflections in
the operator's own words, but it never turns those words into a diagnosis or a score of wellbeing.

!!! note "Current material"
    No HFM Pattern, consented profile store, deterministic meal/movement solver, catalogue,
    reflection ledger, or schedule is registered or executable. Local text inference and general
    persistence do not constitute this sensitive application.

[State of Work](../state-of-the-work.md#composition-portfolio-delivery) owns the delivery boundary for this reference.

## Contract

| Field | Reference contract |
| --- | --- |
| **Identity** | `health.food_movement` revision `1` |
| **Principal Pattern** | `hfm.plan_cycle@1` |
| **Application begins with** | A consented adult profile, selected feature modes, hard restrictions, soft preferences, and pinned source revisions |
| **Application can return** | An editable approved meal, shopping, and ordinary-movement plan, or an explanation that no feasible plan exists |
| **Application stops before** | Diagnosis, treatment, clinical nutrition, medication or supplement advice, rehabilitation, emergency monitoring, and any claim that food or movement is safe |

HFM owns profile versions, restrictions, preferences, plan revisions and decisions, journals,
check-ins, schedules, admitted sources, exports, and deletion records. The Magus approves every
profile, plan, share, external use, export, and deletion. Deterministic tools own units,
ingredient closure, restriction checks, constraint solving, and deletion verification; a Mind may
propose or explain, but cannot relax a hard constraint or restate model prose as operator fact.

Its remaining Patterns are `hfm.profile_setup@1`, `hfm.check_in@1`, `hfm.journal@1`,
`hfm.review_cycle@1`, `hfm.export@1`, and `hfm.delete@1`. A changed graph, input, consent, or
recovery rule requires a new Pattern revision.

## One planning cycle

1. `hfm.profile_setup@1` creates an immutable profile version from reviewed normalization,
   restrictions, preferences, time, equipment, feature modes, and fresh consent. Relaxing a hard
   restriction requires a confirmed successor profile.
2. `hfm.plan_cycle@1` pins the profile, consent, policy, Pattern, catalogue, tool, and provider
   revisions, then resolves local records into typed candidates.
3. Deterministic checks preserve original and normalized units, traverse ingredients and
   subingredients to a finite depth, and classify each candidate as `blocked`, `unresolved`, or
   `eligible`. `eligible` never renders as “safe.”
4. The solver enforces exclusions, equipment, time windows, and operator maxima before optimizing
   softer concerns such as variety, convenience, and cost. It returns no feasible plan instead of
   violating the least convenient hard rule.
5. The Magus edits, approves, or rejects the result. Every substitution and post-model edit is
   checked again before approval.
6. `hfm.check_in@1` records only confirmed completion, skip, substitution, duration, or reflection;
   `hfm.journal@1` preserves original text and optional tags; `hfm.review_cycle@1` may report
   neutral counts and propose the next manual intent, but never changes the next plan by itself.

Unit conversion uses decimal arithmetic and rejects incompatible dimensions. Volume becomes mass
only with a sourced ingredient-specific density, while serving, 100 g, and whole-package bases
remain distinct. Incomplete ingredient closure, ambiguous serving, cross-contact, translation,
identity, or conflicting data stays `unresolved`.

## Sensitive records and household handoff

Records distinguish `user_entered`, `source_imported`, `model_proposed`,
`deterministically_derived`, and `user_confirmed`. Profiles, sources, plan revisions, decisions,
check-ins, journals, derived summaries, schedules, exports, deletion fences, and receipts remain
separate records with parents and revisions; they are not one generic health blob.

Source releases keep identity, URI or record id, retrieval and release time, digest, schema,
licence, locale, normalizer revision, quality flags, and supersession. Refresh imports beside old
releases so an old plan remains reproducible.

HFM may send [Lifestyle Steward](lifestyle-steward.md) only an approved, versioned,
purpose- and expiry-bound `ProvisionConstraintSet`: exclusions, enabled pattern or target interval,
selected variety or preparation needs, privacy class, and unresolved-source flags. Journals,
measurements, symptoms, diagnoses, medication, clinical records, movement history, and genetics do
not cross; Lifestyle owns receipts, inventory, stores, routes, carts, orders, and delivery.

## Medical line, time, and erasure

Children, pregnancy and postpartum, eating-disorder support, injury rehabilitation, clinical
conditions, biomarkers, medication interactions, and emergencies require separately governed
applications. HFM does not certify kitchen cross-contact, infer calorie expenditure, analyze gait
or form, purchase, contact clinicians, share automatically, punish a skipped activity, or read
silence as success. A note such as “my knee hurt” remains operator-authored and halts automated
progression without inferring injury, cause, adherence, or treatment.

Storage and inference are local by default. Remote providers, live lookup, reminders, retained
media, calorie or weight features, imports, sharing, export, or research use require revocable,
purpose-specific consent. Restricted logs redact payloads; raw media, embeddings, caches,
summaries, checkpoints, exports, and backups share the retention and deletion inventory.

Schedules are opt-in, timezone-aware, bounded, pausable, and revocable. Missed reminders expire
and periodic reviews coalesce. Restart resumes only compatible pinned work; changed inputs or
external uncertainty park for review. Deletion first fences admission, revokes schedules and
remote consent, drains atomic work, removes records and derivatives, verifies absence, then writes
a content-free receipt; restored backups must reapply tombstones before reopening records.

## Proving cycle

Use a synthetic adult profile and a small reviewed local catalogue to produce a three-day plan.
Prove calorie-free and weight-neutral operation; rejection of seeded ingredient and activity
conflicts; unresolved ingredients and units; edit, approval, rejection, skip, and check-in;
documented export; complete deletion; clean install, migration, restart, and selected recovery.
Keep the slice single-principal and network-disabled, with no clinical record, Portal, wearable,
biomarker, audio, image, or external lookup.

Related: [Composition Portfolio](index.md) · [Lifestyle Steward](lifestyle-steward.md) ·
[Workflow](../adr/28-workflow.md)
