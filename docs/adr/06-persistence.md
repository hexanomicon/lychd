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

In durable operation, **Phylactery means PostgreSQL**: the one database cluster assigned to an
application partition. It is not a generic storage facade, a repository of interchangeable
save/retrieve backends, or an abstraction that makes committed application truth backend-agnostic.
Domain repositories isolate SQL mechanics and permit bounded test substitutes; they do not turn a
process-local or in-memory store into a deployed Phylactery. LychD does not use loose
application-managed files as a shadow database around PostgreSQL transactions, constraints, and
migrations.

### Schema admission

Core owns the schema-admission seam across native and extension models. Every admitted model
derives from Core's `UUIDBase`; an extension explicitly calls `register_model(MyModel)` during
initialization; Core aggregates those references before Alembic derives migration order. Runtime
package scanning is not admission, and migration generation or application remains an explicit
release or operator act. Colliding models, table names, or migrations refuse before a schema is
changed.

### Database credentials and runtime authority

The configured `database.user` and administrative password retain the bootstrap/migration
identity, including an existing installation's `lich` owner. They never enter the Vessel.
The separate marked runtime role receives application-database CONNECT, public-schema USAGE,
table SELECT/INSERT/UPDATE/DELETE and sequence USAGE/SELECT; Alembic and SAQ version tables
remain read-only. It has no superuser, role/database creation, replication, BYPASSRLS, role
membership, schema CREATE, or application-object ownership. SQLAlchemy checks each new runtime
connection; SAQ verifies schema instead of initializing or migrating it at worker startup.

The explicit migration gate verifies administrative identity and SCRAM TCP policy, refuses
unmarked or overprivileged existing runtime roles, provisions distinct credentials, applies
Alembic and SAQ migrations as administrator, grants runtime data access, and verifies that actual
runtime credential and queue schema before dependents start. Phoenix has a distinct marked role
for its dedicated database. Only known legacy administrator-owned Phoenix relations and enums
transfer to it; unrelated database owners refuse before mutation. PUBLIC database access is
revoked to keep these runtime roles out of one another's database. No general reassignment,
automatic demotion, database reset, or deletion is part of this gate.

The generated versioned HBA file is mounted read-only and selected explicitly on PostgreSQL
startup, covering existing as well as fresh PGDATA. TCP, including shared-Pod localhost, requires
SCRAM; local trust is confined to the private PostgreSQL-container Unix socket. An old MD5-only
administrator verifier cannot authenticate under this policy: startup of dependent services
fails closed until the operator converts that verifier through the private administrative path.
Preserved data and a known backup precede such operator repair; replacing a Podman secret cannot
change a password already stored by PostgreSQL.

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

### Default topology and scale seam

The default topology is one LychD host with one Phylactery—one PostgreSQL cluster—for its
application partition. Capacity scales up before it scales out: an operator may enlarge or
relocate the physical storage beneath the admitted `postgres/data` mount without changing
application authority. Member disks, filesystems, and volume topology remain host substrate rather
than domain or table-routing facts. The move must preserve [Layout](13-layout.md) identity and use
a PostgreSQL-consistent [capture or restore](07-snapshots.md); this decision promises no automatic
or online storage expansion.

#### Retention before expansion

