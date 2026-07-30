---
title: 6. Persistence
icon: material/database
---

# :material-database: 6. Persistence

!!! abstract "Context"
    The Phylactery is LychD's jurisdiction for committed truth. It gives one body a transactional
    home for relational records, JSON documents, vectors, execution history, and recoverable graph
    state; it does not decide what a Domain record means.

## Decision

PostgreSQL is the single-node persistence backend. LychD reaches it through async SQLAlchemy and
`asyncpg`. The Phylactery alone owns engine construction, codecs, sessions and transaction
boundaries, migration order, and schema admission. Domains own record meaning and lifecycle;
neither they nor extension packages gain ambient migration authority.

Core owns the planned federation seam. Every admitted model derives from Core's `UUIDBase`; an
extension explicitly calls `register_model(MyModel)` during initialization; Core aggregates those
references before Alembic derives migration order. Runtime package scanning is not admission, and
migration generation or application remains an explicit release or operator act. Colliding models,
table names, or migrations refuse before a schema is changed.

The target chambers are deliberately logical rather than a claim of present deployment:

| Chamber | Responsibility |
| --- | --- |
| `public` | relational state, configuration, and extension registries |
| `vectors` | attributed vector material, including its trust status |
| `traces` | execution and observability traces |
| `queue` | durable work distribution |
| `verbatim` | JSONB exact values that must be consulted before semantic retrieval |

`vectors` status can distinguish, for example, speculative material from governed precedent;
consecration records authority, not universal factual truth.

## Wire and work contracts

The async boundary uses the repository JSON serializer and deserializer. PostgreSQL binary `json`
is the JSON payload; binary `jsonb` prefixes it with the `\x01` format-version byte. The current
hook applies jsonb framing to both types. Its mapped paths are compatible because the present
schema maps JSONB, but PostgreSQL `json` columns or expressions are not supported by that hook
until codecs are split and live round trips prove both. Avoiding an intermediate text conversion
is not zero-copy storage.

Workers select pending work under row locks with `SKIP LOCKED`. Selection, ownership transition,
and all facts that establish the claim commit atomically: no two workers may own one labor unit.
The replaceable JSONB `run_checkpoint` is one unique, cascading row per `run`; it is recovery
state, not the ordered `run`/`step` ledger.

## Privacy and delivery boundary

Persistence is designed to retain the labels and lineage defined by
[Context](21-context.md#privatization-and-the-privacy-cut): defaults may originate in table or
column metadata, policy may refine them by row, subject, or namespace, and derivatives retain
their material sources and transformations. Checkpoints, history, memory, artifacts, and delegated
records retain the applicable label or omit sensitive content. Missing ORM annotation never makes
raw data public.

This is storage and information-flow support, not declassification. Context owns the Privacy Cut;
the [Dispatcher](22-dispatcher.md) enforces the resulting egress decision. Exact label schema,
row policy, and full production persistence remain subject to the delivery boundary in
[State of Work](../state-of-the-work.md#phylactery-first-light).

## Consequences

One logical state transition can share a PostgreSQL transaction, while write-heavy queue and trace
tables need workload-specific retention and autovacuum policy. The first-light migration and
ledger shapes are evidence of a partial boundary, not evidence of a transactional outbox, complete
PostgreSQL adapter parity, or a production lifecycle receipt.
