---
title: Phylactery
icon: fontawesome/solid/flask
---

# :fontawesome-solid-flask: Phylactery

> _“The Vessel passes. The Phylactery keeps only what was committed.”_

The Phylactery is LychD's durable-data jurisdiction. It owns committed run and continuity records
that must survive a [Vessel](../vessel/index.md) process boundary.

The first-light implementation uses **PostgreSQL** inside the [Crypt](../crypt.md). The Phylactery
owns engine construction, codecs, transactions, migrations, and schema admission; each domain owns
the meaning and lifecycle of its records.

[First-light persistence](../../state-of-the-work.md#phylactery-first-light) is **Partial**:
repository shapes and memory-profile behavior exist, but no production-factory PostgreSQL
lifecycle, full adapter parity, or transactional outbox is proved.

## The Anatomy of Memory

The current Phylactery uses the configured database's default schema and search path:

1. **`public` (The State):** Migration `0001_phylactery_first_light` raises `session`, `run`,
   `run_checkpoint`, `step`, `consent`, `karma`, `soulstone_record`, and
   `codex_preauthorization`. `run` is authoritative lifecycle truth; ordered `step` rows are a
   best-effort evidence projection.
2. **`run_checkpoint`:** one replaceable JSONB document per Run, holding the complete validated
   Graph snapshot history. It is distinct from the Run/Step ledger, contains no runtime
   dependencies or event stream, and cascades with its Run.
3. **SAQ's `saq_*` tables:** durable broker records created on the default search path through a
   separate autocommit pool. Run-row commit and queue publication are not one transaction.
4. **Planned chambers:** `vectors` for governed Karma, `traces` for durable cognitive traces, and
   isolated `queue` storage and roles. Their names reserve architecture, not delivery.

!!! abstract "The Anchor"
    Continuity begins at a declared commit boundary: SAQ jobs, Run and Step rows, consent records,
    and one run-owned checkpoint. Live subscribers, leases, dependencies, and uncommitted frames
    do not survive merely because a related row exists.

Terminal Run status precedes context release and best-effort checkpoint cleanup. On cleanup
failure, status remains authoritative and [Reanimation](./reanimation.md) judges the retained
checkpoint; its presence never authorizes arbitrary replay.

!!! info "The Accumulator of Karma"
    A narrow Karma row exists today. The larger path from consecrated consequence to curated,
    attributable memory and eligible formation data belongs to [HitL
    (25)](../../adr/25-hitl.md), [Memory (27)](../../adr/27-memory.md), and the
    [Karma record in State](../../state-of-the-work.md#karma-semantic-memory).

[ADR 06](../../adr/06-persistence.md) owns persistence and checkpoint storage. [ADR
24](../../adr/24-graph.md) owns checkpoint semantics and terminal order; [Ghouls](../vessel/ghouls.md)
own the worker lifecycle that writes them. Next, enter [Reanimation](./reanimation.md) to follow
committed continuity across process death.
