---
title: Phylactery
icon: fontawesome/solid/flask
---

# :fontawesome-solid-flask: Phylactery

> _“The Vessel passes. The Phylactery keeps only what was committed.”_

The **Phylactery** is the PostgreSQL database cluster assigned to one application partition.
It keeps the committed records from which another [Vessel](../vessel/index.md) may recover Run
and continuity truth. Each domain owns what its records mean and how their lifecycle ends;
the Phylactery owns engines, codecs, transactions, migrations, and schema admission.

## What the inscription keeps

| Record surface | What crosses the process boundary |
| --- | --- |
| Run and delivery ledger | Canonical lifecycle and the exact publication intent for each fresh or resumed worker hop. |
| `run_checkpoint` | One replaceable JSONB document per Run containing validated Graph snapshot history; it cascades with its Run. |
| Consent and delegated-owner records | The exact authority whose settled result may permit a parked Run to return. |
| Ordered `step` rows | Best-effort structural evidence; they do not replace Run truth. |
| `session`, `karma`, `soulstone_record`, and `codex_preauthorization` | Domain-owned records admitted by the application migrations; a persisted row establishes only its own contract. |
| SAQ's `saq_*` tables | Durable broker records through a separate autocommit pool; queue publication and Run admission are not one transaction. |

The application currently uses PostgreSQL's default schema and search path. Migration history and
exact table admission belong to [Persistence](../../adr/06-persistence.md). The planned `vectors`,
`traces`, and isolated `queue` chambers reserve governed memory, cognitive evidence, and broker
separation; their names alone establish no delivered service.

A checkpoint holds declared Graph state, not a process image, runtime dependencies, or an event
stream. Subscribers, leases, live provider handles, and uncommitted frames die with their process.
Terminal Run status commits before context release and best-effort checkpoint cleanup. If cleanup
fails, the retained checkpoint carries no permission to replay; [Reanimation](reanimation.md)
judges it against canonical truth.

## One cluster, one custody boundary

`PGDATA` lives at the exact admitted `postgres/data` mount inside the [Crypt](../crypt.md), and
PostgreSQL runs in its dedicated unit. The default design enlarges this one cluster on one host.
Its storage may move beneath that mount without moving application authority. In-memory and
process-local profiles remain bounded test or execution substitutes; loose files cannot form a
shadow database.

A future named Domain store needs its own custody or projection contract. It does not become an
interchangeable Phylactery backend. Current law selects no scale-out topology.

Growth first requires lifecycle policy. Age or disk pressure permits no deletion, and Shadow's
Reaper collects no database records. Measured partitioning or tablespaces could later place hot
and cold relations on different local tiers while PostgreSQL remains the single query boundary.
Additional mounts require Layout, container, and whole-cluster capture/restore support before use;
[Persistence's scale seam](../../adr/06-persistence.md#default-topology-and-scale-seam) owns that decision.

## Read the evidence before claiming continuity

[First-light persistence](../../state-of-the-work.md#phylactery-first-light) is Partial. The
proved PostgreSQL lifecycle uses offline collaborators; it does not establish a
Consent-plus-Checkpoint restart or a real host, model, or browser journey. Use State's maintained
receipt before relying on a particular return path.

General retention, compaction, and physical tiering remain incomplete. The narrow Karma row does
not deliver the larger admission, curation, retrieval, and formation path owned by
[Memory](../../adr/27-memory.md) and
[State](../../state-of-the-work.md#karma-semantic-memory).

To cross death deliberately, continue to [Reanimation](reanimation.md). To follow the worker that
writes these records, return to [Ghouls](../vessel/ghouls.md).
