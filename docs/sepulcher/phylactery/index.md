---
title: Phylactery
icon: fontawesome/solid/flask
---

# :fontawesome-solid-flask: Phylactery

> _“The Vessel passes. The Phylactery keeps only what was committed.”_

The durable Phylactery is the PostgreSQL database cluster assigned to one application partition.
It owns committed run and continuity records that must survive a
[Vessel](../vessel/index.md) process boundary. It is not a generic storage facade or an
interchangeable save/retrieve backend.

The cluster's `PGDATA` lives inside the [Crypt](../crypt.md), while PostgreSQL runs in its dedicated
unit. The Phylactery owns engine construction, codecs, transactions, migrations, and schema
admission; each domain owns the meaning and lifecycle of its records. Process-local and in-memory
persistence profiles are bounded test or execution substitutes, never deployed Phylacteries.

The default topology scales this one cluster up on one host. Its storage may be enlarged or moved
beneath the exact admitted `postgres/data` mount without changing application authority. Loose
application-managed files never form a shadow database. A future named Domain store may own a
separate custody or projection contract through its own port; it is neither a Phylactery nor an
interchangeable Phylactery backend. Current law selects no scale-out topology; any such design
requires a further [Persistence](../../adr/06-persistence.md#default-topology-and-scale-seam)
amendment and evidence.

Growth first meets explicit lifecycle policy: age or disk pressure alone never permits deletion,
and Shadow's Reaper is not a database collector. PostgreSQL partitioning and tablespaces may later
place measured hot or cold relations, indexes, or partitions on different local storage tiers while
remaining one indivisible Phylactery. The application still queries PostgreSQL rather than choosing
a disk. LychD currently admits only the `postgres/data` mount; additional tablespace mounts require
Layout, container, and whole-cluster capture/restore support before use.

[First-light persistence](../../state-of-the-work.md#phylactery-first-light) is **Partial**:
repository shapes, memory-profile behavior, a transactional Run-delivery outbox, and a disposable
two-boot PostgreSQL application-factory lifecycle are proved. Full memory-profile/PostgreSQL
repository parity, a transactional Step-event outbox, general retention or compaction, physical
tiering, and real host/model/browser receipts are not.

## The Anatomy of Memory

The current Phylactery uses its PostgreSQL database's default schema and search path:

1. **`public` (The State):** Migration `0001_phylactery_first_light` raises `session`, `run`,
   `run_checkpoint`, `step`, `consent`, `karma`, `soulstone_record`, and
   `codex_preauthorization`; migration `0004_run_delivery_outbox` adds the exact publication intent
   for each Run hop, migrations `0005` and `0006` refine preauthorization order and Rune presence,
   and migration `0007_nexus_swap_admission` adds the operator transition duplicate-effect fence.
   `run` is authoritative lifecycle truth; ordered `step` rows are a best-effort evidence
   projection.
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
