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

Each Run hop also owns one `run_delivery` row. Run admission or wait re-admission and its exact
delivery identity commit together; broker publication happens afterward under an idempotent key.
`HELD`, `PENDING`, `PUBLISHED`, `CLAIMED`, and `SETTLED` distinguish admission custody from broker
acknowledgement and execution ownership. One partial unique index permits only one unsettled
delivery per Run, while `(run_id, enqueue_seq)` permanently fences old workers. A process-owned
relay repairs publication without treating the broker as canonical Run truth.

Migration `0004` refuses both introduction and removal of that delivery authority while any Run is
nonterminal. PostgreSQL transactional DDL leaves the schema revision and outbox intact on refusal;
an operator must settle or explicitly fail the work before crossing the boundary. This is a narrow
delivery-schema compatibility fence, not a general application rollback mechanism.

Operator Nexus transitions reserve their caller-owned request id in `nexus_swap_request` before
launch. The unique request id and immutable first target are a durable duplicate-effect fence, not
a transition state machine: loss of the process-local ticket causes exact retries to refuse without
relaunch rather than inventing an outcome. Migration `0007` refuses downgrade while any request
identity remains; erase or archive is an explicit operator act, not an incidental rollback.
The downgrade holds an `ACCESS EXCLUSIVE` lock through the refusal check and table removal so a
concurrent old writer cannot create a request identity between inspection and DDL.

Consent waits persist their exact owner on `Run.consent_id`; newest-row ordering is not ownership.
Settled Consent rows require a decision principal and decision time, while terminal delegated jobs
require result evidence whose job and status match the durable row. Migration `0008` refuses an
upgrade that would have to infer an existing consent-wait owner or accept settled rows without that
evidence. Its downgrade refuses while any Run remains `AWAITING_CONSENT`, so exact ownership cannot
be erased underneath live work.

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
tables need workload-specific retention and autovacuum policy. The delivery outbox is transactional
with Run truth but not with the external SAQ transaction; its relay and exact keys close that gap.
This is not a transactional Step/event outbox, complete PostgreSQL adapter parity, or a production
deployment receipt. A disposable two-boot application-factory lifecycle proves the repository
composition with an offline model and HTTP test client; real host/model/browser operation remains
outside that evidence.