Scale-up does not imply indefinite retention. Before automated retirement, every persisted record
class must declare its owning lifecycle, holds and terminal eligibility, compaction or archival,
deletion or tombstone and derivative handling, and operational maintenance. Age or disk pressure
alone grants no deletion authority. The [Reaper](31-simulation.md#the-branch-reaper) remains
Shadow-owned branch hygiene; it has no ambient authority to trim Phylactery records.

#### Storage placement inside one cluster

One cluster does not require every PostgreSQL object to occupy the same physical storage tier. A
measured later schema may use native partitioning and tablespaces to place identified relations,
indexes, or partitions across local SSD, NVMe, or HDD mounts while callers continue to query one
logical relation. This is physical placement inside one Phylactery, not an application storage
adapter, independent backup target, or shard. Before admission, [Layout](13-layout.md) and
[Containers](08-containers.md) must bind every durable mount, while [Snapshots](07-snapshots.md)
must capture and restore `PGDATA` and every tablespace at one PostgreSQL-consistent boundary. The
current topology admits only the `postgres/data` mount; this decision promises neither a partition
policy nor tablespace delivery.

#### Separate stores and application partitions

A future Domain may admit a separate, named store only by amending the smallest existing Covenant
that owns the responsibility and introducing its typed port. Such a store is not a Phylactery
backend, inherits no authority over Phylactery relational records or PostgreSQL transactions by
proximity, and must define its authorization, commit or handoff, retention and deletion, backup,
restore, and reconciliation contract. A filesystem path alone is storage geography, never
application authority.

This decision neither delivers nor promises sharding. A later amendment may assign different
whole application partitions to separate PostgreSQL Phylacteries, with routing completed before a
unit of work opens and typed handoffs between partitions. It admits no shared `PGDATA`, routing
implementation, table-level, row-level, or intra-partition sharding, and no cross-Phylactery
transaction. A [Portal](../sepulcher/animator/portal.md) remains a remote capability road, while
[Intercom](26-a2a.md) and [Legion](42-legion.md) carry bounded work or references; none forms a
shared database fabric.

## Wire and work contracts

### Codecs and detached values

The async boundary uses the repository JSON serializer and deserializer. PostgreSQL binary `json`
is the JSON payload; binary `jsonb` prefixes it with the `\x01` format-version byte. The connection
hook registers separate codecs for those wire shapes. Focused hook tests pin their exact framing,
and a disposable PostgreSQL receipt round-trips both a plain `json` expression and JSONB through
the production engine factory. Avoiding an intermediate text conversion is not zero-copy storage.

The loop-confined Run-ledger adapter deep-detaches mutable Run records, nested manifests, and event
metadata on write and every public read. That matches the database adapter's value boundary: a
caller cannot mutate canonical truth through an object it was handed. This parity rule does not
turn the memory profile into durable evidence.

The same value boundary applies to loop-confined consent and Bridge-session stores. Censored
arguments, turns, fragments, and model-history values are detached both when retained and when
projected; mutating a submitted object or a read view cannot rewrite the store's canonical value.

### Atomic claims and checkpoints

Workers select pending work under row locks with `SKIP LOCKED`. Selection, ownership transition,
and all facts that establish the claim commit atomically: no two workers may own one labor unit.
The replaceable JSONB `run_checkpoint` is one unique, cascading row per `run`; it is recovery
state, not the ordered `run`/`step` ledger.

### Deployment authority and edge journals

One application partition has exactly one active Phylactery—one PostgreSQL cluster—and authority
epoch. PostgreSQL is never exposed, shared, synchronously replicated, dual-written, or failed over
across a WAN.
Backups and inactive migration restores are recovery artifacts, not live authorities. Moving
authority requires a quiesced, typed export/import that preserves schema, labels, dedupe and
external-effect identities; it never copies an unrelated home partition by implication.

A platform adapter on another host may own a bounded durable journal for immutable envelope bytes,
digests, external identities, attempt generations, and observed receipts. That journal proves only
transport or effect custody. It cannot admit or settle application truth, own a Run, Context, Ward
decision, Sigil, corpus judgment, or become a Phylactery replica. The authoritative body adopts
events and settlements through typed authenticated operations. Loss or ambiguity remains explicit
and never triggers silent application replay.

### Delivery and recovery identities

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

#### Nexus request identities

Operator Nexus transitions reserve their caller-owned request id in `nexus_swap_request` before
launch. The unique request id and immutable first target are a durable duplicate-effect fence, not
a transition state machine: loss of the process-local ticket causes exact retries to refuse without
relaunch rather than inventing an outcome. Migration `0007` refuses downgrade while any request
identity remains; erase or archive is an explicit operator act, not an incidental rollback.
The downgrade holds an `ACCESS EXCLUSIVE` lock through the refusal check and table removal so a
concurrent old writer cannot create a request identity between inspection and DDL.

#### Consent and delegated-wait evidence

Consent waits persist their exact owner on `Run.consent_id`; newest-row ordering is not ownership.
Settled Consent rows require a decision principal and decision time, while terminal delegated jobs
require result evidence whose job and status match the durable row. Migration `0008` refuses an
upgrade that would have to infer an existing consent-wait owner or accept settled rows without that
evidence. Its downgrade refuses while any Run remains `AWAITING_CONSENT`, so exact ownership cannot
be erased underneath live work.

### Atlas records

The initial Atlas Project is one versioned aggregate scoped to a Sigil. Its validated JSONB document
retains the brief, concern definitions, append-only assessments and decisions, and explicit
references to existing sessions and Runs. Assessments retain their judged text and revisions;
editing current requirements cannot rewrite their historical basis. Reference identities are
related activity, not copied execution evidence. A missing target remains an unavailable
reference rather than becoming a successful result.

Project mutation locks the owner-scoped aggregate and commits its new version together with a
request receipt. A receipt binds the exact request payload to its Project; reuse with different
content refuses. An exact replay returns current retained Project truth without repeating the
mutation. Creation similarly binds a caller-generated Project UUID to its initial payload.
The memory profile implements the same detached-value and replay behavior for bounded tests;
only PostgreSQL supplies restart persistence.

No Project, concern, assessment, decision, or reference deletion is admitted in the initial
surface. Closing a Project retains its records and does not cascade into sessions or Runs.
Migration `0009` adds Atlas without rewriting execution identity. Its downgrade takes an
exclusive table lock and refuses while any Project remains, preserving operator material across
an attempted rollback. Deployment migration remains an explicit operator act.

### Independent Concern retention (Designed)

[Frontend](15-frontend.md#independent-concerns-decomposition-and-addressing-designed) defines
Concerns with identity and authorization independent of optional Project membership. Their
definitions, attributed relation revisions, proposal provenance, and judged bases must survive
independently of a Project's lifecycle. Removing an association cannot erase the Concern or
reinterpret another context's judgment. Shared relations refer to retained identities rather than
copying a Concern's mutable definition into each Project.

Historical assessments retain the exact Concern, context, and relation basis they used. Source
and target locators bind the actual revision or content identity inspected; a mutable URL or an
unchanged Covenant number cannot substitute for that identity. Updates preserve prior bases and
use owner-scoped version checks and retry receipts. Migrating the initial Project aggregates must
preserve existing Concern, assessment, reference, and retry identities and their Project context;
it must not infer new shared identities from similar text. This requires a new explicit schema and
migration contract before delivery; migration `0009` supplies only the initial Project aggregate.

## Privacy and delivery boundary

Persistence is designed to retain the labels and lineage defined by
[Context](21-context.md#privatization-and-the-privacy-cut): defaults may originate in table or
column metadata, policy may refine them by row, subject, or namespace, and derivatives retain
their material sources and transformations. Checkpoints, history, memory, artifacts, and delegated
records retain the applicable label or omit sensitive content. Missing ORM annotation never makes
raw data public.

This is storage and information-flow support, not declassification. Context owns the Privacy Cut;
the trusted [Security Egress Gate](09-security.md#portal-privatization-and-egress) enforces the
resulting decision immediately before transmission. Dispatcher may provisionally refuse or bind a
capability, but it cannot declassify bytes. Exact label schema, row policy, and full production
persistence remain subject to the delivery boundary in
[State of Work](../state-of-the-work.md#phylactery-first-light).

### Reversible maps and the Privacy Vault

A reversible Privacy Cut persists no pseudonym map in Run, Graph checkpoint, receipt, event, or
general Phylactery row. Those records may hold one opaque `PseudonymMapLease@1` reference.

Mapping bytes require the Context-owned lease registry and rehydration port backed by a deployment-local
Privacy Vault with exact Cut/Run/attempt ownership, idempotent claim CAS, key epoch, TTL, access
audit, and one per-lease data-encryption key that never enters ordinary backup.

Expiry, revocation, consumption, or abandoned-work cleanup destroys that key; a restore drill proves any retained
ciphertext undecryptable and never claims physical erasure from opaque provider media. Loss or
expiry means rehydration is unavailable and never permits raw-history reconstruction.

The accepted Vault profile also contains transient plaintext: its map pages are unswappable or the
host swap is disabled, core/crash dumps and debugger attachment are disabled, buffers are bounded
and zeroized after use, and map material is excluded from traces and allocator diagnostics. A
deployment unable to verify those properties cannot enable reversible Cuts.

## Consequences

One logical state transition can share a PostgreSQL transaction, while write-heavy queue and trace
tables need workload-specific retention and autovacuum policy. The delivery outbox is transactional
with Run truth but not with the external SAQ transaction; its relay and exact keys close that gap.
Step/event publication still lacks a transactional outbox, and memory profiles do not have complete
behavioral parity with PostgreSQL repositories. The offline lifecycle receipt and its limits are
recorded in the [current evidence envelope](../state-of-the-work.md#current-evidence-envelope);
real host/model/browser operation remains unproved.
