---
title: Phylactery
icon: fontawesome/solid/flask
---

# :fontawesome-solid-flask: Phylactery

> _“The Vessel passes. The Phylactery keeps only what was committed.”_

The Phylactery is LychD's durable-data jurisdiction. It owns committed run and continuity records
that must survive a Vessel process boundary. It does not turn every trace into memory, and
durability alone does not make a record true, formative, or part of an identity.

The first-light implementation uses **PostgreSQL** inside the [Crypt](../crypt.md). The repository
includes `pgvector`, but semantic retrieval, curated Karma, and the full
[Soulforge](../extensions/soulforge.md) formation path remain separate delivery boundaries.

## The Anatomy of Memory

The first-light Phylactery uses the configured database's default schema/search path. Its mature
anatomy reserves sacred chambers, but only the first item and SAQ's default `saq_*` tables exist
today:

1. **`public` (The State):** The current reality. Migration `0001_phylactery_first_light` raises `session`, `run`, `run_checkpoint`, `step`, `consent`, `karma`, `soulstone_record`, and `codex_preauthorization`. The `run`/`step` tables are the run truth written by the **[RunLedger](../vessel/ghouls.md)**; `run_checkpoint` owns one complete durable graph history per run.
2. **`vectors` (The Karma, planned):** The high-dimensional embedding space where verified outcomes may be stored.
3. **`traces` (The Mind's Eye, planned):** The dedicated chamber for durable cognitive traces.
4. **`queue` (The Ghouls, planned isolation):** The future queue schema/role boundary. V1 SAQ
   creates its `saq_*` tables on the default search path and run-row/enqueue is not one transaction.

!!! abstract "The Anchor"
    The primary and most sacred function of the Phylactery is to house the **continuity pattern**.

    A model-backed **[Soulstone](../../sepulcher/animator/soulstone.md)** is a processor with no memory of its own: kill the container and nothing of the Lich is lost, because nothing of the Lich lived there. Continuity lives here.

    The Phylactery survives reboots, crashes, and migrations at each store's declared committed
    boundary. In the current foundation that means SAQ jobs, Postgres run/step rows, and one
    run-owned JSONB graph checkpoint document. Memory/persona/trace stores and a transactional
    graph/queue outbox remain later work. Volatile frames may be reconstructed or
    abandoned according to Graph, Worker, and policy law.

!!! info "The Accumulator of Karma"
    A narrow Karma row exists today. The larger path—consecrated consequence becoming curated,
    attributable memory and later eligible formation data—is Designed. [HitL
    (25)](../../adr/25-hitl.md) owns authorization, [Memory
    (27)](../../adr/27-memory.md) owns retention and retrieval, and
    [State](../../state-of-the-work.md#karma-semantic-memory) owns the delivery boundary.
