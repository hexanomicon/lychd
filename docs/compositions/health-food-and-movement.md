---
title: Health, Food & Movement
icon: material/scale-balance
---

# :material-scale-balance: Health, Food & Movement

**A consenting adult can make their own meal, shopping, and ordinary-movement plans from a
consented profile and pinned local catalogues—then keep private reflections in their own words.**
Everything remains editable; nothing becomes a medical judgment.

| Local maturity | Identity | Default Pattern | Privacy ceiling |
| --- | --- | --- | --- |
| **Accepted Reference Composition** | `health.food_movement/rev1` | `hfm.plan_cycle@1` | `restricted`, local first |

## The line it will not cross

HFM plans meals, shopping needs, and ordinary movement. It can normalize units, enforce a
declared restriction, expose an unresolved source, and summarize only selected stored records.
It does **not** diagnose symptoms; advise on medication or supplements; prescribe treatment,
rehabilitation, or clinical nutrition; monitor emergencies; or certify food or movement as safe.
A request beyond that line stops rather than producing a care plan.

An entry such as “my knee hurt during the walk” may remain an operator-authored journal entry.
It stops automated progression: HFM does not infer an injury, a cause, adherence, wellbeing, or a
treatment. Children, pregnancy and postpartum, eating-disorder support, injury rehabilitation,
clinical conditions, biomarkers, medication interactions, and emergencies are separately
governed expansions, not profile options.

The non-goals are equally deliberate: no kitchen cross-contact certification, calorie or energy
expenditure inference, gait/form analysis, purchase, clinician contact, automatic sharing,
punishment for skipped activity, or reading silence as success.

## What the operator owns

The Magus consents to every profile, plan, sharing/external use, export, and deletion. HFM owns
profile versions, restrictions, preferences, plans and decisions, journals and check-ins,
schedules, admitted sources, exports, and deletion records. Deterministic tools own unit
conversion, ingredient closure, restriction checks, solving, and deletion verification. The Mind
may propose and explain, but cannot relax a hard constraint.

`hfm.profile_setup@1` creates an immutable profile version: hard restrictions, soft preferences,
time, equipment, selected feature modes, normalization review, and fresh consent. A hard
restriction is an instruction to enforce, not clinically verified fact. Relaxing it requires a
separate confirmed edit and a new profile version.

HFM offers calorie-free, weight-neutral, and body-measurement-free operation. Food and movement
records come from admitted immutable local releases; public queries never contain restrictions or
journal text. A source release records identity, URI/record id, release and retrieval time,
digest, schema, licence, locale, importer/normalizer revision, quality flags, and supersession.
Refresh imports beside the old release; historical plans stay pinned.

## Six finite scores

Patterns are immutable under [Workflow](../adr/28-workflow.md): a changed graph, input,
consent, or recovery rule is a new revision.

| Pattern | Operator result | Refusal/recovery law |
| --- | --- | --- |
| `hfm.profile_setup@1` | Immutable normalized profile | Confirmed edits create a successor, never silently alter history. |
| `hfm.plan_cycle@1` | Editable, approved meal/shopping/movement plan or an explanation | Candidates pin profile, consent, policy, source, tool, and provider revisions; post-validation edits validate again. |
| `hfm.check_in@1` | Confirmed completion, skip, substitution, duration, or reflection | Missing is `unknown`; concerning/out-of-scope words preserve only user text and halt automation. |
| `hfm.journal@1` | Private original entry and optional tags | A summary is a separate derived record; no diagnostic, risk, sentiment, or adherence score. |
| `hfm.review_cycle@1` | Neutral count and optional next manual intent | No causality, ranking, or inference from absence; it never changes the next plan itself. |
| `hfm.export@1` / `hfm.delete@1` | Principal-bound snapshot / content-free deletion receipt | Export carries cutoff, digest, retention and deletion state; deletion fences admission before removal. |

The central cycle is short enough to inspect:

```text
pin profile + policy + Pattern + source revisions
→ resolve local records → build typed candidates → normalize
→ solve hard constraints and soft preferences
→ eligible plan with provenance/uncertainty | no feasible plan under these inputs
→ Magus edits, approves, or rejects
```

Declared allergens, exclusions, equipment, time windows, and operator maxima are hard; variety,
convenience, and cost are soft. The solver returns no feasible answer rather than violating the
least convenient hard rule. Any future movement progression is an operator-selected bounded rule
over confirmed logs and stops when pain or injury is recorded.

## Deterministic reading of food and movement

| Matter | Rule |
| --- | --- |
| Units | Decimal arithmetic and canonical codes preserve original and normalized amounts; reject incompatible dimensions and never turn volume into mass without a sourced ingredient-specific density. Serving, 100 g, and whole-package bases stay distinct. |
| Ingredient closure | Preserve source text, normalize aliases, traverse ingredients/subingredients to a finite depth, and treat embedded free text as hostile data. Every substitution revalidates. |
| Restriction status | `blocked` when an ingredient/subingredient or configured precautionary label matches; `unresolved` for incomplete closure, serving, cross-contact, translation, identity, or conflicting data; `eligible` when no known match exists. `eligible` never renders as “safe.” |
| Movement | Sources may identify equipment, duration, and attributed educational context—not personalized energy expenditure or clinical prescription. |

Allergen taxonomies are jurisdictional and incomplete; locale, taxonomy revision, and personal
rules stay explicit. Preparation, manufacturer change, cross-contact, and source gaps remain
outside the available record.

## Time, provenance, and erasure

Schedules are opt-in, timezone-aware, bounded, pausable, and revocable. Missed reminders expire;
periodic reviews coalesce once per period, never becoming a backlog or a compliance record.
Occurrences use stable idempotency keys and ordinary admission. Profile edits, check-ins,
journals, export, and deletion serialize per profile; only an unapproved draft may be superseded.
Compatible work resumes pinned; incompatible or externally changed work parks for review.

Records avoid a generic `health_record` JSON blob. Immutable profile versions, sources/catalogues,
plan revisions, decisions/edits, check-ins, journals, derived summaries, schedules, exports,
deletion fences, and receipts distinguish `user_entered`, `source_imported`, `model_proposed`,
`deterministically_derived`, and `user_confirmed`. Derivations carry parents and revision; model
prose is never retold as operator truth. Migrations must cover clean install, forward/interrupted
upgrade, restore, parked-work compatibility, export/deletion, and no orphaned schedules,
credentials, artifacts, or rows.

Local storage and inference are defaults. Revocable, purpose-specific consent covers calorie or
weight features, a named Portal/provider, live lookup, reminders, media retention, imports,
sharing/export, or research/training (default: never). Restricted logs redact payloads; raw media,
embeddings, caches, summaries, checkpoints, exports, and backups share the deletion inventory.
Retention is explicit by class.

Deletion is: confirm scope → revoke schedules and Portal consent → admission fence → drain atomic
work → remove rows/artifacts/indexes/caches → verify absence → write a content-free receipt.
Backups disclose expiry and must reapply tombstones before reopening records.

## One narrow household handoff

[Lifestyle Steward](lifestyle-steward.md) may receive only an approved, versioned, expiry- and
purpose-bound `ProvisionConstraintSet`: exclusions, an enabled pattern/target interval, selected
variety or preparation needs, privacy class, and unresolved-source flags. It never receives HFM
journals, measurements, symptoms, diagnoses, medication, clinical records, movement history, or
genetics. Lifestyle owns receipts, inventory, stores, routes, carts, orders, and delivery.

## Smallest proof

With a synthetic adult profile and small reviewed local catalogue, prove a three-day plan;
calorie-free and weight-neutral operation; independent rejection of seeded ingredient/activity
conflicts; unresolved ingredients and units; edit/approve/reject/skip/check-in; documented full
export; deletion of rows, derivations, checkpoints, caches, and artifacts; clean install,
migration, restart, and selected recovery. The slice is single-principal and network-disabled:
no clinical record, external lookup, Portal, wearable, biomarker, audio, or image input.

Return to the [Composition Portfolio](index.md) or [Lifestyle Steward](lifestyle-steward.md).
